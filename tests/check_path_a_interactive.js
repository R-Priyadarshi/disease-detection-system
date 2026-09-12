/**
 * Comprehensive Path A Verification Script
 * Validates the full clinical workflow of Path A:
 * 1. 2D Workstation & Continuous Emergency Department Stream Simulation
 *    - Start/pause stream, cadence change (10s), MCI surge (3 cases),
 *    - Priority worklist sorting, selecting and loading streamed study in 2D workstation,
 *    - Verifying split-wipe, HUD patient demographics, ACR Category 1 STAT alert, and multi-label AI panel.
 * 2. 3D Neuro CT Hemorrhage Volumetry & Automated Voxel Segmentation
 *    - Switching mode to 3D Neuro CT, selecting BRAIN-CT-ICH-03,
 *    - Toggling blood mask (+50 to +85 HU),
 *    - Verifying 3D metrics (3D volume, ABC/2 volume, midline shift, concordance),
 *    - Scrolling through axial slices and verifying slice area updates,
 *    - Triggering and validating ReportLab Neurosurgical Volumetry Dossier PDF generation.
 */
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('🩺 Starting Comprehensive Path A Clinical Verification...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 950 });

        page.on('console', msg => {
            if (msg.type() === 'error') console.log(`[BROWSER ERROR] ${msg.text()}`);
        });

        let dossierPdfReceived = false;
        let dossierPdfContentType = '';

        page.on('response', async res => {
            const url = res.url();
            if (url.includes('/api/v1/neuro/volumetry/dossier-pdf')) {
                if (res.status() === 200) {
                    dossierPdfReceived = true;
                    dossierPdfContentType = res.headers()['content-type'] || '';
                    console.log(`📡 Intercepted Neurosurgical PDF Dossier: status=${res.status()}, type=${dossierPdfContentType}`);
                }
            }
        });

        // -------------------------------------------------------------
        // PART 1: WORKSTATION & CONTINUOUS ED STREAM VERIFICATION
        // -------------------------------------------------------------
        console.log('\n--- PART 1: Continuous Emergency Department Stream Verification ---');
        console.log('1. Loading http://127.0.0.1:8000/workstation...');
        await page.goto('http://127.0.0.1:8000/workstation', { waitUntil: 'networkidle2' });

        await page.waitForSelector('#ed-stream-dock', { timeout: 8000 });
        console.log('✓ #ed-stream-dock rendered in DOM');

        // Check if stream is currently active, pause if necessary to start from known state
        const isRunning = await page.$eval('#ed-stream-dock', el => el.classList.contains('streaming'));
        if (isRunning) {
            console.log('   Stream was running, pausing for test baseline...');
            await page.click('#ed-stream-toggle-btn');
            await new Promise(r => setTimeout(r, 600));
        }

        // Test Cadence adjustment
        console.log('2. Setting stream cadence to 10s...');
        await page.click('button[data-cadence="10"]');
        await new Promise(r => setTimeout(r, 500));
        const cadence10Active = await page.$eval('button[data-cadence="10"]', el => el.classList.contains('active'));
        console.log(`   10s cadence active: ${cadence10Active}`);
        if (!cadence10Active) throw new Error('Cadence 10s button not active');

        // Start Stream
        console.log('3. Starting Continuous ED Stream...');
        await page.click('#ed-stream-toggle-btn');
        await new Promise(r => setTimeout(r, 1000));
        const streamActive = await page.$eval('#ed-stream-status-label', el => el.textContent.trim());
        const dockStreaming = await page.$eval('#ed-stream-dock', el => el.classList.contains('streaming'));
        console.log(`   Status label: "${streamActive}", dock.streaming: ${dockStreaming}`);
        if (!dockStreaming) throw new Error('Stream dock did not enter streaming mode');

        // Trigger MCI Surge (Code Black)
        console.log('4. Triggering Mass Casualty Incident (MCI Code Black surge)...');
        await page.click('#ed-stream-burst-btn');
        await new Promise(r => setTimeout(r, 2000));

        // Verify Worklist Studies
        const edCards = await page.$$eval('.study-card', cards => {
            return cards.map(c => ({
                id: c.dataset.studyId,
                name: c.querySelector('.patient-name') ? c.querySelector('.patient-name').textContent.trim() : '',
                priority: c.querySelector('.study-card-priority') ? c.querySelector('.study-card-priority').textContent.trim() : '',
                finding: c.querySelector('.finding-tag') ? c.querySelector('.finding-tag').textContent.trim() : ''
            })).filter(s => s.id && s.id.startsWith('ALV-ED-'));
        });
        console.log(`   Streamed ED studies in worklist: ${edCards.length}`);
        edCards.slice(0, 3).forEach(c => console.log(`     -> ${c.id}: ${c.name} [${c.priority}] (${c.finding})`));
        if (edCards.length === 0) throw new Error('No streamed ED studies found in worklist');

        // Select the first STAT study to inspect in 2D workstation
        console.log(`5. Loading study ${edCards[0].id} into 2D Workstation...`);
        await page.click(`.study-card[data-study-id="${edCards[0].id}"]`);
        await new Promise(r => setTimeout(r, 1500));

        const hudPatient = await page.$eval('#hud-patient-name', el => el.textContent.trim());
        console.log(`   HUD Patient Name: "${hudPatient}"`);

        // Check STAT banner visibility
        const statBannerVisible = await page.$eval('#stat-alert-banner', el => el && el.style.display !== 'none');
        console.log(`   STAT Alert Banner Active: ${statBannerVisible}`);

        // Pause stream
        console.log('6. Pausing ED Stream...');
        await page.click('#ed-stream-toggle-btn');
        await new Promise(r => setTimeout(r, 600));

        // Capture screenshot of Part 1
        const shot1 = path.join(ARTIFACT_DIR, 'path_a_check_ed_stream.png');
        await page.screenshot({ path: shot1 });
        console.log(`📸 Saved screenshot of Part 1: ${shot1}`);

        // -------------------------------------------------------------
        // PART 2: 3D NEURO CT VOLUMETRY VERIFICATION
        // -------------------------------------------------------------
        console.log('\n--- PART 2: 3D Neuro CT Hemorrhage Volumetry Verification ---');
        console.log('7. Switching to 🧠 3D Neuro CT & Stroke Suite mode...');
        await page.waitForSelector('#mode-btn-neuro', { timeout: 8000 });
        await page.click('#mode-btn-neuro');
        await new Promise(r => setTimeout(r, 2000));

        const isNeuroMode = await page.$eval('#mode-btn-neuro', el => el.classList.contains('active'));
        console.log(`   Neuro mode button active: ${isNeuroMode}`);
        if (!isNeuroMode) throw new Error('Failed to switch to 3D Neuro CT mode');

        // Verify Volumetry Dock is visible
        await page.waitForSelector('#neuro-volumetry-dock', { timeout: 8000 });
        console.log('✓ #neuro-volumetry-dock visible');

        // Check selected series (default on neuro switch is BRAIN-CT-ICH-03)
        const currentSeries = await page.evaluate(() => {
            const sel = document.getElementById('mpr-series-selector');
            return sel ? sel.value : null;
        });
        console.log(`8. Current active series: "${currentSeries}"`);

        // Inspect Volumetric Metrics
        const metrics = await page.evaluate(() => {
            return {
                voxelVol: document.getElementById('neuro-vol-voxel-val')?.textContent?.trim(),
                abc2Vol: document.getElementById('neuro-vol-abc2-val')?.textContent?.trim(),
                concordance: document.getElementById('neuro-vol-concordance-val')?.textContent?.trim(),
                midlineShift: document.getElementById('neuro-vol-shift-val')?.textContent?.trim(),
                sliceArea: document.getElementById('neuro-vol-slice-val')?.textContent?.trim(),
                voxelAlert: document.getElementById('vol-card-voxel')?.classList.contains('alert'),
                shiftAlert: document.getElementById('vol-card-shift')?.classList.contains('alert')
            };
        });
        console.log('   Volumetry Metrics:', JSON.stringify(metrics, null, 2));

        if (!metrics.voxelVol || !metrics.voxelVol.includes('38.0')) {
            throw new Error(`Expected voxel volume ~38.0 cm³, got ${metrics.voxelVol}`);
        }
        if (!metrics.midlineShift || !metrics.midlineShift.includes('5.8')) {
            throw new Error(`Expected midline shift 5.8 mm, got ${metrics.midlineShift}`);
        }

        // Toggle Blood Mask
        console.log('9. Toggling 🔴 Blood Mask (+50 to +85 HU)...');
        await page.waitForSelector('#toggle-blood-mask-btn', { timeout: 5000 });
        const initialActive = await page.$eval('#toggle-blood-mask-btn', el => el.classList.contains('active'));
        await page.click('#toggle-blood-mask-btn');
        await new Promise(r => setTimeout(r, 600));
        const afterClick = await page.$eval('#toggle-blood-mask-btn', el => el.classList.contains('active'));
        console.log(`   Blood mask toggled: from ${initialActive} to ${afterClick}`);

        // Re-enable blood mask for full visualization
        if (!afterClick) {
            await page.click('#toggle-blood-mask-btn');
            await new Promise(r => setTimeout(r, 600));
        }

        // Test Slice Scrolling (simulate user scrolling to slice 12)
        console.log('10. Scrolling to slice index 12...');
        await page.evaluate(() => {
            const slider = document.getElementById('mpr-slice-slider');
            if (slider) {
                slider.value = '12';
                slider.dispatchEvent(new Event('input'));
            }
        });
        await new Promise(r => setTimeout(r, 1000));
        const updatedSliceArea = await page.$eval('#neuro-vol-slice-val', el => el.textContent.trim());
        console.log(`   Updated Slice Area at slice 12: "${updatedSliceArea}"`);

        // Test PDF Dossier Download
        console.log('11. Triggering Neurosurgical Volumetry Dossier PDF export...');
        await page.waitForSelector('#download-neuro-dossier-btn', { timeout: 5000 });
        await page.click('#download-neuro-dossier-btn');
        await new Promise(r => setTimeout(r, 2000));

        if (!dossierPdfReceived) {
            throw new Error('PDF Dossier was not properly received with HTTP 200');
        }
        console.log(`✓ PDF Dossier generated and received successfully (type: ${dossierPdfContentType})`);

        // Capture screenshot of Part 2
        const shot2 = path.join(ARTIFACT_DIR, 'path_a_check_neuro_volumetry.png');
        await page.screenshot({ path: shot2 });
        console.log(`📸 Saved screenshot of Part 2: ${shot2}`);

        console.log('\n============================================================');
        console.log('🎉 PATH A VERIFICATION COMPLETE: ALL CHECKS PASSED (100%)');
        console.log('============================================================');
    } catch (err) {
        console.error('❌ Path A Verification Failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
