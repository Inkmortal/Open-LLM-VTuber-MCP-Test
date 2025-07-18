#!/usr/bin/env python3
"""
Stream VTuber using getDisplayMedia approach
This replaces the FFmpeg-based capture with browser's native screen capture
"""
import asyncio
import os
import json
from pathlib import Path
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

# HTML page that captures VTuber and provides it as a virtual camera source
CAPTURE_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>VTuber Virtual Camera Provider</title>
    <style>
        body { 
            margin: 0; 
            padding: 20px; 
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: #fff;
        }
        .status {
            position: fixed;
            top: 10px;
            right: 10px;
            padding: 10px;
            background: rgba(0,0,0,0.8);
            border-radius: 5px;
            font-size: 12px;
        }
        .capture-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
        }
        video {
            width: 640px;
            height: 480px;
            background: #000;
            border: 2px solid #333;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 5px;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
        .hidden { display: none; }
    </style>
</head>
<body>
    <div class="status" id="status">Initializing...</div>
    
    <div class="capture-container">
        <h1>VTuber Virtual Camera Provider</h1>
        <video id="captureVideo" autoplay muted></video>
        <button id="startBtn" onclick="startCapture()">Start VTuber Capture</button>
        <div id="info" class="hidden">
            <p>Stream ID: <span id="streamId"></span></p>
            <p>Tracks: <span id="trackInfo"></span></p>
        </div>
    </div>
    
    <script>
        let captureStream = null;
        
        async function startCapture() {
            const status = document.getElementById('status');
            const btn = document.getElementById('startBtn');
            
            try {
                btn.disabled = true;
                status.textContent = 'Requesting screen capture...';
                
                // Request display capture with audio
                captureStream = await navigator.mediaDevices.getDisplayMedia({
                    video: {
                        width: { ideal: 640 },
                        height: { ideal: 480 },
                        frameRate: { ideal: 30 }
                    },
                    audio: {
                        echoCancellation: false,
                        noiseSuppression: false,
                        autoGainControl: false
                    }
                });
                
                // Display the captured stream
                const video = document.getElementById('captureVideo');
                video.srcObject = captureStream;
                
                // Update UI
                status.textContent = '✅ Capturing VTuber';
                btn.textContent = 'Stop Capture';
                btn.onclick = stopCapture;
                btn.disabled = false;
                
                // Show stream info
                document.getElementById('info').classList.remove('hidden');
                document.getElementById('streamId').textContent = captureStream.id;
                
                const tracks = captureStream.getTracks();
                const trackInfo = tracks.map(t => `${t.kind}: ${t.label}`).join(', ');
                document.getElementById('trackInfo').textContent = trackInfo;
                
                // Handle stream end
                captureStream.getVideoTracks()[0].onended = () => {
                    stopCapture();
                };
                
                // Make stream available globally for other scripts
                window.vtuberStream = captureStream;
                
                // Notify that capture is ready
                window.dispatchEvent(new CustomEvent('vtuberCaptureReady', {
                    detail: { stream: captureStream }
                }));
                
            } catch (err) {
                status.textContent = '❌ Capture failed: ' + err.message;
                btn.disabled = false;
                console.error('Capture error:', err);
            }
        }
        
        function stopCapture() {
            if (captureStream) {
                captureStream.getTracks().forEach(track => track.stop());
                captureStream = null;
                window.vtuberStream = null;
            }
            
            const video = document.getElementById('captureVideo');
            video.srcObject = null;
            
            const btn = document.getElementById('startBtn');
            btn.textContent = 'Start VTuber Capture';
            btn.onclick = startCapture;
            btn.disabled = false;
            
            document.getElementById('status').textContent = 'Capture stopped';
            document.getElementById('info').classList.add('hidden');
        }
        
        // Auto-start capture after page load
        window.addEventListener('load', () => {
            setTimeout(() => {
                document.getElementById('status').textContent = 'Ready to capture';
                // Uncomment to auto-start:
                // startCapture();
            }, 1000);
        });
    </script>
</body>
</html>
'''

async def main():
    """Main function to provide VTuber as virtual camera using getDisplayMedia"""
    print(f"Starting VTuber Virtual Camera Provider")
    print(f"VTuber URL: {VTUBER_URL}")
    
    # Write capture HTML
    capture_html_path = Path('/tmp/vtuber_capture.html')
    capture_html_path.write_text(CAPTURE_HTML)
    
    # Start browsers
    async with async_playwright() as p:
        # First browser: Load VTuber
        print("\nLaunching VTuber browser...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        vtuber_page = await vtuber_browser.new_page()
        await vtuber_page.goto(VTUBER_URL)
        await vtuber_page.set_viewport_size({"width": 640, "height": 480})
        print(f"✅ VTuber loaded at {VTUBER_URL}")
        
        # Second browser: Capture provider
        print("\nLaunching capture provider browser...")
        capture_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--enable-usermedia-screen-capturing',
                '--auto-select-desktop-capture-source=Open LLM VTuber'
            ]
        )
        
        capture_context = await capture_browser.new_context(
            permissions=['camera', 'microphone']
        )
        capture_page = await capture_context.new_page()
        
        # Load capture page
        await capture_page.goto(f"file://{capture_html_path}")
        print("✅ Capture provider loaded")
        
        # Start capture automatically
        await asyncio.sleep(2)
        await capture_page.click('#startBtn')
        print("\n⚠️  Please select the VTuber window in the screen capture dialog")
        
        # Keep running
        print("\n✅ VTuber virtual camera provider is running")
        print("The captured stream is available for other applications to use")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                await asyncio.sleep(1)
                
                # Check if capture is still active
                is_capturing = await capture_page.evaluate('''() => {
                    return window.vtuberStream && window.vtuberStream.active;
                }''')
                
                if not is_capturing:
                    print("⚠️  Capture stopped, waiting for restart...")
                    
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            await capture_browser.close()
            await vtuber_browser.close()

if __name__ == "__main__":
    asyncio.run(main())