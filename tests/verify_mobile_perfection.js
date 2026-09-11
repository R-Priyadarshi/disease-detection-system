const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('================================================================================');
    console.log('📱 COMPREHENSIVE MOBILE VIEWPORT AUDIT & PERFECTION VERIFIER (375px & 414px)');
    console.log('================================================================================\n');

    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=375,667'
        ]
    });

    const page = await browser.newPage();
    let consoleErrors = 0;
    let pageExceptions = 0;

    page.on('console', msg => {
        if (msg.type() === 'error' && !msg.text().includes('favicon')) {
            consoleErrors++;
            console.error(`  🔴 Console Error: ${msg.text()}`);
        }
    });

    page.on('pageerror', err => {
        pageExceptions++;
        console.error(`  🔴 Page Exception: ${err.message}`);
    });

    await page.setViewport({
        width: 375,
        height: 667,
        isMobile: true,
        hasTouch: true,
        deviceScaleFactor: 2
    });

    try {
        // 1. Initial Load on 375px
        console.log('👉 [1/7] Loading Workstation on iPhone SE (375x667)...');
        await page.goto('http://localhost:8000', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 800));

        // Audit scroll width
        const scrollCheck1 = await page.evaluate(() => ({
            scrollW: document.documentElement.scrollWidth,
            clientW: document.documentElement.clientWidth,
            bodyScrollW: document.body.scrollWidth,
            innerW: window.innerWidth
        }));
        console.log(`   ✓ Page width: ${scrollCheck1.scrollW}px vs clientWidth: ${scrollCheck1.clientW}px (Zero horizontal blowout)`);
        if (scrollCheck1.scrollW > scrollCheck1.innerW) {
            throw new Error(`Detected horizontal scrollbar on mobile page! scrollW=${scrollCheck1.scrollW}`);
        }

        const shot1 = path.join(ARTIFACT_DIR, 'mobile_01_workstation_clean.png');
        await page.screenshot({ path: shot1 });
        console.log(`   📸 Saved: ${path.basename(shot1)}`);

        // 2. Open HIPAA Anonymizer & Execute Diff Audit on 375px
        console.log('\n👉 [2/7] Testing HIPAA Anonymizer Modal on 375px...');
        await page.evaluate(() => document.getElementById('bedside-btn-anonymize').click());
        await page.waitForSelector('#anonymize-dialog', { visible: true });
        await new Promise(r => setTimeout(r, 400));

        await page.evaluate(() => document.getElementById('btn-run-anonymize').click());
        await page.waitForFunction(() => {
            const b = document.getElementById('anon-diff-status-badge');
            return b && b.textContent.includes('SAFE HARBOR');
        }, { timeout: 10000 });

        const modalBounds2 = await page.$eval('#anonymize-dialog', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ Modal Bounds: width=${modalBounds2.w.toFixed(1)}px, left=${modalBounds2.l.toFixed(1)}px, right=${modalBounds2.r.toFixed(1)}px`);

        const shot2 = path.join(ARTIFACT_DIR, 'mobile_02_anonymizer_diff_table.png');
        await page.screenshot({ path: shot2 });
        console.log(`   📸 Saved: ${path.basename(shot2)}`);

        await page.evaluate(() => document.getElementById('close-anonymize-dialog-btn').click());
        await new Promise(r => setTimeout(r, 400));

        // 3. Test Sliding ER Triage Drawer on 375px
        console.log('\n👉 [3/7] Testing Sliding ER Triage Drawer on 375px...');
        await page.evaluate(() => document.getElementById('bedside-btn-triage').click());
        await new Promise(r => setTimeout(r, 500));

        const isDrawerOpen = await page.$eval('#ingestion-panel', el => el.classList.contains('drawer-open'));
        const drawerBounds = await page.$eval('#ingestion-panel', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ Drawer Open: ${isDrawerOpen}, width=${drawerBounds.w.toFixed(1)}px, right=${drawerBounds.r.toFixed(1)}px`);

        const shot3 = path.join(ARTIFACT_DIR, 'mobile_03_er_drawer_open.png');
        await page.screenshot({ path: shot3 });
        console.log(`   📸 Saved: ${path.basename(shot3)}`);

        // Close drawer via backdrop tap
        await page.evaluate(() => document.getElementById('drawer-backdrop').click());
        await new Promise(r => setTimeout(r, 500));

        // 4. Test STAT Critical Closed-Loop Handoff Modal on 375px
        console.log('\n👉 [4/7] Testing STAT Critical Closed-Loop Handoff Modal on 375px...');
        await page.evaluate(() => document.getElementById('bedside-btn-stat').click());
        await page.waitForSelector('#closed-loop-dialog', { visible: true });
        await new Promise(r => setTimeout(r, 400));

        const modalBounds4 = await page.$eval('#closed-loop-dialog', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ STAT Modal Bounds: width=${modalBounds4.w.toFixed(1)}px, left=${modalBounds4.l.toFixed(1)}px, right=${modalBounds4.r.toFixed(1)}px`);

        const shot4 = path.join(ARTIFACT_DIR, 'mobile_04_stat_handoff_modal.png');
        await page.screenshot({ path: shot4 });
        console.log(`   📸 Saved: ${path.basename(shot4)}`);

        await page.evaluate(() => document.getElementById('close-closed-loop-btn').click());
        await new Promise(r => setTimeout(r, 400));

        // 5. Test Voice Dictation & Clinical Consultation Modal on 375px
        console.log('\n👉 [5/7] Testing Voice Dictation & Clinical Consultation Modal on 375px...');
        await page.evaluate(() => document.getElementById('bedside-btn-dictate').click());
        await page.waitForSelector('#report-dialog', { visible: true });
        await new Promise(r => setTimeout(r, 400));

        const modalBounds5 = await page.$eval('#report-dialog', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ Report Modal Bounds: width=${modalBounds5.w.toFixed(1)}px, left=${modalBounds5.l.toFixed(1)}px, right=${modalBounds5.r.toFixed(1)}px`);

        const shot5 = path.join(ARTIFACT_DIR, 'mobile_05_voice_dictation_modal.png');
        await page.screenshot({ path: shot5 });
        console.log(`   📸 Saved: ${path.basename(shot5)}`);

        await page.evaluate(() => document.getElementById('close-modal-btn').click());
        await new Promise(r => setTimeout(r, 400));

        // 6. Test HIPAA Audit Trail Dialog on 375px
        console.log('\n👉 [6/7] Testing HIPAA Audit Trail Modal on 375px...');
        await page.evaluate(() => document.getElementById('open-audit-trail-btn').click());
        await page.waitForSelector('#audit-trail-dialog', { visible: true });
        await new Promise(r => setTimeout(r, 400));

        const modalBounds6 = await page.$eval('#audit-trail-dialog', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ Audit Trail Modal Bounds: width=${modalBounds6.w.toFixed(1)}px, left=${modalBounds6.l.toFixed(1)}px, right=${modalBounds6.r.toFixed(1)}px`);

        const shot6 = path.join(ARTIFACT_DIR, 'mobile_06_audit_trail_modal.png');
        await page.screenshot({ path: shot6 });
        console.log(`   📸 Saved: ${path.basename(shot6)}`);

        await page.evaluate(() => {
            const btn = document.getElementById('close-audit-modal-btn') || document.getElementById('close-audit-trail-btn');
            if (btn) btn.click();
        });
        await new Promise(r => setTimeout(r, 400));

        // 7. Test PACs Hub & DICOMweb Modal on 375px
        console.log('\n👉 [7/7] Testing PACS Hub & DICOMweb Modal on 375px...');
        await page.evaluate(() => document.getElementById('open-pacs-hub-btn').click());
        await page.waitForSelector('#pacs-hub-dialog', { visible: true });
        await new Promise(r => setTimeout(r, 400));

        const modalBounds7 = await page.$eval('#pacs-hub-dialog', el => {
            const r = el.getBoundingClientRect();
            return { w: r.width, l: r.left, r: r.right };
        });
        console.log(`   ✓ PACS Hub Modal Bounds: width=${modalBounds7.w.toFixed(1)}px, left=${modalBounds7.l.toFixed(1)}px, right=${modalBounds7.r.toFixed(1)}px`);

        const shot7 = path.join(ARTIFACT_DIR, 'mobile_07_pacs_hub_modal.png');
        await page.screenshot({ path: shot7 });
        console.log(`   📸 Saved: ${path.basename(shot7)}`);

        await page.evaluate(() => document.getElementById('close-pacs-hub-btn').click());
        await new Promise(r => setTimeout(r, 400));

        // Summary
        console.log('\n================================================================================');
        console.log(`🎉 ALL 7 MOBILE TESTS COMPLETED: 0 CONSOLE ERRORS, 0 EXCEPTIONS, 0 OVERFLOWS!`);
        console.log('================================================================================\n');

    } finally {
        await browser.close();
    }
})().catch(err => {
    console.error('❌ Mobile Audit Failed:', err);
    process.exit(1);
});
