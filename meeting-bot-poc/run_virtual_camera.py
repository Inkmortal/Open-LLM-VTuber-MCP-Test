#!/usr/bin/env python3
"""
Run VTuber with virtual camera continuously
Keeps browsers open for VNC monitoring
"""
import asyncio
import os
import base64
from pathlib import Path
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

# Virtual camera injection JavaScript
VIRTUAL_CAMERA_INJECTION = '''
(() => {
    console.log('[VirtualCamera] Initializing virtual camera system...');
    
    // Create canvas for virtual camera
    const canvas = document.createElement('canvas');
    canvas.width = 640;
    canvas.height = 480;
    canvas.style.display = 'none';
    document.body.appendChild(canvas);
    const ctx = canvas.getContext('2d');
    
    // Initial pattern
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, 640, 480);
    ctx.fillStyle = '#4CAF50';
    ctx.font = 'bold 30px Arial';
    ctx.fillText('VTuber Virtual Camera', 140, 240);
    
    // Create MediaStream from canvas
    const virtualVideoStream = canvas.captureStream(30);
    const virtualVideoTrack = virtualVideoStream.getVideoTracks()[0];
    
    // Make track globally accessible
    window.__virtualVideoTrack = virtualVideoTrack;
    console.log('[VirtualCamera] Virtual video track created:', virtualVideoTrack);
    console.log('[VirtualCamera] Track state:', virtualVideoTrack.readyState);
    
    // Store original getUserMedia - wait for it to be available
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.log('[VirtualCamera] Waiting for getUserMedia to be available...');
        // If getUserMedia isn't available yet, we'll override it when it becomes available
        let checkInterval = setInterval(() => {
            if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
                clearInterval(checkInterval);
                const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                navigator.mediaDevices.getUserMedia = async function(constraints) {
                    console.log('[VirtualCamera] getUserMedia called with:', constraints);
                    if (constraints.video) {
                        if (window.__virtualVideoTrack && window.__virtualVideoTrack.readyState === 'live') {
                            console.log('[VirtualCamera] Returning virtual video stream');
                            const stream = new MediaStream();
                            stream.addTrack(window.__virtualVideoTrack.clone());
                            return stream;
                        } else {
                            console.error('[VirtualCamera] Virtual video track not available or not live!');
                            throw new Error('Virtual camera not ready');
                        }
                    }
                    return originalGetUserMedia(constraints);
                };
                console.log('[VirtualCamera] getUserMedia override installed');
            }
        }, 100);
        return;
    }
    
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    
    // Override getUserMedia
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        console.log('[VirtualCamera] getUserMedia called with:', constraints);
        
        if (constraints.video) {
            if (window.__virtualVideoTrack && window.__virtualVideoTrack.readyState === 'live') {
                console.log('[VirtualCamera] Returning virtual video stream');
                const stream = new MediaStream();
                stream.addTrack(window.__virtualVideoTrack.clone());
                return stream;
            } else {
                console.error('[VirtualCamera] Virtual video track not available or not live!');
                throw new Error('Virtual camera not ready');
            }
        }
        
        return originalGetUserMedia(constraints);
    };
    
    // Function to update canvas with VTuber frames
    window.__updateVirtualCamera = function(frameData) {
        return new Promise((resolve, reject) => {
            console.log('[VirtualCamera] __updateVirtualCamera called, data length:', frameData.length);
            const img = new Image();
            img.onload = () => {
                ctx.drawImage(img, 0, 0, 640, 480);
                console.log('[VirtualCamera] Canvas updated with new frame');
                resolve();
            };
            img.onerror = (err) => {
                console.error('[VirtualCamera] Failed to load frame:', err);
                reject(err);
            };
            img.src = frameData;
        });
    };
    
    // Check status function for debugging
    window.__getVirtualCameraStatus = function() {
        return {
            canvasExists: !!canvas,
            trackExists: !!window.__virtualVideoTrack,
            trackState: window.__virtualVideoTrack ? window.__virtualVideoTrack.readyState : 'no track',
            updateFunctionExists: typeof window.__updateVirtualCamera === 'function'
        };
    };
    
    console.log('[VirtualCamera] Virtual camera ready!');
    console.log('[VirtualCamera] Status:', window.__getVirtualCameraStatus());
})();
'''

async def main():
    print("=== VTuber Virtual Camera Service ===")
    print(f"VTuber URL: {VTUBER_URL}")
    
    async with async_playwright() as p:
        # Launch VTuber browser
        print("\nLaunching VTuber browser...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage'
                # Let Playwright manage window size based on viewport
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
        
        # Launch test/demo browser
        print("\nLaunching demo browser with virtual camera...")
        demo_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream'
                # Let Playwright manage window size
            ]
        )
        
        # Create context with permissions and init script
        demo_context = await demo_browser.new_context(
            permissions=['camera', 'microphone']
        )
        
        # Add init script to context before creating page
        await demo_context.add_init_script(VIRTUAL_CAMERA_INJECTION)
        
        # Now create page - script will be injected automatically
        demo_page = await demo_context.new_page()
        
        # Simple demo HTML
        demo_html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo</title>
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
    </style>
</head>
<body>
    <div class="container">
        <h1>VTuber Virtual Camera Demo</h1>
        <p>This demonstrates the VTuber being streamed through a virtual camera.</p>
        
        <video id="virtualVideo" autoplay muted></video>
        
        <button onclick="startCamera()">Start Virtual Camera</button>
        <button onclick="stopCamera()">Stop Camera</button>
        
        <div id="status">Ready to start virtual camera...</div>
    </div>
    
    <script>
        let stream = null;
        
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
        
        // Auto-start camera
        setTimeout(startCamera, 1000);
    </script>
</body>
</html>
'''
        
        # Load demo page using set_content instead of data URL
        await demo_page.set_content(demo_html)
        print("✅ Demo page loaded")
        
        # Wait for page to be ready
        await demo_page.wait_for_load_state('networkidle')
        await asyncio.sleep(1)
        
        # Re-inject the virtual camera code after setting content
        # This ensures it's available in the page context
        try:
            await demo_page.evaluate(VIRTUAL_CAMERA_INJECTION)
            print("✅ Virtual camera injection added to demo page")
        except Exception as e:
            print(f"⚠️  Initial injection failed: {e}")
            print("   This is expected - the context already has the injection from add_init_script")
        
        # Position demo window on the right
        await demo_page.evaluate("window.moveTo(700, 0)")
        
        # Verify injection worked
        status = await demo_page.evaluate("window.__getVirtualCameraStatus ? window.__getVirtualCameraStatus() : null")
        print(f"Virtual camera status: {status}")
        
        # Auto-click start camera button after a short delay
        await asyncio.sleep(2)
        print("Clicking 'Start Virtual Camera' button...")
        await demo_page.click('button[onclick="startCamera()"]')
        
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
                
                # Update virtual camera with error handling
                try:
                    # First check if the injection is still there
                    has_function = await demo_page.evaluate("typeof window.__updateVirtualCamera === 'function'")
                    
                    if not has_function:
                        # Re-inject if needed
                        await demo_page.evaluate(VIRTUAL_CAMERA_INJECTION)
                        await asyncio.sleep(0.1)
                    
                    # Now update the frame
                    result = await demo_page.evaluate(f"""
                        (async () => {{
                            if (typeof window.__updateVirtualCamera === 'function') {{
                                await window.__updateVirtualCamera('{frame_data}');
                                return 'success';
                            }} else {{
                                console.error('[Main] __updateVirtualCamera not found after re-injection!');
                                return 'function not found';
                            }}
                        }})()
                    """)
                    
                    if frame_count == 1 or frame_count % 30 == 0:
                        print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s) - Update: {result}", end='', flush=True)
                except Exception as e:
                    print(f"\nError updating virtual camera: {e}")
                
                frame_count += 1
                
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