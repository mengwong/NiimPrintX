# iOS Integration Guide

This guide shows how to trigger label printing from your iPhone using Siri Shortcuts and NFC tags.

## Prerequisites

1. **Server Setup**: The label API server must be running on your Mac/Linux machine
2. **Network**: Your iPhone and computer must be on the same network
3. **IP Address**: Find your computer's IP address with `ifconfig` or `ip addr`

## Starting the Server

```bash
# On your Mac/Linux machine
cd /path/to/NiimPrintX
poetry run python label_api.py
```

The server will start on port 8080. Note your computer's IP address (e.g., `192.168.1.100`).

## iOS Shortcuts Setup

### 1. Create Basic Shortcut

1. Open **Shortcuts** app on iPhone
2. Tap **+** to create new shortcut
3. Add these actions:

#### Action 1: Ask for Input (Optional)
- Add **Ask for Input** action
- Set prompt to "Label text (optional):"
- Allow empty input
- Variable name: `Volume`

#### Action 2: Get Contents of URL
- Add **Get Contents of URL** action
- URL: `http://YOUR_IP_ADDRESS:8080/print`
- Method: `POST`
- Headers: 
  - `Content-Type`: `application/json`
- Request Body: 
  ```json
  {"text": "[Volume from Ask for Input]", "timestamp_format": "friendly"}
  ```
  
  **Timestamp Format Options:**
  - `"iso8601"` (default): `2025-10-16 15:16:04`
  - `"friendly"`: `Thu 16 Oct` / `11:16 PM` (two lines)

#### Action 3: Show Notification (Optional)
- Add **Show Notification** action
- Title: "Label Printed"
- Body: "Sent: [Volume]"

### 2. Shortcut Variations

#### Simple Version (No Input)
Skip the "Ask for Input" step and just send:
```json
{"text": ""}
```

#### Pre-filled Text
Skip "Ask for Input" and use a fixed value:
```json
{"text": "50mL"}
```

#### Smart Math Version (Backend Processing)
The backend now handles all math automatically! Just send any text:

1. **Ask for Input** action
   - Prompt: "Enter text, numbers, or math (e.g. '50', '25 30', 'buffer'):"
   - Input Type: Text
   - Variable: `UserInput`

2. **Get Contents of URL**
   - URL: `http://YOUR_IP:8080/print`
   - Method: POST
   - Headers: `Content-Type: application/json`
   - Body: `{"text": "[UserInput]", "timestamp_format": "friendly"}`

**The backend automatically:**
- "50" → Prints "50mL"
- "25 30" → Adds numbers and prints "55mL"
- "add 25 and 30" → Extracts numbers and prints "55mL"
- "buffer solution" → Prints "buffer solution" as-is

### 3. Add to Siri

Whatever shortcut you just created, is now a Siri command. It will
prompt you for input. You can give a single number, or a sentence
containing two numbers, and the backend will add the numbers.

## NFC Tag Setup

### 1. Get NFC Tags
- Buy blank NFC tags (NTAG213/215/216 work well)
- Stickers or cards both work

### 2. Program NFC Tag

1. In **Shortcuts** app, open your shortcut
2. Tap **Settings** (gear icon)
3. Tap **Add to Home Screen** or **Use with NFC**
4. Choose **Use with NFC**
5. Hold your iPhone near the NFC tag
6. Follow prompts to program the tag

### 3. Multiple NFC Tags

Create different shortcuts for different use cases:
- **Lab Equipment**: Text input for measurements
- **Quick Timestamp**: No text, just timestamp
- **Inventory**: Pre-filled common items

## Usage Examples

### Siri Commands

#### Basic Commands
- "Hey Siri, print label" → Asks for text input
- "Hey Siri, timestamp label" → Prints just timestamp

#### Voice Parameter Commands (Advanced Setup)
- "Hey Siri, print 50mL" → Prints "50mL" with timestamp
- "Hey Siri, print 127" → Prints "127mL" with timestamp
- "Hey Siri, print 25 30" → Prints "55mL" (math-enabled)
- "Hey Siri, print 12.5 7.3" → Prints "19.8mL"
- "Hey Siri, print buffer solution" → Prints "buffer solution"

#### Math-Enabled Commands
- "Hey Siri, add volumes 25 30" → Prints "55mL"
- "Hey Siri, add volumes 15" → Prints "15mL"

### NFC Workflows
- **Lab Station**: Tap NFC → Enter measurement → Print
- **Storage Area**: Tap NFC → Print timestamp for inventory
- **Quick Labels**: Tap NFC → Instant print with preset text
- **Volume Addition**: Tap NFC → Enter "25 30" → Prints "55mL"
- **Mixing Station**: Different NFC tags for different operations:
  - **Add Volumes**: Math-enabled for combining measurements
  - **Single Volume**: Simple input for single measurements
  - **Quick 50mL**: Pre-set for common volume

## Troubleshooting

### Connection Issues
1. Check if server is running: `curl http://YOUR_IP:8080/status`
2. Verify iPhone and computer are on same WiFi
3. Check firewall settings on your computer

### Server Not Responding
```bash
# Check if server is running
ps aux | grep label_api

# Restart server
poetry run python label_api.py
```

### Printer Issues
- Ensure B21 is in pairing mode (blinking green light)
- Check Bluetooth permissions for Python and Warp
- Test with CLI: `poetry run python -m NiimPrintX.cli info -m b21`

## Advanced Setup

### Auto-start Server
Add to your shell profile (`.zshrc` or `.bashrc`):
```bash
alias label-server='cd /path/to/NiimPrintX && poetry run python label_api.py'
```

### Network Access
To allow access from other devices on your network, the server already binds to `0.0.0.0:8080`.

### HTTPS Setup
For security over public networks, consider using ngrok or similar:
```bash
# Install ngrok, then:
ngrok http 8080
# Use the https URL in your shortcuts
```

## Example API Calls

```bash
# Print with text (ISO format)
curl -X POST http://192.168.1.100:8080/print \
     -H "Content-Type: application/json" \
     -d '{"text": "50mL"}'

# Print with friendly timestamp format
curl -X POST http://192.168.1.100:8080/print \
     -H "Content-Type: application/json" \
     -d '{"text": "50mL", "timestamp_format": "friendly"}'

# Print timestamp only (friendly)
curl -X POST http://192.168.1.100:8080/print \
     -H "Content-Type: application/json" \
     -d '{"text": "", "timestamp_format": "friendly"}'

# Check server status
curl http://192.168.1.100:8080/status
```
