# School Bell -currently_in_development-

A modern school bell system with local control: ring schedules, custom melodies,
voice announcements, alarms, and classroom environment monitoring.

Each classroom (or building zone) gets its own bell device. The device plays the
bell at the start and end of every lesson, plays announcements and alarm sounds,
and reports the temperature, humidity and air quality in the room. An admin
manages all bells from one website.

## Structure

| Part | Path | Stack |
|------|------|-------|
| Hardware | [hardware/esp32](hardware/esp32) | ESP32 (MicroPython): Wi-Fi, schedule, sensors (DHT, air quality, mic), display, alarms |
| Audio | [hardware/pico](hardware/pico) | Raspberry Pi Pico (C++): receives MP3 from the ESP32 over SPI and plays it through an I2S DAC — see [WIRING.md](hardware/pico/WIRING.md) |
| Backend | [backend](backend) | FastAPI + SQLAlchemy: lessons, rooms, devices, measurements, ringtones, voice messages, alarms, auth |
| Streamer | [backend/streamer](backend/streamer) | Python asyncio TCP server that streams MP3 files to the devices |
| Frontend | [frontend](frontend) | React + Vite + TypeScript + Tailwind: admin website for managing the bells |
| PCB | [kicad](kicad) | KiCad schematic and PCB for the bell board |

## How it works

```
 Admin ──► Frontend (React) ──HTTP/JSON──► Backend (FastAPI) ──► SQLite
                                               ▲
                        HTTP polling (X-API-Key)│
                                               │
 Speaker ◄── I2S DAC ◄── Pi Pico ◄──SPI── ESP32 ┘
                        (MP3 decode)       │
                                           └──TCP──► Streamer (MP3 files)
```

The system has one central server and many bell devices. The server holds all
the data. The devices are "thin": they keep only today's schedule and a few
flags in memory, and ask the server for everything else.

### 1. The admin sets things up (frontend → backend)

The admin logs in to the website and manages **rooms**, **devices** (each
registered in a room with a secret key), **lessons** (name, start, end — these
drive the bell), **ringtones** and **voice messages** (uploaded MP3 files),
one **alarm** switch per room, and charts of the sensor **measures**.

### 2. The device starts up (ESP32)

On boot, [mainish.py](hardware/esp32/mainish.py) does this:

1. Reads [config.json](hardware/esp32/config.json), which can hold several
   Wi-Fi networks, each with its own server address.
2. Connects to Wi-Fi (retrying every minute) and sets the RTC from
   `/private/time`. The server sends UTC plus the Kyiv offset, so summer and
   winter time are handled on the server.
3. Sets up the sensors (DHT on GPIO14, air quality on GPIO34) and the SSD1306
   OLED, which shows the time and the Wi-Fi/server status.
4. Starts hardware timers that poll the server in the background.

### 3. Background polling (timers)

Each timer has its own period, set in `config.json`:

| Timer | Endpoint | What it does |
|-------|----------|--------------|
| Time | `GET /private/time` | Updates the display; re-syncs the RTC hourly and at midnight |
| Schedule | `GET /private/schedule` | Downloads today's lessons for this room as unix timestamps |
| Alarm | `GET /private/alarm` | Gets the alarm flag and detects when it turns on or off |
| Voice messages | `GET /private/voice_messages` | Adds new announcements to a local queue |
| Sensors | `POST /private/sensors` | Sends temperature, humidity and air quality |
| Logs | `POST /private/logs` | Uploads the cached device log to the server |

Every request carries the device key in the `X-API-Key` header. The server
finds the device's room from it, so every answer is already filtered by room.

### 4. The main loop — deciding what to play

Only one sound can play at a time, so the main loop decides by priority:

1. **Alarm** (highest). When the alarm flag changes, anything playing is
   stopped at once and the device plays `alarm_start` or `alarm_finish`.
2. **Voice message.** If the queue is not empty, the current ring is
   interrupted and the announcement plays.
3. **Ring.** [ScheduleMonitor](hardware/esp32/schedule.py) checks whether the
   current time is within a tolerance window (`schedule_tolerance`) of a lesson
   start or end. Each lesson boundary rings only once, even if the loop passes
   through the window many times. The device then asks `/private/ringtone_code`
   which ringtone this room uses and starts playing it.

Each sound has a maximum duration in the config; after it the loop stops the
playback. The loop catches all errors, so one failed request never stops the
bell.

### 5. The audio path (streamer → ESP32 → Pico → speaker)

Playing sound is split across two chips: the ESP32 only moves bytes, and a
Raspberry Pi Pico decodes the MP3 and drives the DAC.

1. **Streamer.** The ESP32 opens a TCP connection to
   [streamer/main.py](backend/streamer/main.py) (port 8088) and sends a tiny
   request: one length byte, then a type letter plus the file name — `R` for
   ringtones, `V` for voice messages, `S` for sounds, anything else for misc.
   The streamer checks the path cannot leave its folder and sends the raw MP3
   bytes back in 4 KB chunks.
2. **ESP32 → Pico.** [player.py](hardware/esp32/player.py) runs in a separate
   thread and forwards those bytes to the Pico over SPI in 512-byte chunks. The
   ESP32 is just a pipe here: it does not decode anything. Before each chunk it
   waits for the Pico's **READY** line, which is high only when the Pico has
   room in its buffer (back-pressure). To stop a sound, the ESP32 pulses the
   **STOP** line.
3. **Pico decodes.** In [main.cpp](hardware/pico/i2s/main.cpp), core 0 reads
   SPI into a 16 KB ring buffer. Core 1 decodes MP3 frames with the
   fixed-point Helix decoder (patched with a plain C path, since the RP2040's
   Cortex-M0+ can't run the ARM assembly version).
4. **Pico plays.** Decoded samples go to a PIO program that generates the I2S
   signal. DMA feeds the PIO from one buffer while core 1 decodes the next
   frame into the other, so decoding and playback overlap.

All audio must be **44.1 kHz, 16-bit, stereo MP3**, because the I2S clock on
the Pico is fixed to that rate. Full pin tables are in
[WIRING.md](hardware/pico/WIRING.md).

## Technologies

| Area | Used |
|------|------|
| Device | ESP32, MicroPython, `urequests`, `_thread`, hardware timers, DHT, air-quality sensor, SSD1306 OLED |
| Audio | Raspberry Pi Pico (RP2040), C++ / Pico SDK, PIO, DMA, Helix MP3 decoder, I2S DAC |
| Backend | FastAPI, Uvicorn, Pydantic, async SQLAlchemy + SQLite, bcrypt, OAuth2 bearer tokens for admins, `X-API-Key` for devices |
| Streaming | Python `asyncio` TCP server |
| Frontend | React 19, TypeScript, Vite, Tailwind 4, shadcn/ui (Radix), TanStack Query, React Router, react-hook-form + zod, Recharts |
| Hardware design | KiCad |

Lesson times are stored in UTC; "today" for a device is worked out in the
Europe/Kyiv timezone. [backend/updater](backend/updater) holds a first Google
Calendar reader, meant to import the schedule from a school calendar.

## What still works badly

The project is still in development. Known problems:

**Sound quality**

- The sound quality is still bad. The ESP32 → Pico → DAC path works, but the
  SPI link and I2S output are still being debugged: that is what the beep, SPI
  probe and GPIO test firmwares in [hardware/pico/i2s](hardware/pico/i2s) are
  for, and `main.cpp` still has temporary diagnostic counters.
- MP3 decoding on the Pico is barely fast enough: about 23 ms to decode a frame
  that plays for about 26 ms, so any small delay causes a dropout.
- The SPI mode (mode 3) is still being tested and may change.
- Audio must be 44.1 kHz stereo. Other files play at the wrong speed, and
  uploads are not checked or converted on the server.

**Frontend**

- The admin website is rough and not finished: pages need better UX and more
  testing against the real backend.
- The old frontend build (`frontend/build`) and the default Vite template
  README are still in the repo.

**Other**

- Voice messages are never marked as played on the server, so the device can
  pick up the same announcement again on the next poll.
- The microphone is not used yet; the `volume` value is always sent as `0`.
- The Google Calendar import is a standalone script and is not connected to
  the database.
- The timezone (Europe/Kyiv) is hard-coded in the backend.
