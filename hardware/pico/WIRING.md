# Audio path wiring — ESP32 → Pi Pico → I²S DAC

The ESP32 streams compressed MP3 to the Pico over SPI; the Pico decodes it
(Helix MP3) and drives an I²S DAC.

## ESP32 (SPI master) ⇄ Pi Pico (SPI slave)

| Signal               | ESP32 pin | Dir | Pico pin     | Notes                          |
|----------------------|-----------|-----|--------------|--------------------------------|
| SPI clock            | GP32      | →   | GP18 (SCK)   |                                |
| SPI data (MOSI)      | GP33      | →   | GP19 (RX)    | MP3 bytes ESP32 → Pico         |
| Chip select          | GP26      | →   | GP17 (CSn)   | active low                     |
| SPI MISO             | GP25      | ←   | GP16 (TX)    | unused (one-way), wiring optional |
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

- ESP32 pins avoid the ones already in use: GP5 (LED), GP14 (DHT),
  GP21/GP22 (I²C display), GP34 (air-quality). The old I²S audio pins
  (32/33/25) are reused for SPI now that the ESP32 no longer drives I²S.
- GP35 is input-only — used for READY (an input on the ESP32 side).
- Pin numbers are defined in `i2s/main.cpp` (Pico) and as the
  `PlayerController` defaults in `../esp32/player.py` (ESP32).
- Audio format is fixed at 44.1 kHz / 16-bit / stereo. All media files must
  be encoded that way.
