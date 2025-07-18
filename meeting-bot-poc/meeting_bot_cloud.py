#!/usr/bin/env python3
"""
Cloud-deployable Teams/Zoom meeting bot using Chrome with named pipe video
"""
import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

MEETING_URL = os.environ.get('MEETING_URL', '')
VIDEO_PIPE = '/tmp/vtuber_video'
AUDIO_SOURCE = 'vtuber_source'  # PulseAudio virtual source

async def join_meeting():
    """Join meeting using Chrome with fake video from pipe"""
    if not MEETING_URL:
        print("ERROR: No MEETING_URL provided")
        return
        
    print(f"Joining meeting: {MEETING_URL}")
    
    # Launch Chrome with fake video capture from pipe
    chrome_cmd = [
        'google-chrome',
        '--no-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        f'--use-file-for-fake-video-capture={VIDEO_PIPE}',
        '--use-fake-ui-for-media-stream',  # Auto-accept camera/mic permissions
        '--autoplay-policy=no-user-gesture-required',
        MEETING_URL
    ]
    
    # Set audio to use our virtual source
    env = os.environ.copy()
    env['PULSE_SOURCE'] = AUDIO_SOURCE
    
    print("Launching Chrome with VTuber video feed...")
    chrome_process = subprocess.Popen(chrome_cmd, env=env)
    
    # Use Playwright for additional automation if needed
    async with async_playwright() as p:
        # Connect to existing Chrome instance
        browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        
        # Wait a bit for page to load
        await asyncio.sleep(5)
        
        # Get the page
        pages = browser.contexts[0].pages
        if pages:
            page = pages[0]
            
            # Handle Teams-specific UI
            if 'teams.microsoft.com' in page.url:
                print("Detected Microsoft Teams")
                
                # Click "Join now" button if present
                try:
                    join_button = await page.wait_for_selector('button:has-text("Join now")', timeout=10000)
                    await join_button.click()
                    print("Clicked Join now button")
                except:
                    print("Join button not found or already in meeting")
                    
                # Turn on camera if needed
                try:
                    camera_button = await page.wait_for_selector('[aria-label*="camera"]', timeout=5000)
                    camera_state = await camera_button.get_attribute('aria-pressed')
                    if camera_state == 'false':
                        await camera_button.click()
                        print("Turned on camera")
                except:
                    print("Camera button not found")
                    
            # Handle Zoom-specific UI
            elif 'zoom.us' in page.url:
                print("Detected Zoom")
                # Add Zoom-specific automation here
                
        # Keep running
        try:
            while True:
                await asyncio.sleep(1)
                
                # Check if Chrome is still running
                if chrome_process.poll() is not None:
                    print("Chrome process died")
                    break
                    
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            chrome_process.terminate()

async def main():
    """Main entry point"""
    # Wait a bit for video stream to be ready
    print("Waiting for video stream to be ready...")
    await asyncio.sleep(10)
    
    # Join the meeting
    await join_meeting()

if __name__ == "__main__":
    asyncio.run(main())