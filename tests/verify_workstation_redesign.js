const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    console.log('🚀 Starting Alveon OS Workstation Redesign Verification...');
    const browser = await puppeteer.launch({ 
        headless: 'new', 
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });

    try {
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 20000 });
        console.log('✅ Page loaded at http://localhost:8000/');

        // Wait for worklist to render and auto-load study
        await page.waitForSelector('.study-card', { timeout: 10000 });
        console.log('✅ Triage worklist cards detected');

        // Allow DICOM plate & Grad-CAM to finish rendering
        await new Promise(r => setTimeout(r, 1500));

        // 1. Inspect DOM Layout geometry
        const layoutMetrics = await page.evaluate(() => {
            const container = document.querySelector('.workstation-container');
            const grid = document.querySelector('.workstation-grid');
            const ingestionPanel = document.querySelector('#ingestion-panel');
            const canvasStage = document.querySelector('.viewport-canvas-stage');
            const inspector = document.querySelector('#viewport-inspector');
            const caliperToolbar = document.querySelector('#pacs-measure-toolbar');
            const viewport = document.querySelector('#dicom-viewport');

            return {
                windowHeight: window.innerHeight,
                windowWidth: window.innerWidth,
                bodyScrollHeight: document.body.scrollHeight,
                containerHeight: container ? container.offsetHeight : 0,
                ingestionWidth: ingestionPanel ? ingestionPanel.offsetWidth : 0,
                canvasStageWidth: canvasStage ? canvasStage.offsetWidth : 0,
                canvasStageHeight: canvasStage ? canvasStage.offsetHeight : 0,
                inspectorWidth: inspector ? inspector.offsetWidth : 0,
                inspectorHeight: inspector ? inspector.offsetHeight : 0,
                caliperToolbarPosition: caliperToolbar ? window.getComputedStyle(caliperToolbar).position : '',
                caliperToolbarBottom: caliperToolbar ? window.getComputedStyle(caliperToolbar).bottom : '',
                caliperToolbarBorderRadius: caliperToolbar ? window.getComputedStyle(caliperToolbar).borderRadius : '',
                viewportHeight: viewport ? viewport.offsetHeight : 0,
                viewportWidth: viewport ? viewport.offsetWidth : 0,
            };
        });

        console.log('📊 Layout Metrics:', JSON.stringify(layoutMetrics, null, 2));

        // 2. Screenshot Standard Expansive Pro Workstation
        const screenshotPathStandard = path.join(artifactDir, 'alveon_os_workstation_1440.png');
        await page.screenshot({ path: screenshotPathStandard, fullPage: false });
        console.log(`📸 Saved standard workstation screenshot: ${screenshotPathStandard}`);

        // 3. Test Theater Mode (Sidebar Collapse)
        console.log('🎬 Testing Theater Mode (Collapsing sidebar)...');
        await page.click('#sidebar-collapse-btn');
        await new Promise(r => setTimeout(r, 400));

        const theaterMetrics = await page.evaluate(() => {
            const grid = document.querySelector('.workstation-grid');
            const canvasStage = document.querySelector('.viewport-canvas-stage');
            const expandBtn = document.querySelector('#sidebar-expand-btn');
            return {
                isCollapsed: grid.classList.contains('sidebar-collapsed'),
                expandBtnVisible: expandBtn ? window.getComputedStyle(expandBtn).display : 'none',
                canvasStageWidth: canvasStage ? canvasStage.offsetWidth : 0,
                canvasStageHeight: canvasStage ? canvasStage.offsetHeight : 0,
            };
        });
        console.log('📊 Theater Mode Metrics:', JSON.stringify(theaterMetrics, null, 2));

        const screenshotPathTheater = path.join(artifactDir, 'alveon_os_theater_mode_1440.png');
        await page.screenshot({ path: screenshotPathTheater, fullPage: false });
        console.log(`📸 Saved theater mode screenshot: ${screenshotPathTheater}`);

        // 4. Test Expand Sidebar
        console.log('🔄 Restoring sidebar...');
        await page.click('#sidebar-expand-btn');
        await new Promise(r => setTimeout(r, 400));

        // 5. Test Caliper functionality inside the floating capsule
        console.log('📏 Testing Caliper linear measurement tool...');
        await page.click('#tool-ruler');
        await new Promise(r => setTimeout(r, 200));

        // Perform drag on canvas
        const canvasBox = await page.$eval('#pacs-annotation-canvas', el => {
            const r = el.getBoundingClientRect();
            return { x: r.left, y: r.top, w: r.width, h: r.height };
        });

        const startX = canvasBox.x + canvasBox.w * 0.35;
        const startY = canvasBox.y + canvasBox.h * 0.45;
        const endX = canvasBox.x + canvasBox.w * 0.65;
        const endY = canvasBox.y + canvasBox.h * 0.55;

        await page.mouse.move(startX, startY);
        await page.mouse.down();
        await page.mouse.move(endX, endY, { steps: 8 });
        await page.mouse.up();
        await new Promise(r => setTimeout(r, 300));

        const screenshotPathCaliper = path.join(artifactDir, 'alveon_os_caliper_measurement.png');
        await page.screenshot({ path: screenshotPathCaliper, fullPage: false });
        console.log(`📸 Saved caliper measurement screenshot: ${screenshotPathCaliper}`);

        console.log('🎉 Verification successfully finished!');
    } catch (err) {
        console.error('❌ Verification failed:', err);
        process.exitCode = 1;
    } finally {
        await browser.close();
    }
})();
