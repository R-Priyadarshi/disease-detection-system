const puppeteer = require('puppeteer');
const path = require('path');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 950 });

        console.log('Navigating to workstation...');
        await page.goto('http://127.0.0.1:8000/workstation', { waitUntil: 'networkidle2' });

        // 1. Capture Fleischner Guidelines Modal
        console.log('Opening Fleischner modal...');
        await page.click('#tool-fleischner');
        await page.waitForSelector('#fleischner-dialog[open]', { timeout: 4000 });
        await new Promise(r => setTimeout(r, 1000));

        const fleischnerPic = path.join(ARTIFACT_DIR, 'alveon_fleischner_consultation_verified.png');
        await page.screenshot({ path: fleischnerPic });
        console.log('Saved:', fleischnerPic);

        await page.click('#btn-close-fleischner-modal');
        await new Promise(r => setTimeout(r, 500));

        // 2. Capture Model Benchmark Modal
        console.log('Opening Model Benchmark modal...');
        await page.click('#btn-open-model-benchmark');
        await page.waitForSelector('#benchmark-dialog[open]', { timeout: 4000 });
        await new Promise(r => setTimeout(r, 1500));

        const benchmarkPic = path.join(ARTIFACT_DIR, 'alveon_model_benchmark_verified.png');
        await page.screenshot({ path: benchmarkPic });
        console.log('Saved:', benchmarkPic);

        console.log('Modal captures completed successfully.');
    } catch (err) {
        console.error('Capture error:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
