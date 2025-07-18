#!/usr/bin/env python3
"""
Test video pipeline by launching Chrome with test page and fake video
"""
import asyncio
import os
import subprocess
import time
from pathlib import Path
from playwright.async_api import async_playwright

VIDEO_PIPE = "/tmp/vtuber_video"
TEST_PAGE = "/test_av_pipeline.html"

async def test_video_pipeline():
    """Test the complete video pipeline"""
    print("=== Testing Video Pipeline ===\n")
    
    # Step 1: Ensure pipe exists
    print("1. Checking video pipe...")
    if not os.path.exists(VIDEO_PIPE):
        print(f"   Creating pipe at {VIDEO_PIPE}")
        os.makedirs(os.path.dirname(VIDEO_PIPE), exist_ok=True)
        os.mkfifo(VIDEO_PIPE)
    else:
        print(f"   Pipe exists at {VIDEO_PIPE}")
    
    # Step 2: Start FFmpeg streaming test pattern to pipe
    print("\n2. Starting FFmpeg test pattern...")
    ffmpeg_cmd = [
        'ffmpeg',
        '-f', 'lavfi',
        '-i', 'testsrc=size=640x480:rate=30',
        '-pix_fmt', 'yuv420p',
        '-f', 'yuv4mpegpipe',
        '-y',
        VIDEO_PIPE
    ]
    
    ffmpeg_proc = subprocess.Popen(
        ffmpeg_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    print("   FFmpeg started (PID: {})".format(ffmpeg_proc.pid))
    
    # Give FFmpeg time to start
    await asyncio.sleep(2)
    
    # Step 3: Launch Chrome with fake video from pipe
    print("\n3. Launching Chrome with fake video...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                f'--use-file-for-fake-video-capture={VIDEO_PIPE}',
                '--use-fake-ui-for-media-stream',
                '--auto-accept-camera-and-microphone-capture'
            ]
        )
        
        page = await browser.new_page()
        
        # Navigate to test page
        test_page_path = Path(__file__).parent / "test_av_pipeline.html"
        await page.goto(f"file://{test_page_path}")
        
        print("   Chrome launched with test page")
        
        # Step 4: Test camera access
        print("\n4. Testing camera access...")
        
        # Click test camera button
        await page.click('button[onclick="testCamera()"]')
        await asyncio.sleep(3)
        
        # Check if video element has stream
        has_stream = await page.evaluate('''() => {
            const video = document.getElementById('preview');
            return video && video.srcObject && video.srcObject.active;
        }''')
        
        if has_stream:
            print("   ✅ Camera access successful - video stream active")
            
            # Get video stats
            stats = await page.evaluate('''() => {
                const video = document.getElementById('preview');
                const stream = video.srcObject;
                const track = stream.getVideoTracks()[0];
                const settings = track.getSettings();
                return {
                    width: settings.width,
                    height: settings.height,
                    frameRate: settings.frameRate,
                    deviceId: settings.deviceId
                };
            }''')
            
            print(f"   Video settings: {stats['width']}x{stats['height']} @ {stats['frameRate']}fps")
            print(f"   Device ID: {stats['deviceId']}")
        else:
            print("   ❌ Camera access failed - no video stream")
        
        # Step 5: Check if FFmpeg is still running
        print("\n5. Checking FFmpeg status...")
        if ffmpeg_proc.poll() is None:
            print("   ✅ FFmpeg still running")
        else:
            print("   ❌ FFmpeg crashed")
            stderr = ffmpeg_proc.stderr.read().decode()
            print(f"   Error: {stderr}")
        
        # Step 6: Test WebRTC capabilities
        print("\n6. Testing WebRTC capabilities...")
        
        # Enumerate devices
        await page.click('button[onclick="enumerateDevices()"]')
        await asyncio.sleep(1)
        
        device_info = await page.inner_text('#deviceList')
        print("   Available devices:")
        for line in device_info.split('\n'):
            if line.strip():
                print(f"     {line}")
        
        # Keep browser open for manual inspection
        print("\n7. Browser ready for manual inspection")
        print("   - Check if video shows test pattern")
        print("   - Try different test patterns")
        print("   - Monitor VNC at localhost:5900")
        print("\nPress Enter to close test...")
        
        # Wait for user input
        await asyncio.get_event_loop().run_in_executor(None, input)
        
        # Cleanup
        await browser.close()
        ffmpeg_proc.terminate()
        
    print("\nTest completed!")

async def main():
    """Run the video pipeline test"""
    try:
        await test_video_pipeline()
    except Exception as e:
        print(f"\nError during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())