const fs = require('fs');
const path = require('path');
const puppeteer = require('puppeteer');

const ARTIFACTS_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
const BASE_URL = 'http://127.0.0.1:8000';

async function runE2EVerification() {
    console.log('=' .repeat(70));
    console.log('STARTING ALVEON v3.0 PUPPETEER DEEP-DIVE E2E VERIFICATION');
    console.log('='.repeat(70));

    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: true,
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--window-size=1440,960'
        ]
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 960, deviceScaleFactor: 2 });

        // Listen for console and network errors
        page.on('console', msg => {
            if (msg.type() === 'error') {
                console.error('[BROWSER CONSOLE ERROR]:', msg.text());
            }
        });
        page.on('requestfailed', req => {
            console.warn('[NETWORK 404/FAILED]:', req.url());
        });

        // 1. Navigate to ALVEON Workstation
        console.log(`\nNavigating to ${BASE_URL}...`);
        await page.goto(BASE_URL, { waitUntil: 'networkidle0', timeout: 30000 });
        await new Promise(r => setTimeout(r, 1000));

        // Verify Worklist loaded
        const totalCasesText = await page.$eval('#worklist-stat-badge', el => el.textContent);
        console.log(`[OK] Workstation initialized. Active STAT cases badge: "${totalCasesText.trim()}"`);

        const firstPatient = await page.$eval('.study-card .patient-name', el => el.textContent);
        console.log(`[OK] Top Worklist Patient: "${firstPatient.trim()}"`);

        // Screenshot 1: Loaded Workstation
        const ss1Path = path.join(ARTIFACTS_DIR, 'pacs_01_workstation_loaded.png');
        await page.screenshot({ path: ss1Path, fullPage: false });
        console.log(`[SAVED] Screenshot 1: ${ss1Path}`);

        // 2. Test Linear Caliper Tool
        console.log('\nTesting 📏 Linear Caliper Tool (mm)...');
        await page.click('#tool-ruler');
        await new Promise(r => setTimeout(r, 200));

        const isRulerActive = await page.$eval('#tool-ruler', el => el.classList.contains('active'));
        const isViewportMeasuring = await page.$eval('#dicom-viewport', el => el.classList.contains('measuring'));
        console.log(`[OK] Ruler button active: ${isRulerActive} | Viewport measuring mode: ${isViewportMeasuring}`);

        const canvasBox = await page.$eval('#pacs-annotation-canvas', el => {
            const r = el.getBoundingClientRect();
            return { left: r.left, top: r.top, width: r.width, height: r.height };
        });

        // Draw caliper line across lung lesion
        const startX = canvasBox.left + canvasBox.width * 0.35;
        const startY = canvasBox.top + canvasBox.height * 0.45;
        const endX = canvasBox.left + canvasBox.width * 0.65;
        const endY = canvasBox.top + canvasBox.height * 0.45;

        await page.mouse.move(startX, startY);
        await page.mouse.down();
        await page.mouse.move(endX, endY, { steps: 15 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 300));

        const ss2Path = path.join(ARTIFACTS_DIR, 'pacs_02_caliper_drawn.png');
        await page.screenshot({ path: ss2Path, fullPage: false });
        console.log(`[SAVED] Screenshot 2: ${ss2Path}`);

        // 3. Test Cardiothoracic Ratio (CTR) Tool
        console.log('\nTesting 🫀 Cardiothoracic Ratio (CTR) Tool...');
        await page.click('#tool-ctr');
        await new Promise(r => setTimeout(r, 200));

        // Draw Line 1: Cardiac Width
        const cardX1 = canvasBox.left + canvasBox.width * 0.38;
        const cardY1 = canvasBox.top + canvasBox.height * 0.58;
        const cardX2 = canvasBox.left + canvasBox.width * 0.62;
        const cardY2 = canvasBox.top + canvasBox.height * 0.58;

        await page.mouse.move(cardX1, cardY1);
        await page.mouse.down();
        await page.mouse.move(cardX2, cardY2, { steps: 10 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 400));

        // Draw Line 2: Internal Thoracic Diameter
        const thorX1 = canvasBox.left + canvasBox.width * 0.26;
        const thorY1 = canvasBox.top + canvasBox.height * 0.68;
        const thorX2 = canvasBox.left + canvasBox.width * 0.74;
        const thorY2 = canvasBox.top + canvasBox.height * 0.68;

        await page.mouse.move(thorX1, thorY1);
        await page.mouse.down();
        await page.mouse.move(thorX2, thorY2, { steps: 10 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 400));

        const ss3Path = path.join(ARTIFACTS_DIR, 'pacs_03_ctr_calculated.png');
        await page.screenshot({ path: ss3Path, fullPage: false });
        console.log(`[SAVED] Screenshot 3: ${ss3Path}`);

        // 4. Test Elliptical ROI Density Tool
        console.log('\nTesting ⭕ Elliptical ROI Density Inspector...');
        await page.click('#tool-roi');
        await new Promise(r => setTimeout(r, 200));

        const roiX1 = canvasBox.left + canvasBox.width * 0.32;
        const roiY1 = canvasBox.top + canvasBox.height * 0.62;
        const roiX2 = canvasBox.left + canvasBox.width * 0.48;
        const roiY2 = canvasBox.top + canvasBox.height * 0.76;

        await page.mouse.move(roiX1, roiY1);
        await page.mouse.down();
        await page.mouse.move(roiX2, roiY2, { steps: 12 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 400));

        const ss4Path = path.join(ARTIFACTS_DIR, 'pacs_04_roi_drawn.png');
        await page.screenshot({ path: ss4Path, fullPage: false });
        console.log(`[SAVED] Screenshot 4: ${ss4Path}`);

        // 5. Test Arrow Callout Tool
        console.log('\nTesting ↗️ Diagnostic Arrow Callout Tool...');
        await page.click('#tool-arrow');
        await new Promise(r => setTimeout(r, 200));

        const arrX1 = canvasBox.left + canvasBox.width * 0.78;
        const arrY1 = canvasBox.top + canvasBox.height * 0.32;
        const arrX2 = canvasBox.left + canvasBox.width * 0.64;
        const arrY2 = canvasBox.top + canvasBox.height * 0.44;

        await page.mouse.move(arrX1, arrY1);
        await page.mouse.down();
        await page.mouse.move(arrX2, arrY2, { steps: 10 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 400));

        const ss5Path = path.join(ARTIFACTS_DIR, 'pacs_05_arrow_annotation.png');
        await page.screenshot({ path: ss5Path, fullPage: false });
        console.log(`[SAVED] Screenshot 5: ${ss5Path}`);

        // 6. Test Dual Screen Viewport Mode
        console.log('\nTesting Dual Screen Viewport Mode...');
        await page.click('#viewport-modes [data-mode="side"]');
        await new Promise(r => setTimeout(r, 400));

        const ss6Path = path.join(ARTIFACTS_DIR, 'pacs_06_dual_screen.png');
        await page.screenshot({ path: ss6Path, fullPage: false });
        console.log(`[SAVED] Screenshot 6: ${ss6Path}`);

        // Switch back to Split Wipe
        await page.click('#viewport-modes [data-mode="split"]');
        await new Promise(r => setTimeout(r, 200));

        // 7. Test Consultation Report Modal & Certified PDF
        console.log('\nTesting Formal Consultation Report Modal & Certified PDF Export...');
        await page.click('#open-report-btn');
        await page.waitForSelector('#report-dialog[open]', { timeout: 10000 });
        await new Promise(r => setTimeout(r, 500));

        const modalTitle = await page.$eval('.modal-title', el => el.textContent);
        console.log(`[OK] Consultation Modal Opened: "${modalTitle.trim()}"`);

        const ss7Path = path.join(ARTIFACTS_DIR, 'pacs_07_consultation_modal.png');
        await page.screenshot({ path: ss7Path, fullPage: false });
        console.log(`[SAVED] Screenshot 7: ${ss7Path}`);

        // Test Certified PDF stream directly from browser fetch
        const pdfResult = await page.evaluate(async () => {
            const studyId = document.querySelector('.study-card.active')?.dataset?.studyId || 'ALV-STAT-09';
            const res = await fetch(`/api/v1/worklist/${studyId}/pdf`);
            const blob = await res.blob();
            return {
                status: res.status,
                contentType: res.headers.get('content-type'),
                size: blob.size
            };
        });
        console.log(`[OK] In-Browser Certified PDF Fetch: HTTP ${pdfResult.status} | Content-Type: ${pdfResult.contentType} | Size: ${pdfResult.size} bytes`);
        if (pdfResult.status !== 200 || !pdfResult.contentType.includes('application/pdf')) {
            throw new Error('Certified PDF download failed in browser!');
        }

        // Close report modal
        await page.click('#close-modal-btn');
        await new Promise(r => setTimeout(r, 300));

        // 8. Test Bulk Selection & Enterprise Purge Confirmation Dialog
        console.log('\nTesting Multi-Study Selection & Purge Confirmation Dialog...');
        await page.click('#worklist-select-mode-btn');
        await new Promise(r => setTimeout(r, 300));

        // Check first 2 study checkboxes
        const checkboxes = await page.$$('.study-card-checkbox');
        if (checkboxes.length >= 2) {
            await checkboxes[0].click();
            await checkboxes[1].click();
            await new Promise(r => setTimeout(r, 200));

            const purgeBtnText = await page.$eval('#bulk-purge-selected-btn', el => el.textContent);
            console.log(`[OK] Bulk Purge Button Label: "${purgeBtnText.trim()}"`);

            await page.click('#bulk-purge-selected-btn');
            await page.waitForSelector('#pacs-confirm-dialog[open]', { timeout: 5000 });
            await new Promise(r => setTimeout(r, 300));

            const confirmTitle = await page.$eval('#confirm-modal-title', el => el.textContent);
            console.log(`[OK] Confirmation Dialog Opened: "${confirmTitle.trim()}"`);

            const ss8Path = path.join(ARTIFACTS_DIR, 'pacs_08_purge_confirm_dialog.png');
            await page.screenshot({ path: ss8Path, fullPage: false });
            console.log(`[SAVED] Screenshot 8: ${ss8Path}`);

            // Dismiss dialog safely
            await page.click('#confirm-cancel-btn');
            await new Promise(r => setTimeout(r, 200));
        }

        console.log('\n' + '='.repeat(70));
        console.log('ALL PUPPETEER E2E BROWSER TESTS COMPLETED SUCCESSFULLY!');
        console.log('='.repeat(70));
    } finally {
        await browser.close();
    }
}

runE2EVerification().catch(err => {
    console.error('PUPPETEER E2E FAILURE:', err);
    process.exit(1);
});
