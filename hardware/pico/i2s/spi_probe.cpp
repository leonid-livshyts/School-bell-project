// Raw bus-edge logger. Diagnostic only -- does NOT use the SPI peripheral at
// all. GP16 (MOSI), GP17 (CS), GP18 (SCK) are read as plain GPIO inputs, so
// this records exactly what the ESP32 master drives onto the wires during one
// CS-low window, independent of any SPI-slave sampling behaviour.
//
// Purpose: the SPI slave (spi_test/main.cpp) latches only ONE byte per window.
// This tells us whether that is because the clock never reaches the pin
// (physical) or because the pin sees a full clock train the peripheral fails
// to sample (peripheral/config). Run with spi_hello_test.py on the ESP32.
#include <stdio.h>
#include <stdint.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"
#include "hardware/structs/sio.h"

#define PIN_MOSI  16
#define PIN_CS    17
#define PIN_SCK   18
#define PIN_READY 20
#define PIN_STOP  21

// Transition ring. 4096 bytes * 8 bits * 2 edges = 65536 SCK edges for a full
// clean transfer; if we fill this, the clock is clearly toggling heavily.
#define MAXEV 16000
static uint32_t ev_t[MAXEV]; // microseconds since CS fell
static uint8_t  ev_s[MAXEV]; // bit0=SCK, bit1=MOSI, bit2=CS

// Read the three pins in one shot from the raw input register.
static inline uint8_t sample(void) {
    uint32_t g = sio_hw->gpio_in;
    return (uint8_t)(((g >> PIN_SCK) & 1u)
                   | (((g >> PIN_MOSI) & 1u) << 1)
                   | (((g >> PIN_CS) & 1u) << 2));
}

int main() {
    gpio_init(PIN_READY); gpio_set_dir(PIN_READY, GPIO_OUT); gpio_put(PIN_READY, 0);
    gpio_init(PIN_STOP);  gpio_set_dir(PIN_STOP, GPIO_IN);  gpio_pull_down(PIN_STOP);

    // Plain inputs, no pulls -- read exactly what the master drives.
    gpio_init(PIN_SCK);  gpio_set_dir(PIN_SCK, GPIO_IN);  gpio_disable_pulls(PIN_SCK);
    gpio_init(PIN_MOSI); gpio_set_dir(PIN_MOSI, GPIO_IN); gpio_disable_pulls(PIN_MOSI);
    gpio_init(PIN_CS);   gpio_set_dir(PIN_CS, GPIO_IN);   gpio_disable_pulls(PIN_CS);

    stdio_init_all();
    for (int i = 0; i < 6; i++) {
        printf("=== spi_probe boot (raw edge logger: SCK=GP%d MOSI=GP%d CS=GP%d) ===\n",
               PIN_SCK, PIN_MOSI, PIN_CS);
        sleep_ms(500);
    }

    uint32_t count = 0;
    while (1) {
        gpio_put(PIN_READY, 1); // let spi_hello_test.py proceed
        printf("[%lu] waiting for CS low...\n", (unsigned long)count);

        uint32_t last_status = time_us_32();
        while (sample() & 0x4) { // CS bit (active low) still high
            if (time_us_32() - last_status >= 500000) {
                printf("[%lu] ...still waiting for CS low\n", (unsigned long)count);
                last_status = time_us_32();
            }
        }

        // CS is low: capture every transition until CS rises or the buffer
        // fills. Tight loop, no printf -- printing here would miss edges.
        uint32_t t0 = time_us_32();
        uint8_t last = sample();
        uint32_t n = 0;
        ev_t[n] = 0; ev_s[n] = last; n++; // initial state at CS-low
        while (n < MAXEV) {
            uint8_t s = sample();
            if (s != last) {
                ev_t[n] = time_us_32() - t0;
                ev_s[n] = s;
                last = s;
                n++;
                if (s & 0x4) break; // CS went high -> window over
            }
        }
        gpio_put(PIN_READY, 0);

        // Summarise: how much did each line actually toggle?
        uint32_t sck_rise = 0, sck_fall = 0, mosi_edges = 0;
        for (uint32_t i = 1; i < n; i++) {
            uint8_t a = ev_s[i - 1], b = ev_s[i];
            if ((b & 1) && !(a & 1)) sck_rise++;
            if (!(b & 1) && (a & 1)) sck_fall++;
            if ((b & 2) != (a & 2)) mosi_edges++;
        }
        printf("[%lu] WINDOW: transitions=%lu sck_rise=%lu sck_fall=%lu mosi_edges=%lu window=%luus%s\n",
               (unsigned long)count, (unsigned long)n,
               (unsigned long)sck_rise, (unsigned long)sck_fall,
               (unsigned long)mosi_edges, (unsigned long)ev_t[n - 1],
               (n >= MAXEV) ? " [BUFFER FULL: clock toggling heavily]" : "");

        // Dump the first transitions so we can see the actual waveform shape.
        uint32_t dump = n < 64 ? n : 64;
        for (uint32_t i = 0; i < dump; i++) {
            printf("  t=%luus SCK=%d MOSI=%d CS=%d\n", (unsigned long)ev_t[i],
                   ev_s[i] & 1, (ev_s[i] >> 1) & 1, (ev_s[i] >> 2) & 1);
        }

        count++;
        sleep_ms(500);
    }
}
