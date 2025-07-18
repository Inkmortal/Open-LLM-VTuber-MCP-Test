#!/usr/bin/env python3
"""
Complete audio/video pipeline test without joining a meeting
Tests that VTuber audio and video flow through virtual channels
Using canvas-based virtual camera injection
"""
import asyncio
import subprocess
import os
import sys
import base64
from pathlib import Path
from playwright.async_api import async_playwright
import json

# Configuration
# Frontend is now available!
VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')
PULSE_SINK = 'vtuber_sink'
PULSE_SOURCE = 'vtuber_source'

class AVPipelineTest:
    def __init__(self):
        self.processes = []
        
    async def setup_audio(self):
        """Setup PulseAudio virtual devices"""
        print("Setting up audio devices...")
        
        # Check/create virtual sink
        result = subprocess.run(['pactl', 'list', 'sinks'], capture_output=True, text=True)
        if PULSE_SINK not in result.stdout:
            subprocess.run([
                'pactl', 'load-module', 'module-null-sink',
                f'sink_name={PULSE_SINK}',
                'sink_properties=device.description="VTuber_Audio"'
            ])
            print(f"✅ Created virtual sink: {PULSE_SINK}")
        
        # Check/create virtual source
        result = subprocess.run(['pactl', 'list', 'sources'], capture_output=True, text=True)
        if PULSE_SOURCE not in result.stdout:
            subprocess.run([
                'pactl', 'load-module', 'module-virtual-source',
                f'source_name={PULSE_SOURCE}',
                f'master={PULSE_SINK}.monitor'
            ])
            print(f"✅ Created virtual source: {PULSE_SOURCE}")
    
    async def setup_video(self):
        """Setup video capture - using canvas-based virtual camera"""
        print("Setting up video capture...")
        print("✅ Will use canvas-based virtual camera injection")
    
    def get_virtual_camera_injection(self):
        """Get JavaScript code for virtual camera injection"""
        return '''
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
    ctx.fillStyle = '#1a1a1a';
    ctx.fillRect(0, 0, 640, 480);
    ctx.fillStyle = '#4CAF50';
    ctx.font = 'bold 30px Arial';
    ctx.fillText('VTuber Virtual Camera', 140, 240);
    
    // Create MediaStream from canvas
    const virtualVideoStream = canvas.captureStream(30);
    const virtualVideoTrack = virtualVideoStream.getVideoTracks()[0];
    
    // Store original getUserMedia
    const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
    
    // Override getUserMedia
    navigator.mediaDevices.getUserMedia = async function(constraints) {
        console.log('[VirtualCamera] getUserMedia called with:', constraints);
        
        if (constraints.video) {
            console.log('[VirtualCamera] Returning virtual video stream');
            const stream = new MediaStream();
            stream.addTrack(virtualVideoTrack.clone());
            
            if (constraints.audio && window.__virtualAudioTrack) {
                stream.addTrack(window.__virtualAudioTrack.clone());
            }
            
            return stream;
        }
        
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
    
    // Check status function
    window.__getVirtualCameraStatus = function() {
        return {
            videoActive: virtualVideoTrack.readyState === 'live',
            canvasSize: { width: canvas.width, height: canvas.height }
        };
    };
    
    console.log('[VirtualCamera] Virtual camera ready!');
})();
'''

    async def start_vtuber_capture(self):
        """Start capturing VTuber browser window using canvas injection"""
        print("\nStarting VTuber capture...")
        
        # Test HTML for virtual camera
        test_html_content = '''
<!DOCTYPE html>
<html>
<head>
    <title>VTuber Virtual Camera Test</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            margin: 20px;
            background: #f5f5f5;
        }
        .container { 
            display: flex; 
            gap: 20px; 
            flex-wrap: wrap;
        }
        .section { 
            background: white;
            border: 1px solid #ddd; 
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        video { 
            width: 640px; 
            height: 480px; 
            background: #000;
            border-radius: 4px;
        }
        button { 
            margin: 5px; 
            padding: 10px 20px;
            background: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
        button:hover {
            background: #45a049;
        }
        #status { 
            margin-top: 20px; 
            padding: 15px; 
            background: #e8f5e9;
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
            max-height: 200px;
            overflow-y: auto;
        }
        #audioMeter {
            margin-top: 10px;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
    </style>
</head>
<body>
    <h1>VTuber Virtual Camera Pipeline Test</h1>
    
    <div class="container">
        <div class="section">
            <h2>Virtual Camera Test</h2>
            <video id="virtualVideo" autoplay muted></video>
            <br>
            <button onclick="testVirtualCamera()">Test Virtual Camera</button>
            <button onclick="stopVirtualCamera()">Stop Camera</button>
            <br>
            <canvas id="audioMeter" width="640" height="60"></canvas>
        </div>
    </div>
    
    <div id="status">Initializing virtual camera system...</div>
    
    <script>
        let currentStream = null;
        
        async function testVirtualCamera() {
            try {
                updateStatus('Requesting virtual camera access...');
                
                // This will use our injected virtual camera
                currentStream = await navigator.mediaDevices.getUserMedia({
                    video: {
                        width: 640,
                        height: 480
                    },
                    audio: false
                });
                
                document.getElementById('virtualVideo').srcObject = currentStream;
                
                const tracks = currentStream.getTracks();
                const trackInfo = tracks.map(t => `${t.kind}: ${t.label} (${t.readyState})`).join('\\n');
                
                updateStatus(`✅ Virtual camera active!\\n\\nTracks:\\n${trackInfo}`);
                
                // Setup audio visualization if available
                if (currentStream.getAudioTracks().length > 0) {
                    setupAudioMeter(currentStream);
                }
                
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
                
                // Clear audio meter
                const canvas = document.getElementById('audioMeter');
                const ctx = canvas.getContext('2d');
                ctx.fillStyle = '#f0f0f0';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
            }
        }
        
        function setupAudioMeter(stream) {
            const audioTrack = stream.getAudioTracks()[0];
            if (!audioTrack) return;
            
            const audioContext = new AudioContext();
            const source = audioContext.createMediaStreamSource(stream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            
            source.connect(analyser);
            
            const canvas = document.getElementById('audioMeter');
            const ctx = canvas.getContext('2d');
            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            
            function draw() {
                if (!currentStream) return;
                
                analyser.getByteFrequencyData(dataArray);
                
                ctx.fillStyle = 'rgb(240, 240, 240)';
                ctx.fillRect(0, 0, canvas.width, canvas.height);
                
                const barWidth = (canvas.width / bufferLength) * 2.5;
                let barHeight;
                let x = 0;
                
                for (let i = 0; i < bufferLength; i++) {
                    barHeight = (dataArray[i] / 255) * canvas.height;
                    
                    // Green gradient
                    const greenValue = Math.floor((barHeight / canvas.height) * 255);
                    ctx.fillStyle = `rgb(${255 - greenValue}, ${greenValue + 100}, 50)`;
                    
                    ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
                    x += barWidth + 1;
                }
                
                requestAnimationFrame(draw);
            }
            
            draw();
            updateStatus(updateStatus.lastMessage + '\\n✅ Audio meter active');
        }
        
        function updateStatus(message) {
            const status = document.getElementById('status');
            const timestamp = new Date().toLocaleTimeString();
            status.textContent = `[${timestamp}] ${message}`;
            updateStatus.lastMessage = message;
        }
        
        // Check virtual camera status on load
        window.addEventListener('load', () => {
            setTimeout(() => {
                if (window.__getVirtualCameraStatus) {
                    const status = window.__getVirtualCameraStatus();
                    updateStatus(`Virtual camera ready!\\nStatus: ${JSON.stringify(status, null, 2)}`);
                } else {
                    updateStatus('⚠️ Virtual camera injection not detected');
                }
            }, 1000);
        });
    </script>
</body>
</html>
''';
        
        # Write test HTML
        test_html_path = Path('/tmp/test_virtual_camera.html')
        test_html_path.write_text(test_html_content)
        
        # Launch browser with VTuber
        async with async_playwright() as p:
            # First browser: VTuber display
            vtuber_browser = await p.chromium.launch(
                headless=False,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            
            vtuber_page = await vtuber_browser.new_page()
            await vtuber_page.goto(VTUBER_URL)
            print(f"✅ VTuber loaded at {VTUBER_URL}")
            
            # Position window for capture
            await vtuber_page.set_viewport_size({"width": 640, "height": 480})
            
            # Wait for VTuber to fully initialize
            print("Waiting for VTuber to fully initialize...")
            await asyncio.sleep(5)
            
            # Route browser audio to virtual sink
            self.route_browser_audio()
            
            # Second browser: Test browser with virtual camera injection
            print("\nLaunching test browser with virtual camera...")
            test_browser = await p.chromium.launch(
                headless=False,
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-fake-ui-for-media-stream',
                    '--window-size=640,600',
                    '--window-position=700,0'
                ]
            )
            
            # Create context with virtual camera injection
            test_context = await test_browser.new_context(
                permissions=['camera', 'microphone']
            )
            
            # Add init script to context before creating page
            await test_context.add_init_script(self.get_virtual_camera_injection())
            
            # Create page - script will be automatically injected
            test_page = await test_context.new_page()
            
            # Load test page
            await test_page.goto(f"file://{test_html_path}")
            print("✅ Test page loaded with virtual camera injection")
            
            # Wait for page to be fully loaded and check injection
            await asyncio.sleep(2)
            
            # Verify injection worked
            injection_check = await test_page.evaluate('''() => {
                return {
                    hasUpdateFunction: typeof window.__updateVirtualCamera === 'function',
                    hasStatusFunction: typeof window.__getVirtualCameraStatus === 'function',
                    hasGetUserMedia: typeof navigator.mediaDevices.getUserMedia === 'function'
                };
            }''')
            
            print(f"Injection check: {injection_check}")
            
            if not injection_check['hasUpdateFunction']:
                print("❌ Virtual camera injection failed!")
                # Try injecting again directly
                await test_page.evaluate(self.get_virtual_camera_injection())
                await asyncio.sleep(1)
            
            # Start streaming VTuber frames to virtual camera
            print("\nStarting VTuber frame streaming...")
            frame_count = 0
            test_start_time = asyncio.get_event_loop().time()
            
            # Click test button after a short delay
            await asyncio.sleep(1)
            await test_page.click('button[onclick="testVirtualCamera()"]')
            
            # Stream frames for testing
            print("\nStreaming VTuber to virtual camera...")
            for i in range(300):  # Stream for ~10 seconds at 30fps
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
                if frame_count % 30 == 0:
                    print(f"\rStreaming: {frame_count} frames ({frame_count // 30}s)", end='', flush=True)
                
                # Maintain 30 FPS
                await asyncio.sleep(1/30)
            
            # Check status
            print("\n\nChecking virtual camera status...")
            status = await test_page.evaluate('''() => {
                const video = document.getElementById('virtualVideo');
                const hasVideo = video && video.srcObject && video.srcObject.active;
                const status = window.__getVirtualCameraStatus ? window.__getVirtualCameraStatus() : null;
                return {
                    hasVideo,
                    status,
                    videoWidth: video ? video.videoWidth : 0,
                    videoHeight: video ? video.videoHeight : 0
                };
            }''')
            
            if status['hasVideo']:
                print(f"✅ Virtual camera test successful!")
                print(f"   Video dimensions: {status['videoWidth']}x{status['videoHeight']}")
                print(f"   Camera status: {status['status']}")
            else:
                print("❌ Virtual camera test failed")
            
            # Test microphone access
            await test_page.click('button[onclick="testMicrophone()"]')
            await asyncio.sleep(2)
            
            # Trigger some audio on VTuber
            print("\n\nTriggering VTuber audio test...")
            try:
                # Try to find and trigger TTS
                await vtuber_page.evaluate('''() => {
                    // Look for text input field
                    const inputs = document.querySelectorAll('input[type="text"], textarea');
                    for (const input of inputs) {
                        if (input && !input.disabled) {
                            input.value = "Hello, this is a test of the virtual camera audio pipeline.";
                            input.dispatchEvent(new Event('input', { bubbles: true }));
                            
                            // Try different submission methods
                            if (input.form) {
                                input.form.dispatchEvent(new Event('submit', { bubbles: true }));
                            } else {
                                input.dispatchEvent(new KeyboardEvent('keypress', { key: 'Enter', bubbles: true }));
                            }
                            console.log('Triggered TTS input');
                            return true;
                        }
                    }
                    return false;
                }''')
                print("✅ Attempted to trigger VTuber audio")
            except Exception as e:
                print(f"⚠️  Could not trigger audio: {e}")
            
            print("\n=== AUDIO/VIDEO PIPELINE TEST COMPLETE ===")
            print("\nWhat you should see:")
            print("1. VTuber browser window (source)")
            print("2. Test browser showing virtual camera feed")
            print("   - The video should show the VTuber avatar")
            print("   - Audio meter reacts if VTuber has audio")
            print("\nVirtual devices created:")
            print("- Video: Canvas-based virtual camera (browser-level injection)")
            print(f"- Audio: PulseAudio sink '{PULSE_SINK}' and source '{PULSE_SOURCE}'")
            print("\nThis approach works without:")
            print("- Kernel modules (v4l2loopback)")
            print("- FFmpeg pipes")
            print("- Manual window selection")
            print("\nPress Enter to close test...")
            
            await asyncio.get_event_loop().run_in_executor(None, input)
            
            # Cleanup
            await test_browser.close()
            await vtuber_browser.close()
    
    def route_browser_audio(self):
        """Route browser audio to virtual sink"""
        try:
            # Find browser sink inputs
            result = subprocess.run(['pactl', 'list', 'sink-inputs'], capture_output=True, text=True)
            
            for line in result.stdout.split('\n'):
                if 'Sink Input #' in line:
                    sink_id = line.split('#')[1].strip()
                elif 'application.name' in line and 'chrom' in line.lower():
                    # Move this sink input to our virtual sink
                    subprocess.run(['pactl', 'move-sink-input', sink_id, PULSE_SINK])
                    print(f"✅ Routed browser audio (sink input #{sink_id}) to {PULSE_SINK}")
                    break
        except Exception as e:
            print(f"⚠️  Could not route browser audio: {e}")
    
    async def run(self):
        """Run the complete test"""
        try:
            print("=== VTuber Audio/Video Pipeline Test ===\n")
            
            # Setup
            await self.setup_audio()
            await self.setup_video()
            
            # Run test
            await self.start_vtuber_capture()
            
        except Exception as e:
            print(f"\n❌ Test failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            # Cleanup processes
            for proc in self.processes:
                proc.terminate()

async def main():
    test = AVPipelineTest()
    await test.run()

if __name__ == "__main__":
    # Check if running in Docker
    if not os.environ.get('DISPLAY'):
        print("ERROR: DISPLAY not set. Are you running in Docker with X11?")
        sys.exit(1)
    
    asyncio.run(main())