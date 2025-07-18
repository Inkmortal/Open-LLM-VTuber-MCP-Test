#!/usr/bin/env python3
"""
Run VTuber with virtual camera - Hybrid approach
Combines Mesa environment variables with aggressive Chrome flags
"""
import asyncio
import os
import base64
import http.server
import threading
import socketserver
import subprocess
from playwright.async_api import async_playwright

# Set Mesa environment variables for software rendering
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '4.5'
os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '450'

# Additional environment variables
os.environ['DISPLAY'] = ':99'
os.environ['LIBGL_ALWAYS_INDIRECT'] = '0'  # Direct rendering
os.environ['DRI_PRIME'] = '0'

# Get Windows host IP
def get_host_ip():
    try:
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True)
        for line in result.stdout.split('\n'):
            if 'default' in line:
                return line.split()[2]
    except:
        pass
    return os.environ.get('HOST_IP', '172.23.144.1')

HOST_IP = get_host_ip()
DEMO_PORT = 8080

# Start a proxy
def start_proxy():
    """Simple proxy to forward localhost:12393 to Windows host"""
    import socket
    import select
    
    print(f"Starting proxy: localhost:12393 -> {HOST_IP}:12393")
    
    proxy_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_socket.bind(('127.0.0.1', 12393))
    proxy_socket.listen(5)
    
    while True:
        client, addr = proxy_socket.accept()
        
        try:
            remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote.connect((HOST_IP, 12393))
            
            client.setblocking(0)
            remote.setblocking(0)
            
            while True:
                ready_to_read, _, _ = select.select([client, remote], [], [], 0.1)
                
                if client in ready_to_read:
                    data = client.recv(4096)
                    if not data:
                        break
                    remote.sendall(data)
                
                if remote in ready_to_read:
                    data = remote.recv(4096)
                    if not data:
                        break
                    client.sendall(data)
                    
        except Exception as e:
            print(f"Proxy error: {e}")
        finally:
            client.close()
            if 'remote' in locals():
                remote.close()

# Demo HTML
DEMO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo (Hybrid)</title>
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
        <h1>VTuber Virtual Camera (Hybrid)</h1>
        <p>Streaming VTuber with hybrid rendering approach</p>
        
        <video id="virtualVideo" autoplay muted playsinline></video>
        
        <button id="startBtn" onclick="startCamera()">Start Virtual Camera</button>
        <button id="stopBtn" onclick="stopCamera()" disabled>Stop Camera</button>
        
        <div id="status">Initializing...</div>
    </div>
    
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
            status.scrollTop = status.scrollHeight;
        }
        
        function initializeVirtualCamera() {
            try {
                log('Checking browser APIs...');
                
                if (!navigator || !navigator.mediaDevices) {
                    log('❌ Media devices API not available!', true);
                    return;
                }
                
                log('✅ Media devices API available');
                
                const canvas = document.getElementById('virtualCanvas');
                const ctx = canvas.getContext('2d', { 
                    alpha: false,
                    desynchronized: true,
                    willReadFrequently: true
                });
                
                ctx.fillStyle = '#1a1a1a';
                ctx.fillRect(0, 0, 640, 480);
                ctx.fillStyle = '#4CAF50';
                ctx.font = 'bold 24px Arial';
                ctx.fillText('VTuber Virtual Camera Ready', 140, 240);
                ctx.font = '16px Arial';
                ctx.fillText('Click "Start Virtual Camera" to begin', 180, 270);
                
                const virtualStream = canvas.captureStream(30);
                virtualTrack = virtualStream.getVideoTracks()[0];
                
                if (!virtualTrack) {
                    log('❌ Failed to create virtual track', true);
                    return;
                }
                
                log(`✅ Virtual track created: ${virtualTrack.label}`);
                
                const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
                
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
                
                window.__frameQueue = [];
                window.__isProcessing = false;
                
                window.__processFrameQueue = async function() {
                    if (window.__isProcessing || window.__frameQueue.length === 0) return;
                    
                    window.__isProcessing = true;
                    const frameData = window.__frameQueue.shift();
                    
                    const img = new Image();
                    img.onload = () => {
                        ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, 640, 480);
                        frameCount++;
                        
                        const now = Date.now();
                        if (now - lastUpdate > 1000) {
                            const fps = Math.round(frameCount / ((now - lastUpdate) / 1000));
                            log(`Streaming: ${frameCount} frames @ ${fps} FPS`);
                            frameCount = 0;
                            lastUpdate = now;
                        }
                        
                        window.__isProcessing = false;
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
                
                window.__addFrame = function(frameData) {
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
        
        window.addEventListener('load', () => {
            log('Page loaded in secure context: ' + window.isSecureContext);
            log('Origin: ' + window.location.origin);
            setTimeout(initializeVirtualCamera, 100);
        });
        
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
        pass

def start_http_server():
    with socketserver.TCPServer(("", DEMO_PORT), DemoHTTPHandler) as httpd:
        print(f"Demo HTTP server running on port {DEMO_PORT}")
        httpd.serve_forever()

async def main():
    print("=== VTuber Virtual Camera Service (Hybrid) ===")
    print(f"Windows host IP: {HOST_IP}")
    print("Using hybrid approach: Mesa + Chrome flags")
    print(f"Mesa environment variables set:")
    print(f"  LIBGL_ALWAYS_SOFTWARE: {os.environ.get('LIBGL_ALWAYS_SOFTWARE')}")
    print(f"  GALLIUM_DRIVER: {os.environ.get('GALLIUM_DRIVER')}")
    print(f"  MESA_GL_VERSION_OVERRIDE: {os.environ.get('MESA_GL_VERSION_OVERRIDE')}")
    
    # Start proxy
    proxy_thread = threading.Thread(target=start_proxy, daemon=True)
    proxy_thread.start()
    
    # Start HTTP server
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    await asyncio.sleep(2)
    
    async with async_playwright() as p:
        # Launch with comprehensive flags for WebGL in containers
        print("\nLaunching VTuber browser with hybrid rendering...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                # Force software rendering through SwiftShader
                '--use-gl=swiftshader',
                '--use-angle=swiftshader-webgl',
                '--enable-unsafe-swiftshader',
                # Enable WebGL explicitly
                '--enable-webgl',
                '--enable-webgl2',
                # Override GPU detection
                '--ignore-gpu-blocklist',
                '--ignore-gpu-blacklist',
                '--disable-gpu-sandbox',
                '--disable-gpu-compositing',
                # Additional WebGL flags
                '--enable-unsafe-webgpu',
                '--enable-features=WebGL2ComputeContext',
                '--disable-features=VizDisplayCompositor',
                # Force software rasterization
                '--disable-accelerated-2d-canvas',
                '--disable-gpu-rasterization',
                # Override renderer
                '--override-use-software-gl-for-tests'
            ]
        )
        
        vtuber_page = await vtuber_browser.new_page()
        
        # Add console logging
        vtuber_page.on("console", lambda msg: print(f"[VTuber Console] {msg.text}"))
        vtuber_page.on("pageerror", lambda msg: print(f"[VTuber Error] {msg}"))
        
        try:
            vtuber_url = 'http://localhost:12393'
            print(f"Loading VTuber from {vtuber_url}")
            await vtuber_page.goto(vtuber_url, wait_until='networkidle', timeout=30000)
            await vtuber_page.set_viewport_size({"width": 1280, "height": 720})
            print(f"✅ VTuber page loaded")
            
            # Comprehensive WebGL check
            webgl_check = await vtuber_page.evaluate('''() => {
                const results = {
                    webgl1: false,
                    webgl2: false,
                    renderer: 'unknown',
                    vendor: 'unknown',
                    version: 'unknown',
                    extensions: []
                };
                
                // Test WebGL 1
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (gl) {
                        results.webgl1 = true;
                        results.renderer = gl.getParameter(gl.RENDERER);
                        results.vendor = gl.getParameter(gl.VENDOR);
                        results.version = gl.getParameter(gl.VERSION);
                        
                        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                        if (debugInfo) {
                            results.unmaskedRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                            results.unmaskedVendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                        }
                        
                        // Get supported extensions
                        const exts = gl.getSupportedExtensions();
                        results.extensions = exts ? exts.slice(0, 10) : [];
                    }
                } catch (e) {
                    results.webgl1Error = e.toString();
                }
                
                // Test WebGL 2
                try {
                    const canvas2 = document.createElement('canvas');
                    const gl2 = canvas2.getContext('webgl2');
                    results.webgl2 = !!gl2;
                } catch (e) {
                    results.webgl2Error = e.toString();
                }
                
                // Check for PIXI.js
                results.hasPixi = typeof window.PIXI !== 'undefined';
                if (results.hasPixi) {
                    results.pixiVersion = window.PIXI.VERSION;
                }
                
                return results;
            }''')
            
            print("\n=== WebGL Status ===")
            for key, value in webgl_check.items():
                if key == 'extensions':
                    print(f"{key}: {', '.join(value[:5])}...")
                else:
                    print(f"{key}: {value}")
            
            print("\nWaiting for VTuber to initialize...")
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"❌ Failed to load VTuber: {e}")
            await vtuber_browser.close()
            return
        
        await vtuber_page.evaluate("if (window.moveTo) window.moveTo(0, 0)")
        
        # Launch demo browser
        print("\nLaunching demo browser...")
        demo_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-fake-ui-for-media-stream',
                '--window-position=650,0',
                '--window-size=640,600'
            ]
        )
        
        demo_page = await demo_browser.new_page()
        await demo_page.goto(f"http://localhost:{DEMO_PORT}/")
        await demo_page.wait_for_load_state('domcontentloaded')
        print("✅ Demo page loaded")
        
        await asyncio.sleep(3)
        
        print("\n✅ Starting VTuber streaming...")
        frame_count = 0
        error_count = 0
        fps = 30
        frame_interval = 1.0 / fps
        
        try:
            while True:
                start_time = asyncio.get_event_loop().time()
                
                try:
                    screenshot = await vtuber_page.screenshot(
                        type='jpeg',
                        quality=70
                    )
                    
                    if screenshot and len(screenshot) > 0:
                        frame_data = f"data:image/jpeg;base64,{base64.b64encode(screenshot).decode()}"
                        
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
                                print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s) - Hybrid", end='', flush=True)
                    
                except Exception as e:
                    error_count += 1
                    if error_count % 30 == 0:
                        print(f"\n⚠️  Stream error #{error_count}: {e}")
                
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