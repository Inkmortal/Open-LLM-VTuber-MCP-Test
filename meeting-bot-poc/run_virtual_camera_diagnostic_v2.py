#!/usr/bin/env python3
"""
Diagnostic VTuber rendering - Test different WebGL approaches
Runs within the xvfb environment
"""
import asyncio
import os
import subprocess
import sys
import json
from playwright.async_api import async_playwright

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

def ensure_proxy():
    """Ensure proxy is running"""
    try:
        test_socket = subprocess.run(['nc', '-z', '127.0.0.1', '12393'], capture_output=True)
        if test_socket.returncode == 0:
            print("Proxy already running on localhost:12393")
            return None
    except:
        pass
    
    print(f"Starting proxy: localhost:12393 -> {HOST_IP}:12393")
    proxy_proc = subprocess.Popen([
        'python3', '-c', f'''
import socket, select, sys
HOST_IP = "{HOST_IP}"
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    s.bind(("127.0.0.1", 12393))
except:
    sys.exit(0)
s.listen(5)
print("Proxy started on localhost:12393")
while True:
    c, _ = s.accept()
    try:
        r = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        r.connect((HOST_IP, 12393))
        c.setblocking(0)
        r.setblocking(0)
        while True:
            ready = select.select([c, r], [], [], 0.1)[0]
            if c in ready:
                d = c.recv(4096)
                if not d: break
                r.sendall(d)
            if r in ready:
                d = r.recv(4096)
                if not d: break
                c.sendall(d)
    except: pass
    finally:
        c.close()
        try: r.close()
        except: pass
'''
    ])
    return proxy_proc

async def test_configuration(name, chrome_args, env_vars=None):
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"{'='*60}")
    
    # Set environment variables
    original_env = {}
    if env_vars:
        for key, value in env_vars.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value
            print(f"Set {key}={value}")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=False,
                args=chrome_args
            )
            
            page = await browser.new_page()
            
            # Capture console messages
            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            page.on("pageerror", lambda msg: console_logs.append(f"[ERROR] {msg}"))
            
            # Add Live2D monitoring
            await page.add_init_script('''() => {
                // Monitor Live2D loading
                window._live2dLoadStatus = [];
                
                // Hook into script loading
                const origCreateElement = document.createElement;
                document.createElement = function(tagName) {
                    const elem = origCreateElement.call(this, tagName);
                    if (tagName.toLowerCase() === 'script') {
                        elem.addEventListener('load', function() {
                            if (this.src && this.src.includes('live2d')) {
                                window._live2dLoadStatus.push({
                                    type: 'loaded',
                                    src: this.src,
                                    time: Date.now()
                                });
                                console.log('Live2D script loaded:', this.src);
                            }
                        });
                        elem.addEventListener('error', function() {
                            if (this.src && this.src.includes('live2d')) {
                                window._live2dLoadStatus.push({
                                    type: 'error',
                                    src: this.src,
                                    time: Date.now()
                                });
                                console.error('Live2D script failed:', this.src);
                            }
                        });
                    }
                    return elem;
                };
                
                // Monitor WebGL context creation
                const origGetContext = HTMLCanvasElement.prototype.getContext;
                HTMLCanvasElement.prototype.getContext = function(type, ...args) {
                    console.log('Canvas getContext called:', type);
                    const ctx = origGetContext.call(this, type, ...args);
                    if (ctx && (type === 'webgl' || type === 'webgl2')) {
                        console.log('WebGL context created successfully');
                    }
                    return ctx;
                };
            }''')
            
            print(f"\nLoading VTuber page...")
            await page.goto('http://localhost:12393', wait_until='domcontentloaded', timeout=20000)
            await page.set_viewport_size({"width": 1280, "height": 720})
            await asyncio.sleep(10)
            
            # Comprehensive check
            result = await page.evaluate('''() => {
                const info = {
                    webgl: false,
                    webgl2: false,
                    renderer: 'none',
                    hasPixi: typeof window.PIXI !== 'undefined',
                    hasLive2D: typeof window.Live2D !== 'undefined',
                    hasLive2DCubismCore: typeof window.Live2DCubismCore !== 'undefined',
                    canvasCount: document.querySelectorAll('canvas').length,
                    live2dScripts: window._live2dLoadStatus || [],
                    canvasDetails: []
                };
                
                // Test WebGL
                try {
                    const canvas = document.createElement('canvas');
                    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                    if (gl) {
                        info.webgl = true;
                        info.renderer = gl.getParameter(gl.RENDERER);
                        const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                        if (debugInfo) {
                            info.unmaskedRenderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                        }
                    }
                } catch (e) {
                    info.webglError = e.toString();
                }
                
                // Test WebGL2
                try {
                    const canvas2 = document.createElement('canvas');
                    const gl2 = canvas2.getContext('webgl2');
                    info.webgl2 = !!gl2;
                } catch (e) {
                    info.webgl2Error = e.toString();
                }
                
                // Check PIXI version and renderer
                if (info.hasPixi && window.PIXI) {
                    info.pixiVersion = window.PIXI.VERSION;
                    if (window.PIXI.Renderer) {
                        info.pixiRendererType = 'Modern PIXI (v5+)';
                    } else if (window.PIXI.WebGLRenderer) {
                        info.pixiRendererType = 'Legacy PIXI (v4)';
                    }
                }
                
                // Check all canvases
                const canvases = document.querySelectorAll('canvas');
                canvases.forEach((canvas, i) => {
                    const detail = {
                        index: i,
                        width: canvas.width,
                        height: canvas.height,
                        id: canvas.id,
                        className: canvas.className,
                        visible: window.getComputedStyle(canvas).display !== 'none',
                        hasContext: false
                    };
                    
                    // Try to get context type
                    try {
                        if (canvas.getContext('webgl2')) {
                            detail.contextType = 'webgl2';
                            detail.hasContext = true;
                        } else if (canvas.getContext('webgl')) {
                            detail.contextType = 'webgl';
                            detail.hasContext = true;
                        } else if (canvas.getContext('2d')) {
                            detail.contextType = '2d';
                            detail.hasContext = true;
                        }
                    } catch (e) {}
                    
                    info.canvasDetails.push(detail);
                });
                
                return info;
            }''')
            
            print(f"\nResults:")
            print(f"  WebGL: {result['webgl']}")
            print(f"  WebGL2: {result['webgl2']}")
            print(f"  Renderer: {result.get('renderer', 'none')}")
            print(f"  Unmasked: {result.get('unmaskedRenderer', 'N/A')}")
            pixi_version = f"(v{result.get('pixiVersion', '?')})" if result['hasPixi'] else ''
            print(f"  PIXI.js: {result['hasPixi']} {pixi_version}")
            if result.get('pixiRendererType'):
                print(f"  PIXI Type: {result['pixiRendererType']}")
            print(f"  Live2D: {result['hasLive2D']}")
            print(f"  Live2D Core: {result['hasLive2DCubismCore']}")
            print(f"  Canvas count: {result['canvasCount']}")
            
            if result.get('canvasDetails'):
                print(f"\n  Canvas details:")
                for detail in result['canvasDetails']:
                    print(f"    Canvas {detail['index']}: {detail['width']}x{detail['height']}")
                    print(f"      ID: {detail.get('id', 'none')}, Class: {detail.get('className', 'none')}")
                    print(f"      Visible: {detail['visible']}, Context: {detail.get('contextType', 'none')}")
            
            if result.get('live2dScripts'):
                print(f"\n  Live2D script loading:")
                for script in result['live2dScripts']:
                    print(f"    {script['type']}: {script['src']}")
            
            if result.get('webglError'):
                print(f"  WebGL Error: {result['webglError']}")
            
            # Show console logs
            if console_logs:
                print(f"\nConsole logs (relevant):")
                relevant_logs = []
                for log in console_logs:
                    if any(keyword in log.lower() for keyword in ['webgl', 'live2d', 'pixi', 'canvas', 'error', 'failed']):
                        if 'GroupMarkerNotSet' not in log and 'Autofill.enable' not in log:
                            relevant_logs.append(log)
                
                for log in relevant_logs[-20:]:
                    print(f"  {log}")
            
            # Take screenshot
            screenshot_name = f"/tmp/vtuber_{name.lower().replace(' ', '_').replace('.', '')}.png"
            await page.screenshot(path=screenshot_name)
            print(f"\nScreenshot saved: {screenshot_name}")
            
            # Additional debugging - check if VTuber model files are accessible
            model_check = await page.evaluate('''async () => {
                const modelUrls = [
                    '/models/るなちゃん/るなちゃん.model3.json',
                    '/models/Haru/Haru.model3.json',
                    '/models/Hiyori/Hiyori.model3.json'
                ];
                
                const results = [];
                for (const url of modelUrls) {
                    try {
                        const response = await fetch('http://localhost:12393' + url);
                        results.push({
                            url: url,
                            status: response.status,
                            ok: response.ok
                        });
                    } catch (e) {
                        results.push({
                            url: url,
                            error: e.toString()
                        });
                    }
                }
                return results;
            }''')
            
            print(f"\nModel file accessibility:")
            for check in model_check:
                if check.get('error'):
                    print(f"  {check['url']}: ERROR - {check['error']}")
                else:
                    print(f"  {check['url']}: {check['status']} {'OK' if check['ok'] else 'FAIL'}")
            
            await browser.close()
            
    except Exception as e:
        print(f"\nFailed: {e}")
    
    finally:
        # Restore environment
        if env_vars:
            for key, original in original_env.items():
                if original is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = original

async def main():
    print("=== Live2D Rendering Diagnostics ===")
    print(f"Windows host IP: {HOST_IP}")
    print(f"Display: {os.environ.get('DISPLAY', 'Not set')}")
    
    # Ensure proxy is running
    proxy_proc = ensure_proxy()
    await asyncio.sleep(2)
    
    # Test configurations
    configurations = [
        {
            "name": "1. Current Working (Hybrid)",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=swiftshader',
                '--use-angle=swiftshader-webgl',
                '--enable-unsafe-swiftshader',
                '--enable-webgl',
                '--enable-webgl2'
            ],
            "env": {
                'LIBGL_ALWAYS_SOFTWARE': '1',
                'GALLIUM_DRIVER': 'llvmpipe',
                'MESA_GL_VERSION_OVERRIDE': '4.5',
                'MESA_GLSL_VERSION_OVERRIDE': '450'
            }
        },
        {
            "name": "2. ANGLE with Desktop GL",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=angle',
                '--use-angle=gl',
                '--enable-webgl',
                '--enable-webgl2',
                '--enable-webgl-draft-extensions',
                '--ignore-gpu-blocklist'
            ],
            "env": {}
        },
        {
            "name": "3. EGL with Software",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=egl',
                '--enable-webgl',
                '--enable-webgl2'
            ],
            "env": {
                'LIBGL_ALWAYS_SOFTWARE': '1',
                'GALLIUM_DRIVER': 'llvmpipe'
            }
        },
        {
            "name": "4. ANGLE with SwiftShader",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=angle',
                '--use-angle=swiftshader',
                '--enable-webgl',
                '--enable-webgl2'
            ],
            "env": {}
        }
    ]
    
    for config in configurations:
        await test_configuration(config["name"], config["args"], config.get("env", {}))
        await asyncio.sleep(2)
    
    if proxy_proc:
        proxy_proc.terminate()
    
    print("\n\n=== Summary ===")
    print("Check the screenshots in /tmp/ to see which configuration shows the VTuber character.")
    print("Look for:")
    print("  - PIXI.js = True with version")
    print("  - Canvas count > 0 with visible canvases")
    print("  - No WebGL/Live2D errors")
    print("  - Model files accessible (200 OK)")

if __name__ == "__main__":
    asyncio.run(main())