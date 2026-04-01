# Raspberry Pi 5 NFC API Server & Writer

This repository contains a complete Python-based hardware stack to read and write NDEF-formatted text to NTAG213 NFC tags using an RC522 RFID module. 

Designed specifically for the Raspberry Pi 5, this project bypasses legacy GPIO limitations, handles the complex 7-byte Cascade Level 2 handshake for Ultralight tags, and exposes the hardware via a FastAPI "long-polling" endpoint for seamless frontend integration.

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

![Raspberry Pi 5 Pinout Diagram](https://github.com/user-attachments/assets/b8d6ae61-62c5-452f-9046-d57cf2778953)

## Software Installation

Because the Raspberry Pi 5 handles hardware memory differently than older models, the legacy `RPi.GPIO` library will throw a SOC peripheral base address error. We use the modern `rpi-lgpio` drop-in replacement.

1. Enable the SPI interface on your Raspberry Pi:
   ```bash
   sudo raspi-config
   # Navigate to Interface Options -> SPI -> Enable
   ```
2. Install all required dependencies using the provided requirements file:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: This includes `fastapi`, `uvicorn`, `requests`, `mfrc522`, and `rpi-lgpio`)*

## Usage Guide

The architecture is split into three main operations: Writing data to tags, running the API server, and fetching data as a client.

### 1. Provisioning Tags (`write.py`)
Use this script to format blank tags. It takes a standard text string, wraps it in a standard NDEF Text Record envelope, and burns it to the NTAG213 memory. Tags formatted with this script can be natively read by this system or any standard Android/iOS smartphone.
```bash
python write.py
```

### 2. Starting the API Server (`main.py` & `nfc_reader.py`)
This spins up a FastAPI server on port 8000. It initializes the hardware once and waits for HTTP requests. When the `/scan` endpoint is hit, it uses a "long-polling" method—blocking for up to 10 seconds while the hardware actively scans for a tag before returning a clean JSON response.
```bash
python main.py
```
*Test the API locally in your browser at: `http://127.0.0.1:8000/scan`*

### 3. Fetching Data (`client.py`)
A sample Python client to test the API. It sends a single request to the server, waits for the 10-second hardware scan window, and prints any extracted NDEF text records directly to the terminal upon a successful read.
```bash
python client.py
```