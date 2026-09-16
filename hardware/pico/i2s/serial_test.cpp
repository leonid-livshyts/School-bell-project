// Minimal serial-only test. No SPI, no I2S, no decoder -- just proves the
// Pico boots and USB/UART serial output works. Diagnostic only; not part of
// the real player.
#include <stdio.h>
#include "pico/stdlib.h"

int main() {
    stdio_init_all();

    uint32_t count = 0;
    while (1) {
        printf("[%lu] hello from pico\n", (unsigned long)count);
        count++;
        sleep_ms(1000);
    }
}
