# Audio path wiring — ESP32 → Pi Pico → I²S DAC

The ESP32 streams compressed MP3 to the Pico over SPI; the Pico decodes it
(Helix MP3) and drives an I²S DAC.

## ESP32 (SPI master) ⇄ Pi Pico (SPI slave)

ESP32 SPI uses the VSPI peripheral (machine.SPI id=2) on its native pins.

| Signal               | ESP32 pin | Dir | Pico pin     | Notes                          |
|----------------------|-----------|-----|--------------|--------------------------------|
| SPI clock            | GP18      | →   | GP18 (SCK)   | VSPI native SCK                |
| SPI data (MOSI)      | GP23      | →   | GP19 (RX)    | VSPI native MOSI; MP3 bytes ESP32 → Pico |
| SPI MISO             | GP19      | ←   | GP16 (TX)    | VSPI native MISO; unused (one-way), wiring optional |
| Chip select          | GP26      | →   | GP17 (CSn)   | active low; driven manually in code |
| READY (handshake)    | GP35      | ←   | GP20         | Pico high = ring buffer has room |
| STOP                 | GP27      | →   | GP21         | ESP32 high = flush & go silent |
| Ground               | GND       | ⇄   | GND          | common ground REQUIRED         |

## Pi Pico → I²S DAC

| Signal     | Pico pin | Dir | DAC       |
|------------|----------|-----|-----------|
| Bit clock  | GP2      | →   | BCLK      |
| L/R clock  | GP3      | →   | LRC / WS  |
| Data       | GP4      | →   | DIN / SD  |

## Notes

- ESP32 SPI uses the VSPI peripheral on its native pins (SCK=18, MOSI=23,
  MISO=19) for direct IO-MUX routing. The old ESP32 I²S audio pins
  (32/33/25) are now free.
- ESP32 pins avoid the ones already in use: GP5 (LED), GP14 (DHT),
  GP21/GP22 (I²C display), GP34 (air-quality).
- GP35 is input-only — used for READY (an input on the ESP32 side).
- Pin numbers are defined in `i2s/main.cpp` (Pico) and as the
  `PlayerController` defaults in `../esp32/player.py` (ESP32).
- Audio format is fixed at 44.1 kHz / 16-bit / stereo. All media files must
  be encoded that way.
