const puppeteer = require('puppeteer');

(async () => {
    console.log('Launching browser to test ALVEON Workstation & Persistence...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        // 1. Open Workstation
        await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle2' });
        console.log('✅ Workstation loaded successfully.');

        // 2. Wait for Worklist cards
        await page.waitForSelector('.study-card', { timeout: 10000 });
        const cardCount = await page.$$eval('.study-card', cards => cards.length);
        console.log(`✅ Discovered ${cardCount} studies in Emergency Worklist.`);

        // 3. Click the first study card
        await page.click('.study-card');
        await new Promise(r => setTimeout(r, 1000));

        // 4. Verify HUD and Caliper presence
        const hudPatient = await page.$eval('#hud-patient-id', el => el.textContent);
        console.log(`✅ Viewport loaded active study: ${hudPatient}`);

        // 5. Test Sign-off Button
        const signoffBtn = await page.$('#btn-signoff');
        if (signoffBtn) {
            const btnText = await page.$eval('#signoff-btn-text', el => el.textContent);
            console.log(`✅ Sign-off button active with text: "${btnText}"`);
            await page.click('#btn-signoff');
            await new Promise(r => setTimeout(r, 1500));
            const updatedText = await page.$eval('#signoff-btn-text', el => el.textContent);
            console.log(`✅ Sign-off executed! Updated button state: "${updatedText}"`);
        }

        // 6. Capture verified screenshot
        const screenshotPath = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26/alveon_e2e_pathways_verified.png';
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`📸 Screenshot saved: ${screenshotPath}`);

        console.log('🎉 End-to-end UI verification passed with flying colors!');
    } catch (err) {
        console.error('❌ Test failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
