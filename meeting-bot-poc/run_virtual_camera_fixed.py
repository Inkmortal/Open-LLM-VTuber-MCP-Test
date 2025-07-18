#!/usr/bin/env python3
"""
Run VTuber with virtual camera - Fixed version
Addresses JavaScript context isolation issues
"""
import asyncio
import os
import base64
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

async def main():
    print("=== VTuber Virtual Camera Service (Fixed) ===")
    print(f"VTuber URL: {VTUBER_URL}")
    
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
        
        # Position VTuber window
        await vtuber_page.evaluate("window.moveTo(0, 0)")
        
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
                '--use-fake-ui-for-media-stream'
            ]
        )
        
        demo_page = await demo_browser.new_page()
        
        # Create demo page with better frame handling
        demo_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo (Fixed)</title>
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
            max-width: 680px;
            margin: 0 auto;
        }
        video { 
            width: 640px; 
            height: 480px; 
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
        #status {
            margin-top: 20px;
            padding: 15px;
            background: #e8f5e9;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>VTuber Virtual Camera (Fixed)</h1>
        <p>Streaming VTuber through virtual camera with proper context handling.</p>
        
        <video id="virtualVideo" autoplay muted playsinline></video>
        
        <button onclick="startCamera()">Start Virtual Camera</button>
        <button onclick="stopCamera()">Stop Camera</button>
        
        <div id="status">Initializing...</div>
    </div>
    
    <!-- Hidden elements for virtual camera -->
    <canvas id="virtualCanvas" width="640" height="480" style="display:none;"></canvas>
    
    <script>
        let stream = null;
        let virtualTrack = null;
        let frameCount = 0;
        let lastUpdate = Date.now();
        
        // Initialize virtual camera
        const canvas = document.getElementById('virtualCanvas');
        const ctx = canvas.getContext('2d', { alpha: false });
        
        // Initial pattern
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(0, 0, 640, 480);
        ctx.fillStyle = '#4CAF50';
        ctx.font = 'bold 30px Arial';
        ctx.fillText('Waiting for VTuber...', 180, 240);
        
        // Create stream from canvas
        const virtualStream = canvas.captureStream(30);
        virtualTrack = virtualStream.getVideoTracks()[0];
        
        // Store original getUserMedia
        const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        
        // Override getUserMedia
        navigator.mediaDevices.getUserMedia = async function(constraints) {
            console.log('[Virtual Camera] getUserMedia called with:', constraints);
            if (constraints.video && virtualTrack && virtualTrack.readyState === 'live') {
                console.log('[Virtual Camera] Returning virtual stream');
                const stream = new MediaStream();
                stream.addTrack(virtualTrack.clone());
                return stream;
            }
            return originalGetUserMedia(constraints);
        };
        
        // Expose frame update method using exposeFunction approach
        window.__frameQueue = [];
        window.__isProcessing = false;
        
        // Process frames from queue
        async function processFrameQueue() {
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
                    updateStatus(`Streaming active\\nFrames: ${frameCount}\\nFPS: ${fps}`);
                    frameCount = 0;
                    lastUpdate = now;
                }
                
                window.__isProcessing = false;
                // Process next frame if available
                if (window.__frameQueue.length > 0) {
                    requestAnimationFrame(processFrameQueue);
                }
            };
            img.onerror = () => {
                console.error('[Virtual Camera] Failed to load frame');
                window.__isProcessing = false;
            };
            img.src = frameData;
        }
        
        // Method to add frames to queue
        window.__addFrame = function(frameData) {
            // Limit queue size to prevent memory issues
            if (window.__frameQueue.length < 5) {
                window.__frameQueue.push(frameData);
                processFrameQueue();
            }
            return true;
        };
        
        async function startCamera() {
            try {
                updateStatus('Requesting camera access...');
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480 },
                    audio: false
                });
                
                document.getElementById('virtualVideo').srcObject = stream;
                updateStatus('✅ Virtual camera active!\\nShowing VTuber stream');
            } catch (err) {
                updateStatus('❌ Error: ' + err.message);
                console.error('[Virtual Camera] Error:', err);
            }
        }
        
        function stopCamera() {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
                stream = null;
                document.getElementById('virtualVideo').srcObject = null;
                updateStatus('Camera stopped');
            }
        }
        
        function updateStatus(msg) {
            document.getElementById('status').textContent = msg;
        }
        
        // Auto-start camera after page load
        window.addEventListener('load', () => {
            setTimeout(startCamera, 1000);
        });
        
        console.log('[Virtual Camera] Ready!');
        updateStatus('Virtual camera initialized\\nClick "Start Virtual Camera" or wait for auto-start');
    </script>
</body>
</html>
'''
        
        await demo_page.set_content(demo_html)
        print("✅ Demo page loaded")
        await demo_page.wait_for_load_state('domcontentloaded')
        
        # Position demo window
        await demo_page.evaluate("window.moveTo(700, 0)")
        
        # Wait for auto-start
        await asyncio.sleep(2)
        
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
                    # Capture VTuber frame with error handling
                    screenshot = await vtuber_page.screenshot(
                        type='jpeg',
                        quality=70,  # Reduced quality for better performance
                        clip={'x': 0, 'y': 0, 'width': 640, 'height': 480}
                    )
                    
                    # Validate screenshot
                    if not screenshot or len(screenshot) == 0:
                        print("⚠️  Empty screenshot received")
                        error_count += 1
                        if error_count > 10:
                            print("❌ Too many errors, exiting...")
                            break
                        continue
                    
                    # Convert to base64 data URL
                    frame_data = f"data:image/jpeg;base64,{base64.b64encode(screenshot).decode()}"
                    
                    # Send frame using exposed function
                    success = await demo_page.evaluate(f"window.__addFrame && window.__addFrame('{frame_data}')")
                    
                    if success:
                        frame_count += 1
                        error_count = 0  # Reset error count on success
                        
                        if frame_count % 30 == 0:
                            print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s)", end='', flush=True)
                    
                except Exception as e:
                    error_count += 1
                    if error_count % 10 == 0:
                        print(f"\n⚠️  Streaming error ({error_count}): {e}")
                    
                    if error_count > 30:
                        print("\n❌ Too many consecutive errors, stopping...")
                        break
                
                # Maintain target FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\n✅ Shutting down gracefully...")
        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
        finally:
            # Cleanup
            print("Cleaning up...")
            await demo_browser.close()
            await vtuber_browser.close()

if __name__ == "__main__":
    asyncio.run(main())