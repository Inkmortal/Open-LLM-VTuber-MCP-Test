#!/usr/bin/env python3
"""
Stream VTuber using canvas-based virtual camera approach
This works by injecting a virtual camera at the browser level
"""
import asyncio
import os
import base64
from pathlib import Path
from playwright.async_api import async_playwright

# Frontend is now available!
VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

# JavaScript code to inject virtual camera
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
    
    // Fill with test pattern initially
    ctx.fillStyle = '#000';
    ctx.fillRect(0, 0, 640, 480);
    ctx.fillStyle = '#fff';
    ctx.font = '30px Arial';
    ctx.fillText('Virtual Camera Ready', 150, 240);
    
    // Create MediaStream from canvas
    const virtualVideoStream = canvas.captureStream(30);
    const virtualVideoTrack = virtualVideoStream.getVideoTracks()[0];
    
    console.log('[VirtualCamera] Created virtual video track:', virtualVideoTrack);
    
    // Store original getUserMedia
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    const originalEnumerateDevices = navigator.mediaDevices.enumerateDevices.bind(navigator.mediaDevices);
    
    // Create virtual audio context for audio stream
    const audioContext = new AudioContext();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    const destination = audioContext.createMediaStreamDestination();
    
    oscillator.connect(gainNode);
    gainNode.connect(destination);
    gainNode.gain.value = 0; // Start muted
    oscillator.start();
    
    const virtualAudioStream = destination.stream;
    const virtualAudioTrack = virtualAudioStream.getAudioTracks()[0];
    
    // Override enumerateDevices to include our virtual camera
    navigator.mediaDevices.enumerateDevices = async function() {
        const devices = await originalEnumerateDevices();
        
        // Add virtual camera to device list
        devices.push({
            deviceId: 'virtual-vtuber-camera',
            groupId: 'virtual-group',
            kind: 'videoinput',
            label: 'VTuber Virtual Camera'
        });
        
        devices.push({
            deviceId: 'virtual-vtuber-audio',
            groupId: 'virtual-group',
            kind: 'audioinput',
            label: 'VTuber Virtual Audio'
        });
        
        console.log('[VirtualCamera] Device list with virtual devices:', devices);
        return devices;
    };
    
    // Override getUserMedia
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        console.log('[VirtualCamera] getUserMedia called with constraints:', constraints);
        
        if (constraints.video) {
            console.log('[VirtualCamera] Returning virtual video stream');
            
            // Create new MediaStream with our tracks
            const stream = new MediaStream();
            
            // Clone tracks to avoid issues with multiple consumers
            stream.addTrack(virtualVideoTrack.clone());
            
            if (constraints.audio) {
                stream.addTrack(virtualAudioTrack.clone());
            }
            
            return stream;
        }
        
        // For audio-only requests, use original
        return originalGetUserMedia(constraints);
    };
    
    // Function to update canvas with VTuber frames
    window.__updateVirtualCamera = function(frameData) {
        return new Promise((resolve) => {
            const img = new Image();
            img.onload = () => {
                ctx.drawImage(img, 0, 0, 640, 480);
                resolve();
            };
            img.onerror = () => {
                console.error('[VirtualCamera] Failed to load frame');
                resolve();
            };
            img.src = frameData;
        });
    };
    
    // Function to update virtual audio
    window.__updateVirtualAudio = function(volume) {
        gainNode.gain.value = volume;
    };
    
    // Function to check virtual camera status
    window.__getVirtualCameraStatus = function() {
        return {
            videoActive: virtualVideoTrack.readyState === 'live',
            audioActive: virtualAudioTrack.readyState === 'live',
            canvas: {
                width: canvas.width,
                height: canvas.height
            }
        };
    };
    
    console.log('[VirtualCamera] Virtual camera system initialized successfully');
})();
'''

async def main():
    """Main function to provide VTuber as virtual camera using canvas injection"""
    print(f"Starting VTuber Virtual Camera Provider (Canvas-based)")
    print(f"VTuber URL: {VTUBER_URL}")
    
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
        
        # Wait for VTuber to fully load
        await asyncio.sleep(3)
        
        # Second browser: Test browser with virtual camera
        print("\nLaunching test browser with virtual camera...")
        test_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',  # Auto-accept camera prompts
            ]
        )
        
        # Create context with init script
        test_context = await test_browser.new_context(
            permissions=['camera', 'microphone']
        )
        
        # Add init script to context (not page)
        await test_context.add_init_script(VIRTUAL_CAMERA_INJECTION)
        
        # Now create page - script will be injected automatically
        test_page = await test_context.new_page()
        
        # Create test page HTML
        test_html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Test</title>
    <style>
        body { 
            margin: 20px; 
            font-family: Arial, sans-serif;
            background: #f0f0f0;
        }
        .container { 
            display: flex; 
            gap: 20px; 
            flex-wrap: wrap;
        }
        .video-container {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        video { 
            width: 640px; 
            height: 480px; 
            background: #000;
            border-radius: 5px;
        }
        button {
            margin: 10px 0;
            padding: 10px 20px;
            font-size: 16px;
            border: none;
            border-radius: 5px;
            background: #4CAF50;
            color: white;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
        #status {
            margin-top: 10px;
            padding: 10px;
            background: #e0e0e0;
            border-radius: 5px;
            font-family: monospace;
            white-space: pre-wrap;
        }
    </style>
</head>
<body>
    <h1>VTuber Virtual Camera Test</h1>
    
    <div class="container">
        <div class="video-container">
            <h2>Virtual Camera Output</h2>
            <video id="virtualVideo" autoplay muted></video>
            <br>
            <button onclick="startVirtualCamera()">Start Virtual Camera</button>
            <button onclick="stopVirtualCamera()">Stop Virtual Camera</button>
            <button onclick="listDevices()">List Devices</button>
        </div>
    </div>
    
    <div id="status">Ready to test virtual camera...</div>
    
    <script>
        let currentStream = null;
        
        async function startVirtualCamera() {
            try {
                updateStatus('Requesting camera access...');
                
                // Request video with virtual camera
                currentStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: 640,
                        height: 480
                    },
                    audio: true
                });
                
                document.getElementById('virtualVideo').srcObject = currentStream;
                
                const tracks = currentStream.getTracks();
                const trackInfo = tracks.map(t => `${t.kind}: ${t.label} (${t.readyState})`).join('\\n');
                
                updateStatus(`✅ Virtual camera active!\\nTracks:\\n${trackInfo}`);
                
            } catch (err) {
                updateStatus(`❌ Error: ${err.message}`);
                console.error('Camera error:', err);
            }
        }
        
        function stopVirtualCamera() {
            if (currentStream) {
                currentStream.getTracks().forEach(track => track.stop());
                currentStream = null;
                document.getElementById('virtualVideo').srcObject = null;
                updateStatus('Camera stopped');
            }
        }
        
        async function listDevices() {
            try {
                const devices = await navigator.mediaDevices.enumerateDevices();
                const deviceList = devices
                    .filter(d => d.kind === 'videoinput' || d.kind === 'audioinput')
                    .map(d => `${d.kind}: ${d.label || d.deviceId}`)
                    .join('\\n');
                
                updateStatus(`Available devices:\\n${deviceList}`);
            } catch (err) {
                updateStatus(`❌ Error listing devices: ${err.message}`);
            }
        }
        
        function updateStatus(message) {
            const status = document.getElementById('status');
            const timestamp = new Date().toLocaleTimeString();
            status.textContent = `[${timestamp}] ${message}`;
        }
        
        // Check virtual camera status on load
        window.addEventListener('load', () => {
            if (window.__getVirtualCameraStatus) {
                const status = window.__getVirtualCameraStatus();
                updateStatus(`Virtual camera initialized: ${JSON.stringify(status, null, 2)}`);
            }
        });
    </script>
</body>
</html>
'''
        
        # Write test HTML
        test_html_path = Path('/tmp/test_virtual_camera.html')
        test_html_path.write_text(test_html_content)
        
        # Navigate to test page
        await test_page.goto(f"file://{test_html_path}")
        print("✅ Test page loaded with virtual camera")
        
        # Wait and verify injection
        await asyncio.sleep(2)
        
        injection_check = await test_page.evaluate('''() => {
            return {
                hasUpdateFunction: typeof window.__updateVirtualCamera === 'function',
                hasStatusFunction: typeof window.__getVirtualCameraStatus === 'function'
            };
        }''')
        
        print(f"Injection check: {injection_check}")
        
        if not injection_check['hasUpdateFunction']:
            print("❌ Virtual camera injection failed, trying direct injection...")
            await test_page.evaluate(VIRTUAL_CAMERA_INJECTION)
            await asyncio.sleep(1)
        
        # Start streaming VTuber frames to virtual camera
        print("\n✅ Starting VTuber frame capture...")
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
                await test_page.evaluate(f"window.__updateVirtualCamera('{frame_data}')")
                
                frame_count += 1
                if frame_count % fps == 0:
                    print(f"\rStreaming: {frame_count} frames captured ({frame_count // fps}s)", end='', flush=True)
                
                # Maintain target FPS
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n\nShutting down...")
        finally:
            await test_browser.close()
            await vtuber_browser.close()

if __name__ == "__main__":
    asyncio.run(main())