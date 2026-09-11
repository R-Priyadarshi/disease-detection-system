const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch({ 
        headless: 'new', 
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    const results = [];
    
    try {
        // 1. Screenshot landing page header
        const landingPage = await browser.newPage();
        await landingPage.setViewport({ width: 1440, height: 900 });
        await landingPage.goto('http://localhost:8000/landing', { waitUntil: 'networkidle2', timeout: 15000 });
        
        // Full page screenshot
        await landingPage.screenshot({ 
            path: path.join(artifactDir, 'brand_landing_full.png'),
            fullPage: false
        });
        
        // Extract brand elements
        const landingBrand = await landingPage.evaluate(() => {
            const title = document.querySelector('.brand-title');
            const badge = document.querySelector('.brand-badge');
            const sub = document.querySelector('.brand-sub');
            const logo = document.querySelector('.nav-brand-logo');
            const logoSvg = logo ? logo.querySelector('svg') : null;
            const logoStyle = logo ? window.getComputedStyle(logo) : null;
            
            return {
                titleText: title ? title.textContent.trim() : 'NOT FOUND',
                badgeText: badge ? badge.textContent.trim() : 'NOT FOUND',
                subText: sub ? sub.textContent.trim() : 'NOT FOUND',
                logoViewBox: logoSvg ? logoSvg.getAttribute('viewBox') : 'NOT FOUND',
                logoBg: logoStyle ? logoStyle.backgroundColor : 'NOT FOUND',
                logoWidth: logoStyle ? logoStyle.width : 'NOT FOUND',
                titleFontFamily: title ? window.getComputedStyle(title).fontFamily : 'NOT FOUND',
                titleFontSize: title ? window.getComputedStyle(title).fontSize : 'NOT FOUND',
                titleLetterSpacing: title ? window.getComputedStyle(title).letterSpacing : 'NOT FOUND',
                badgeBg: badge ? window.getComputedStyle(badge).backgroundColor : 'NOT FOUND',
                badgeColor: badge ? window.getComputedStyle(badge).color : 'NOT FOUND',
            };
        });
        results.push({ page: 'LANDING', ...landingBrand });
        await landingPage.close();
        
        // 2. Screenshot dashboard header
        const dashPage = await browser.newPage();
        await dashPage.setViewport({ width: 1440, height: 900 });
        await dashPage.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 15000 });
        
        await dashPage.screenshot({ 
            path: path.join(artifactDir, 'brand_dashboard_full.png'),
            fullPage: false
        });
        
        const dashBrand = await dashPage.evaluate(() => {
            const title = document.querySelector('.brand-name');
            const badge = document.querySelector('.brand-badge');
            const sub = document.querySelector('.brand-subtext');
            const logo = document.querySelector('.alveon-emblem');
            const logoSvg = logo ? logo.querySelector('svg') : null;
            const logoStyle = logo ? window.getComputedStyle(logo) : null;
            
            return {
                titleText: title ? title.textContent.trim() : 'NOT FOUND',
                badgeText: badge ? badge.textContent.trim() : 'NOT FOUND',
                subText: sub ? sub.textContent.trim() : 'NOT FOUND',
                logoViewBox: logoSvg ? logoSvg.getAttribute('viewBox') : 'NOT FOUND',
                logoBg: logoStyle ? logoStyle.backgroundColor : 'NOT FOUND',
                logoWidth: logoStyle ? logoStyle.width : 'NOT FOUND',
                titleFontFamily: title ? window.getComputedStyle(title).fontFamily : 'NOT FOUND',
                titleFontSize: title ? window.getComputedStyle(title).fontSize : 'NOT FOUND',
                titleLetterSpacing: title ? window.getComputedStyle(title).letterSpacing : 'NOT FOUND',
                badgeBg: badge ? window.getComputedStyle(badge).backgroundColor : 'NOT FOUND',
                badgeColor: badge ? window.getComputedStyle(badge).color : 'NOT FOUND',
            };
        });
        results.push({ page: 'DASHBOARD', ...dashBrand });
        await dashPage.close();

        // 3. Compare and report
        console.log('\n' + '='.repeat(80));
        console.log('BRAND CONSISTENCY VERIFICATION REPORT');
        console.log('='.repeat(80));
        
        const landing = results[0];
        const dashboard = results[1];
        
        const checks = [
            { name: 'Brand Name', landingVal: landing.titleText, dashVal: dashboard.titleText },
            { name: 'Badge Text', landingVal: landing.badgeText, dashVal: dashboard.badgeText },
            { name: 'Subtitle', landingVal: landing.subText, dashVal: dashboard.subText },
            { name: 'Logo SVG ViewBox', landingVal: landing.logoViewBox, dashVal: dashboard.logoViewBox },
            { name: 'Logo BG Color', landingVal: landing.logoBg, dashVal: dashboard.logoBg },
            { name: 'Logo Width', landingVal: landing.logoWidth, dashVal: dashboard.logoWidth },
            { name: 'Title Font Size', landingVal: landing.titleFontSize, dashVal: dashboard.titleFontSize },
            { name: 'Title Letter Spacing', landingVal: landing.titleLetterSpacing, dashVal: dashboard.titleLetterSpacing },
            { name: 'Badge BG Color', landingVal: landing.badgeBg, dashVal: dashboard.badgeBg },
            { name: 'Badge Text Color', landingVal: landing.badgeColor, dashVal: dashboard.badgeColor },
        ];
        
        let allPass = true;
        for (const check of checks) {
            const match = check.landingVal === check.dashVal;
            if (!match) allPass = false;
            const icon = match ? '✅' : '❌';
            console.log(`${icon} ${check.name.padEnd(22)} | Landing: ${check.landingVal.padEnd(35)} | Dashboard: ${check.dashVal}`);
        }

        // Font family check (partial match is OK since fonts load differently)
        console.log(`ℹ️  Title Font Family    | Landing: ${landing.titleFontFamily}`);
        console.log(`ℹ️  Title Font Family    | Dashboard: ${dashboard.titleFontFamily}`);
        
        console.log('\n' + '='.repeat(80));
        console.log(allPass ? '✅ ALL BRANDING ELEMENTS MATCH PERFECTLY' : '⚠️  SOME ELEMENTS DIFFER (see above)');
        console.log('='.repeat(80));
        console.log('\nScreenshots saved:');
        console.log(`  Landing:   ${path.join(artifactDir, 'brand_landing_full.png')}`);
        console.log(`  Dashboard: ${path.join(artifactDir, 'brand_dashboard_full.png')}`);
        
    } catch (err) {
        console.error('ERROR:', err.message);
    } finally {
        await browser.close();
    }
})();
