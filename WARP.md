# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

NiimPrintX is a Python library for interfacing with NiimBot label printers via Bluetooth. It provides both CLI and GUI applications for designing and printing labels.

**Key Technologies:**
- Python 3.12+ with Poetry for dependency management
- Bluetooth Low Energy (BLE) communication via `bleak` library
- Image processing with PIL/Pillow and ImageMagick/Wand
- GUI built with tkinter
- CLI built with Click
- Async/await architecture for Bluetooth operations

## Development Setup

### Initial Setup
```bash
# Install system dependencies (macOS)
brew install libffi glib gobject-introspection cairo pkg-config

# Set environment variables
export PKG_CONFIG_PATH="/usr/local/opt/libffi/lib/pkgconfig"
export LDFLAGS="-L/usr/local/opt/libffi/lib"
export CFLAGS="-I/usr/local/opt/libffi/include"

# Install dependencies
python -m venv venv
poetry install
```

### Running the Application
```bash
# GUI Application
python -m NiimPrintX.ui

# CLI Application
python -m NiimPrintX.cli --help
python -m NiimPrintX.cli print -m d110 -d 3 -n 1 -r 90 -i path/to/image.png
python -m NiimPrintX.cli info -m d110
```

## Architecture Overview

### Core Components

**`NiimPrintX.nimmy/`** - Core Bluetooth and printer communication
- `bluetooth.py`: BLE device discovery and transport layer
- `printer.py`: Main PrinterClient class with async printer operations
- `packet.py`: Protocol packet handling for NiimBot communication
- `exception.py`: Custom exception classes
- `logger_config.py`: Centralized logging configuration

**`NiimPrintX.cli/`** - Command-line interface
- `command.py`: Click-based CLI with print and info commands
- Supports multiple printer models (B1, B18, B21, D11, D110)
- Image processing and validation before printing

**`NiimPrintX.ui/`** - Graphical user interface
- `main.py`: Main tkinter application with tabbed interface
- `AppConfig.py`: Application configuration management
- Widget system for text labels, icons, and printing options
- Cross-platform UI styling (aqua for macOS, xpnative for Windows)

### Communication Protocol

The printer communication follows a specific async pattern:
1. BLE device discovery by name prefix
2. Connection establishment and characteristic discovery
3. Packet-based command/response communication
4. Image encoding to monochrome bitmap with line-by-line transmission
5. Print job status monitoring and completion handling

### Image Processing Pipeline

Images are processed through multiple stages:
1. Convert to monochrome using PIL ImageOps.invert()
2. Apply rotation (counterclockwise conversion for PIL)
3. Handle horizontal/vertical offsets with cropping/padding
4. Encode as binary data with line headers for printer protocol
5. Validate against printer model width constraints (240px for D11/D110, 384px for B1/B18/B21)

## Printer Models and Constraints

- **D11, D110**: Max width 240px, max density 3
- **B1, B18, B21**: Max width 384px
- **B18, D11, D110**: Density limited to max 3 (others support up to 5)

## Key Development Patterns

### Async Bluetooth Operations
All printer operations are async and follow this pattern:
```python
async def operation():
    device = await find_device(model)
    printer = PrinterClient(device)
    await printer.connect()
    result = await printer.some_operation()
    await printer.disconnect()
```

### Error Handling
- Custom exceptions: `BLEException`, `PrinterException`
- Comprehensive logging with loguru
- Graceful disconnection in error scenarios

### Cross-Platform Considerations
- PyInstaller packaging with runtime hooks
- Platform-specific library loading (ImageMagick paths)
- UI theme selection based on OS detection

## Dependencies and External Requirements

- **ImageMagick**: Required system dependency for image processing
- **Poetry**: Used for dependency management instead of pip
- **Python 3.12+**: Strict version requirement
- **Platform Libraries**: Core Bluetooth framework bindings for macOS