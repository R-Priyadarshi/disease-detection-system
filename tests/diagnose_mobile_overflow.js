const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

const ARTIFACT_DIR = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';

(async () => {
    const browser = await puppeteer.launch({
        executablePath: '/usr/bin/google-chrome',
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu']
    });

    const page = await browser.newPage();

    const viewports = [
        { name: 'iphone_se_375', width: 375, height: 667 },
        { name: 'iphone_xr_414', width: 414, height: 896 }
    ];

    for (const vp of viewports) {
        console.log(`\n======================================================`);
        console.log(`📱 INSPECTING VIEWPORT: ${vp.name} (${vp.width}x${vp.height})`);
        console.log(`======================================================`);

        await page.setViewport({
            width: vp.width,
            height: vp.height,
            isMobile: true,
            hasTouch: true,
            deviceScaleFactor: 2
        });

        await page.goto('http://localhost:8000', { waitUntil: 'networkidle0' });
        await new Promise(r => setTimeout(r, 1000));

        // Detect all overflowing elements
        const overflowReport = await page.evaluate((docWidth) => {
            const elements = Array.from(document.querySelectorAll('*'));
            const offenders = [];

            for (const el of elements) {
                if (['SCRIPT', 'STYLE', 'HEAD', 'META', 'LINK', 'TITLE'].includes(el.tagName)) continue;
                const style = window.getComputedStyle(el);
                if (style.display === 'none' || style.visibility === 'hidden') continue;

                const rect = el.getBoundingClientRect();
                const scrollW = el.scrollWidth;
                const clientW = el.clientWidth;

                const exceedsRight = rect.right > docWidth + 2;
                const exceedsLeft = rect.left < -2;
                const internalOverflow = (scrollW > clientW + 5) && !['auto', 'scroll'].includes(style.overflowX);

                if (exceedsRight || exceedsLeft || internalOverflow) {
                    offenders.push({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || null,
                        className: el.className || null,
                        rect: { left: rect.left, right: rect.right, width: rect.width, height: rect.height },
                        scrollW,
                        clientW,
                        styleOverflowX: style.overflowX,
                        exceedsRight,
                        exceedsLeft,
                        internalOverflow,
                        textSnippet: (el.textContent || '').trim().substring(0, 40)
                    });
                }
            }

            return {
                docScrollWidth: document.documentElement.scrollWidth,
                docClientWidth: document.documentElement.clientWidth,
                bodyScrollWidth: document.body.scrollWidth,
                windowInnerWidth: window.innerWidth,
                offendersCount: offenders.length,
                offenders: offenders.slice(0, 30)
            };
        }, vp.width);

        console.log(`Document ScrollWidth: ${overflowReport.docScrollWidth} vs InnerWidth: ${overflowReport.windowInnerWidth}`);
        console.log(`Body ScrollWidth: ${overflowReport.bodyScrollWidth}`);
        console.log(`Detected ${overflowReport.offendersCount} overflowing elements:`);

        for (const o of overflowReport.offenders) {
            const idStr = o.id ? `#${o.id}` : '';
            const classStr = o.className && typeof o.className === 'string' ? `.${o.className.split(' ').join('.')}` : '';
            console.log(`  • <${o.tag}${idStr}${classStr}> [left: ${o.rect.left.toFixed(1)}, right: ${o.rect.right.toFixed(1)}, width: ${o.rect.width.toFixed(1)}]`);
            if (o.exceedsRight) console.log(`      ⚠️ Exceeds Right by ${(o.rect.right - vp.width).toFixed(1)}px`);
            if (o.exceedsLeft) console.log(`      ⚠️ Exceeds Left by ${Math.abs(o.rect.left).toFixed(1)}px`);
            if (o.internalOverflow) console.log(`      ⚠️ Internal scroll overflow: scrollW=${o.scrollW}, clientW=${o.clientW}`);
        }

        const shotPath = path.join(ARTIFACT_DIR, `diagnose_overflow_${vp.name}.png`);
        await page.screenshot({ path: shotPath, fullPage: true });
        console.log(`📸 Saved screenshot: ${path.basename(shotPath)}`);
    }

    await browser.close();
})().catch(err => {
    console.error(err);
    process.exit(1);
});
