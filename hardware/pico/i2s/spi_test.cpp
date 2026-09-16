// Minimal SPI-slave echo/print test. Bypasses MP3 decoding, the ring buffer,
// and core1 entirely -- just proves raw bytes can travel ESP32 -> Pico over
// the existing SPI wiring. Diagnostic only; not part of the real player.
//
// Uses a GPIO interrupt on CS purely for diagnostics: it sees the pad's raw
// input level regardless of which peripheral function is selected on the
// pin, so it gives ground-truth timing even if the SPI peripheral itself
// never manages to shift in a byte. Deliberately NOT doing this on SCK too:
// at hundreds of kHz that's enough interrupts to starve the core of time to
// drain the RX FIFO. Use an oscilloscope for SCK frequency instead.
#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/spi.h"
#include "hardware/gpio.h"

#define SPI_PORT    spi0
// RP2040 SPI0 pin functions are fixed: GP16=RX, GP17=CSn, GP18=SCK, GP19=TX.
// In slave mode the master's MOSI (data IN) must land on RX (GP16), and the
// slave's TX (GP19) drives the master's MISO. Wiring the master's MOSI to the
// TX pin makes two outputs fight the line (~1.8V) and receives nothing.
#define PIN_MOSI    16   // master MOSI -> slave SPI0 RX; incoming data
#define PIN_CS      17   // SPI0 CSn
#define PIN_SCK     18   // SPI0 SCK
#define PIN_MISO    19   // slave SPI0 TX -> master MISO; outgoing (unused)

#define PIN_READY   20
#define PIN_STOP    21

// Long on purpose: at 1 MHz this is a ~32ms-long SPI transaction, easy to
// find and trigger on an oscilloscope. Must match MSG_LEN in spi_hello_test.py.
#define MSG_LEN     4096

volatile bool cs_asserted = false;
volatile uint64_t cs_low_time_us = 0;
volatile uint64_t cs_high_time_us = 0;

static void gpio_callback(uint gpio, uint32_t events) {
    if (gpio == PIN_CS) {
        if (events & GPIO_IRQ_EDGE_FALL) {
            cs_low_time_us = time_us_64();
            cs_asserted = true;
        }
        if (events & GPIO_IRQ_EDGE_RISE) {
            cs_high_time_us = time_us_64();
            cs_asserted = false;
        }
    }
}

int main() {
    gpio_init(PIN_READY); gpio_set_dir(PIN_READY, GPIO_OUT); gpio_put(PIN_READY, 0);
    gpio_init(PIN_STOP);  gpio_set_dir(PIN_STOP, GPIO_IN);   gpio_pull_down(PIN_STOP);

    stdio_init_all();
    printf("\n=== spi_test boot ===\n");

    spi_init(SPI_PORT, 1000000); // slow (1 MHz) on purpose for this test
    spi_set_slave(SPI_PORT, true);
    // TEST: SPI mode 3 (CPOL=1, CPHA=1) -- clock idles high, sample on the
    // second (rising) edge. MUST match polarity=1/phase=1 on the ESP32 side
    // (spi_hello_test.py). Trying mode 3 to see whether it changes the current
    // 1-byte-per-window reception. (Was mode 0; mode 3 previously showed a
    // 1-bit slip -- watch the first-16-bytes line for that.)
    spi_set_format(SPI_PORT, 8, SPI_CPOL_1, SPI_CPHA_1, SPI_MSB_FIRST);
    gpio_set_function(PIN_MISO, GPIO_FUNC_SPI);
    gpio_set_function(PIN_SCK, GPIO_FUNC_SPI);
    gpio_set_function(PIN_MOSI, GPIO_FUNC_SPI);
    gpio_set_function(PIN_CS, GPIO_FUNC_SPI);

    // RP2040 pads reset with an internal pull-down enabled; gpio_set_function()
    // does not touch pulls, so it stays active even once the pin is claimed by
    // the SPI peripheral. That pull-down was loading down the ESP32's MOSI
    // driver -- disable it explicitly on all four SPI pins.
    gpio_disable_pulls(PIN_MISO);
    gpio_disable_pulls(PIN_SCK);
    gpio_disable_pulls(PIN_MOSI);
    gpio_disable_pulls(PIN_CS);

    // Diagnostic-only IRQ. The pin's alternate function (SPI) and the
    // edge-detect logic are independent blocks in the RP2040, so this works
    // even though the pin is simultaneously claimed by the SPI peripheral.
    gpio_set_irq_enabled_with_callback(PIN_CS, GPIO_IRQ_EDGE_FALL | GPIO_IRQ_EDGE_RISE,
                                        true, &gpio_callback);

    static uint8_t buf[MSG_LEN]; // static: too big for the core0 stack
    uint32_t count = 0;

    while (1) {
        gpio_put(PIN_READY, 1);
        printf("[%lu] waiting for CS to go low...\n", (unsigned long)count);

        uint64_t last_status_us = time_us_64();
        while (!cs_asserted) {
            uint64_t now_us = time_us_64();
            if (now_us - last_status_us >= 500000) {
                printf("[%lu] ... still waiting for CS low\n", (unsigned long)count);
                last_status_us = now_us;
            }
        }

        uint64_t t_cs_low = cs_low_time_us;
        printf("[%lu] CS LOW at t=%lluus\n", (unsigned long)count,
               (unsigned long long)t_cs_low);

        size_t received = 0;
        size_t rx_remaining = MSG_LEN;
        size_t tx_remaining = MSG_LEN; // must keep feeding TX or the slave's
                                       // shared shift register stalls RX too
        const size_t fifo_depth = 8;
        bool first_byte_logged = false;
        uint64_t first_byte_us = 0;
        uint8_t first_byte_val = 0;

        // No printf in here -- USB-serial output can block long enough to
        // stall this loop, overflow the 8-entry RX FIFO, and silently lose
        // every byte after the first. Just record; print after CS goes high.
        while (cs_asserted && rx_remaining) {
            if (tx_remaining && spi_is_writable(SPI_PORT) &&
                rx_remaining < tx_remaining + fifo_depth) {
                spi_get_hw(SPI_PORT)->dr = 0x00; // dummy TX, keeps RX shifting
                tx_remaining--;
            }
            if (spi_is_readable(SPI_PORT)) {
                buf[received++] = (uint8_t)spi_get_hw(SPI_PORT)->dr;
                rx_remaining--;
                if (!first_byte_logged) {
                    first_byte_us = time_us_64() - t_cs_low;
                    first_byte_val = buf[0];
                    first_byte_logged = true;
                }
            }
        }

        // Covers both: CS already went high, or we filled the buffer while
        // CS is still asserted (extra clocked bits we're not consuming).
        while (cs_asserted) { tight_loop_contents(); }

        uint64_t t_cs_high = cs_high_time_us;
        double elapsed_ms = (double)(t_cs_high - t_cs_low) / 1000.0;

        if (first_byte_logged) {
            printf("[%lu] first data byte arrived %lluus after CS low (0x%02x)\n",
                   (unsigned long)count, (unsigned long long)first_byte_us, first_byte_val);
        }

        printf("[%lu] CS HIGH at t=%lluus -- received %u/%d bytes over %.2fms\n",
               (unsigned long)count, (unsigned long long)t_cs_high,
               (unsigned)received, MSG_LEN, elapsed_ms);

        if (!first_byte_logged) {
            printf("[%lu] WARNING: CS was asserted but no data byte ever appeared in the SPI RX FIFO\n",
                   (unsigned long)count);
        }

        gpio_put(PIN_READY, 0);

        printf("[%lu] first 16 bytes received: \"", (unsigned long)count);
        for (size_t i = 0; i < 16 && i < received; i++) {
            uint8_t c = buf[i];
            if (c >= 32 && c < 127) putchar(c);
            else printf("\\x%02x", c);
        }
        printf("\"\n");

        count++;
        sleep_ms(500); // pace it so output is easy to read
    }
}
