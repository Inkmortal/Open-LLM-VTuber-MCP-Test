#!/usr/bin/env python3
"""
Debug VTuber rendering issues - check WebGL and canvas
"""
import asyncio
import os
from playwright.async_api import async_playwright

VTUBER_URL = 'http://localhost:12393'

async def main():
    print("=== VTuber Rendering Debug ===")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox', 
                '--disable-dev-shm-usage',
                '--use-gl=swiftshader',  # Force software rendering
                '--disable-gpu-sandbox',
                '--enable-webgl',
                '--ignore-gpu-blacklist',
                '--enable-accelerated-2d-canvas'
            ]
        )
        
        page = await browser.new_page()
        
        # Capture all console messages
        console_logs = []
        page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))
        page.on("pageerror", lambda msg: console_logs.append(f"[ERROR] {msg}"))
        
        await page.goto(VTUBER_URL, wait_until='networkidle', timeout=30000)
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        print("\nWaiting for page to fully load...")
        await asyncio.sleep(5)
        
        # Check WebGL support
        webgl_check = await page.evaluate('''() => {
            const results = {
                webgl1: false,
                webgl2: false,
                renderer: 'unknown',
                vendor: 'unknown',
                canvases: []
            };
            
            // Check WebGL 1
            try {
                const canvas = document.createElement('canvas');
                const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                if (gl) {
                    results.webgl1 = true;
                    const debugInfo = gl.getExtension('WEBGL_debug_renderer_info');
                    if (debugInfo) {
                        results.renderer = gl.getParameter(debugInfo.UNMASKED_RENDERER_WEBGL);
                        results.vendor = gl.getParameter(debugInfo.UNMASKED_VENDOR_WEBGL);
                    }
                }
            } catch (e) {
                results.webgl1Error = e.toString();
            }
            
            // Check WebGL 2
            try {
                const canvas2 = document.createElement('canvas');
                const gl2 = canvas2.getContext('webgl2');
                results.webgl2 = !!gl2;
            } catch (e) {
                results.webgl2Error = e.toString();
            }
            
            // Find all canvases
            const canvases = document.querySelectorAll('canvas');
            canvases.forEach((canvas, i) => {
                results.canvases.push({
                    index: i,
                    width: canvas.width,
                    height: canvas.height,
                    display: window.getComputedStyle(canvas).display,
                    visibility: window.getComputedStyle(canvas).visibility,
                    opacity: window.getComputedStyle(canvas).opacity,
                    position: canvas.getBoundingClientRect(),
                    id: canvas.id,
                    className: canvas.className
                });
            });
            
            return results;
        }''')
        
        print("\n=== WebGL Support ===")
        print(f"WebGL 1.0: {webgl_check['webgl1']}")
        print(f"WebGL 2.0: {webgl_check['webgl2']}")
        print(f"Renderer: {webgl_check['renderer']}")
        print(f"Vendor: {webgl_check['vendor']}")
        
        print("\n=== Canvas Elements ===")
        for canvas in webgl_check['canvases']:
            print(f"Canvas {canvas['index']}:")
            print(f"  Size: {canvas['width']}x{canvas['height']}")
            print(f"  Display: {canvas['display']}, Visibility: {canvas['visibility']}, Opacity: {canvas['opacity']}")
            print(f"  Position: {canvas['position']}")
            print(f"  ID: {canvas['id']}, Class: {canvas['className']}")
        
        # Check for Live2D
        live2d_check = await page.evaluate('''() => {
            return {
                hasLive2D: typeof window.Live2D !== 'undefined',
                hasLive2DFramework: typeof window.Live2DFramework !== 'undefined',
                pixiVersion: typeof window.PIXI !== 'undefined' ? window.PIXI.VERSION : 'not found'
            };
        }''')
        
        print("\n=== Live2D Status ===")
        print(f"Live2D: {live2d_check['hasLive2D']}")
        print(f"Live2D Framework: {live2d_check['hasLive2DFramework']}")
        print(f"PIXI.js Version: {live2d_check['pixiVersion']}")
        
        # Check for specific rendering issues
        rendering_check = await page.evaluate('''() => {
            const checks = {
                hasWebGLContext: false,
                activeContexts: 0,
                contextLost: false
            };
            
            // Check all canvases for WebGL contexts
            document.querySelectorAll('canvas').forEach(canvas => {
                const gl = canvas.getContext('webgl') || canvas.getContext('webgl2');
                if (gl) {
                    checks.hasWebGLContext = true;
                    checks.activeContexts++;
                    if (gl.isContextLost()) {
                        checks.contextLost = true;
                    }
                }
            });
            
            return checks;
        }''')
        
        print("\n=== Rendering Status ===")
        print(f"Has WebGL Context: {rendering_check['hasWebGLContext']}")
        print(f"Active Contexts: {rendering_check['activeContexts']}")
        print(f"Context Lost: {rendering_check['contextLost']}")
        
        print("\n=== Console Logs ===")
        for log in console_logs[-20:]:  # Last 20 logs
            print(log)
        
        # Take screenshot
        await page.screenshot(path='/tmp/vtuber_debug_render.png')
        print("\n✅ Screenshot saved to /tmp/vtuber_debug_render.png")
        
        input("\nPress Enter to close browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())