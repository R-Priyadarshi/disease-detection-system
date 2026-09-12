const puppeteer = require('puppeteer');

(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        await page.goto('http://127.0.0.1:8000/workstation', { waitUntil: 'networkidle2' });
        await page.waitForSelector('.study-card', { timeout: 10000 });
        await page.click('.study-card');
        await new Promise(r => setTimeout(r, 1200));

        // Activate Caliper tool and draw a line
        const caliperBtn = await page.$('#tool-btn-caliper');
        if (caliperBtn) {
            await caliperBtn.click();
            await new Promise(r => setTimeout(r, 300));
            const canvas = await page.$('#pacs-annotation-canvas');
            if (canvas) {
                const box = await canvas.boundingBox();
                if (box) {
                    await page.mouse.move(box.x + 100, box.y + 120);
                    await page.mouse.down();
                    await page.mouse.move(box.x + 280, box.y + 220, { steps: 5 });
                    await page.mouse.up();
                    await new Promise(r => setTimeout(r, 500));
                }
            }
        }

        const artifactPath = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26/alveon_workstation_sc_caliper_view.png';
        await page.screenshot({ path: artifactPath, fullPage: false });
        console.log(`📸 Workstation screenshot saved: ${artifactPath}`);
    } finally {
        await browser.close();
    }
})();
