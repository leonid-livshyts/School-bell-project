#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "pico/multicore.h"
#include "hardware/spi.h"
#include "hardware/pio.h"
#include "i2s.pio.h"
#include "mp3dec.h" // Helix MP3 Decoder library
#include "hardware/clocks.h"
#include <string.h> // memmove


#define SPI_PORT    spi0
#define PIN_MISO    16
#define PIN_CS      17
#define PIN_SCK     18
#define PIN_MOSI    19

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
    
    // Initialize GPIO pins as PIO outputs
    pio_gpio_init(pio, pin_din);
    pio_gpio_init(pio, pin_bclk);
    pio_gpio_init(pio, PIN_I2S_LRC);
    
    // Set pins as outputs
    gpio_set_dir(pin_din, GPIO_OUT);
    gpio_set_dir(pin_bclk, GPIO_OUT);
    gpio_set_dir(PIN_I2S_LRC, GPIO_OUT);
    
    // Load configuration and start state machine
    pio_sm_init(pio, sm, offset, &c);
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
        if (off < 0) { mp3len = 0; continue; } // no sync in buffer, discard
        if (off > 0) { memmove(mp3buf, mp3buf + off, mp3len - off); mp3len -= off; }

        unsigned char *inp = mp3buf;
        int bytes_left = mp3len;
        int err = MP3Decode(hMP3Decoder, &inp, &bytes_left, sample_buffer, 0);

        if (err == ERR_MP3_NONE) {
            int consumed = mp3len - bytes_left;
            memmove(mp3buf, mp3buf + consumed, bytes_left);
            mp3len = bytes_left;

            MP3FrameInfo fi;
            MP3GetLastFrameInfo(hMP3Decoder, &fi);

            // Pack into 32-bit FIFO words: left in the high 16 bits, right in
            // the low 16 (PIO shifts MSB first, left channel first). Mono is
            // duplicated to both channels.
            int n = fi.outputSamps;
            if (fi.nChans == 2) {
                for (int i = 0; i + 1 < n; i += 2) {
                    uint32_t w = ((uint32_t)(uint16_t)sample_buffer[i] << 16)
                               | (uint16_t)sample_buffer[i + 1];
                    pio_sm_put_blocking(pio, sm, w);
                }
            } else {
                for (int i = 0; i < n; i++) {
                    uint32_t w = ((uint32_t)(uint16_t)sample_buffer[i] << 16)
                               | (uint16_t)sample_buffer[i];
                    pio_sm_put_blocking(pio, sm, w);
                }
            }
        } else if (err == ERR_MP3_INDATA_UNDERFLOW || err == ERR_MP3_MAINDATA_UNDERFLOW) {
            // Frame not fully present yet; keep bytes and refill next loop.
            // If the buffer is full and still underflowing, the data is junk:
            // drop a byte to resync and avoid a deadlock.
            if (mp3len >= MP3BUF_SIZE) { memmove(mp3buf, mp3buf + 1, --mp3len); }
        } else {
            // Decode error: skip one byte past this sync and try again.
            memmove(mp3buf, mp3buf + 1, mp3len - 1);
            mp3len -= 1;
        }
    }
}

// Core 0: High-Speed SPI Slave Data Ingest Loop
int main() {
    stdio_init_all();

    // Setup SPI Slave to accept data from the ESP32
    spi_init(SPI_PORT, 10000000); // 10 MHz clock rate
    spi_set_slave(SPI_PORT, true);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI);

    // Flow-control / control lines.
    gpio_init(PIN_READY); gpio_set_dir(PIN_READY, GPIO_OUT); gpio_put(PIN_READY, 0);
    gpio_init(PIN_STOP);  gpio_set_dir(PIN_STOP, GPIO_IN);   gpio_pull_down(PIN_STOP);

    // Launch Core 1 DSP Engine
    multicore_launch_core1(core1_entry);

    uint8_t spi_rx_packet[512];

    while (1) {
        // Only accept a chunk when there is guaranteed room for it, and tell
        // the ESP32 via the READY line. This is the back-pressure handshake:
        // the ESP32 must see READY high before clocking each 512-byte chunk.
        uint32_t used = (write_ptr - read_ptr + BUFFER_SIZE) % BUFFER_SIZE;
        uint32_t freeb = BUFFER_SIZE - 1 - used;

        if (freeb >= sizeof(spi_rx_packet)) {
            gpio_put(PIN_READY, 1); // room available: ESP32 may send
            spi_read_blocking(SPI_PORT, 0, spi_rx_packet, sizeof(spi_rx_packet));

            // Room is guaranteed, so copy the whole chunk in.
            for (size_t i = 0; i < sizeof(spi_rx_packet); i++) {
                ring_buffer[write_ptr] = spi_rx_packet[i];
                write_ptr = (write_ptr + 1) % BUFFER_SIZE;
            }
        } else {
            gpio_put(PIN_READY, 0); // buffer full: hold the ESP32 off
        }
    }
}
