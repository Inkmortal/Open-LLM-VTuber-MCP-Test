#!/usr/bin/env python3
"""
Stream VTuber avatar to named pipe using FFmpeg
"""
import asyncio
import subprocess
import os
from playwright.async_api import async_playwright

VTUBER_URL = os.environ.get('VTUBER_URL', 'http://host.docker.internal:12393')
VIDEO_PIPE = '/tmp/vtuber_video'

async def main():
    """Main function to capture VTuber and stream to pipe"""
    print(f"Connecting to VTuber at {VTUBER_URL}")
    
    # Start browser to load VTuber
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        page = await browser.new_page()
        
        # Navigate to VTuber page - the main interface is at root
        print(f"Navigating to {VTUBER_URL}")
        await page.goto(VTUBER_URL)
        await page.wait_for_timeout(3000)  # Wait for VTuber to load
        
        # Get browser window info for screen capture
        # In a real implementation, you'd position the window properly
        # For now, we'll capture the full screen
        
        # Start FFmpeg to capture screen and output to pipe
        ffmpeg_cmd = [
            'ffmpeg',
            '-f', 'x11grab',
            '-r', '30',
            '-s', '640x480',
            '-i', ':99+640,240',  # Capture from middle of screen
            '-pix_fmt', 'yuv420p',
            '-f', 'yuv4mpegpipe',  # Use Y4M format as tested
            '-y',
            VIDEO_PIPE
        ]
        
        print("Starting FFmpeg screen capture...")
        ffmpeg_process = subprocess.Popen(ffmpeg_cmd)
        
        try:
            # Keep browser open and streaming
            while True:
                await asyncio.sleep(1)
                
                # Check if FFmpeg is still running
                if ffmpeg_process.poll() is not None:
                    print("FFmpeg process died, restarting...")
                    ffmpeg_process = subprocess.Popen(ffmpeg_cmd)
                    
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            ffmpeg_process.terminate()
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())