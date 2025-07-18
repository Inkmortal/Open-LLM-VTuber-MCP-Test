#!/usr/bin/env python3
"""
Debug script to check virtual camera status
"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    print("=== Virtual Camera Debug ===")
    
    async with async_playwright() as p:
        # Connect to existing browsers
        browser = await p.chromium.launch(
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        # Create a test page
        page = await browser.new_page()
        
        # Simple HTML to check camera
        test_html = '''
        <html>
        <body>
            <h1>Camera Test</h1>
            <video id="test" autoplay muted style="width:640px;height:480px;background:black;"></video>
            <div id="status"></div>
            <script>
                async function testCamera() {
                    const status = document.getElementById('status');
                    try {
                        const stream = await navigator.mediaDevices.getUserMedia({video: true});
                        document.getElementById('test').srcObject = stream;
                        const track = stream.getVideoTracks()[0];
                        status.innerHTML = `<p>Success! Track: ${track.label}</p>`;
                        console.log('Camera working:', track);
                    } catch (e) {
                        status.innerHTML = `<p>Error: ${e.message}</p>`;
                        console.error('Camera error:', e);
                    }
                }
                testCamera();
            </script>
        </body>
        </html>
        '''
        
        await page.set_content(test_html)
        await asyncio.sleep(3)
        
        # Check status
        status = await page.evaluate('''() => {
            const video = document.getElementById('test');
            const statusDiv = document.getElementById('status');
            return {
                hasVideo: video && video.srcObject && video.srcObject.active,
                statusText: statusDiv ? statusDiv.textContent : 'No status',
                videoWidth: video ? video.videoWidth : 0,
                videoHeight: video ? video.videoHeight : 0
            };
        }''')
        
        print(f"Status: {status}")
        
        # Keep open for 10 seconds
        await asyncio.sleep(10)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())