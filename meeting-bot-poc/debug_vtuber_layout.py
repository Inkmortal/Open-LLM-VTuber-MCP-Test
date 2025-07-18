#!/usr/bin/env python3
"""
Debug VTuber page layout to find the character position
"""
import asyncio
import os
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')

async def main():
    print("=== VTuber Layout Debug ===")
    print(f"VTuber URL: {VTUBER_URL}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        page = await browser.new_page()
        await page.goto(VTUBER_URL, wait_until='networkidle', timeout=30000)
        await page.set_viewport_size({"width": 1280, "height": 720})
        
        print("\nWaiting for page to load...")
        await asyncio.sleep(3)
        
        # Get page dimensions
        dimensions = await page.evaluate('''() => {
            return {
                pageWidth: document.documentElement.scrollWidth,
                pageHeight: document.documentElement.scrollHeight,
                viewportWidth: window.innerWidth,
                viewportHeight: window.innerHeight
            }
        }''')
        print(f"\nPage dimensions: {dimensions}")
        
        # Look for canvas elements (VTuber is likely rendered on canvas)
        canvases = await page.query_selector_all('canvas')
        print(f"\nFound {len(canvases)} canvas elements")
        
        for i, canvas in enumerate(canvases):
            bbox = await canvas.bounding_box()
            if bbox:
                print(f"Canvas {i}: x={bbox['x']}, y={bbox['y']}, width={bbox['width']}, height={bbox['height']}")
        
        # Look for video elements
        videos = await page.query_selector_all('video')
        print(f"\nFound {len(videos)} video elements")
        
        for i, video in enumerate(videos):
            bbox = await video.bounding_box()
            if bbox:
                print(f"Video {i}: x={bbox['x']}, y={bbox['y']}, width={bbox['width']}, height={bbox['height']}")
        
        # Take full page screenshot
        print("\nTaking full page screenshot...")
        await page.screenshot(path='vtuber_full_page.png', full_page=True)
        print("Saved as vtuber_full_page.png")
        
        # Take viewport screenshot
        await page.screenshot(path='vtuber_viewport.png')
        print("Saved as vtuber_viewport.png")
        
        # Check for main content containers
        main_elements = await page.query_selector_all('div[id], div[class*="main"], div[class*="content"], div[class*="vtuber"], div[class*="character"]')
        print(f"\nFound {len(main_elements)} potential container elements")
        
        input("Press Enter to close browser...")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())