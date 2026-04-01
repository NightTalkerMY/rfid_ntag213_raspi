# Raspberry Pi 5 NFC Reader/Writer

This repository contains the core Python scripts required to reliably read and write NDEF-formatted text to NTAG213 NFC tags using an RC522 RFID module. 

It is specifically optimized for the Raspberry Pi 5, bypassing legacy GPIO limitations and handling the 7-byte Cascade Level 2 handshake required for NTAGs.

## Hardware Setup
* **Microcomputer:** Raspberry Pi 5
* **NFC Module:** MFRC522 (RC522)
* **NFC Tags:** NTAG213 (Ultralight, 7-byte UID)

### Wiring / Pinout
Connect the RC522 module to the Raspberry Pi 5 using the standard SPI interface:

| RC522 Pin | Raspberry Pi 5 Pin | Notes |
| :--- | :--- | :--- |
| **SDA** | GPIO 8 (CE0) | SPI Chip Enable 0 |
| **SCLK** | GPIO 11 (SCLK) | SPI Clock |
| **MOSI** | GPIO 10 (MOSI) | Master Out Slave In |
| **MISO** | GPIO 9 (MISO) | Master In Slave Out |
| **RST** | GPIO 25 | Reset Pin |
| **3.3V** | 3.3V | Power (Do NOT connect to 5V) |
| **GND** | GND | Ground |

![Raspberry Pi 5 Pinout Diagram](path/to/your/pinout_image.png)

## Software Installation

Because the Raspberry Pi 5 handles hardware memory differently than older models, the legacy `RPi.GPIO` library will throw a SOC peripheral base address error. You must use the modern `rpi-lgpio` drop-in replacement.

1. Enable the SPI interface on your Raspberry Pi:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options -> SPI -> Enable
   ```
2. Install the required Python libraries:
   ```bash
   pip install --force-reinstall rpi-lgpio
   pip install mfrc522
   ```

## Usage

### 1. Reading Tags (`read.py`)
This script patiently waits for an NTAG213, performs the 7-byte wake-up handshake, and pulls the first 48 bytes of user memory. It features a custom NDEF parser that strips away formatting envelopes to output clean text records.
```bash
python read.py
```

### 2. Writing Tags (`write.py`)
This script takes a standard text string from the user, wraps it in a standard NDEF Text Record envelope, and burns it to the NTAG213 memory 4 bytes at a time. Tags formatted with this script can be natively read by standard Android and iOS smartphones.
```bash
python write.py
```
```