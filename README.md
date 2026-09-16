# School Bell

A modern school bell system with local control: ring schedules, custom melodies,
voice announcements, and classroom environment monitoring.

## Structure

| Part | Path | Stack |
|------|------|-------|
| Hardware | [hardware/esp32](hardware/esp32) | ESP32 (MicroPython): Wi-Fi, schedule, sensors (DHT, air quality, mic), display, alarms |
| Audio | [hardware/pico](hardware/pico) | Raspberry Pi Pico (C++): receives MP3 from the ESP32 over SPI and plays it through an I2S DAC — see [WIRING.md](hardware/pico/WIRING.md) |
| Backend | [backend](backend) | FastAPI + SQLAlchemy: lessons, rooms, devices, measurements, ringtones, voice messages, alarms, auth |
| Frontend | [frontend](frontend) | React + Vite + TypeScript + Tailwind: admin website for managing the bells |
| PCB | [kicad](kicad) | KiCad hardware design |

## Quick start

```bash
# Backend
cd backend && python main.py

# Frontend
cd frontend && npm install && npm run dev
```
