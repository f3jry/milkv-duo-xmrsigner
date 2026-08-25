---
name: repo_instructions
type: repo
version: 1.0.0
agent: CodeActAgent
---

# Milk-V Duo XmrSigner / SeedSigner Repository Guide

## Project Overview
This repository contains the port of **XmrSigner** (Monero air-gapped hardware signer) to the **Milk-V Duo (CV1800B RISC-V, 64MB RAM)**.

### Target Hardware
- **SoC:** SOPHGO CV1800B (T-Head C906 RISC-V 64-bit @ 1.0 GHz, 64MB RAM)
- **Displays Supported:**
  - 1.8" 128x160 SPI TFT with XPT2046 Touch (`128x160 1.8TFT SPI V1.1` / `L07-1.8TFT-ChuMo`, ST7735 driver)
  - 1.3" 240x240 SPI LCD HAT (Waveshare ST7789 driver)
- **Cameras Supported:** V4L2 (`/dev/video0`) CV1800B MIPI-CSI GC2053 & USB UVC cameras.
- **Input:** 5-way D-Pad Joystick & Pushbuttons via sysfs GPIO + XPT2046 Touch Screen zones.

---

## Directory Architecture
- `src/xmrsigner/`: Core application logic (Controller, Views, Screens, Navigation).
  - `src/xmrsigner/hardware/`: Hardware abstraction layer (HAL) for Milk-V Duo.
    - `milkv_gpio.py`: Sysfs GPIO backend and RPi.GPIO compatibility layer.
    - `ST7735.py`: 1.8" 128x160 SPI TFT driver with 4KB buffer chunking.
    - `ST7789.py`: 1.3" 240x240 SPI LCD driver.
    - `xpt2046.py`: 12-bit resistive touch screen controller.
    - `milkv_camera.py`: V4L2 / OpenCV QR scanning camera module.
- `src/ots/`: Self-contained Monero Offline Transaction Signing (OTS) cryptographic engine.
  - `crypto.py`: Keccak-256 (Monero standard), Ed25519 point arithmetic, Base58 Monero encoder/decoder.
  - `seed.py`: Monero 25-word mnemonics, 13-word legacy mnemonics, 16-word Polyseeds.
  - `address.py`: Standard addresses (`4...`), Subaddresses (`8...`), Integrated addresses (`4...`).
  - `transaction.py`: Transaction parsing, CLSAG ring signatures, Key Image generation.
- `tools/`: Build and image packaging scripts.

---

## Running Tests
Run the test suite under Python or QEMU RISC-V:
```bash
python3 /home/cachy/milkv/test_xmrsigner.py
```
For QEMU RISC-V User Emulation:
```bash
qemu-riscv64 -cpu thead-c906 -L /run/media/cachy/rootfs -E LD_LIBRARY_PATH=/usr/lib:/lib /run/media/cachy/rootfs/usr/bin/python3 /home/cachy/milkv/test_xmrsigner.py
```
