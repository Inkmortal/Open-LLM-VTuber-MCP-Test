#!/usr/bin/env python3
"""
Check Live2D and PIXI.js status in the VTuber page
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

async def main():
    print("Checking Live2D rendering...")
    
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
    sys.exit(0)  # Already running
s.listen(5)
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
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        page = await browser.new_page()
        
        # Capture all console messages
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda msg: console_logs.append(f"[ERROR] {msg}"))
        
        print(f"Loading VTuber from http://localhost:12393...")
        await page.goto('http://localhost:12393', wait_until='networkidle', timeout=30000)
        
        # Wait for page to fully load
        await asyncio.sleep(5)
        
        # Deep inspection of Live2D and PIXI
        result = await page.evaluate('''() => {
            const info = {
                pixiLoaded: typeof window.PIXI !== 'undefined',
                live2dLoaded: typeof window.Live2D !== 'undefined',
                errors: [],
                canvases: [],
                pixiDetails: null,
                live2dModels: []
            };
            
            // Check canvases
            document.querySelectorAll('canvas').forEach((canvas, i) => {
                const rect = canvas.getBoundingClientRect();
                const style = window.getComputedStyle(canvas);
                info.canvases.push({
                    index: i,
                    id: canvas.id,
                    className: canvas.className,
                    width: canvas.width,
                    height: canvas.height,
                    clientWidth: canvas.clientWidth,
                    clientHeight: canvas.clientHeight,
                    display: style.display,
                    visibility: style.visibility,
                    opacity: style.opacity,
                    position: style.position,
                    zIndex: style.zIndex,
                    rect: {
                        top: rect.top,
                        left: rect.left,
                        width: rect.width,
                        height: rect.height
                    }
                });
            });
            
            // Check PIXI application
            if (window.PIXI && window.app) {
                info.pixiDetails = {
                    version: window.PIXI.VERSION,
                    rendererType: window.app.renderer.type,
                    rendererClass: window.app.renderer.constructor.name,
                    resolution: window.app.renderer.resolution,
                    width: window.app.renderer.width,
                    height: window.app.renderer.height,
                    backgroundColor: window.app.renderer.backgroundColor,
                    stageChildren: window.app.stage.children.length,
                    stageVisible: window.app.stage.visible
                };
                
                // Check stage children
                window.app.stage.children.forEach((child, i) => {
                    if (child.name && child.name.includes('Live2D')) {
                        info.live2dModels.push({
                            index: i,
                            name: child.name,
                            visible: child.visible,
                            x: child.x,
                            y: child.y,
                            width: child.width,
                            height: child.height,
                            alpha: child.alpha
                        });
                    }
                });
            }
            
            // Check for Live2D Cubism
            if (window.PIXI && window.PIXI.live2d) {
                info.live2dCubism = {
                    loaded: true,
                    version: window.PIXI.live2d.VERSION || 'unknown'
                };
            }
            
            // Look for any Live2D model containers
            const live2dContainers = document.querySelectorAll('[class*="live2d"], [id*="live2d"]');
            info.live2dContainerCount = live2dContainers.length;
            
            return info;
        }''')
        
        print("\n=== Live2D/PIXI Analysis ===")
        print(f"PIXI.js loaded: {result['pixiLoaded']}")
        print(f"Live2D loaded: {result['live2dLoaded']}")
        print(f"Live2D containers found: {result['live2dContainerCount']}")
        
        if result['pixiDetails']:
            print("\nPIXI Application:")
            for key, value in result['pixiDetails'].items():
                print(f"  {key}: {value}")
        
        print(f"\nCanvases found: {len(result['canvases'])}")
        for canvas in result['canvases']:
            print(f"\nCanvas {canvas['index']}:")
            print(f"  ID: {canvas['id']}, Class: {canvas['className']}")
            print(f"  Size: {canvas['width']}x{canvas['height']} (client: {canvas['clientWidth']}x{canvas['clientHeight']})")
            print(f"  Style: display={canvas['display']}, visibility={canvas['visibility']}, opacity={canvas['opacity']}")
            print(f"  Position: {canvas['position']}, z-index={canvas['zIndex']}")
            print(f"  Rect: {canvas['rect']}")
        
        if result['live2dModels']:
            print(f"\nLive2D Models: {len(result['live2dModels'])}")
            for model in result['live2dModels']:
                print(f"  Model {model['index']}: {model}")
        
        # Check for specific errors
        error_check = await page.evaluate('''() => {
            const logs = [];
            
            // Override console.error to capture errors
            const originalError = console.error;
            console.error = function(...args) {
                logs.push({type: 'error', message: args.join(' ')});
                originalError.apply(console, args);
            };
            
            // Check if WebGL context was lost
            const canvases = document.querySelectorAll('canvas');
            canvases.forEach((canvas, i) => {
                const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                if (gl && gl.isContextLost()) {
                    logs.push({type: 'webgl', message: `Canvas ${i} context lost`});
                }
            });
            
            return logs;
        }''')
        
        if error_check:
            print("\nErrors detected:")
            for err in error_check:
                print(f"  [{err['type']}] {err['message']}")
        
        # Show recent console logs
        print("\nRecent console logs:")
        for log in console_logs[-20:]:
            print(f"  {log}")
        
        await browser.close()
    
    proxy_proc.terminate()

if __name__ == "__main__":
    asyncio.run(main())