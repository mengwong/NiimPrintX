#!/usr/bin/env python3
"""
Remote Label Printing API
Accepts HTTP requests to print timestamped labels via NFC/Siri triggers
"""

from flask import Flask, request, jsonify
from datetime import datetime
import asyncio
import threading
from PIL import Image, ImageDraw, ImageFont
import os
import tempfile
import re
from pathlib import Path

from NiimPrintX.nimmy.bluetooth import find_device
from NiimPrintX.nimmy.printer import PrinterClient
from NiimPrintX.nimmy.logger_config import setup_logger, get_logger

# Setup logging
setup_logger()
logger = get_logger()

app = Flask(__name__)

class LabelPrinter:
    def __init__(self, printer_model="b21"):
        self.printer_model = printer_model
    
    def process_text_input(self, text):
        """Process text input to extract and potentially add numbers
        
        Examples:
        - "50" -> "50mL"
        - "25 30" -> "55mL" 
        - "12.5 7.3" -> "19.8mL"
        - "buffer solution" -> "buffer solution"
        - "add 25 and 30" -> "55mL"
        """
        if not text or not text.strip():
            return ""
        
        # Extract all numbers (integers and decimals) from the text
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        
        if len(numbers) >= 2:
            # Two or more numbers found - add the first two
            try:
                num1 = float(numbers[0])
                num2 = float(numbers[1])
                total = num1 + num2
                
                # Format nicely (remove .0 for whole numbers)
                if total == int(total):
                    return f"{int(total)}mL"
                else:
                    return f"{total}mL"
            except (ValueError, IndexError):
                # If parsing fails, fall back to original text
                return text
        elif len(numbers) == 1:
            # Single number found - add mL unit
            try:
                num = float(numbers[0])
                if num == int(num):
                    return f"{int(num)}mL"
                else:
                    return f"{num}mL"
            except ValueError:
                return text
        else:
            # No numbers found - return original text
            return text
        
    def create_timestamped_label(self, text="", timestamp_format="iso8601", width=384, height=230):
        """Create a label with timestamp and optional text
        
        Args:
            text: Optional text to display
            timestamp_format: 'iso8601' or 'friendly'
            width, height: Label dimensions in pixels
        """
        # Create white background
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)
        
        # Try to load a system font
        font_large = self._get_font(48)  # For main text (increased from 32)
        font_small = self._get_font(48)  # For timestamp (doubled from 24)
        
        # Get current timestamp in requested format
        now = datetime.now()
        if timestamp_format.lower() == "friendly":
            # Format: "Thu 16 Oct\n11:16 PM"
            timestamp = now.strftime("%a %d %b\n%I:%M %p")
        else:
            # Default ISO8601 format: "2025-10-16 15:16:04"
            timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # Layout: Main text on top, timestamp on bottom
        y_offset = 35  # Increased top margin from 20 to 35
        
        if text:
            # Draw main text
            bbox = draw.textbbox((0, 0), text, font=font_large)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            draw.text((x, y_offset), text, fill='black', font=font_large)
            y_offset += bbox[3] - bbox[1] + 20
        
        # Draw timestamp (handle multi-line)
        if '\n' in timestamp:
            # Multi-line timestamp (friendly format)
            lines = timestamp.split('\n')
            line_height = font_small.getbbox('A')[3] - font_small.getbbox('A')[1]
            total_height = len(lines) * line_height + (len(lines) - 1) * 12  # 12px line spacing (~1mm)
            
            # Position at bottom if there's main text, otherwise center
            if text:
                start_y = height - total_height - 20
            else:
                start_y = (height - total_height) // 2
            
            for i, line in enumerate(lines):
                bbox = draw.textbbox((0, 0), line, font=font_small)
                line_width = bbox[2] - bbox[0]
                x = (width - line_width) // 2
                y = start_y + i * (line_height + 12)
                draw.text((x, y), line, fill='black', font=font_small)
        else:
            # Single-line timestamp (ISO format)
            bbox = draw.textbbox((0, 0), timestamp, font=font_small)
            text_width = bbox[2] - bbox[0]
            x = (width - text_width) // 2
            # Position timestamp at bottom if there's main text, otherwise center
            if text:
                y = height - (bbox[3] - bbox[1]) - 20
            else:
                y = (height - (bbox[3] - bbox[1])) // 2
                
            draw.text((x, y), timestamp, fill='black', font=font_small)
        
        return img
    
    def _get_font(self, size):
        """Get system font or fallback to default"""
        font_paths = [
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Arial.ttf',
            '/Library/Fonts/Arial.ttf'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        
        return ImageFont.load_default()
    
    async def print_label_async(self, text="", timestamp_format="iso8601"):
        """Print a timestamped label"""
        printer = None
        try:
            # Process the input text (extract/add numbers if present)
            processed_text = self.process_text_input(text)
            
            logger.info(f"Starting print job - input: '{text}', processed: '{processed_text}', format: '{timestamp_format}'")
            
            # Create the label image with processed text
            img = self.create_timestamped_label(processed_text, timestamp_format)
            
            # Connect to printer and print
            device = await find_device(self.printer_model)
            printer = PrinterClient(device)
            
            if await printer.connect():
                logger.info(f"Connected to {device.name}")
                await printer.print_image(img, density=3, quantity=1)
                logger.info("Print job completed successfully")
                return {"status": "success", "message": f"Label printed: '{processed_text}' (from input: '{text}')"}
            else:
                logger.error("Failed to connect to printer")
                return {"status": "error", "message": "Failed to connect to printer"}
                
        except Exception as e:
            logger.error(f"Print job failed: {e}")
            return {"status": "error", "message": str(e)}
        finally:
            # Always try to disconnect, but don't let it crash the whole operation
            if printer:
                try:
                    await asyncio.wait_for(printer.disconnect(), timeout=2.0)
                except Exception as disconnect_error:
                    logger.warning(f"Error during disconnect: {disconnect_error}")
    
    def print_label(self, text="", timestamp_format="iso8601"):
        """Synchronous wrapper for async print function"""
        import threading
        import time
        
        result = {"status": "error", "message": "Unknown error"}
        
        def run_async():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result.update(loop.run_until_complete(self.print_label_async(text, timestamp_format)))
            except Exception as e:
                result.update({"status": "error", "message": str(e)})
            finally:
                # Give a moment for any pending callbacks before closing
                time.sleep(0.5)
                try:
                    # Cancel any remaining tasks
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                except Exception:
                    pass
                finally:
                    loop.close()
        
        thread = threading.Thread(target=run_async)
        thread.start()
        thread.join(timeout=60)  # 60 second timeout
        
        if thread.is_alive():
            return {"status": "error", "message": "Print job timed out"}
        
        return result

# Global printer instance and job tracking
printer = LabelPrinter()
print_queue = []  # Simple list to track recent jobs
max_queue_size = 10  # Keep last 10 jobs

@app.route('/print', methods=['POST'])
def print_label():
    """API endpoint to print a label"""
    try:
        # Get text and timestamp format from JSON body or form data
        if request.is_json:
            data = request.get_json()
            text = data.get('text', '') if data else ''
            timestamp_format = data.get('timestamp_format', 'iso8601') if data else 'iso8601'
        else:
            text = request.form.get('text', '')
            timestamp_format = request.form.get('timestamp_format', 'iso8601')
        
        # Validate timestamp format
        if timestamp_format not in ['iso8601', 'friendly']:
            return jsonify({"status": "error", "message": "timestamp_format must be 'iso8601' or 'friendly'"}), 400
        
        logger.info(f"Received print request with text: '{text}', format: '{timestamp_format}'")
        
        # Process text and create job entry
        processed_text = printer.process_text_input(text)
        job_id = datetime.now().strftime("%H:%M:%S")
        
        job_entry = {
            "id": job_id,
            "input": text,
            "processed": processed_text,
            "format": timestamp_format,
            "status": "printing",
            "timestamp": datetime.now().isoformat()
        }
        
        # Add to queue (keep only recent jobs)
        print_queue.append(job_entry)
        if len(print_queue) > max_queue_size:
            print_queue.pop(0)
        
        # Start print job in background thread and return immediately
        def background_print():
            try:
                result = printer.print_label(text, timestamp_format)
                job_entry["status"] = "completed" if result["status"] == "success" else "failed"
                logger.info(f"Background print completed: {result}")
            except Exception as e:
                job_entry["status"] = "failed"
                job_entry["error"] = str(e)
                logger.error(f"Background print failed: {e}")
        
        thread = threading.Thread(target=background_print, daemon=True)
        thread.start()
        
        # Return immediate success response
        return jsonify({
            "status": "success", 
            "message": f"Print job {job_id} queued: '{processed_text}'",
            "job_id": job_id,
            "processed_text": processed_text,
            "timestamp_format": timestamp_format
        })
        
    except Exception as e:
        logger.error(f"API error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/status', methods=['GET'])
def status():
    """Health check endpoint"""
    return jsonify({"status": "online", "timestamp": datetime.now().isoformat()})

@app.route('/queue', methods=['GET'])
def queue_status():
    """Print queue status (lpq equivalent)"""
    if not print_queue:
        return jsonify({
            "status": "empty",
            "message": "No print jobs in queue",
            "jobs": []
        })
    
    return jsonify({
        "status": "active",
        "total_jobs": len(print_queue),
        "jobs": print_queue
    })

@app.route('/', methods=['GET'])
def home():
    """Simple home page with usage instructions"""
    html = """
    <html>
    <head><title>Label Printer API</title></head>
    <body>
    <h1>Label Printer API</h1>
    <p>A modern take on the classic Unix print system (lpr/lpq) for Bluetooth label printers!</p>
    <p>Send POST requests to <code>/print</code> with optional text parameter.</p>
    
    <h3>Test Form:</h3>
    <form method="post" action="/print">
        <input type="text" name="text" placeholder="Enter label text (optional)"><br><br>
        <label>Timestamp Format:</label><br>
        <input type="radio" name="timestamp_format" value="iso8601" checked> ISO8601 (2025-10-16 15:16:04)<br>
        <input type="radio" name="timestamp_format" value="friendly"> Friendly (Thu 16 Oct<br>11:16 PM)<br><br>
        <button type="submit">Print Label</button>
    </form>
    
    <h3>API Usage:</h3>
    <pre>
    # ISO8601 format (default)
    curl -X POST http://localhost:8080/print \\
         -H "Content-Type: application/json" \\
         -d '{"text": "50mL"}'
    
    # Friendly format
    curl -X POST http://localhost:8080/print \\
         -H "Content-Type: application/json" \\
         -d '{"text": "50mL", "timestamp_format": "friendly"}'
    </pre>
    
    <p><a href="/queue">📋 View Print Queue (lpq)</a> | <a href="/status">✅ Server Status</a></p>
    </body>
    </html>
    """
    return html

if __name__ == '__main__':
    print("Starting Label Printer API server...")
    print("Access at: http://localhost:8080")
    print("API endpoint: POST /print with optional 'text' parameter")
    app.run(host='0.0.0.0', port=8080, debug=True)
