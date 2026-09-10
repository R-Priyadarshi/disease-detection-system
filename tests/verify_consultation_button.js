const puppeteer = require('puppeteer');
const path = require('path');

const ARTIFACTS_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        console.log("Navigating to http://127.0.0.1:8000...");
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle2' });

        await new Promise(r => setTimeout(r, 1200));

        // Screenshot 1: Banner with Clinical Consultation button prominently visible
        const bannerBtn = await page.$('#banner-report-btn');
        console.log("Banner Report Button found:", !!bannerBtn);

        await page.screenshot({
            path: path.join(ARTIFACTS_DIR, 'pacs_24_clinical_consultation_visible.png'),
            fullPage: false
        });
        console.log("Saved pacs_24_clinical_consultation_visible.png");

        // Click the banner consultation button
        console.log("Clicking #banner-report-btn...");
        await page.click('#banner-report-btn');
        await new Promise(r => setTimeout(r, 1500));

        const isModalOpen = await page.evaluate(() => {
            const dialog = document.getElementById('report-dialog');
            return dialog && dialog.open;
        });
        console.log("Report dialog is open:", isModalOpen);

        // Screenshot 2: Modal open
        await page.screenshot({
            path: path.join(ARTIFACTS_DIR, 'pacs_25_consultation_modal_opened.png'),
            fullPage: false
        });
        console.log("Saved pacs_25_consultation_modal_opened.png");

    } catch (err) {
        console.error("Verification failed:", err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
