const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

    try {
        // 1. Workstation Page
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 });
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 1200));

        // Close-up of workstation header brand cluster
        const brandCluster = await page.$('.brand-cluster');
        if (brandCluster) {
            await brandCluster.screenshot({
                path: path.join(artifactDir, 'alveon_split_wipe_workstation_header.png')
            });
            console.log('Saved alveon_split_wipe_workstation_header.png');
        }

        // Full Workstation Viewport screenshot to demonstrate visual harmony
        await page.screenshot({
            path: path.join(artifactDir, 'alveon_split_wipe_workstation_full.png'),
            fullPage: false
        });
        console.log('Saved alveon_split_wipe_workstation_full.png');

        // 2. Landing Page
        await page.goto('http://localhost:8000/landing', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 1000));

        // Close-up of landing navbar brand
        const landingBrand = await page.$('.nav-brand');
        if (landingBrand) {
            await landingBrand.screenshot({
                path: path.join(artifactDir, 'alveon_split_wipe_landing_navbar.png')
            });
            console.log('Saved alveon_split_wipe_landing_navbar.png');
        }

        // Close-up of landing footer
        const landingFooter = await page.$('.landing-footer');
        if (landingFooter) {
            await landingFooter.screenshot({
                path: path.join(artifactDir, 'alveon_split_wipe_landing_footer.png')
            });
            console.log('Saved alveon_split_wipe_landing_footer.png');
        }

        console.log('ALL SCREENSHOTS CAPTURED SUCCESSFULLY');
    } catch (err) {
        console.error('Error capturing screenshots:', err);
    } finally {
        await browser.close();
    }
})();
