#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "pico/time.h"
#include "hardware/spi.h"
#include "hardware/pio.h"
#include "hardware/gpio.h"
#include "hardware/dma.h"
#include "i2s.pio.h"
#include "mp3dec.h" // Helix MP3 Decoder library
#include "hardware/clocks.h"
#include <string.h> // memmove

// --- TEMPORARY DIAGNOSTIC INSTRUMENTATION ---
// Counters updated by core1 (decoder), read/printed by core0. Remove once the
// silent-playback / no-back-pressure issue is root-caused.
volatile uint32_t diag_mp3_frames_decoded = 0;
volatile uint32_t diag_mp3_decode_errors = 0;
volatile uint32_t diag_mp3_no_sync_discards = 0;
volatile uint32_t diag_mp3_underflows = 0;
volatile uint32_t diag_spi_chunks_received = 0;
volatile uint32_t diag_spi_bytes_received = 0;
// RX FIFO overrun events (PL022 SSPRIS.RORRIS). Sets ONLY when a byte is
// clocked in while the 8-deep RX FIFO is already full -- i.e. hard proof the
// peripheral is actually receiving the whole stream and our drain is the thing
// falling behind. If bytes==cs_asserts (1/window) AND ovr stays 0, the opposite
// is true: the peripheral itself shifts in only one byte per window.
volatile uint32_t diag_rx_overruns = 0;
// CS edge count via GPIO IRQ -- sees the raw pad even though CS is muxed to
// SPI, so it proves whether the ESP32 is asserting chip-select at all.
volatile uint32_t diag_cs_asserts = 0;
// True while CS is asserted (low). Drives the RX drain so it runs exactly for
// the duration of each chunk and exits when CS deasserts (never hangs).
volatile bool cs_asserted = false;
// Duration (us) of the most recent CS-low window. Decisive diagnostic: a full
// 512-byte chunk should hold CS low for ~1ms (4MHz) to ~4ms (1MHz); a value of
// only a few us means the ESP32 is clocking ~1 byte per assertion.
volatile uint64_t diag_cs_low_start_us = 0;
volatile uint64_t diag_last_cs_low_dur_us = 0;


#define SPI_PORT    spi0
// RP2040 SPI0 pin functions are fixed: GP16=RX, GP17=CSn, GP18=SCK, GP19=TX.
// In slave mode the master's MOSI (data IN) must land on RX (GP16), and the
// slave's TX (GP19) drives the master's MISO. Wiring the master's MOSI to the
// TX pin makes two outputs fight the line (~1.8V) and receives nothing.
#define PIN_MOSI    16   // master MOSI -> slave SPI0 RX; incoming MP3 data
#define PIN_CS      17   // SPI0 CSn
#define PIN_SCK     18   // SPI0 SCK
#define PIN_MISO    19   // slave SPI0 TX -> master MISO; outgoing (unused)

#define PIN_I2S_BCLK 2
#define PIN_I2S_LRC  3
#define PIN_I2S_DIN  4

// Flow-control / control lines to/from the ESP32 master:
//   READY (output): high tells the ESP32 the ring buffer has room for a chunk.
//   STOP  (input) : high tells the Pico to drop all buffered audio and go silent.
#define PIN_READY   20
#define PIN_STOP    21

// Initialize I2S PIO state machine
static inline void i2s_output_program_init(PIO pio, uint sm, uint offset, 
                                           uint pin_din, uint pin_bclk, float clk_div) {
    pio_sm_config c = i2s_output_program_get_default_config(offset);
    
    // Set data output pin
    sm_config_set_out_pins(&c, pin_din, 1);
    
    // Set side-set pins (BCLK and LRC)
    sm_config_set_sideset_pins(&c, pin_bclk);
    
    // Set the clock divider
    sm_config_set_clkdiv(&c, clk_div);
    
    // Set shift configuration for I2S
    sm_config_set_out_shift(&c, false, true, 32);
    
    // Mux the pins to PIO
    pio_gpio_init(pio, pin_din);
    pio_gpio_init(pio, pin_bclk);
    pio_gpio_init(pio, PIN_I2S_LRC);

    // Load configuration and start state machine
    pio_sm_init(pio, sm, offset, &c);

    // CRITICAL: enable the PIO outputs for BCLK/LRC/DIN. gpio_set_dir() does
    // NOTHING once a pin is muxed to PIO -- the pad output-enable comes from the
    // PIO block's pindirs, not SIO. Without this the state machine runs and
    // drains its FIFO (audio "decodes") but the pins stay high-impedance at 0V
    // and the DAC is silent. This was why decoded MP3 produced no sound.
    uint32_t io_mask = (1u << pin_bclk) | (1u << PIN_I2S_LRC) | (1u << pin_din);
    pio_sm_set_pindirs_with_mask(pio, sm, io_mask, io_mask);

    pio_sm_set_enabled(pio, sm, true);
}

#define BUFFER_SIZE 16384 // 16KB compressed data ring buffer (core0 -> core1)
#define MP3BUF_SIZE  4096  // linear working buffer the decoder reads from
uint8_t ring_buffer[BUFFER_SIZE];
volatile uint32_t write_ptr = 0; // owned by core0 (SPI ingest)
volatile uint32_t read_ptr = 0;  // owned by core1 (decoder)

// Core 1: Dedicated Audio Decoding & I2S Output Loop
void core1_entry() {
    HMP3Decoder hMP3Decoder = MP3InitDecoder();

    // PCM output for ONE frame. MPEG1 Layer3 is 2 granules x 1152/2 samples
    // per channel, so a full stereo frame is MAX_NGRAN*MAX_NCHAN*MAX_NSAMP
    // (=2304) shorts. The previous MAX_NCHAN*MAX_NSAMP was half that and
    // overflowed on stereo files. static => kept off the small core1 stack.
    static short sample_buffer[MAX_NGRAN * MAX_NCHAN * MAX_NSAMP];

    // Linear buffer the decoder works on. We copy out of the circular ring
    // buffer into this contiguous buffer so a frame can never straddle the
    // ring's wrap point (which would make the decoder read out of bounds).
    static uint8_t mp3buf[MP3BUF_SIZE];
    int mp3len = 0; // valid bytes currently in mp3buf

    // Initialize PIO for I2S
    PIO pio = pio0;
    uint sm = pio_claim_unused_sm(pio, true);
    uint offset = pio_add_program(pio, &i2s_output_program);

    // Configure PIO clock rate for 44.1kHz 16-bit Stereo audio
    float div = (float)clock_get_hz(clk_sys) / (44100 * 32 * 2);
    i2s_output_program_init(pio, sm, offset, PIN_I2S_DIN, PIN_I2S_BCLK, div);

    // DMA double-buffer for I2S output. Pushing samples with pio_sm_put_blocking
    // blocked core1 for a whole frame (~26ms), so decode (~23ms) and playback ran
    // sequentially => ~50ms/frame, 2x too slow, with starvation gaps. Instead one
    // DMA channel streams a finished buffer to the PIO (paced by its TX DREQ)
    // while core1 decodes the NEXT frame into the other buffer. Since decode
    // (~23ms) < playback (~26ms), the output never starves and speed is correct.
    static uint32_t i2s_buf[2][MAX_NGRAN * MAX_NSAMP]; // max stereo words/frame
    int cur = 0;
    int dma_chan = dma_claim_unused_channel(true);
    dma_channel_config dcfg = dma_channel_get_default_config(dma_chan);
    channel_config_set_transfer_data_size(&dcfg, DMA_SIZE_32);
    channel_config_set_read_increment(&dcfg, true);
    channel_config_set_write_increment(&dcfg, false);
    channel_config_set_dreq(&dcfg, pio_get_dreq(pio, sm, true)); // PIO TX DREQ
    dma_channel_configure(dma_chan, &dcfg, &pio->txf[sm], NULL, 0, false);

    while (1) {
        // STOP requested: drop everything queued and go silent.
        if (gpio_get(PIN_STOP)) {
            read_ptr = write_ptr; // discard buffered compressed audio
            mp3len = 0;           // discard any partial frame
            continue;
        }

        // Refill mp3buf contiguously from the ring buffer.
        while (mp3len < MP3BUF_SIZE) {
            uint32_t avail = (write_ptr - read_ptr + BUFFER_SIZE) % BUFFER_SIZE;
            if (avail == 0) break;
            uint32_t space = MP3BUF_SIZE - mp3len;
            uint32_t n = avail < space ? avail : space;
            for (uint32_t i = 0; i < n; i++) {
                mp3buf[mp3len++] = ring_buffer[read_ptr];
                read_ptr = (read_ptr + 1) % BUFFER_SIZE;
            }
        }

        // Need at least a frame's worth before trying to decode.
        if (mp3len < 1024) continue;

        // Locate next valid MP3 frame header.
        int off = MP3FindSyncWord(mp3buf, mp3len);
        if (off < 0) { diag_mp3_no_sync_discards++; mp3len = 0; continue; } // no sync in buffer, discard
        if (off > 0) { memmove(mp3buf, mp3buf + off, mp3len - off); mp3len -= off; }

        unsigned char *inp = mp3buf;
        int bytes_left = mp3len;
        uint64_t _t_dec0 = time_us_64();
        int err = MP3Decode(hMP3Decoder, &inp, &bytes_left, sample_buffer, 0);
        uint64_t _t_dec1 = time_us_64();

        if (err == ERR_MP3_NONE) {
            diag_mp3_frames_decoded++;
            int consumed = mp3len - bytes_left;
            memmove(mp3buf, mp3buf + consumed, bytes_left);
            mp3len = bytes_left;

            MP3FrameInfo fi;
            MP3GetLastFrameInfo(hMP3Decoder, &fi);

            // ONE-TIME diagnostic: what does the decoder actually report? The
            // I2S clock is hardwired to 44.1kHz -- if samprate differs, playback
            // speed is wrong (2x slow = I2S running at half the file's rate, or
            // twice as many samples emitted as the audio contains).
            static int fi_printed = 0;
            if (!fi_printed) {
                fi_printed = 1;
                printf("FRAMEINFO: samprate=%d nChans=%d outputSamps=%d bitrate=%d bps=%d ver=%d layer=%d\n",
                       fi.samprate, fi.nChans, fi.outputSamps, fi.bitrate,
                       fi.bitsPerSample, fi.version, fi.layer);
            }

            // Pack into 32-bit FIFO words: left in the high 16 bits, right in
            // the low 16 (PIO shifts MSB first, left channel first). Mono is
            // duplicated to both channels.
            int n = fi.outputSamps;
            int wcount = 0;
            uint32_t *ob = i2s_buf[cur];
            if (fi.nChans == 2) {
                for (int i = 0; i + 1 < n; i += 2) {
                    ob[wcount++] = ((uint32_t)(uint16_t)sample_buffer[i] << 16)
                                 | (uint16_t)sample_buffer[i + 1];
                }
            } else {
                for (int i = 0; i < n; i++) {
                    ob[wcount++] = ((uint32_t)(uint16_t)sample_buffer[i] << 16)
                                 | (uint16_t)sample_buffer[i];
                }
            }
            // Wait for the previous buffer to finish streaming to the PIO, then
            // start this one via DMA. Core1 spent the decode time overlapping the
            // previous buffer's playback, so this wait is short (~3ms) and the
            // I2S output is continuous -- correct speed, no starvation gaps.
            dma_channel_wait_for_finish_blocking(dma_chan);
            dma_channel_set_read_addr(dma_chan, ob, false);
            dma_channel_set_trans_count(dma_chan, wcount, true); // start now
            cur ^= 1;

            // DIAGNOSTIC: decode vs push time. pio_sm_put_blocking is paced by
            // how fast the I2S actually drains, so avg push_us reveals the true
            // output rate: ~26000us/frame => 44.1kHz (correct), ~52000us => the
            // PIO is running at half rate (clock bug). decode_us over ~26000
            // means core1 can't decode in real time (the other possible cause).
            uint64_t _t_push1 = time_us_64();
            static uint64_t _acc_dec = 0, _acc_push = 0; static int _acc_n = 0;
            _acc_dec += (_t_dec1 - _t_dec0);
            _acc_push += (_t_push1 - _t_dec1);
            if (++_acc_n >= 100) {
                printf("TIMING/100f avg: decode=%luus push=%luus (real-time budget=26100us/frame)\n",
                       (unsigned long)(_acc_dec / _acc_n), (unsigned long)(_acc_push / _acc_n));
                _acc_dec = 0; _acc_push = 0; _acc_n = 0;
            }
        } else if (err == ERR_MP3_INDATA_UNDERFLOW || err == ERR_MP3_MAINDATA_UNDERFLOW) {
            diag_mp3_underflows++;
            // Frame not fully present yet; keep bytes and refill next loop.
            // If the buffer is full and still underflowing, the data is junk:
            // drop a byte to resync and avoid a deadlock.
            if (mp3len >= MP3BUF_SIZE) { memmove(mp3buf, mp3buf + 1, --mp3len); }
        } else {
            diag_mp3_decode_errors++;
            // Decode error: skip one byte past this sync and try again.
            memmove(mp3buf, mp3buf + 1, mp3len - 1);
            mp3len -= 1;
        }
    }
}

// Tracks CS assertion. Works even though CS is muxed to the SPI function,
// because the pad's edge-detect is an independent block. The falling edge
// (CS low = selected) starts a chunk; the rising edge ends it.
static void cs_irq_callback(uint gpio, uint32_t events) {
    if (gpio != PIN_CS) return;
    if (events & GPIO_IRQ_EDGE_FALL) {
        cs_asserted = true; diag_cs_asserts++;
        diag_cs_low_start_us = time_us_64();
    }
    if (events & GPIO_IRQ_EDGE_RISE) {
        cs_asserted = false;
        diag_last_cs_low_dur_us = time_us_64() - diag_cs_low_start_us;
    }
}

// Core 0: High-Speed SPI Slave Data Ingest Loop
int main() {
    // Drive READY low first, before anything else (including USB/stdio
    // bring-up), so the ESP32 never has a chance to read a floating/unset
    // pin as "ready" before the SPI slave is actually listening.
    gpio_init(PIN_READY); gpio_set_dir(PIN_READY, GPIO_OUT); gpio_put(PIN_READY, 0);
    gpio_init(PIN_STOP);  gpio_set_dir(PIN_STOP, GPIO_IN);   gpio_pull_down(PIN_STOP);

    stdio_init_all();

    // Give USB-CDC time to enumerate before the boot banner, otherwise the
    // first prints are emitted into a not-yet-connected port and lost. READY
    // is held low throughout, so the ESP32 waits and no data is missed. The
    // repeated banner means a freshly-attached serial monitor catches one.
    for (int i = 0; i < 6; i++) {
        printf("=== i2s pico boot [b15-clean] === (waiting for SPI; MOSI=GP%d CS=GP%d SCK=GP%d)\n",
               PIN_MOSI, PIN_CS, PIN_SCK);
        sleep_ms(500);
    }

    // Setup SPI Slave to accept data from the ESP32. This MUST mirror the
    // proven spi_test.cpp init exactly. spi_set_slave() flips CR1.MS while the
    // peripheral is enabled, which the PL022 does not properly support; the
    // explicit spi_set_format() below rewrites CR0 and re-latches the config
    // after the mode switch. Without it the slave RX path comes up
    // half-configured and latches only the first byte of each CS window
    // (bytes == cs_asserts). spi_test has this call; main.cpp was missing it.
    // Mode 3 (CPOL=1, CPHA=1). The slave-side baud is NOT irrelevant: empirically
    // a 1 MHz slave setting against a 100 kHz master corrupts reception (nosync
    // spikes), while matching the master's 100 kHz decodes cleanly (nosync=0).
    // Keep this equal to the ESP32 master's baud.
    spi_init(SPI_PORT, 100000);
    spi_set_slave(SPI_PORT, true);
    spi_set_format(SPI_PORT, 8, SPI_CPOL_1, SPI_CPHA_1, SPI_MSB_FIRST);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI);

    // RP2040 pads reset with an internal pull-down enabled; gpio_set_function()
    // does not touch pulls, so it stays active even once the pin is claimed by
    // the SPI peripheral. Disable it explicitly on all four SPI pins so it
    // doesn't load down the ESP32's drivers.
    gpio_disable_pulls(PIN_MISO);
    gpio_disable_pulls(PIN_SCK);
    gpio_disable_pulls(PIN_MOSI);
    gpio_disable_pulls(PIN_CS);

    // CS edge IRQ (see cs_irq_callback): tracks the assert/deassert window that
    // frames each chunk, and counts asserts for the STATUS diagnostic.
    gpio_set_irq_enabled_with_callback(PIN_CS, GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE,
                                        true, &cs_irq_callback);

    // Launch Core 1 DSP Engine
    multicore_launch_core1(core1_entry);

    uint8_t spi_rx_packet[512];
    uint64_t diag_last_print_us = time_us_64();

    // Core 0 runs ONE continuous drain -- it does NOT frame on CS. The PL022
    // slave only shifts while CS is asserted, so when the ESP32 holds CS low for
    // the whole stream this loop pulls every clocked byte into the ring buffer,
    // feeds dummy TX to keep the shared shift register alive, and drives the
    // READY back-pressure line the entire time. Per-chunk CS windows were
    // fatally fragile: each ~4ms window is narrow enough that any ms-scale stall
    // (printf, MicroPython GC, USB-CDC flow control) on either side lands inside
    // it and corrupts or drops the chunk. A single continuous window turns those
    // stalls into harmless idle-clock gaps on byte boundaries that the ring
    // simply absorbs, and the MP3 decoder resyncs on the next frame header.
    const int32_t fifo_depth = 8;
    int32_t tx_lead = 0;
    while (1) {
        // Periodic STATUS printf REMOVED (was tag b14). A blocking printf on core0
        // stalls this drain long enough to overrun the 8-deep RX FIFO, corrupting
        // ~1 MP3 frame each time -- those were the ovr/err counts and the audible
        // pops. For clean audio, core0's hot loop must not block. (The absence of
        // STATUS spam in the serial log confirms this b15 build is running.)
        (void)diag_last_print_us;

        // READY back-pressure, updated continuously from ring fullness.
        uint32_t used = (write_ptr - read_ptr + BUFFER_SIZE) % BUFFER_SIZE;
        uint32_t freeb = BUFFER_SIZE - 1 - used;
        gpio_put(PIN_READY, freeb >= sizeof(spi_rx_packet) ? 1 : 0);

        // Diagnostic: count RX FIFO overruns (a byte clocked onto a full FIFO).
        if (spi_get_hw(SPI_PORT)->ris & SPI_SSPRIS_RORRIS_BITS) {
            diag_rx_overruns++;
            spi_get_hw(SPI_PORT)->icr = SPI_SSPICR_RORIC_BITS;
        }

        // Keep the dummy-TX feed at most fifo_depth ahead of consumed RX so the
        // shared shift register neither starves (stalls RX) nor over-supplies.
        // CRITICAL: only feed TX while CS is asserted. Pre-loading the TX FIFO
        // before the slave is selected desyncs the PL022's shared TX/RX shift
        // register and latches exactly one byte per selection (bytes==cs_asserts,
        // ovr==0). spi_test leaves TX empty until CS falls -- we do the same.
        if (cs_asserted && tx_lead < fifo_depth && spi_is_writable(SPI_PORT)) {
            spi_get_hw(SPI_PORT)->dr = 0x00;
            tx_lead++;
        }
        // Drain one RX byte into the ring; drop on overflow so we never lock up.
        if (spi_is_readable(SPI_PORT)) {
            uint8_t b = (uint8_t)spi_get_hw(SPI_PORT)->dr;
            tx_lead--;
            if (freeb > 0) {
                ring_buffer[write_ptr] = b;
                write_ptr = (write_ptr + 1) % BUFFER_SIZE;
                diag_spi_bytes_received++;
            }
        }
    }
}
