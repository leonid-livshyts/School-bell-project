// Ground-truth electrical test. NO SPI peripheral at all -- GP16/18/19 are
// plain GPIO INPUTS, so the Pico physically cannot drive them. Pair with
// gpio_drive_test.py on the ESP32, which drives the data + clock wires high/
// low with plain GPIO. This isolates "is a valid logic level reaching the
// Pico?" from any SPI-protocol or driver-contention question.
//
// Measure the wire's voltage with a meter/scope at the same time:
//   - If the Pico reads 1 and the wire is ~3.3V when the ESP32 drives high,
//     the link is electrically fine and the problem is SPI config/protocol.
//   - If the wire sits at ~1.8V even though the Pico pin is a pure input,
//     something else is loading it (a real electrical fault to chase).
#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/gpio.h"

#define PIN_RX   16  // SPI0 RX  -- where the ESP32's MOSI must land in slave mode
#define PIN_SCK  18  // SPI0 SCK
#define PIN_TX   19  // SPI0 TX  -- where MOSI was wrongly wired before

int main() {
    stdio_init_all();
    printf("\n=== gpio_level_test boot (pure inputs, no SPI) ===\n");

    gpio_init(PIN_RX);  gpio_set_dir(PIN_RX, GPIO_IN);  gpio_disable_pulls(PIN_RX);
    gpio_init(PIN_SCK); gpio_set_dir(PIN_SCK, GPIO_IN); gpio_disable_pulls(PIN_SCK);
    gpio_init(PIN_TX);  gpio_set_dir(PIN_TX, GPIO_IN);  gpio_disable_pulls(PIN_TX);

    while (1) {
        printf("GP16(RX)=%d  GP18(SCK)=%d  GP19(TX-pin)=%d\n",
               gpio_get(PIN_RX), gpio_get(PIN_SCK), gpio_get(PIN_TX));
        sleep_ms(500);
    }
}
