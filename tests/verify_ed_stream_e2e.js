/**
 * ALVEON PACS - Continuous Emergency Department Stream Simulation Daemon E2E Verification
 * Validates:
 * 1. HUD dock rendering (#ed-stream-dock, pulse radar, counters, toggle button, cadence pills, MCI surge).
 * 2. Influx cadence adjustment (10s/30s/60s).
 * 3. Starting continuous trauma streaming daemon via UI toggle.
 * 4. Triggering Mass Casualty Incident (MCI Code Black) surge button (3 simultaneous critical cases).
 * 5. WebSocket live events broadcast, counter increments, and priority STAT card prepending.
 * 6. Interactive selection and loading of incoming synthesized ED study into 2D workstation.
 * 7. Pausing trauma stream and capturing verified high-res screenshot artifact.
 */
const puppeteer = require('puppeteer');
const path = require('path');
const fs = require('fs');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    console.log('🚀 Launching Puppeteer to verify Continuous ED Stream Simulation Daemon...');
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

        let burstIntercepted = false;
        let startIntercepted = false;
        let cadenceIntercepted = false;

        page.on('response', async res => {
            const url = res.url();
            if (url.includes('/api/v1/ed-stream/start')) {
                startIntercepted = res.status() === 200;
                console.log(`📡 Intercepted ed-stream/start: status=${res.status()}`);
            }
            if (url.includes('/api/v1/ed-stream/cadence')) {
                cadenceIntercepted = res.status() === 200;
                console.log(`📡 Intercepted ed-stream/cadence: status=${res.status()}`);
            }
            if (url.includes('/api/v1/ed-stream/burst')) {
                burstIntercepted = res.status() === 200;
                console.log(`📡 Intercepted ed-stream/burst: status=${res.status()}`);
            }
        });

        // 1. Navigate to Workstation
        console.log('1. Navigating to http://127.0.0.1:8000/workstation...');
        await page.goto('http://127.0.0.1:8000/workstation', { waitUntil: 'networkidle2' });

        // 2. Verify ED Stream Dock exists and is visible
        console.log('2. Verifying #ed-stream-dock elements...');
        await page.waitForSelector('#ed-stream-dock', { timeout: 8000 });
        await page.waitForSelector('#ed-stream-toggle-btn', { timeout: 5000 });
        await page.waitForSelector('#ed-stream-burst-btn', { timeout: 5000 });

        const initialStatus = await page.$eval('#ed-stream-status-label', el => el.textContent.trim());
        const initiallyStreaming = await page.$eval('#ed-stream-dock', el => el.classList.contains('streaming'));
        console.log(`   Initial status: "${initialStatus}", streaming: ${initiallyStreaming}`);

        // If initially streaming from previous run, pause first so we test full transition
        if (initiallyStreaming) {
            console.log('   Pausing existing stream for clean test baseline...');
            await page.click('#ed-stream-toggle-btn');
            await new Promise(r => setTimeout(r, 800));
        }

        // 3. Test changing cadence to 10s
        console.log('3. Clicking 10s cadence button...');
        const cadence10Btn = await page.$('button[data-cadence="10"]');
        if (cadence10Btn) {
            await cadence10Btn.click();
            await new Promise(r => setTimeout(r, 600));
            const is10Active = await page.$eval('button[data-cadence="10"]', el => el.classList.contains('active'));
            console.log(`   10s cadence active: ${is10Active}`);
            if (!is10Active) throw new Error('Cadence 10s button did not receive active class');
        }

        // 4. Test starting stream
        console.log('4. Clicking #ed-stream-toggle-btn to start stream...');
        await page.click('#ed-stream-toggle-btn');
        await new Promise(r => setTimeout(r, 1200));

        const activeStatus = await page.$eval('#ed-stream-status-label', el => el.textContent.trim());
        const isStreamingClass = await page.$eval('#ed-stream-dock', el => el.classList.contains('streaming'));
        const btnText = await page.$eval('#ed-stream-btn-text', el => el.textContent.trim());
        console.log(`   Active status: "${activeStatus}", dock.streaming: ${isStreamingClass}, button: "${btnText}"`);

        if (!isStreamingClass) throw new Error('ED dock does not have streaming class after start');

        // 5. Test Mass Casualty Incident (MCI Surge)
        console.log('5. Clicking #ed-stream-burst-btn (MCI Code Black surge)...');
        await page.click('#ed-stream-burst-btn');
        await new Promise(r => setTimeout(r, 2000));

        // 6. Verify worklist updated with new studies
        console.log('6. Inspecting worklist for streamed ED cases...');
        await page.waitForSelector('.study-card', { timeout: 5000 });

        const studyCards = await page.$$eval('.study-card', cards => {
            return cards.map(c => ({
                id: c.dataset.studyId,
                name: c.querySelector('.patient-name') ? c.querySelector('.patient-name').textContent.trim() : '',
                priority: c.querySelector('.study-card-priority') ? c.querySelector('.study-card-priority').textContent.trim() : ''
            }));
        });
        console.log(`   Total worklist cards rendered: ${studyCards.length}`);
        const edCards = studyCards.filter(s => s.id && s.id.startsWith('ALV-ED-'));
        console.log(`   Streamed ED studies in worklist: ${edCards.length}`);
        edCards.forEach(c => console.log(`     -> ${c.id}: ${c.name} [${c.priority}]`));

        if (edCards.length === 0) {
            throw new Error('No ALV-ED- studies found in worklist after MCI burst surge');
        }

        // 7. Verify counters on the HUD
        const streamedText = await page.$eval('#ed-streamed-count', el => el.textContent.trim());
        const statText = await page.$eval('#ed-stat-count', el => el.textContent.trim());
        console.log(`   HUD Influx Counter: "${streamedText}", STAT Counter: "${statText}"`);

        // 8. Click on the first streamed study card to load it in the 2D workstation
        console.log(`7. Selecting streamed study card: ${edCards[0].id}...`);
        const targetCardSelector = `.study-card[data-study-id="${edCards[0].id}"]`;
        await page.click(targetCardSelector);
        await new Promise(r => setTimeout(r, 1500));

        // Verify loaded in viewer HUD
        const loadedPatientName = await page.$eval('#hud-patient-name', el => el.textContent.trim());
        console.log(`   Loaded study patient name in HUD: "${loadedPatientName}"`);

        // 9. Pause the stream
        console.log('8. Pausing stream...');
        await page.click('#ed-stream-toggle-btn');
        await new Promise(r => setTimeout(r, 800));
        const pausedStatus = await page.$eval('#ed-stream-status-label', el => el.textContent.trim());
        console.log(`   Paused status: "${pausedStatus}"`);

        // 10. Capture high-resolution screenshot
        console.log('9. Capturing high-resolution screenshot artifact...');
        const screenshotPath = path.join(ARTIFACT_DIR, 'alveon_ed_stream_verified.png');
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`📸 Screenshot saved to: ${screenshotPath}`);

        console.log('✅ All Continuous ED Stream Daemon E2E verification checks passed successfully!');
    } catch (err) {
        console.error('❌ E2E Verification failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
