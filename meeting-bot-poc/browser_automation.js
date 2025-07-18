const { chromium } = require('playwright');

async function startMeetingBot() {
    console.log('Starting browser automation...');
    
    const browser = await chromium.launch({
        headless: false, // Show browser for debugging
        args: [
            '--use-fake-ui-for-media-stream', // Auto-grant permissions
            '--enable-usermedia-screen-capturing',
            '--auto-select-desktop-capture-source=Entire screen',
            '--disable-web-security', // For local avatar iframe
            '--disable-features=IsolateOrigins,site-per-process',
            '--use-file-for-fake-video-capture=/tmp/video_pipe/video_stream' // Use named pipe for video
        ]
    });
    
    const context = await browser.newContext({
        permissions: ['microphone', 'camera']
    });
    
    const page = await context.newPage();
    
    // First, let's test with webcammictest.com
    console.log('Navigating to webcam/mic test site...');
    await page.goto('https://webcammictest.com/');
    
    // Wait for page to load
    await page.waitForLoadState('networkidle');
    
    // Click webcam test
    try {
        await page.click('button:has-text("Test Webcam")', { timeout: 5000 });
        console.log('Started webcam test');
        
        // Select our virtual camera if dropdown exists
        const cameraSelect = await page.$('select[id*="camera"], select[aria-label*="camera"]');
        if (cameraSelect) {
            await cameraSelect.selectOption({ label: /video/i });
            console.log('Selected virtual camera');
        }
    } catch (e) {
        console.log('Could not find webcam test button:', e.message);
    }
    
    // Click microphone test
    try {
        await page.click('button:has-text("Test Microphone")', { timeout: 5000 });
        console.log('Started microphone test');
        
        // Select our virtual microphone if dropdown exists
        const micSelect = await page.$('select[id*="mic"], select[aria-label*="microphone"]');
        if (micSelect) {
            await micSelect.selectOption({ label: /VTuber/i });
            console.log('Selected virtual microphone');
        }
    } catch (e) {
        console.log('Could not find microphone test button:', e.message);
    }
    
    // Keep browser open for testing
    console.log('Browser automation ready. Press Ctrl+C to exit.');
    
    // For actual Teams meeting, uncomment below:
    /*
    await page.goto('https://teams.microsoft.com');
    // Add Teams-specific automation here
    */
    
    // Prevent script from exiting
    await new Promise(() => {});
}

startMeetingBot().catch(console.error);