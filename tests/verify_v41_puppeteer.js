/**
 * Puppeteer Visual E2E Verification Suite for Alveon PACS v4.1 Enterprise Features
 * 
 * Verifies:
 * 1. Active triage worklist with OHIF Viewer header button & card links
 * 2. Standalone OHIF Diagnostic Web Viewer v3 Bridge (/viewer)
 * 3. Consultation modal with Voice Dictation bar, soundwave & RADLEX editor
 * 4. Real-time voice macro execution with automated RADLEX & ACR synthesis
 * 5. Orthanc FOSS Hospital PACS Integration tab in PACS Hub modal
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('🚀 Launching Chrome for Alveon PACS v4.1 Visual Verification...');
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1650,1100'
        ],
        defaultViewport: {
            width: 1650,
            height: 1100,
            deviceScaleFactor: 1.5
        }
    });

    const page = await browser.newPage();

    page.on('console', msg => {
        if (msg.type() === 'error') console.error(`[PAGE ERROR] ${msg.text()}`);
    });
    page.on('pageerror', err => {
        console.error(`[UNCAUGHT EXCEPTION] ${err.toString()}`);
    });

    try {
        // ---------------------------------------------------------
        // 1. Worklist with OHIF Quick Launch Buttons
        // ---------------------------------------------------------
        console.log('Navigating to Alveon PACS Workstation (http://127.0.0.1:8000)...');
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0', timeout: 30000 });
        await new Promise(r => setTimeout(r, 1500));

        // Select the first study in the worklist
        await page.waitForSelector('.study-card');
        const cards = await page.$$('.study-card');
        if (cards.length > 0) {
            await cards[0].click();
            await new Promise(r => setTimeout(r, 1200));
        }

        const shot19 = path.join(ARTIFACT_DIR, 'pacs_19_worklist_ohif_buttons.png');
        await page.screenshot({ path: shot19 });
        console.log(`📸 [1/5] Captured: ${shot19}`);

        // ---------------------------------------------------------
        // 2. Standalone OHIF Diagnostic Web Viewer (/viewer)
        // ---------------------------------------------------------
        console.log('Navigating to OHIF Diagnostic Viewer (/viewer)...');
        const viewerPage = await browser.newPage();
        await viewerPage.setViewport({ width: 1650, height: 1100, deviceScaleFactor: 1.5 });
        await viewerPage.goto('http://127.0.0.1:8000/viewer', { waitUntil: 'networkidle0', timeout: 30000 });
        await new Promise(r => setTimeout(r, 1500));

        const shot20 = path.join(ARTIFACT_DIR, 'pacs_20_ohif_diagnostic_viewer.png');
        await viewerPage.screenshot({ path: shot20 });
        console.log(`📸 [2/5] Captured: ${shot20}`);
        await viewerPage.close();

        // ---------------------------------------------------------
        // 3. Consultation Modal with Voice Dictation Bar & RADLEX
        // ---------------------------------------------------------
        console.log('Opening Radiology Consultation Suite Modal...');
        await page.bringToFront();
        await page.waitForSelector('#open-report-btn');
        await page.click('#open-report-btn');
        await new Promise(r => setTimeout(r, 1500));

        // Scroll modal so voice dictation bar and RADLEX fields are prominent
        await page.evaluate(() => {
            const scroll = document.getElementById('modal-report-scroll');
            if (scroll) scroll.scrollTop = 260;
        });
        await new Promise(r => setTimeout(r, 600));

        const shot21 = path.join(ARTIFACT_DIR, 'pacs_21_voice_dictation_modal.png');
        await page.screenshot({ path: shot21 });
        console.log(`📸 [3/5] Captured: ${shot21}`);

        // ---------------------------------------------------------
        // 4. Voice Macro Trigger (Trauma / Pneumothorax)
        // ---------------------------------------------------------
        console.log('Triggering Trauma Pneumothorax Voice Macro...');
        const traumaChip = await page.$('.voice-chip[data-macro*="trauma"]');
        if (traumaChip) {
            await traumaChip.click();
            await new Promise(r => setTimeout(r, 1200));
        }

        // Scroll to show the updated RADLEX findings, ACR Category 1 badge & Voice indicator
        await page.evaluate(() => {
            const card = document.getElementById('radlex-structured-card');
            if (card) card.scrollIntoView({ behavior: 'instant', block: 'center' });
        });
        await new Promise(r => setTimeout(r, 600));

        const shot22 = path.join(ARTIFACT_DIR, 'pacs_22_voice_macro_executed.png');
        await page.screenshot({ path: shot22 });
        console.log(`📸 [4/5] Captured: ${shot22}`);

        // Close report modal
        await page.click('#close-modal-btn');
        await new Promise(r => setTimeout(r, 500));

        // ---------------------------------------------------------
        // 5. Orthanc Hospital PACS Integration Tab
        // ---------------------------------------------------------
        console.log('Opening PACS Hub and switching to Orthanc PACS tab...');
        await page.click('#open-pacs-hub-btn');
        await new Promise(r => setTimeout(r, 800));

        const orthancTabBtn = await page.$('.pacs-hub-tab-btn[data-pacs-tab="tab-orthanc"]');
        if (orthancTabBtn) {
            await orthancTabBtn.click();
            await new Promise(r => setTimeout(r, 1200));
        }

        const shot23 = path.join(ARTIFACT_DIR, 'pacs_23_orthanc_pacs_hub_tab.png');
        await page.screenshot({ path: shot23 });
        console.log(`📸 [5/5] Captured: ${shot23}`);

        console.log('✅ Visual verification suite completed successfully!');
    } catch (err) {
        console.error('❌ Visual verification failed:', err);
        process.exitCode = 1;
    } finally {
        await browser.close();
    }
})();
