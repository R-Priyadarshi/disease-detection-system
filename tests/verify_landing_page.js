/**
 * ============================================================================
 * ALVEON PACS v5.1 — EXECUTIVE LANDING PAGE VERIFICATION SUITE
 * ============================================================================
 * Autonomous validation of the executive landing page, responsiveness across
 * desktop/mobile, seamless bidirectional navigation to the workstation, and
 * zero console/network errors.
 * ============================================================================
 */

const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACTS_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('================================================================================');
    console.log('🌟 ALVEON PACS v5.1 — EXECUTIVE LANDING PAGE AUDIT');
    console.log('================================================================================\n');

    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--window-size=1920,1080'
        ]
    });

    const page = await browser.newPage();
    let consoleErrors = [];
    let pageExceptions = [];
    let networkFailures = [];

    page.on('console', msg => {
        if (msg.type() === 'error' && !msg.text().includes('favicon')) {
            consoleErrors.push(msg.text());
            console.error(`  🔴 Console Error: ${msg.text()}`);
        }
    });

    page.on('pageerror', err => {
        pageExceptions.push(err.message);
        console.error(`  🔴 Page Exception: ${err.message}`);
    });

    page.on('requestfailed', req => {
        if (!req.url().includes('favicon')) {
            networkFailures.push(`${req.method()} ${req.url()} - ${req.failure().errorText}`);
            console.error(`  🔴 Network Failure: ${req.method()} ${req.url()} (${req.failure().errorText})`);
        }
    });

    try {
        // ---------------------------------------------------------------------
        // STEP 1: Desktop Landing Page Loading (1920x1080)
        // ---------------------------------------------------------------------
        console.log('👉 [STEP 1/5] Loading Executive Landing Page at http://localhost:8000/landing (1920x1080)...');
        await page.setViewport({ width: 1920, height: 1080 });
        await page.goto('http://localhost:8000/landing', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 600));

        const pageMeta = await page.evaluate(() => ({
            title: document.title,
            h1: document.querySelector('h1')?.textContent?.trim().replace(/\s+/g, ' '),
            heroPill: document.getElementById('live-system-beacon')?.textContent?.trim(),
            bentoCardsCount: document.querySelectorAll('.bento-card').length,
            metricCardsCount: document.querySelectorAll('.metric-card').length,
            workflowStepsCount: document.querySelectorAll('.workflow-step').length
        }));

        console.log(`   ✓ Page Title: "${pageMeta.title}"`);
        console.log(`   ✓ Hero Headline: "${pageMeta.h1}"`);
        console.log(`   ✓ Live Telemetry Beacon: "${pageMeta.heroPill}"`);
        console.log(`   ✓ Bento Grid Pillars: ${pageMeta.bentoCardsCount} cards`);
        console.log(`   ✓ Performance Metric Cards: ${pageMeta.metricCardsCount} cards`);
        console.log(`   ✓ Clinical Workflow Steps: ${pageMeta.workflowStepsCount} steps`);

        if (pageMeta.bentoCardsCount !== 6) throw new Error(`Expected 6 bento cards, found ${pageMeta.bentoCardsCount}`);
        if (pageMeta.metricCardsCount !== 4) throw new Error(`Expected 4 metric cards, found ${pageMeta.metricCardsCount}`);

        const shot1 = path.join(ARTIFACTS_DIR, 'landing_01_desktop.png');
        await page.screenshot({ path: shot1, fullPage: false });
        console.log(`   📸 Saved: ${path.basename(shot1)}`);

        // ---------------------------------------------------------------------
        // STEP 2: Bidirectional Navigation (Landing -> Workstation)
        // ---------------------------------------------------------------------
        console.log('\n👉 [STEP 2/5] Testing "Launch Workstation" CTA Gateway...');
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0' }),
            page.evaluate(() => document.getElementById('hero-btn-launch')?.click())
        ]);
        await new Promise(r => setTimeout(r, 800));

        const currentUrl = page.url();
        const studyCardsCount = await page.$$eval('.study-card', els => els.length);
        console.log(`   ✓ Successfully navigated to: ${currentUrl}`);
        console.log(`   ✓ Active Triage Worklist Loaded: ${studyCardsCount} clinical studies`);
        if (studyCardsCount === 0) throw new Error('Workstation did not populate study cards!');

        const shot2 = path.join(ARTIFACTS_DIR, 'landing_02_workstation_nav.png');
        await page.screenshot({ path: shot2 });
        console.log(`   📸 Saved: ${path.basename(shot2)}`);

        // ---------------------------------------------------------------------
        // STEP 3: Bidirectional Return Navigation (Workstation -> Landing)
        // ---------------------------------------------------------------------
        console.log('\n👉 [STEP 3/5] Testing Workstation Header "Overview" Button...');
        const overviewBtnExists = await page.$('#open-landing-btn');
        if (!overviewBtnExists) throw new Error('Header #open-landing-btn not found in workstation!');

        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle0' }),
            page.evaluate(() => document.getElementById('open-landing-btn')?.click())
        ]);
        await new Promise(r => setTimeout(r, 600));

        const returnedUrl = page.url();
        console.log(`   ✓ Successfully returned to landing page: ${returnedUrl}`);
        if (!returnedUrl.includes('/landing')) throw new Error(`Expected URL to contain /landing, got ${returnedUrl}`);

        // ---------------------------------------------------------------------
        // STEP 4: Mobile Viewport Audit (375x667 iPhone SE)
        // ---------------------------------------------------------------------
        console.log('\n👉 [STEP 4/5] Auditing Mobile Boundary Containment (iPhone SE 375x667)...');
        await page.setViewport({ width: 375, height: 667, isMobile: true, hasTouch: true });
        await new Promise(r => setTimeout(r, 600));

        const mobileCheck = await page.evaluate(() => ({
            scrollW: document.documentElement.scrollWidth,
            innerW: window.innerWidth,
            bodyScrollW: document.body.scrollWidth
        }));

        console.log(`   ✓ Document scrollWidth: ${mobileCheck.scrollW}px vs Viewport: ${mobileCheck.innerW}px`);
        if (mobileCheck.scrollW > mobileCheck.innerW) {
            throw new Error(`Horizontal blowout on landing page! scrollWidth=${mobileCheck.scrollW} > innerWidth=${mobileCheck.innerW}`);
        }

        const shot3 = path.join(ARTIFACTS_DIR, 'landing_03_mobile_375px.png');
        await page.screenshot({ path: shot3, fullPage: false });
        console.log(`   📸 Saved: ${path.basename(shot3)}`);

        // ---------------------------------------------------------------------
        // STEP 5: Production Runtime Stability & Health
        // ---------------------------------------------------------------------
        console.log('\n👉 [STEP 5/5] Production Stability & Health Audit...');
        console.log(`   • Browser Console Errors : ${consoleErrors.length}`);
        console.log(`   • Uncaught Exceptions    : ${pageExceptions.length}`);
        console.log(`   • Network Failures       : ${networkFailures.length}`);

        if (consoleErrors.length > 0 || pageExceptions.length > 0 || networkFailures.length > 0) {
            throw new Error('Runtime health audit failed on landing page!');
        }

        console.log('\n================================================================================');
        console.log('🏆 LANDING PAGE VERIFICATION: 100% SUCCESS WITH ZERO DEFECTS!');
        console.log('================================================================================\n');

    } finally {
        await browser.close();
    }
})().catch(err => {
    console.error('❌ Landing Page Verification Failed:', err);
    process.exit(1);
});
