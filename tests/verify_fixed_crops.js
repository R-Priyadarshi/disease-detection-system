const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    console.log('🔍 Verifying layout fixes and capturing close-up crops...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 }); // 2x retina for super crisp crops

    page.on('console', msg => console.log('PAGE LOG:', msg.text()));
    page.on('pageerror', err => console.log('PAGE ERROR:', err.message));

    try {
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 20000 });
        console.log('✅ Connected to http://localhost:8000/');

        await page.waitForSelector('.triage-actions-bar', { timeout: 5000 });
        console.log('✅ Found .triage-actions-bar');
        await page.waitForSelector('.study-card', { timeout: 10000 });
        await new Promise(r => setTimeout(r, 1500));

        // 1. Verify Triage Actions Bar Overflow & Sizing
        const triageBarMetrics = await page.evaluate(() => {
            const bar = document.querySelector('.triage-actions-bar');
            const btns = Array.from(bar.querySelectorAll('.btn-quick-upload'));
            return {
                barScrollWidth: bar.scrollWidth,
                barClientWidth: bar.clientWidth,
                hasHorizontalOverflow: bar.scrollWidth > bar.clientWidth,
                buttons: btns.map(b => ({
                    id: b.id,
                    text: b.innerText.trim(),
                    width: b.offsetWidth,
                    scrollWidth: b.scrollWidth,
                    clipped: b.scrollWidth > b.offsetWidth
                }))
            };
        });
        console.log('📊 Triage Actions Bar Metrics:', JSON.stringify(triageBarMetrics, null, 2));

        // 2. Capture Exact Crop matching User Pic 2
        const triageBarEl = await page.$('.triage-actions-bar');
        const triageBarCropPath = path.join(artifactDir, 'crop_01_triage_actions_bar.png');
        await triageBarEl.screenshot({ path: triageBarCropPath });
        console.log(`📸 Saved triage actions bar crop: ${triageBarCropPath}`);

        // Also capture context crop (header + tabs + actions bar + top study card)
        const triagePanelEl = await page.$('#ingestion-panel');
        const triageHeaderCropPath = path.join(artifactDir, 'crop_02_triage_panel_context.png');
        const panelBox = await triagePanelEl.boundingBox();
        await page.screenshot({
            path: triageHeaderCropPath,
            clip: {
                x: panelBox.x,
                y: panelBox.y,
                width: panelBox.width,
                height: 280
            }
        });
        console.log(`📸 Saved triage panel context crop: ${triageHeaderCropPath}`);

        // 3. Inspect and Crop Multilabel Findings
        const multilabelMetrics = await page.evaluate(() => {
            const strip = document.querySelector('.viewport-inspector .multilabel-findings-strip');
            const chips = Array.from(strip.querySelectorAll('.pathology-chip'));
            return {
                count: chips.length,
                stripWidth: strip.offsetWidth,
                chips: chips.map(c => {
                    const title = c.querySelector('.pathology-chip-title');
                    const badge = c.querySelector('.pathology-chip-prob');
                    return {
                        title: title ? title.innerText : '',
                        prob: badge ? badge.innerText : '',
                        isOverflowing: title ? title.scrollWidth > title.offsetWidth : false
                    };
                })
            };
        });
        console.log('📊 Multilabel Findings Metrics:', JSON.stringify(multilabelMetrics, null, 2));

        const multilabelEl = await page.$('#multilabel-panel');
        const multilabelCropPath = path.join(artifactDir, 'crop_03_multilabel_findings.png');
        await multilabelEl.screenshot({ path: multilabelCropPath });
        console.log(`📸 Saved multilabel findings crop: ${multilabelCropPath}`);

        // 4. Test Caliper and Bottom Viewport HUD
        await page.click('#tool-ruler');
        await new Promise(r => setTimeout(r, 200));

        // Draw caliper line to activate Clear button
        const canvasBox = await page.$eval('#pacs-annotation-canvas', el => {
            const r = el.getBoundingClientRect();
            return { x: r.left, y: r.top, w: r.width, h: r.height };
        });
        await page.mouse.move(canvasBox.x + canvasBox.w * 0.35, canvasBox.y + canvasBox.h * 0.45);
        await page.mouse.down();
        await page.mouse.move(canvasBox.x + canvasBox.w * 0.55, canvasBox.y + canvasBox.h * 0.45, { steps: 5 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 300));

        const bottomViewportCropPath = path.join(artifactDir, 'crop_04_bottom_viewport_hud_caliper.png');
        const caliperToolbarEl = await page.$('#pacs-measure-toolbar');
        if (caliperToolbarEl) {
            await caliperToolbarEl.screenshot({ path: bottomViewportCropPath });
            console.log(`📸 Saved bottom Caliper capsule crop: ${bottomViewportCropPath}`);
        }

        // 5. Full Workstation Screenshot
        const fullWorkstationPath = path.join(artifactDir, 'alveon_os_workstation_verified.png');
        await page.screenshot({ path: fullWorkstationPath, fullPage: false });
        console.log(`📸 Saved full workstation screenshot: ${fullWorkstationPath}`);

        console.log('🎉 Verification completed successfully!');
    } catch (err) {
        console.error('❌ Verification failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
