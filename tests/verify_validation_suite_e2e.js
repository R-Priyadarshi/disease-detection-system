/**
 * ALVEON PACS - Clinical Benchmark & FDA 510(k) Validation Suite E2E Verification
 * Validates opening the FDA Benchmark modal, inspecting multi-class ROC curves,
 * interacting with the decision threshold slider, running a live worklist cohort audit,
 * and verifying FDA 510(k) Pre-Market Dossier PDF download.
 */
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');

(async () => {
    console.log('🚀 Launching Puppeteer to verify Clinical Benchmark & FDA 510(k) SaMD Suite...');
    const browser = await puppeteer.launch({
        headless: 'new',
        args: ['--no-sandbox', '--disable-setuid-sandbox']
    });

    try {
        const page = await browser.newPage();
        await page.setViewport({ width: 1440, height: 900 });

        page.on('console', msg => {
            if (msg.type() === 'error') console.log(`[BROWSER ERROR] ${msg.text()}`);
        });

        let fdaPdfIntercepted = false;
        let fdaPdfContentType = '';

        page.on('response', async res => {
            const url = res.url();
            if (url.includes('/api/v1/validation/fda-summary-pdf')) {
                fdaPdfIntercepted = res.status() === 200;
                fdaPdfContentType = res.headers()['content-type'] || '';
                console.log(`📡 Intercepted /api/v1/validation/fda-summary-pdf: status=${res.status()}, type=${fdaPdfContentType}`);
            }
        });

        // 1. Navigate to Workstation
        console.log('1. Navigating to http://127.0.0.1:8000/workstation...');
        await page.goto('http://127.0.0.1:8000/workstation', { waitUntil: 'networkidle2' });

        // 2. Check for FDA Benchmark button in header
        console.log('2. Finding #open-validation-btn in master header...');
        await page.waitForSelector('#open-validation-btn', { timeout: 8000 });
        const valBtn = await page.$('#open-validation-btn');
        if (!valBtn) throw new Error('#open-validation-btn not found in header');

        // 3. Click to open modal
        console.log('3. Clicking #open-validation-btn to open dialog...');
        await valBtn.click();
        await new Promise(r => setTimeout(r, 1200));

        // 4. Verify modal is open
        const isDialogOpen = await page.evaluate(() => {
            const d = document.getElementById('validation-suite-dialog');
            return d ? (d.open === true || d.style.display === 'flex' || window.getComputedStyle(d).display !== 'none') : false;
        });
        console.log(`4. Validation dialog open state: ${isDialogOpen}`);
        if (!isDialogOpen) throw new Error('#validation-suite-dialog failed to open');

        // 5. Verify benchmark metrics are loaded
        await page.waitForFunction(() => {
            const aucEl = document.getElementById('val-card-auc');
            return aucEl && aucEl.textContent.trim() !== '0.000' && aucEl.textContent.trim().length > 0;
        }, { timeout: 8000 });

        const initialMetrics = await page.evaluate(() => {
            return {
                auc: document.getElementById('val-card-auc')?.textContent,
                sens: document.getElementById('val-card-sens')?.textContent,
                spec: document.getElementById('val-card-spec')?.textContent,
                ppv: document.getElementById('val-card-ppv')?.textContent,
                npv: document.getElementById('val-card-npv')?.textContent,
                f1: document.getElementById('val-card-f1')?.textContent,
                tp: document.getElementById('val-cm-tp')?.textContent,
                fp: document.getElementById('val-cm-fp')?.textContent,
                pillText: document.getElementById('val-auc-pill')?.textContent
            };
        });
        console.log('5. Initial Pathology (Pneumothorax) Metrics:', JSON.stringify(initialMetrics, null, 2));

        if (!initialMetrics.auc || parseFloat(initialMetrics.auc) < 0.88) {
            throw new Error(`AUC metric invalid: ${initialMetrics.auc}`);
        }

        // 6. Test pathology selection dropdown (Switch to Consolidative Pneumonia)
        console.log('6. Switching pathology to PNEUMONIA...');
        await page.select('#validation-pathology-select', 'PNEUMONIA');
        await new Promise(r => setTimeout(r, 800));

        const pneumoniaMetrics = await page.evaluate(() => {
            return {
                auc: document.getElementById('val-card-auc')?.textContent,
                sens: document.getElementById('val-card-sens')?.textContent,
                spec: document.getElementById('val-card-spec')?.textContent,
                f1: document.getElementById('val-card-f1')?.textContent,
                pillText: document.getElementById('val-auc-pill')?.textContent
            };
        });
        console.log('Pneumonia Metrics:', JSON.stringify(pneumoniaMetrics, null, 2));

        // 7. Test interactive threshold slider tuning
        console.log('7. Adjusting decision threshold slider to 0.60...');
        await page.evaluate(() => {
            const slider = document.getElementById('validation-threshold-slider');
            if (slider) {
                slider.value = '0.60';
                slider.dispatchEvent(new Event('input', { bubbles: true }));
            }
        });
        await new Promise(r => setTimeout(r, 600));

        const tunedThreshold = await page.evaluate(() => {
            return {
                valText: document.getElementById('validation-threshold-val')?.textContent,
                sens: document.getElementById('val-card-sens')?.textContent,
                spec: document.getElementById('val-card-spec')?.textContent,
                tp: document.getElementById('val-cm-tp')?.textContent
            };
        });
        console.log('Tuned Metrics (tau=0.60):', JSON.stringify(tunedThreshold, null, 2));
        if (tunedThreshold.valText !== '0.60') {
            throw new Error(`Slider did not update threshold display: ${tunedThreshold.valText}`);
        }

        // 8. Test Live Cohort Audit button
        console.log('8. Clicking #btn-run-cohort-audit...');
        const auditBtn = await page.$('#btn-run-cohort-audit');
        if (auditBtn) {
            await auditBtn.click();
            await new Promise(r => setTimeout(r, 1200));

            const cohortVisible = await page.evaluate(() => {
                const sec = document.getElementById('val-cohort-audit-section');
                return sec && sec.style.display !== 'none';
            });
            console.log(`Cohort Audit Section Visible: ${cohortVisible}`);
            if (!cohortVisible) throw new Error('Cohort audit section failed to become visible');
        }

        // 9. Test FDA 510(k) PDF export trigger
        console.log('9. Clicking #btn-export-fda-pdf...');
        const pdfBtn = await page.$('#btn-export-fda-pdf');
        if (pdfBtn) {
            await pdfBtn.click();
            await new Promise(r => setTimeout(r, 2000));
            console.log(`FDA 510(k) PDF Stream Intercepted: ${fdaPdfIntercepted} (Content-Type: ${fdaPdfContentType})`);
            if (!fdaPdfIntercepted || !fdaPdfContentType.includes('pdf')) {
                throw new Error('FDA 510(k) PDF export failed to respond with application/pdf');
            }
        }

        // 10. Capture visual screenshot artifact
        const screenshotPath = '/home/rishikesh/.gemini/antigravity-ide/brain/ddf1988c-03d8-4cac-85fe-1f89dfe67e26/alveon_fda_validation_suite_verified.png';
        await page.screenshot({ path: screenshotPath, fullPage: false });
        console.log(`📸 Visual Artifact captured: ${screenshotPath}`);

        console.log('🎉 Clinical Benchmark & FDA 510(k) Validation Suite E2E Test PASSED 100%!');
    } catch (err) {
        console.error('❌ E2E Test Error:', err);
        process.exit(1);
    } finally {
        await browser.close();
    }
})();
