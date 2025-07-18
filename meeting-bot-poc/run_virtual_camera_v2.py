#!/usr/bin/env python3
"""
Run VTuber with virtual camera continuously - Simplified version
Keeps browsers open for VNC monitoring
"""
import asyncio
import os
import base64
from pathlib import Path
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

async def main():
    print("=== VTuber Virtual Camera Service V2 ===")
    print(f"VTuber URL: {VTUBER_URL}")
    
    async with async_playwright() as p:
        # Launch VTuber browser
        print("\nLaunching VTuber browser...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ]
        )
        
        vtuber_page = await vtuber_browser.new_page()
        await vtuber_page.goto(VTUBER_URL)
        await vtuber_page.set_viewport_size({"width": 640, "height": 480})
        print(f"✅ VTuber loaded at {VTUBER_URL}")
        
        # Position VTuber window on the left
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
        
        # Create a simple demo page with virtual camera
        demo_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo V2</title>
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
        }
        #vtuberFrame {
            position: absolute;
            left: -9999px;
            width: 640px;
            height: 480px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>VTuber Virtual Camera Demo V2</h1>
        <p>This demonstrates the VTuber being streamed through a virtual camera.</p>
        
        <video id="virtualVideo" autoplay muted></video>
        
        <button onclick="startCamera()">Start Virtual Camera</button>
        <button onclick="stopCamera()">Stop Camera</button>
        
        <div id="status">Ready to start virtual camera...</div>
    </div>
    
    <!-- Hidden canvas for virtual camera -->
    <canvas id="virtualCanvas" width="640" height="480" style="display:none;"></canvas>
    <img id="vtuberFrame" />
    
    <script>
        let stream = null;
        let virtualTrack = null;
        let animationId = null;
        
        // Create virtual camera
        const canvas = document.getElementById('virtualCanvas');
        const ctx = canvas.getContext('2d');
        const frameImg = document.getElementById('vtuberFrame');
        
        // Initial pattern
        ctx.fillStyle = '#1a1a1a';
        ctx.fillRect(0, 0, 640, 480);
        ctx.fillStyle = '#4CAF50';
        ctx.font = 'bold 30px Arial';
        ctx.fillText('Waiting for VTuber...', 180, 240);
        
        // Create stream from canvas
        const virtualStream = canvas.captureStream(30);
        virtualTrack = virtualStream.getVideoTracks()[0];
        
        // Override getUserMedia
        const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
        navigator.mediaDevices.getUserMedia = async function(constraints) {
            console.log('getUserMedia called with:', constraints);
            if (constraints.video && virtualTrack) {
                const stream = new MediaStream();
                stream.addTrack(virtualTrack.clone());
                return stream;
            }
            return originalGetUserMedia(constraints);
        };
        
        // Update canvas function
        window.updateVirtualCamera = function(frameData) {
            frameImg.src = frameData;
            frameImg.onload = () => {
                ctx.drawImage(frameImg, 0, 0, 640, 480);
            };
        };
        
        async function startCamera() {
            try {
                updateStatus('Requesting camera access...');
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { width: 640, height: 480 },
                    audio: false
                });
                
                document.getElementById('virtualVideo').srcObject = stream;
                updateStatus('✅ Virtual camera active! Showing VTuber stream.');
            } catch (err) {
                updateStatus('❌ Error: ' + err.message);
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
        
        console.log('Virtual camera ready!');
    </script>
</body>
</html>
'''
        
        await demo_page.set_content(demo_html)
        print("✅ Demo page loaded")
        await demo_page.wait_for_load_state('networkidle')
        
        # Position demo window on the right
        await demo_page.evaluate("window.moveTo(700, 0)")
        
        # Auto-start camera
        await asyncio.sleep(2)
        print("Starting virtual camera...")
        await demo_page.evaluate("startCamera()")
        
        # Start streaming VTuber frames
        print("\n✅ Starting continuous VTuber streaming...")
        frame_count = 0
        fps = 30
        frame_interval = 1.0 / fps
        
        try:
            while True:
                start_time = asyncio.get_event_loop().time()
                
                # Capture VTuber frame
                screenshot = await vtuber_page.screenshot(
                    type='jpeg',
                    quality=80,
                    clip={'x': 0, 'y': 0, 'width': 640, 'height': 480}
                )
                
                # Convert to base64 data URL
                frame_data = f"data:image/jpeg;base64,{base64.b64encode(screenshot).decode()}"
                
                # Update virtual camera
                try:
                    await demo_page.evaluate(f"window.updateVirtualCamera('{frame_data}')")
                    
                    frame_count += 1
                    if frame_count % 30 == 0:
                        print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s)", end='', flush=True)
                except Exception as e:
                    print(f"\nError updating virtual camera: {e}")
                
                # Maintain target FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        except Exception as e:
            print(f"\nError: {e}")
        finally:
            await demo_browser.close()
            await vtuber_browser.close()

if __name__ == "__main__":
    asyncio.run(main())