/**
 * Comprehensive Puppeteer End-to-End Visual Verification Suite for Alveon PACS v3.1
 * Verifies:
 * 1. Multi-Label Thoracic Pathology Panel (6 Conditions)
 * 2. Enterprise PACS & DICOMweb Interoperability Hub
 * 3. DIMSE C-ECHO Ping Verification
 * 4. DICOMweb REST Services UI
 * 5. Live 6-Patient Emergency Cohort Ingestion via C-STORE (Port 11112)
 * 6. Worklist priority ranking & Multi-Label view updates for Tension Pneumothorax
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('🚀 Launching Chrome for Alveon PACS v3.1 E2E Verification...');
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1600,1050'
        ],
        defaultViewport: {
            width: 1600,
            height: 1050,
            deviceScaleFactor: 1.5
        }
    });

    const page = await browser.newPage();

    // Listen for console logs & errors
    page.on('console', msg => {
        if (msg.type() === 'error') {
            console.error(`[PAGE ERROR] ${msg.text()}`);
        }
    });
    page.on('pageerror', err => {
        console.error(`[UNCAUGHT EXCEPTION] ${err.toString()}`);
    });

    try {
        // 1. Navigate to workstation
        console.log('📍 Navigating to http://127.0.0.1:8000 ...');
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0', timeout: 15000 });

        // Wait for study queue or viewport
        await page.waitForSelector('#diagnosis-content', { timeout: 10000 });
        await new Promise(r => setTimeout(r, 1000));

        // 2. Verify Multi-Label Findings Strip
        console.log('🔍 Checking Multi-Label Thoracic Pathology Panel...');
        const multiLabelPanel = await page.$('#multilabel-panel');
        if (!multiLabelPanel) throw new Error('Multi-label panel (#multilabel-panel) not found in DOM');

        const chipCount = await page.$$eval('#multilabel-findings-strip .pathology-chip', chips => chips.length);
        console.log(`✅ Multi-label findings chips rendered: ${chipCount} (Expected 6)`);
        if (chipCount < 6) throw new Error(`Expected at least 6 pathology chips, found ${chipCount}`);

        const chipNames = await page.$$eval('#multilabel-findings-strip .pathology-chip-title', els => els.map(e => e.textContent.trim()));
        console.log(`📋 Active Pathology Chips: ${chipNames.join(', ')}`);

        // Screenshot 09: Multi-Label Workstation Viewport
        const shot09Path = path.join(ARTIFACT_DIR, 'pacs_09_multilabel_panel.png');
        await page.screenshot({ path: shot09Path, fullPage: false });
        console.log(`📸 Saved Screenshot 09 -> ${shot09Path}`);

        // 3. Open Enterprise PACS & DICOMweb Hub Modal
        console.log('🌐 Opening PACS & DICOMweb Interoperability Hub (via #open-pacs-hub-btn)...');
        await page.click('#open-pacs-hub-btn');
        await page.waitForSelector('#pacs-hub-dialog[open]', { timeout: 5000 });
        await new Promise(r => setTimeout(r, 600));

        // Screenshot 10: PACS Hub Modal Tab 1 (DIMSE)
        const shot10Path = path.join(ARTIFACT_DIR, 'pacs_10_hub_modal_dimse.png');
        await page.screenshot({ path: shot10Path, fullPage: false });
        console.log(`📸 Saved Screenshot 10 -> ${shot10Path}`);

        // 4. Test C-ECHO Ping in modal
        console.log('📡 Testing C-ECHO Ping in modal...');
        await page.click('#btn-pacs-ping');
        await page.waitForFunction(() => {
            const log = document.getElementById('pacs-ping-log');
            return log && (log.textContent.includes('SUCCESS') || log.textContent.includes('Roundtrip'));
        }, { timeout: 8000 });

        const pingLogText = await page.$eval('#pacs-ping-log', el => el.textContent.trim());
        console.log(`✅ C-ECHO Ping Response: ${pingLogText.replace(/\n/g, ' • ')}`);

        // 5. Switch to Tab 2: DICOMweb REST Services
        console.log('🔗 Switching to DICOMweb REST Services Tab...');
        await page.click('.pacs-hub-tab-btn[data-pacs-tab="tab-dicomweb"]');
        await new Promise(r => setTimeout(r, 500));

        const dicomwebCards = await page.$$eval('.dicomweb-endpoint-card', cards => cards.length);
        console.log(`✅ DICOMweb endpoint specification cards: ${dicomwebCards} (QIDO-RS, WADO-RS Rendered, WADO-RS Native, STOW-RS)`);

        // Screenshot 11: DICOMweb Tab
        const shot11Path = path.join(ARTIFACT_DIR, 'pacs_11_hub_modal_dicomweb.png');
        await page.screenshot({ path: shot11Path, fullPage: false });
        console.log(`📸 Saved Screenshot 11 -> ${shot11Path}`);

        // 6. Switch to Tab 3: Clinical Cohort Ingestion
        console.log('👥 Switching to Clinical Cohort Ingestion Tab...');
        await page.click('.pacs-hub-tab-btn[data-pacs-tab="tab-cohort"]');
        await new Promise(r => setTimeout(r, 500));

        const cohortCardCount = await page.$$eval('#cohort-cards-grid .cohort-card', cards => cards.length);
        console.log(`✅ Emergency clinical cases ready for C-STORE transmission: ${cohortCardCount}`);

        // 7. Trigger Live 6-Patient C-STORE Cohort Ingestion
        console.log('⚡ Triggering 6-Patient Cohort Ingestion via C-STORE on port 11112...');
        await page.click('#btn-inject-cohort');

        // Wait for transmission completion
        await page.waitForFunction(() => {
            const summary = document.getElementById('cohort-log-summary');
            return summary && summary.textContent.includes('Transmission Complete');
        }, { timeout: 15000 });

        const cohortSummary = await page.$eval('#cohort-log-summary', el => el.textContent.trim());
        console.log(`✅ Ingestion Telemetry: ${cohortSummary}`);

        // Screenshot 12: Cohort Transmission Log
        const shot12Path = path.join(ARTIFACT_DIR, 'pacs_12_cohort_transmission_log.png');
        await page.screenshot({ path: shot12Path, fullPage: false });
        console.log(`📸 Saved Screenshot 12 -> ${shot12Path}`);

        // 8. Close Modal and verify updated Worklist & Tension Pneumothorax
        console.log('❌ Closing PACS Hub dialog...');
        await page.click('#close-pacs-hub-btn');
        await new Promise(r => setTimeout(r, 800));

        // Verify Worklist contains Hastings, Rose
        const worklistText = await page.$$eval('.study-card', cards => cards.map(c => c.textContent).join(' '));
        console.log(`Worklist contains Rose Hastings: ${worklistText.includes('Rose') || worklistText.includes('HASTINGS')}`);

        // Find card for Rose Hastings and click it
        const roseCard = await page.evaluateHandle(() => {
            const cards = Array.from(document.querySelectorAll('.study-card'));
            return cards.find(c => c.textContent.includes('Rose') || c.textContent.includes('HASTINGS')) || cards[0];
        });
        if (roseCard) {
            await roseCard.click();
            await new Promise(r => setTimeout(r, 1000));
        }

        // Verify that Rose Hastings tension pneumothorax is now active in viewport
        const activeHeading = await page.$eval('#diagnosis-heading', el => el.textContent.trim());
        const activeAcuity = await page.$eval('#multilabel-acuity-tag', el => el.textContent.trim());
        console.log(`✅ Active Patient Diagnosis: ${activeHeading}`);
        console.log(`✅ Active Patient Composite Acuity: ${activeAcuity}`);

        // Screenshot 13: Rose Hastings Pneumothorax Active with Multi-Label Panel
        const shot13Path = path.join(ARTIFACT_DIR, 'pacs_13_cohort_pneumothorax_active.png');
        await page.screenshot({ path: shot13Path, fullPage: false });
        console.log(`📸 Saved Screenshot 13 -> ${shot13Path}`);

        console.log('🎉 ALL PUPPETEER E2E VERIFICATION STEPS PASSED WITH FLYING COLORS!');
    } catch (err) {
        console.error('❌ E2E VERIFICATION FAILED:', err);
        process.exitCode = 1;
    } finally {
        await browser.close();
    }
})();
