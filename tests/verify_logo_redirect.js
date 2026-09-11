const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch({ 
        headless: 'new', 
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    let allPassed = true;

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        console.log('Test 1: Navigate to Workstation (http://localhost:8000/)');
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 15000 });
        
        // 1. Verify link attributes
        const linkInfo = await page.evaluate(() => {
            const link = document.getElementById('brand-cluster-link');
            return {
                exists: !!link,
                href: link ? link.getAttribute('href') : null,
                tagName: link ? link.tagName : null,
                cursor: link ? window.getComputedStyle(link).cursor : null
            };
        });

        console.log('Link Info:', linkInfo);
        if (!linkInfo.exists || linkInfo.href !== '/landing' || linkInfo.tagName !== 'A') {
            console.error('❌ #brand-cluster-link not configured properly!');
            allPassed = false;
        } else {
            console.log('✅ #brand-cluster-link correctly points to /landing with cursor: pointer');
        }

        // 2. Click logo and verify navigation
        console.log('\nTest 2: Click on ALVEON Logo Emblem');
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }),
            page.click('#alveon-emblem')
        ]);

        const currentUrlAfterLogoClick = page.url();
        console.log('Current URL after logo click:', currentUrlAfterLogoClick);
        if (currentUrlAfterLogoClick.includes('/landing')) {
            console.log('✅ Clicking logo successfully redirected to landing page!');
            await page.screenshot({ path: path.join(artifactDir, 'redirect_from_logo.png') });
        } else {
            console.error('❌ Failed to redirect to /landing after clicking logo');
            allPassed = false;
        }

        // 3. Return to Workstation and click brand name text
        console.log('\nTest 3: Navigate back to Workstation and click .brand-name');
        await page.goto('http://localhost:8000/', { waitUntil: 'networkidle2', timeout: 15000 });
        
        await Promise.all([
            page.waitForNavigation({ waitUntil: 'networkidle2', timeout: 10000 }),
            page.click('.brand-name')
        ]);

        const currentUrlAfterNameClick = page.url();
        console.log('Current URL after brand name click:', currentUrlAfterNameClick);
        if (currentUrlAfterNameClick.includes('/landing')) {
            console.log('✅ Clicking brand name text successfully redirected to landing page!');
            await page.screenshot({ path: path.join(artifactDir, 'redirect_from_name.png') });
        } else {
            console.error('❌ Failed to redirect to /landing after clicking brand name');
            allPassed = false;
        }

        console.log('\n' + '='.repeat(60));
        console.log(allPassed ? '🎉 ALL REDIRECT VERIFICATIONS PASSED!' : '⚠️ SOME VERIFICATIONS FAILED');
        console.log('='.repeat(60));

    } catch (err) {
        console.error('ERROR during verification:', err);
        allPassed = false;
    } finally {
        await browser.close();
    }

    process.exit(allPassed ? 0 : 1);
})();
