#!/usr/bin/env python3
"""
Run VTuber with virtual camera - HTTP server version
Serves demo page via HTTP to provide secure context for WebRTC
"""
import asyncio
import os
import base64
import http.server
import threading
import socketserver
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')
DEMO_PORT = 8080

# Demo HTML content
DEMO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo (HTTP)</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px;
            background: #f0f0f0;
        }
        .container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 600px;
            margin: 0 auto;
        }
        video { 
            width: 560px; 
            height: 420px; 
            background: #000;
            border-radius: 5px;
            display: block;
            margin: 20px 0;
        }
        button {
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            background: #4CAF50;
            color: white;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background: #45a049;
        }
        button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }
        #status {
            margin-top: 20px;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        .error {
            background: #ffebee !important;
            color: #c62828;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>VTuber Virtual Camera (HTTP)</h1>
        <p>Streaming VTuber through virtual camera with proper secure context</p>
        
        <video id="virtualVideo" autoplay muted playsinline></video>
        
        <button id="startBtn" onclick="startCamera()">Start Virtual Camera</button>
        <button id="stopBtn" onclick="stopCamera()" disabled>Stop Camera</button>
        
        <div id="status">Initializing...</div>
    </div>
    
    <!-- Hidden canvas for virtual camera -->
    <canvas id="virtualCanvas" width="640" height="480" style="display:none;"></canvas>
    
    <script>
        let stream = null;
        let virtualTrack = null;
        let frameCount = 0;
        let lastUpdate = Date.now();
        let isReady = false;
        
        function log(msg, isError = false) {
            const status = document.getElementById('status');
            const timestamp = new Date().toLocaleTimeString();
            const line = `[${timestamp}] ${msg}`;
            status.textContent = status.textContent + '\\n' + line;
            if (isError) status.classList.add('error');
            else status.classList.remove('error');
            console.log(line);
            // Auto-scroll to bottom
            status.scrollTop = status.scrollHeight;
        }
        
        // Initialize virtual camera
        function initializeVirtualCamera() {
            try {
                log('Checking browser APIs...');
                
                // Verify we're in a secure context
                if (!window.isSecureContext) {
                    log('⚠️ Not a secure context!', true);
                }
                
                // Check if browser APIs are available
                if (!navigator || !navigator.mediaDevices) {
                    log('❌ Media devices API not available!', true);
                    return;
                }
                
                log('✅ Media devices API available');
                
                // Get canvas and context
                const canvas = document.getElementById('virtualCanvas');
                const ctx = canvas.getContext('2d', { alpha: false });
                
                // Initial pattern
                ctx.fillStyle = '#1a1a1a';
                ctx.fillRect(0, 0, 640, 480);
                ctx.fillStyle = '#4CAF50';
                ctx.font = 'bold 24px Arial';
                ctx.fillText('VTuber Virtual Camera Ready', 140, 240);
                ctx.font = '16px Arial';
                ctx.fillText('Click "Start Virtual Camera" to begin', 180, 270);
                
                // Create stream from canvas
                const virtualStream = canvas.captureStream(30);
                virtualTrack = virtualStream.getVideoTracks()[0];
                
                if (!virtualTrack) {
                    log('❌ Failed to create virtual track', true);
                    return;
                }
                
                log(`✅ Virtual track created: ${virtualTrack.label}`);
                
                // Store original getUserMedia
                const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                
                // Override getUserMedia
                navigator.mediaDevices.getUserMedia = async function(constraints) {
                    log('getUserMedia called with: ' + JSON.stringify(constraints));
                    
                    if (constraints.video && virtualTrack && virtualTrack.readyState === 'live') {
                        log('Returning virtual camera stream');
                        const stream = new MediaStream();
                        stream.addTrack(virtualTrack.clone());
                        return stream;
                    }
                    
                    return originalGetUserMedia(constraints);
                };
                
                log('✅ getUserMedia override installed');
                
                // Frame update queue
                window.__frameQueue = [];
                window.__isProcessing = false;
                
                // Process frames from queue
                window.__processFrameQueue = async function() {
                    if (window.__isProcessing || window.__frameQueue.length === 0) return;
                    
                    window.__isProcessing = true;
                    const frameData = window.__frameQueue.shift();
                    
                    const img = new Image();
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0, 640, 480);
                        frameCount++;
                        
                        // Update status periodically
                        const now = Date.now();
                        if (now - lastUpdate > 1000) {
                            const fps = Math.round(frameCount / ((now - lastUpdate) / 1000));
                            log(`Streaming: ${frameCount} frames @ ${fps} FPS`);
                            frameCount = 0;
                            lastUpdate = now;
                        }
                        
                        window.__isProcessing = false;
                        // Process next frame if available
                        if (window.__frameQueue.length > 0) {
                            requestAnimationFrame(window.__processFrameQueue);
                        }
                    };
                    img.onerror = () => {
                        log('Failed to load frame', true);
                        window.__isProcessing = false;
                    };
                    img.src = frameData;
                };
                
                // Method to add frames to queue
                window.__addFrame = function(frameData) {
                    // Limit queue size to prevent memory issues
                    if (window.__frameQueue.length < 3) {
                        window.__frameQueue.push(frameData);
                        if (window.__processFrameQueue) {
                            window.__processFrameQueue();
                        }
                    }
                    return true;
                };
                
                isReady = true;
                log('✅ Virtual camera system ready!');
                document.getElementById('startBtn').disabled = false;
                
            } catch (err) {
                log('❌ Initialization error: ' + err.message, true);
            }
        }
        
        async function startCamera() {
            if (!isReady) {
                log('System not ready yet', true);
                return;
            }
            
            try {
                log('Requesting camera access...');
                document.getElementById('startBtn').disabled = true;
                
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480 },
                    audio: false
                });
                
                document.getElementById('virtualVideo').srcObject = stream;
                document.getElementById('stopBtn').disabled = false;
                log('✅ Virtual camera active! Showing VTuber stream');
                
            } catch (err) {
                log('❌ Camera error: ' + err.message, true);
                document.getElementById('startBtn').disabled = false;
            }
        }
        
        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
                document.getElementById('virtualVideo').srcObject = null;
                document.getElementById('startBtn').disabled = false;
                document.getElementById('stopBtn').disabled = true;
                log('Camera stopped');
            }
        }
        
        // Start initialization when page loads
        window.addEventListener('load', () => {
            log('Page loaded in secure context: ' + window.isSecureContext);
            log('Origin: ' + window.location.origin);
            setTimeout(initializeVirtualCamera, 100);
        });
        
        // Auto-start camera after initialization
        window.addEventListener('load', () => {
            setTimeout(() => {
                if (isReady && !stream) {
                    startCamera();
                }
            }, 2000);
        });
    </script>
</body>
</html>
'''

class DemoHTTPHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(DEMO_HTML.encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress HTTP server logs
        pass

def start_http_server():
    """Start HTTP server in background thread"""
    with socketserver.TCPServer(("", DEMO_PORT), DemoHTTPHandler) as httpd:
        print(f"Demo HTTP server running on port {DEMO_PORT}")
        httpd.serve_forever()

async def main():
    print("=== VTuber Virtual Camera Service (HTTP) ===")
    print(f"VTuber URL: {VTUBER_URL}")
    
    # Start HTTP server in background
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(1)
    
    async with async_playwright() as p:
        # Launch VTuber browser
        print("\nLaunching VTuber browser...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        vtuber_page = await vtuber_browser.new_page()
        
        # Add error handling for VTuber page load
        try:
            await vtuber_page.goto(VTUBER_URL, wait_until='networkidle', timeout=30000)
            await vtuber_page.set_viewport_size({"width": 640, "height": 480})
            print(f"✅ VTuber loaded at {VTUBER_URL}")
        except Exception as e:
            print(f"❌ Failed to load VTuber: {e}")
            await vtuber_browser.close()
            return
        
        # Position VTuber window on the left
        await vtuber_page.evaluate("if (window.moveTo) window.moveTo(0, 0)")
        
        # Wait for VTuber to initialize
        print("Waiting for VTuber to initialize...")
        await asyncio.sleep(5)
        
        # Launch demo browser
        print("\nLaunching demo browser...")
        demo_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',
                '--window-position=650,0',  # Position to the right
                '--window-size=640,600'
            ]
        )
        
        demo_page = await demo_browser.new_page()
        
        # Navigate to HTTP server
        demo_url = f"http://localhost:{DEMO_PORT}/"
        print(f"Loading demo page from {demo_url}")
        await demo_page.goto(demo_url)
        await demo_page.wait_for_load_state('domcontentloaded')
        print("✅ Demo page loaded via HTTP server")
        
        # Wait for initialization
        await asyncio.sleep(3)
        
        # Start streaming VTuber frames
        print("\n✅ Starting VTuber streaming...")
        frame_count = 0
        error_count = 0
        fps = 30
        frame_interval = 1.0 / fps
        
        try:
            while True:
                start_time = asyncio.get_event_loop().time()
                
                try:
                    # Capture VTuber frame
                    screenshot = await vtuber_page.screenshot(
                        type='jpeg',
                        quality=70,
                        clip={'x': 0, 'y': 0, 'width': 640, 'height': 480}
                    )
                    
                    if screenshot and len(screenshot) > 0:
                        # Convert to base64 data URL
                        frame_data = f"data:image/jpeg;base64,{base64.b64encode(screenshot).decode()}"
                        
                        # Send frame using exposed function
                        success = await demo_page.evaluate(f"""
                            if (window.__addFrame) {{
                                window.__addFrame('{frame_data}');
                                true;
                            }} else {{
                                false;
                            }}
                        """)
                        
                        if success:
                            frame_count += 1
                            error_count = 0
                            
                            if frame_count % 30 == 0:
                                print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s)", end='', flush=True)
                    
                except Exception as e:
                    error_count += 1
                    if error_count % 30 == 0:
                        print(f"\n⚠️  Stream error #{error_count}: {e}")
                
                # Maintain target FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\n✅ Shutting down...")
        finally:
            await demo_browser.close()
            await vtuber_browser.close()

if __name__ == "__main__":
    asyncio.run(main())