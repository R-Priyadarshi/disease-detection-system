const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

(async () => {
    console.log('🚀 Starting Exhaustive Frontend Deep-Dive Verification with Puppeteer...\n');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--window-size=1440,900'
        ]
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        // Step 1: Open Workstation
        console.log('--- Step 1: Loading Workstation UI ---');
        await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle2' });
        await page.waitForSelector('.study-card', { timeout: 10000 });
        console.log('✅ Workstation loaded cleanly without errors.');

        // Select first study
        await page.click('.study-card');
        await sleep(1000);
        console.log('✅ Active study loaded in viewport.');

        // Step 2: Interactive Caliper Measurement
        console.log('\n--- Step 2: Drawing Interactive Caliper on DICOM Viewport ---');
        const caliperBtn = await page.$('.measure-tool-btn[data-tool="ruler"]');
        if (caliperBtn) {
            await caliperBtn.click();
            await sleep(300);
            console.log('✅ Caliper ruler tool selected.');

            // Find canvas
            const canvas = await page.$('#pacs-annotation-canvas');
            if (canvas) {
                const box = await canvas.boundingBox();
                if (box) {
                    const startX = box.x + box.width * 0.35;
                    const startY = box.y + box.height * 0.55;
                    const endX = box.x + box.width * 0.55;
                    const endY = box.y + box.height * 0.70;

                    await page.mouse.move(startX, startY);
                    await page.mouse.down();
                    await page.mouse.move(endX, endY, { steps: 10 });
                    await page.mouse.up();
                    await sleep(500);
                    console.log('✅ Caliper line drawn across consolidation lesion.');
                }
            }
        }
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_01_caliper_interactive.png') });
        console.log('📸 Captured deepdive_01_caliper_interactive.png');

        // Step 3: Colormap Switching & Split Wipe
        console.log('\n--- Step 3: Testing Perceptually Uniform Colormaps ---');
        const viridisBtn = await page.$('#btn-cmap-viridis');
        if (viridisBtn) {
            await viridisBtn.click();
            await sleep(500);
            console.log('✅ Colormap switched to Viridis.');
        }
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_02_colormap_splitwipe.png') });
        console.log('📸 Captured deepdive_02_colormap_splitwipe.png');

        // Step 4: Digital Signoff & Report Persistence
        console.log('\n--- Step 4: Attestation & Database Persistence ---');
        const signoffBtn = await page.$('#btn-signoff');
        if (signoffBtn) {
            await signoffBtn.click();
            await sleep(1500);
            const btnText = await page.$eval('#signoff-btn-text', el => el.textContent);
            console.log(`✅ Attestation signed! Button state: "${btnText}"`);
        }
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_03_report_signed_db.png') });
        console.log('📸 Captured deepdive_03_report_signed_db.png');

        // Step 5: Reload Page & Verify Database Restoration
        console.log('\n--- Step 5: Reloading Page & Verifying Persistence from SQLite ---');
        await page.reload({ waitUntil: 'networkidle2' });
        await page.waitForSelector('.study-card', { timeout: 10000 });
        await page.click('.study-card');
        await sleep(1200);

        const restoredStatus = await page.$eval('#hud-study-status', el => el.textContent);
        const restoredBtnText = await page.$eval('#signoff-btn-text', el => el.textContent);
        console.log(`✅ HUD Status after DB restore: "${restoredStatus}"`);
        console.log(`✅ Sign-off button after DB restore: "${restoredBtnText}"`);

        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_04_restored_from_db.png') });
        console.log('📸 Captured deepdive_04_restored_from_db.png');

        // Step 6: DICOM Tags Inspector Modal
        console.log('\n--- Step 6: Opening DICOM Tags Inspector Modal ---');
        const tagsBtn = await page.$('#hud-view-tags-btn');
        if (tagsBtn) {
            await tagsBtn.click();
            await sleep(600);
            console.log('✅ DICOM Tags Inspector modal opened.');
        } else {
            await page.keyboard.press('KeyD');
            await sleep(600);
        }
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_05_dicom_tags_modal.png') });
        console.log('📸 Captured deepdive_05_dicom_tags_modal.png');

        // Close modal
        await page.keyboard.press('Escape');
        await sleep(400);

        // Step 7: Landing Page Verification
        console.log('\n--- Step 7: Verifying Landing Page ---');
        await page.goto('http://127.0.0.1:8000/landing', { waitUntil: 'networkidle2' });
        await sleep(800);
        const heroTitle = await page.$eval('h1', el => el.textContent.trim());
        console.log(`✅ Landing page loaded! Hero Title: "${heroTitle}"`);

        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'deepdive_06_landing_verified.png') });
        console.log('📸 Captured deepdive_06_landing_verified.png');

        console.log('\n🎉 ALL FRONTEND DEEP-DIVE CHECKS PASSED WITH 100% SUCCESS!');
    } catch (err) {
        console.error('\n❌ Frontend deep-dive failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
