#!/usr/bin/env python3
"""
Diagnostic VTuber rendering - Try multiple approaches
"""
import asyncio
import os
import subprocess
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
            
            print(f"\nLoading VTuber page...")
            await page.goto('http://localhost:12393', wait_until='domcontentloaded', timeout=20000)
            await asyncio.sleep(5)
            
            # Check WebGL and Live2D status
            result = await page.evaluate('''() => {
                const info = {
                    webgl: false,
                    webgl2: false,
                    renderer: 'none',
                    hasPixi: typeof window.PIXI !== 'undefined',
                    hasLive2D: typeof window.Live2D !== 'undefined',
                    canvasCount: document.querySelectorAll('canvas').length,
                    live2dError: null
                };
                
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
                
                // Check for Live2D specific errors
                if (window._live2dError) {
                    info.live2dError = window._live2dError;
                }
                
                return info;
            }''')
            
            print(f"\nResults:")
            print(f"  WebGL: {result['webgl']}")
            print(f"  WebGL2: {result['webgl2']}")
            print(f"  Renderer: {result.get('renderer', 'none')}")
            print(f"  Unmasked: {result.get('unmaskedRenderer', 'N/A')}")
            print(f"  PIXI.js: {result['hasPixi']}")
            print(f"  Live2D: {result['hasLive2D']}")
            print(f"  Canvas count: {result['canvasCount']}")
            
            if result.get('webglError'):
                print(f"  WebGL Error: {result['webglError']}")
            if result.get('live2dError'):
                print(f"  Live2D Error: {result['live2dError']}")
            
            # Show console logs
            if console_logs:
                print(f"\nConsole logs (first 10):")
                for log in console_logs[:10]:
                    if 'GroupMarkerNotSet' not in log:
                        print(f"  {log}")
            
            # Take screenshot
            screenshot_name = f"/tmp/vtuber_{name.lower().replace(' ', '_')}.png"
            await page.screenshot(path=screenshot_name)
            print(f"\nScreenshot saved: {screenshot_name}")
            
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
    
    # Start proxy
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
    
    await asyncio.sleep(2)
    
    # Test configurations
    configurations = [
        {
            "name": "1. Default Chrome",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage'
            ],
            "env": {}
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
                '--enable-webgl-draft-extensions'
            ],
            "env": {}
        },
        {
            "name": "3. Mesa LLVMpipe",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=desktop',
                '--enable-webgl',
                '--enable-webgl2'
            ],
            "env": {
                'LIBGL_ALWAYS_SOFTWARE': '1',
                'GALLIUM_DRIVER': 'llvmpipe'
            }
        },
        {
            "name": "4. Mesa SWR",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=desktop',
                '--enable-webgl',
                '--enable-webgl2'
            ],
            "env": {
                'LIBGL_ALWAYS_SOFTWARE': '1',
                'GALLIUM_DRIVER': 'swr'
            }
        },
        {
            "name": "5. Chrome SwiftShader",
            "args": [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--use-gl=swiftshader',
                '--enable-webgl',
                '--enable-webgl2',
                '--enable-unsafe-webgl',
                '--enable-webgl-draft-extensions'
            ],
            "env": {}
        }
    ]
    
    for config in configurations:
        await test_configuration(config["name"], config["args"], config["env"])
        await asyncio.sleep(2)
    
    proxy_proc.terminate()
    
    print("\n\n=== Summary ===")
    print("Check the screenshots in /tmp/ to see which configuration shows the VTuber character.")
    print("Look for:")
    print("  - PIXI.js = True")
    print("  - Canvas count > 0")
    print("  - No WebGL/Live2D errors")

if __name__ == "__main__":
    asyncio.run(main())