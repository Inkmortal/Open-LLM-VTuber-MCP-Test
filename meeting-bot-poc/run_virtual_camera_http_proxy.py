#!/usr/bin/env python3
"""
Run VTuber with virtual camera - HTTP-aware proxy version
Uses a proper HTTP proxy that handles headers, CORS, and WebSocket upgrade
"""
import asyncio
import os
import base64
import http.server
import threading
import socketserver
import subprocess
from playwright.async_api import async_playwright
from aiohttp import web
import aiohttp
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Set environment variables for software rendering
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '4.5'
os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '450'
os.environ['DISPLAY'] = ':99'

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
PROXY_PORT = 12393
DEMO_PORT = 8080

# HTTP/WebSocket Proxy Handler
class ProxyHandler:
    def __init__(self, target_host, target_port):
        self.target_host = target_host
        self.target_port = target_port
        self.session = None
    
    async def start(self):
        self.session = aiohttp.ClientSession(
            connector=aiohttp.TCPConnector(ssl=False),
            timeout=aiohttp.ClientTimeout(total=30)
        )
    
    async def stop(self):
        if self.session:
            await self.session.close()
    
    async def handle_request(self, request):
        """Handle regular HTTP requests"""
        try:
            # Build target URL
            target_url = f'http://{self.target_host}:{self.target_port}{request.path_qs}'
            
            # Copy headers but update Host
            headers = dict(request.headers)
            headers['Host'] = f'{self.target_host}:{self.target_port}'
            
            # Remove hop-by-hop headers
            for header in ['Connection', 'Keep-Alive', 'Transfer-Encoding', 'TE', 'Trailer', 'Upgrade']:
                headers.pop(header, None)
            
            logger.info(f"Proxying {request.method} {request.path_qs} -> {target_url}")
            
            # Forward the request
            async with self.session.request(
                method=request.method,
                url=target_url,
                headers=headers,
                data=await request.read(),
                allow_redirects=False
            ) as resp:
                # Copy response headers
                response_headers = dict(resp.headers)
                
                # Add CORS headers to allow cross-origin requests
                response_headers['Access-Control-Allow-Origin'] = '*'
                response_headers['Access-Control-Allow-Methods'] = '*'
                response_headers['Access-Control-Allow-Headers'] = '*'
                
                # Remove hop-by-hop headers
                for header in ['Connection', 'Keep-Alive', 'Transfer-Encoding', 'TE', 'Trailer']:
                    response_headers.pop(header, None)
                
                body = await resp.read()
                
                return web.Response(
                    body=body,
                    status=resp.status,
                    headers=response_headers
                )
                
        except Exception as e:
            logger.error(f"Proxy error: {e}")
            return web.Response(text=str(e), status=502)
    
    async def handle_websocket(self, request):
        """Handle WebSocket upgrade requests"""
        ws_server = web.WebSocketResponse()
        await ws_server.prepare(request)
        
        try:
            # Connect to target WebSocket
            target_url = f'ws://{self.target_host}:{self.target_port}{request.path_qs}'
            logger.info(f"WebSocket proxy: {request.path_qs} -> {target_url}")
            
            session = aiohttp.ClientSession()
            ws_client = await session.ws_connect(target_url)
            
            # Bidirectional message forwarding
            async def forward_to_client():
                async for msg in ws_client:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await ws_server.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await ws_server.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws_client.exception()}")
                        break
            
            async def forward_to_server():
                async for msg in ws_server:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        await ws_client.send_str(msg.data)
                    elif msg.type == aiohttp.WSMsgType.BINARY:
                        await ws_client.send_bytes(msg.data)
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        logger.error(f"WebSocket error: {ws_server.exception()}")
                        break
            
            # Run both directions concurrently
            await asyncio.gather(
                forward_to_client(),
                forward_to_server()
            )
            
        except Exception as e:
            logger.error(f"WebSocket proxy error: {e}")
        finally:
            await ws_client.close()
            await session.close()
            await ws_server.close()
        
        return ws_server

async def start_proxy_server(proxy_handler):
    """Start the HTTP/WebSocket proxy server"""
    app = web.Application()
    
    async def handle(request):
        # Check if this is a WebSocket upgrade request
        if request.headers.get('Upgrade', '').lower() == 'websocket':
            return await proxy_handler.handle_websocket(request)
        else:
            return await proxy_handler.handle_request(request)
    
    # Route all requests through the proxy
    app.router.add_route('*', '/{path:.*}', handle)
    
    # Start the proxy handler
    await proxy_handler.start()
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', PROXY_PORT)
    await site.start()
    
    logger.info(f"HTTP/WebSocket proxy started on localhost:{PROXY_PORT} -> {HOST_IP}:{PROXY_PORT}")
    return runner

# Demo HTML (same as before)
DEMO_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <title>Virtual Camera Demo (HTTP Proxy)</title>
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
        <h1>VTuber Virtual Camera (HTTP Proxy)</h1>
        <p>Using proper HTTP proxy for resource loading</p>
        
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
        logger.info(f"Demo HTTP server running on port {DEMO_PORT}")
        httpd.serve_forever()

async def main():
    print("=== VTuber Virtual Camera Service (HTTP Proxy) ===")
    print(f"Windows host IP: {HOST_IP}")
    print("Using proper HTTP/WebSocket proxy for full compatibility")
    
    # Start HTTP proxy
    proxy_handler = ProxyHandler(HOST_IP, PROXY_PORT)
    proxy_runner = await start_proxy_server(proxy_handler)
    
    # Start demo HTTP server
    server_thread = threading.Thread(target=start_http_server, daemon=True)
    server_thread.start()
    
    await asyncio.sleep(2)
    
    async with async_playwright() as p:
        # Launch with hybrid rendering for WebGL
        print("\nLaunching VTuber browser...")
        vtuber_browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                '--use-gl=swiftshader',
                '--use-angle=swiftshader-webgl',
                '--enable-unsafe-swiftshader',
                '--enable-webgl',
                '--enable-webgl2'
            ]
        )
        
        vtuber_page = await vtuber_browser.new_page()
        
        # Monitor console
        vtuber_page.on("console", lambda msg: logger.info(f"[VTuber] {msg.text}"))
        vtuber_page.on("pageerror", lambda msg: logger.error(f"[VTuber Error] {msg}"))
        
        # Add debugging for resource loading
        vtuber_page.on("requestfailed", lambda req: logger.error(f"[Request Failed] {req.url} - {req.failure}"))
        
        try:
            vtuber_url = f'http://localhost:{PROXY_PORT}'
            print(f"Loading VTuber from {vtuber_url} (via HTTP proxy)")
            await vtuber_page.goto(vtuber_url, wait_until='networkidle', timeout=30000)
            await vtuber_page.set_viewport_size({"width": 1280, "height": 720})
            print(f"✅ VTuber page loaded via proxy")
            
            # Quick check for PIXI.js
            await asyncio.sleep(5)
            pixi_check = await vtuber_page.evaluate('typeof window.PIXI !== "undefined"')
            print(f"PIXI.js loaded: {pixi_check}")
            
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
                                print(f"\rStreaming: {frame_count} frames ({frame_count // fps}s) - HTTP Proxy", end='', flush=True)
                    
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
            await proxy_runner.cleanup()
            await proxy_handler.stop()

if __name__ == "__main__":
    asyncio.run(main())