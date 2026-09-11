const puppeteer = require('puppeteer');
const path = require('path');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

(async () => {
    console.log('🚀 Starting Landing Page Deep-Dive Verification...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--window-size=1440,900']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        const errors = [];
        page.on('pageerror', err => {
            console.error('❌ Page Error:', err.message);
            errors.push(err.message);
        });

        console.log('1. Loading http://127.0.0.1:8000/landing ...');
        await page.goto('http://127.0.0.1:8000/landing', { waitUntil: 'networkidle2' });
        await sleep(1000);

        // Verify Trust Badges Bar
        const trustBadges = await page.$$('.trust-badge');
        console.log(`  ✓ Found ${trustBadges.length} Trust & Regulatory Badges.`);

        // Test Interactive Case Selector
        console.log('2. Testing Interactive Pathology Case Explorer...');
        const caseBtns = await page.$$('.case-btn');
        console.log(`  ✓ Found ${caseBtns.length} Case Switcher Buttons.`);

        // Click Case 2 (Effusion)
        await page.click('.case-btn[data-case="effusion"]');
        await sleep(300);
        let title = await page.$eval('#mock-window-title', el => el.textContent);
        let urgency = await page.$eval('#mock-urgency-tag', el => el.textContent);
        console.log(`  ✓ Switched to Effusion: Title="${title}", Urgency="${urgency}"`);

        // Click Case 3 (Stroke)
        await page.click('.case-btn[data-case="stroke"]');
        await sleep(300);
        title = await page.$eval('#mock-window-title', el => el.textContent);
        urgency = await page.$eval('#mock-urgency-tag', el => el.textContent);
        console.log(`  ✓ Switched to Neuro Stroke: Title="${title}", Urgency="${urgency}"`);

        // Click Case 4 (Normal)
        await page.click('.case-btn[data-case="normal"]');
        await sleep(300);
        title = await page.$eval('#mock-window-title', el => el.textContent);
        console.log(`  ✓ Switched to Normal Baseline: Title="${title}"`);

        // Click back to Case 1 (Pneumothorax)
        await page.click('.case-btn[data-case="pneumothorax"]');
        await sleep(300);

        // Screenshot Hero & Cases
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'landing_v2_01_hero_cases.png') });
        console.log('  📸 Captured landing_v2_01_hero_cases.png');

        // 3. Scroll to Benchmarks & Comparison
        console.log('3. Scrolling to Benchmarks & Comparison Matrix...');
        await page.evaluate(() => {
            document.getElementById('benchmarks').scrollIntoView();
        });
        await sleep(600);
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'landing_v2_02_benchmarks.png') });
        console.log('  📸 Captured landing_v2_02_benchmarks.png');

        // Scroll to Comparison
        await page.evaluate(() => {
            document.getElementById('comparison').scrollIntoView();
        });
        await sleep(600);
        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'landing_v2_03_comparison.png') });
        console.log('  📸 Captured landing_v2_03_comparison.png');

        // 4. Scroll to Specs & Deployment Terminal
        console.log('4. Testing Technical Specs & Deployment Terminal...');
        await page.evaluate(() => {
            document.getElementById('deployment').scrollIntoView();
        });
        await sleep(400);

        // Click Terminal Tabs
        await page.click('.terminal-tab-btn[data-tab="hf"]');
        await sleep(200);
        let terminalText = await page.$eval('#terminal-code-display', el => el.textContent);
        console.log(`  ✓ Hugging Face Tab Active: Contains "${terminalText.substring(0, 45)}..."`);

        await page.click('.terminal-tab-btn[data-tab="render"]');
        await sleep(200);
        await page.click('.terminal-tab-btn[data-tab="docker"]');
        await sleep(200);

        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'landing_v2_04_terminal_specs.png') });
        console.log('  📸 Captured landing_v2_04_terminal_specs.png');

        // 5. Scroll to FAQ Accordion
        console.log('5. Testing FAQ Accordion...');
        await page.evaluate(() => {
            document.getElementById('faq').scrollIntoView();
        });
        await sleep(400);

        // Click question 2 to expand
        const questions = await page.$$('.faq-question');
        if (questions.length >= 2) {
            await questions[1].click();
            await sleep(300);
            console.log('  ✓ Toggled Question 2 in FAQ Accordion.');
        }

        await page.screenshot({ path: path.join(ARTIFACT_DIR, 'landing_v2_05_faq.png') });
        console.log('  📸 Captured landing_v2_05_faq.png');

        if (errors.length > 0) {
            console.error(`❌ Total Uncaught Errors: ${errors.length}`);
            process.exit(1);
        } else {
            console.log('🎉 ALL LANDING PAGE INTERACTIVE VERIFICATIONS PASSED WITH 0 ERRORS!');
        }

    } catch (e) {
        console.error('Fatal Error:', e);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
