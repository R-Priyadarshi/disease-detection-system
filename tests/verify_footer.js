const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    const browser = await puppeteer.launch({ 
        headless: 'new', 
        args: ['--no-sandbox', '--disable-setuid-sandbox'] 
    });

    const artifactDir = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26';
    
    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });
        await page.goto('http://localhost:8000/landing', { waitUntil: 'networkidle2', timeout: 15000 });
        
        // Scroll to the bottom
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await new Promise(r => setTimeout(r, 600));
        
        // Screenshot of the footer
        const footer = await page.$('.landing-footer');
        if (footer) {
            await footer.screenshot({ 
                path: path.join(artifactDir, 'footer_built_by.png')
            });
            console.log('✅ Footer screenshot saved to:', path.join(artifactDir, 'footer_built_by.png'));
        }

        const footerText = await page.evaluate(() => {
            const fb = document.querySelector('.footer-bottom');
            return fb ? fb.innerText : '';
        });
        console.log('Footer bottom text content:', footerText);

    } catch (err) {
        console.error('ERROR:', err.message);
    } finally {
        await browser.close();
    }
})();
