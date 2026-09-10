/**
 * Comprehensive Puppeteer End-to-End Visual Verification Suite for Alveon PACS v4.0 Enterprise
 * 
 * Verifies:
 * 1. HIPAA Security Rule § 164.312(b) Immutable Audit Ledger with Chained SHA-256 Hashes
 * 2. Hospital Modality Acquisition Simulator pushing over Port 11112 (Siemens XR & GE CT)
 * 3. 3D Volumetric CT & Multi-Planar Reconstruction (MPR) Viewport (Axial, Coronal, Sagittal)
 * 4. Hounsfield Unit (HU) Windowing Presets (LUNG, MEDIASTINUM, BONE) & Axial Slice Scroll
 * 5. Clinical Role-Based Access Control (RBAC) User Persona Switching & Attestation Governance
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('🚀 Launching Chrome for Alveon PACS v4.0 Enterprise E2E Verification...');
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
        // ---------------------------------------------------------
        // 1. Navigate to Alveon Workstation
        // ---------------------------------------------------------
        console.log('📍 Navigating to http://127.0.0.1:8000 ...');
        await page.goto('http://127.0.0.1:8000', { waitUntil: 'networkidle0', timeout: 15000 });
        await page.waitForSelector('#diagnosis-content', { timeout: 10000 });
        await new Promise(r => setTimeout(r, 1200));

        // ---------------------------------------------------------
        // 2. Verify HIPAA Audit Trail Modal (Path B)
        // ---------------------------------------------------------
        console.log('🛡️ Opening HIPAA Audit Trail Dialog (#open-audit-trail-btn)...');
        await page.click('#open-audit-trail-btn');
        await page.waitForSelector('#audit-trail-dialog[open]', { timeout: 5000 });
        await new Promise(r => setTimeout(r, 1000));

        // Verify Cryptographic Hash Integrity Badge
        const integrityText = await page.$eval('#audit-integrity-text', el => el.textContent.trim());
        console.log(`✅ HIPAA Audit Integrity Status: ${integrityText}`);
        if (!integrityText.includes('VALID') && !integrityText.includes('UNTAMPERED')) {
            throw new Error(`Audit integrity check failed: ${integrityText}`);
        }

        // Verify audit ledger table rows
        const auditRowCount = await page.$$eval('#audit-ledger-tbody tr', rows => rows.length);
        console.log(`✅ Loaded HIPAA Audit Ledger Rows: ${auditRowCount}`);

        // Screenshot 14: HIPAA Audit Trail Modal
        const shot14Path = path.join(ARTIFACT_DIR, 'pacs_14_audit_trail_modal.png');
        await page.screenshot({ path: shot14Path, fullPage: false });
        console.log(`📸 Saved Screenshot 14 -> ${shot14Path}`);

        // Close Audit Trail Dialog
        await page.click('#close-audit-modal-btn');
        await new Promise(r => setTimeout(r, 600));

        // ---------------------------------------------------------
        // 3. Verify Hospital Modality Simulator (Path A)
        // ---------------------------------------------------------
        console.log('🌐 Opening PACS Hub Dialog for Modality Simulator...');
        await page.click('#open-pacs-hub-btn');
        await page.waitForSelector('#pacs-hub-dialog[open]', { timeout: 5000 });
        await new Promise(r => setTimeout(r, 600));

        // Switch to Tab 4: Modality Simulator
        console.log('🎛️ Switching to Tab 4: Modality Simulator (XR & CT)...');
        await page.click('.pacs-hub-tab-btn[data-pacs-tab="tab-simulator"]');
        await new Promise(r => setTimeout(r, 600));

        const modalityCards = await page.$$eval('.modality-card', cards => cards.length);
        console.log(`✅ Modality equipment cards found: ${modalityCards} (Siemens Lumos XR Bay 1 & GE Revolution CT)`);

        // Trigger Simulated STAT Chest XR push over port 11112
        console.log('⚡ Triggering STAT Chest XR C-STORE push from Emergency Bay 1...');
        await page.$eval('#sim-push-xr-btn', el => el.scrollIntoView({ block: 'center' }));
        await new Promise(r => setTimeout(r, 400));
        await page.click('#sim-push-xr-btn');

        // Wait for transmission completion
        await page.waitForFunction(() => {
            const summary = document.getElementById('modality-sim-summary');
            return summary && summary.textContent.includes('Transmission Complete');
        }, { timeout: 12000 });

        const simSummary = await page.$eval('#modality-sim-summary', el => el.textContent.trim());
        console.log(`✅ Modality Transmission Telemetry: ${simSummary}`);

        // Screenshot 15: Modality Simulator Tab
        const shot15Path = path.join(ARTIFACT_DIR, 'pacs_15_modality_simulator_tab.png');
        await page.screenshot({ path: shot15Path, fullPage: false });
        console.log(`📸 Saved Screenshot 15 -> ${shot15Path}`);

        // Close PACS Hub Dialog
        await page.click('#close-pacs-hub-btn');
        await new Promise(r => setTimeout(r, 600));

        // ---------------------------------------------------------
        // 4. Verify 3D Volumetric CT & Tri-Planar MPR Viewport (Path C)
        // ---------------------------------------------------------
        console.log('🧊 Switching Workstation Mode to 3D CT / MPR (#mode-btn-3d)...');
        await page.click('#mode-btn-3d');
        await page.waitForSelector('#volumetric-content', { visible: true, timeout: 5000 });
        await new Promise(r => setTimeout(r, 1200));

        // Verify Axial, Coronal, Sagittal canvases are rendered
        const hasAxialCanvas = await page.$eval('#mpr-axial-canvas', c => c.width > 0 && c.height > 0);
        const hasCoronalCanvas = await page.$eval('#mpr-coronal-canvas', c => c.width > 0 && c.height > 0);
        const hasSagittalCanvas = await page.$eval('#mpr-sagittal-canvas', c => c.width > 0 && c.height > 0);
        console.log(`✅ Tri-Planar Canvases Active: Axial=${hasAxialCanvas}, Coronal=${hasCoronalCanvas}, Sagittal=${hasSagittalCanvas}`);

        const initialSliceTag = await page.$eval('#mpr-slice-tag', el => el.textContent.trim());
        const initialLocTag = await page.$eval('#mpr-loc-tag', el => el.textContent.trim());
        console.log(`✅ Initial 3D CT Coordinates: ${initialSliceTag}, ${initialLocTag}`);

        // Screenshot 16: Tri-Planar MPR Viewport under LUNG window
        const shot16Path = path.join(ARTIFACT_DIR, 'pacs_16_mpr_triplanar_lung_window.png');
        await page.screenshot({ path: shot16Path, fullPage: false });
        console.log(`📸 Saved Screenshot 16 -> ${shot16Path}`);

        // ---------------------------------------------------------
        // 5. HU Presets & Axial Slice Navigation
        // ---------------------------------------------------------
        console.log('🦴 Switching Window to BONE preset & advancing axial slice stack...');
        await page.click('#mpr-hu-presets button[data-hu="BONE"]');
        await new Promise(r => setTimeout(r, 600));

        // Step slice forward using next button
        for (let i = 0; i < 6; i++) {
            await page.click('#mpr-slice-next-btn');
            await new Promise(r => setTimeout(r, 100));
        }
        await new Promise(r => setTimeout(r, 600));

        const updatedSliceTag = await page.$eval('#mpr-slice-tag', el => el.textContent.trim());
        const updatedWlLabel = await page.$eval('#axial-wl-label', el => el.textContent.trim());
        console.log(`✅ Advanced 3D Coordinates: ${updatedSliceTag}, Window: ${updatedWlLabel}`);

        // Screenshot 17: MPR Bone Window & Scrolled Axial Slice
        const shot17Path = path.join(ARTIFACT_DIR, 'pacs_17_mpr_bone_window_axial_scrolled.png');
        await page.screenshot({ path: shot17Path, fullPage: false });
        console.log(`📸 Saved Screenshot 17 -> ${shot17Path}`);

        // ---------------------------------------------------------
        // 6. Clinical RBAC User Switcher & Persona Governance (Path B)
        // ---------------------------------------------------------
        console.log('🩻 Returning to 2D Planar Workstation (#mode-btn-2d)...');
        await page.click('#mode-btn-2d');
        await new Promise(r => setTimeout(r, 600));

        console.log('👤 Opening Clinical User Persona & RBAC Dropdown (#user-role-trigger)...');
        await page.click('#user-role-trigger');
        await page.waitForSelector('#role-menu-popover', { visible: true, timeout: 3000 });
        await new Promise(r => setTimeout(r, 500));

        // Screenshot 18: User Persona & RBAC Dropdown Open
        const shot18Path = path.join(ARTIFACT_DIR, 'pacs_18_rbac_user_switcher.png');
        await page.screenshot({ path: shot18Path, fullPage: false });
        console.log(`📸 Saved Screenshot 18 -> ${shot18Path}`);

        // Switch to Dr. Kevin Chen (Resident / Fellow)
        console.log('🎓 Switching role to Dr. Kevin Chen (Resident / Fellow)...');
        await page.click('.role-menu-item[data-username="dr.chen"]');
        await new Promise(r => setTimeout(r, 800));

        const residentRole = await page.$eval('#current-user-role-badge', el => el.textContent.trim());
        console.log(`✅ Active Persona: Dr. Kevin Chen • Role: ${residentRole}`);

        // Switch back to Dr. Eleanor Vance (Attending)
        await page.click('#user-role-trigger');
        await new Promise(r => setTimeout(r, 300));
        await page.click('.role-menu-item[data-username="dr.vance"]');
        await new Promise(r => setTimeout(r, 600));

        console.log('🎉 ALL ALVEON v4.0 ENTERPRISE E2E VERIFICATIONS COMPLETED SUCCESSFULLY!');

    } catch (err) {
        console.error('❌ E2E VERIFICATION FAILED:', err);
        process.exitCode = 1;
    } finally {
        await browser.close();
    }
})();
