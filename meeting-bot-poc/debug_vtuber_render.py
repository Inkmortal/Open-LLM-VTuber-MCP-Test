#!/usr/bin/env python3
"""
Comprehensive VTuber rendering debug script
"""
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

# Set ALL possible environment variables for software rendering
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
os.environ['GALLIUM_DRIVER'] = 'llvmpipe'
os.environ['MESA_GL_VERSION_OVERRIDE'] = '4.5'
os.environ['MESA_GLSL_VERSION_OVERRIDE'] = '450'
os.environ['DISPLAY'] = ':99'
os.environ['LIBGL_ALWAYS_INDIRECT'] = '0'
os.environ['DRI_PRIME'] = '0'
os.environ['MESA_DEBUG'] = '1'
os.environ['LIBGL_DEBUG'] = 'verbose'

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

async def main():
    print("=== VTuber Rendering Debug ===")
    print(f"Windows host IP: {HOST_IP}")
    print("\nEnvironment variables:")
    for key in ['LIBGL_ALWAYS_SOFTWARE', 'GALLIUM_DRIVER', 'MESA_GL_VERSION_OVERRIDE', 'DISPLAY']:
        print(f"  {key}: {os.environ.get(key)}")
    
    async with async_playwright() as p:
        # Try multiple browser configurations
        configs = [
            {
                "name": "SwiftShader + All Flags",
                "args": [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-gl=swiftshader',
                    '--use-angle=swiftshader-webgl',
                    '--enable-webgl',
                    '--enable-webgl2',
                    '--ignore-gpu-blocklist',
                    '--disable-gpu-sandbox',
                    '--enable-unsafe-webgpu',
                    '--disable-features=VizDisplayCompositor',
                    '--enable-features=WebGL2ComputeContext',
                    '--override-use-software-gl-for-tests',
                    '--disable-accelerated-2d-canvas',
                    '--disable-gpu-rasterization'
                ]
            },
            {
                "name": "ANGLE + Desktop GL",
                "args": [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-gl=angle',
                    '--use-angle=gl',
                    '--enable-webgl',
                    '--enable-webgl2',
                    '--ignore-gpu-blocklist',
                    '--disable-gpu-sandbox'
                ]
            },
            {
                "name": "EGL + Software",
                "args": [
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--use-gl=egl',
                    '--enable-webgl',
                    '--enable-webgl2',
                    '--ignore-gpu-blocklist',
                    '--disable-gpu',
                    '--disable-software-rasterizer'
                ]
            }
        ]
        
        for config in configs:
            print(f"\n\n=== Testing: {config['name']} ===")
            
            browser = await p.chromium.launch(
                headless=False,
                args=config['args']
            )
            
            page = await browser.new_page()
            
            # Capture console messages
            console_logs = []
            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
            page.on("pageerror", lambda msg: console_logs.append(f"[ERROR] {msg}"))
            
            try:
                # First check WebGL on a simple test page
                await page.goto('data:text/html,<canvas id="test"></canvas>')
                
                webgl_test = await page.evaluate('''() => {
                    const canvas = document.getElementById('test');
                    const contexts = ['webgl2', 'webgl', 'experimental-webgl'];
                    const results = {};
                    
                    for (const contextType of contexts) {
                        try {
                            const gl = canvas.getContext(contextType);
                            if (gl) {
                                results[contextType] = {
                                    success: true,
                                    renderer: gl.getParameter(gl.RENDERER),
                                    vendor: gl.getParameter(gl.VENDOR),
                                    version: gl.getParameter(gl.VERSION)
                                };
                            } else {
                                results[contextType] = { success: false, error: 'null context' };
                            }
                        } catch (e) {
                            results[contextType] = { success: false, error: e.toString() };
                        }
                    }
                    
                    return results;
                }''')
                
                print("\nWebGL Test Results:")
                for ctx, result in webgl_test.items():
                    if result['success']:
                        print(f"  {ctx}: ✅ {result['renderer']}")
                    else:
                        print(f"  {ctx}: ❌ {result['error']}")
                
                # Now test the actual VTuber page
                print(f"\nLoading VTuber from http://localhost:12393...")
                await page.goto('http://localhost:12393', wait_until='networkidle', timeout=30000)
                await asyncio.sleep(5)
                
                # Check for Live2D and PIXI
                vtuber_check = await page.evaluate('''() => {
                    const results = {
                        hasLive2D: typeof window.Live2D !== 'undefined',
                        hasLive2DFramework: typeof window.Live2DFramework !== 'undefined',
                        hasPixi: typeof window.PIXI !== 'undefined',
                        pixiVersion: typeof window.PIXI !== 'undefined' ? window.PIXI.VERSION : null,
                        canvases: []
                    };
                    
                    // Check all canvases
                    const canvases = document.querySelectorAll('canvas');
                    canvases.forEach((canvas, i) => {
                        const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                        results.canvases.push({
                            index: i,
                            width: canvas.width,
                            height: canvas.height,
                            hasContext: !!gl,
                            display: window.getComputedStyle(canvas).display,
                            visibility: window.getComputedStyle(canvas).visibility,
                            zIndex: window.getComputedStyle(canvas).zIndex
                        });
                    });
                    
                    // Check for any errors in console
                    results.pixiApp = typeof window.app !== 'undefined';
                    
                    return results;
                }''')
                
                print("\nVTuber Page Analysis:")
                print(f"  Live2D loaded: {vtuber_check['hasLive2D']}")
                print(f"  Live2D Framework: {vtuber_check['hasLive2DFramework']}")
                print(f"  PIXI.js loaded: {vtuber_check['hasPixi']}")
                print(f"  PIXI version: {vtuber_check['pixiVersion']}")
                print(f"  PIXI app exists: {vtuber_check['pixiApp']}")
                
                print(f"\n  Found {len(vtuber_check['canvases'])} canvas elements:")
                for canvas in vtuber_check['canvases']:
                    print(f"    Canvas {canvas['index']}: {canvas['width']}x{canvas['height']}, "
                          f"WebGL: {canvas['hasContext']}, Display: {canvas['display']}, "
                          f"Visibility: {canvas['visibility']}, Z-Index: {canvas['zIndex']}")
                
                # Try to get any PIXI errors
                pixi_state = await page.evaluate('''() => {
                    if (window.PIXI && window.app) {
                        return {
                            rendererType: window.app.renderer.type,
                            rendererWidth: window.app.renderer.width,
                            rendererHeight: window.app.renderer.height,
                            stage: {
                                children: window.app.stage.children.length,
                                visible: window.app.stage.visible
                            }
                        };
                    }
                    return null;
                }''')
                
                if pixi_state:
                    print("\n  PIXI Application State:")
                    print(f"    Renderer type: {pixi_state['rendererType']}")
                    print(f"    Renderer size: {pixi_state['rendererWidth']}x{pixi_state['rendererHeight']}")
                    print(f"    Stage children: {pixi_state['stage']['children']}")
                    print(f"    Stage visible: {pixi_state['stage']['visible']}")
                
                # Take screenshot
                screenshot_path = f'/tmp/vtuber_debug_{config["name"].replace(" ", "_")}.png'
                await page.screenshot(path=screenshot_path)
                print(f"\n  Screenshot saved: {screenshot_path}")
                
                # Show console logs
                if console_logs:
                    print("\n  Console logs (last 10):")
                    for log in console_logs[-10:]:
                        print(f"    {log}")
                
            except Exception as e:
                print(f"\n  ❌ Error: {e}")
            
            await browser.close()
            await asyncio.sleep(2)
        
        print("\n\n=== Debug Summary ===")
        print("Check the screenshots in /tmp/ to see which configuration works best.")
        print("Look for any error patterns in the console logs.")

if __name__ == "__main__":
    # Start proxy in background
    proxy_script = '''
import socket
import select
import threading

def proxy():
    HOST_IP = '%s'
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
                ready = select.select([client, remote], [], [], 0.1)[0]
                if client in ready:
                    data = client.recv(4096)
                    if not data: break
                    remote.sendall(data)
                if remote in ready:
                    data = remote.recv(4096)
                    if not data: break
                    client.sendall(data)
        except: pass
        finally:
            client.close()
            try: remote.close()
            except: pass

threading.Thread(target=proxy, daemon=True).start()
''' % get_host_ip()
    
    import threading
    exec(proxy_script)
    
    asyncio.run(main())