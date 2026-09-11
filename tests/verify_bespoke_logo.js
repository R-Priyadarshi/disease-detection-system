const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    console.log('🎨 Verifying ALVEON Bespoke Logo across Workstation and Landing...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    const page = await browser.newPage();
    await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 2 }); // High-DPI Retina capture

    try {
        // 1. Workstation Header Logo
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 15000 });
        console.log('✅ Loaded Workstation');
        await new Promise(r => setTimeout(r, 1000));

        const wsBrand = await page.$('#brand-cluster-link');
        const wsBrandCropPath = path.join(artifactDir, 'alveon_logo_workstation_header.png');
        await wsBrand.screenshot({ path: wsBrandCropPath });
        console.log(`📸 Saved workstation brand cluster crop: ${wsBrandCropPath}`);

        // Full workstation screenshot with new logo
        const wsFullPath = path.join(artifactDir, 'alveon_workstation_with_bespoke_logo.png');
        await page.screenshot({ path: wsFullPath });
        console.log(`📸 Saved full workstation screenshot: ${wsFullPath}`);

        // 2. Landing Page Header Logo
        await page.goto('http://localhost:8000/landing', { waitUntil: 'networkidle2', timeout: 15000 });
        console.log('✅ Loaded Landing Page');
        await new Promise(r => setTimeout(r, 800));

        const landNavBrand = await page.$('.landing-nav .nav-brand');
        const landNavCropPath = path.join(artifactDir, 'alveon_logo_landing_navbar.png');
        await landNavBrand.screenshot({ path: landNavCropPath });
        console.log(`📸 Saved landing navbar brand cluster crop: ${landNavCropPath}`);

        // 3. Landing Page Footer Logo
        const landFootBrand = await page.$('.landing-footer .nav-brand');
        const landFootCropPath = path.join(artifactDir, 'alveon_logo_landing_footer.png');
        await landFootBrand.screenshot({ path: landFootCropPath });
        console.log(`📸 Saved landing footer brand cluster crop: ${landFootCropPath}`);

        // Full landing hero screenshot
        const landHeroPath = path.join(artifactDir, 'alveon_landing_hero_with_bespoke_logo.png');
        await page.screenshot({ path: landHeroPath });
        console.log(`📸 Saved landing hero screenshot: ${landHeroPath}`);

        console.log('🎉 Logo verification completed successfully!');
    } catch (err) {
        console.error('❌ Logo verification failed:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
