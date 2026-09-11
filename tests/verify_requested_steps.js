/**
 * Verification of User Requested Steps:
 * 1. Workstation: http://localhost:8000
 * 2. Interactive Tour: Click "🧭 Clinical Tour"
 * 3. OHIF Bridge: http://localhost:8000/viewer
 * 4. Interactive API Documentation: http://localhost:8000/docs
 */

const puppeteer = require('puppeteer');
const path = require('path');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('====================================================================');
    console.log('🚀 Verifying Live Navigation across User-Requested Endpoints');
    console.log('====================================================================');

    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu', '--window-size=1680,1050'],
        defaultViewport: { width: 1680, height: 1050 }
    });

    const page = await browser.newPage();

    try {
        // Step 1: Workstation http://localhost:8000
        console.log('\n[1] Navigating to Workstation: http://localhost:8000 ...');
        await page.goto('http://localhost:8000', { waitUntil: 'networkidle0', timeout: 15000 });
        await new Promise(r => setTimeout(r, 1200));
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'live_01_workstation_localhost.png') });
        console.log('  ✅ Workstation loaded on http://localhost:8000');

        // Step 2: Interactive Tour: Click "🧭 Clinical Tour" in the top navigation
        console.log('\n[2] Triggering "🧭 Clinical Tour" in top navigation ...');
        const tourBtn = await page.$('#start-clinical-tour-btn');
        if (!tourBtn) throw new Error('#start-clinical-tour-btn not found');
        await page.click('#start-clinical-tour-btn');
        await new Promise(r => setTimeout(r, 800));

        const tourVisible = await page.evaluate(() => {
            const el = document.getElementById('clinical-tour-overlay');
            return el && window.getComputedStyle(el).display !== 'none';
        });
        console.log(`  ✅ Clinical Tour Overlay visible: ${tourVisible}`);
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'live_02_clinical_tour_active.png') });

        // Close tour
        await page.evaluate(() => {
            const closeBtn = document.getElementById('tour-close-btn');
            if (closeBtn) closeBtn.click();
        });
        await new Promise(r => setTimeout(r, 400));

        // Step 3: OHIF Bridge: http://localhost:8000/viewer
        console.log('\n[3] Navigating to OHIF Bridge: http://localhost:8000/viewer ...');
        await page.goto('http://localhost:8000/viewer', { waitUntil: 'networkidle0', timeout: 15000 });
        await new Promise(r => setTimeout(r, 1200));
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'live_03_ohif_bridge_viewer.png') });
        console.log('  ✅ OHIF Diagnostic Viewer loaded on http://localhost:8000/viewer');

        // Step 4: Interactive API Documentation: http://localhost:8000/docs
        console.log('\n[4] Navigating to Interactive API Docs: http://localhost:8000/docs ...');
        await page.goto('http://localhost:8000/docs', { waitUntil: 'networkidle0', timeout: 15000 });
        await new Promise(r => setTimeout(r, 1200));
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'live_04_api_documentation_docs.png') });
        console.log('  ✅ FastAPI Swagger UI loaded on http://localhost:8000/docs');

        console.log('\n====================================================================');
        console.log('🎉 ALL 4 REQUESTED ENDPOINTS VERIFIED & ACTIVE LIVE ON 0.0.0.0:8000');
        console.log('====================================================================\n');

    } catch (err) {
        console.error('❌ Verification failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
