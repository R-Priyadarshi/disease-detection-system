/**
 * ALVEON THORACIC PACS - Clinical Workstation Engine
 * Implements interactive Window/Level, 2.5x Inspection Loupe,
 * Multi-Colormap Grad-CAM, Anatomical Zonation, and PACS Reporting.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Cache
    const fileInput = document.getElementById('file-input');
    const dropZone = document.getElementById('drop-zone');
    const browseBtn = document.getElementById('browse-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analyzeSpinner = document.getElementById('analyze-spinner');
    const analyzeBtnText = document.getElementById('analyze-btn-text');

    const sampleNormalBtn = document.getElementById('sample-normal-btn');
    const samplePneumoniaBtn = document.getElementById('sample-pneumonia-btn');

    const emptyState = document.getElementById('empty-state');
    const loadingState = document.getElementById('loading-state');
    const diagnosisContent = document.getElementById('diagnosis-content');
    const viewportModes = document.getElementById('viewport-modes');

    const diagnosisBanner = document.getElementById('diagnosis-banner');
    const diagnosisBadge = document.getElementById('diagnosis-badge');
    const diagnosisHeading = document.getElementById('diagnosis-heading');
    const riskSubtitle = document.getElementById('risk-subtitle');
    const confidencePercentage = document.getElementById('confidence-percentage');
    const confidenceRing = document.getElementById('confidence-ring');
    const latencyChip = document.getElementById('latency-chip');
    const clinicalRecommendationText = document.getElementById('clinical-recommendation-text');

    const dicomViewport = document.getElementById('dicom-viewport');
    const splitSliderWrapper = document.getElementById('split-slider-wrapper');
    const splitClipped = document.getElementById('split-clipped');
    const sliderHandle = document.getElementById('slider-handle');
    const viewUnderlay = document.getElementById('view-underlay');
    const viewOverlay = document.getElementById('view-overlay');

    const sideBySideWrapper = document.getElementById('side-by-side-wrapper');
    const sideOrig = document.getElementById('side-orig');
    const sideHeatmap = document.getElementById('side-heatmap');
    const loupeLens = document.getElementById('loupe-lens');
    const loupeToggleBtn = document.getElementById('loupe-toggle-btn');
    const hudLoupeDisplay = document.getElementById('hud-loupe-display');
    const hudWlDisplay = document.getElementById('hud-wl-display');

    const contrastSlider = document.getElementById('contrast-slider');
    const brightnessSlider = document.getElementById('brightness-slider');
    const heatmapOpacitySlider = document.getElementById('heatmap-opacity');
    const wwVal = document.getElementById('ww-val');
    const wlVal = document.getElementById('wl-val');
    const opacityVal = document.getElementById('opacity-val');

    const zoneRulVal = document.getElementById('zone-rul-val');
    const zoneRulFill = document.getElementById('zone-rul-fill');
    const zoneRllVal = document.getElementById('zone-rll-val');
    const zoneRllFill = document.getElementById('zone-rll-fill');
    const zoneLulVal = document.getElementById('zone-lul-val');
    const zoneLulFill = document.getElementById('zone-lul-fill');
    const zoneLllVal = document.getElementById('zone-lll-val');
    const zoneLllFill = document.getElementById('zone-lll-fill');
    const dominantZoneChip = document.getElementById('dominant-zone-chip');

    const openReportBtn = document.getElementById('open-report-btn');
    const downloadOverlayBtn = document.getElementById('download-overlay-btn');
    const reportDialog = document.getElementById('report-dialog');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalPrintBtn = document.getElementById('modal-print-btn');
    const modalReportContainer = document.getElementById('modal-report-container');

    // Workstation State
    let currentFile = null;
    let currentPrediction = null;
    let isDraggingSlider = false;
    let currentViewMode = 'split';
    let isLoupeActive = false;
    let isInverted = false;
    let isClaheActive = false;
    let selectedColormap = 'inferno';

    // 1. Initial Health & Engine Check
    async function checkSystemHealth() {
        try {
            const res = await fetch('/health');
            if (res.ok) {
                const data = await res.json();
                document.getElementById('engine-status').textContent = `TF ${data.tensorflow_version} • ${data.device}`;
                document.getElementById('telemetry-station').textContent = 'ACTIVE / CALIBRATED';
            }
        } catch (err) {
            console.warn('Backend initializing...', err);
        }
    }
    checkSystemHealth();

    // 2. Study Ingestion & File Drag-and-Drop
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(name => {
        dropZone.addEventListener(name, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) handleFileSelected(files[0]);
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) handleFileSelected(e.target.files[0]);
    });

    function handleFileSelected(file) {
        currentFile = file;
        analyzeBtn.disabled = false;
        dropZone.querySelector('.drop-text-primary').textContent = `STUDY: ${file.name}`;
        dropZone.querySelector('.drop-text-secondary').textContent = `${(file.size / 1024).toFixed(1)} KB • Ingested into PACS Memory`;
        dropZone.style.borderColor = 'var(--titanium-200)';
    }

    // 3. PACS Verification Callsets (Samples)
    async function loadSample(sampleId) {
        try {
            setLoading(true);
            const res = await fetch('/api/v1/samples');
            const data = await res.json();
            const sample = data.samples.find(s => s.id === sampleId);
            if (!sample) return;

            const response = await fetch(sample.image_b64);
            const blob = await response.blob();
            const file = new File([blob], `${sampleId}.jpg`, { type: 'image/jpeg' });

            handleFileSelected(file);
            await executeAnalysis();
        } catch (err) {
            console.error('Callset ingestion error:', err);
            alert('PACS Verification Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    sampleNormalBtn.addEventListener('click', () => loadSample('sample_normal'));
    samplePneumoniaBtn.addEventListener('click', () => loadSample('sample_pneumonia'));

    // 4. Window / Level Contrast & Presets
    function updateVisualFilters() {
        const contrast = contrastSlider.value;
        const brightness = brightnessSlider.value;
        const invert = isInverted ? 100 : 0;

        wwVal.textContent = `${contrast}%`;
        wlVal.textContent = `${brightness}%`;

        const filterStyle = `contrast(${contrast}%) brightness(${brightness}%) invert(${invert}%)`;
        viewUnderlay.style.filter = filterStyle;
        viewOverlay.style.filter = filterStyle;
        sideOrig.style.filter = filterStyle;
        sideHeatmap.style.filter = filterStyle;

        hudWlDisplay.textContent = `W: ${Math.round(contrast * 15)} L: ${Math.round((brightness - 100) * 10 - 600)}`;
    }

    contrastSlider.addEventListener('input', updateVisualFilters);
    brightnessSlider.addEventListener('input', updateVisualFilters);

    heatmapOpacitySlider.addEventListener('input', (e) => {
        opacityVal.textContent = `${e.target.value}%`;
    });

    heatmapOpacitySlider.addEventListener('change', () => {
        if (currentFile && currentPrediction) executeAnalysis();
    });

    // Window/Level Preset Buttons
    document.querySelectorAll('#wl-presets .tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const wl = btn.dataset.wl;
            if (wl === 'invert') {
                isInverted = !isInverted;
                btn.classList.toggle('active', isInverted);
                updateVisualFilters();
                return;
            }
            if (wl === 'clahe') {
                isClaheActive = !isClaheActive;
                btn.classList.toggle('active', isClaheActive);
                if (currentFile && currentPrediction) executeAnalysis();
                return;
            }

            document.querySelectorAll('#wl-presets .tool-btn:not(#btn-invert):not(#btn-clahe)')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (wl === 'default') {
                contrastSlider.value = 100;
                brightnessSlider.value = 100;
            } else if (wl === 'lung') {
                contrastSlider.value = 160;
                brightnessSlider.value = 95;
            } else if (wl === 'bone') {
                contrastSlider.value = 210;
                brightnessSlider.value = 80;
            }
            updateVisualFilters();
        });
    });

    // Colormap Switcher
    document.querySelectorAll('#colormap-selectors .colormap-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('#colormap-selectors .colormap-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedColormap = pill.dataset.color;

            // If in Film Only mode, switch to Split Wipe or Thermal Only so the colormap is visible
            if (currentViewMode === 'original') {
                applyViewMode('split');
            }

            if (currentFile && currentPrediction) executeAnalysis();
        });
    });

    // Keyboard Shortcuts (I = Invert)
    window.addEventListener('keydown', (e) => {
        if (e.key === 'i' || e.key === 'I') {
            document.getElementById('btn-invert').click();
        }
    });

    // 5. Interactive 2.5x Inspection Loupe
    loupeToggleBtn.addEventListener('click', () => {
        isLoupeActive = !isLoupeActive;
        loupeToggleBtn.classList.toggle('active', isLoupeActive);
        hudLoupeDisplay.textContent = isLoupeActive ? 'LOUPE: 2.5x' : 'LOUPE: OFF';
        loupeLens.hidden = !isLoupeActive;
    });

    dicomViewport.addEventListener('mousemove', (e) => {
        if (!isLoupeActive || !currentPrediction) return;

        const rect = dicomViewport.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;

        // Position loupe centered at cursor
        loupeLens.style.left = `${x - 65}px`;
        loupeLens.style.top = `${y - 65}px`;

        // 2.5x Zoom calculation
        const zoom = 2.5;
        const bgWidth = rect.width * zoom;
        const bgHeight = rect.height * zoom;
        const bgX = -(x * zoom - 65);
        const bgY = -(y * zoom - 65);

        loupeLens.style.backgroundImage = `url(${currentPrediction.gradcam_overlay_b64})`;
        loupeLens.style.backgroundSize = `${bgWidth}px ${bgHeight}px`;
        loupeLens.style.backgroundPosition = `${bgX}px ${bgY}px`;
    });

    dicomViewport.addEventListener('mouseleave', () => {
        if (isLoupeActive) loupeLens.hidden = true;
    });

    dicomViewport.addEventListener('mouseenter', () => {
        if (isLoupeActive && currentPrediction) loupeLens.hidden = false;
    });

    // 6. Master Diagnostic Sweep (Inference)
    analyzeBtn.addEventListener('click', executeAnalysis);

    async function executeAnalysis() {
        if (!currentFile) return;

        setLoading(true);
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('apply_clahe', isClaheActive);
        formData.append('colormap', selectedColormap);
        formData.append('heatmap_alpha', heatmapOpacitySlider.value / 100.0);

        try {
            const res = await fetch('/api/v1/predict', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Diagnostic execution failed');
            }

            const data = await res.json();
            currentPrediction = data;
            renderDiagnosisResults(data);
        } catch (err) {
            console.error('Sweep failure:', err);
            alert('Diagnostic Sweep Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        analyzeBtn.disabled = isLoading;
        analyzeSpinner.hidden = !isLoading;
        analyzeBtnText.textContent = isLoading ? 'Executing Synaptic Sweep...' : 'Execute Diagnostic Neural Sweep';

        if (isLoading) {
            emptyState.hidden = true;
            diagnosisContent.hidden = true;
            loadingState.hidden = false;
        } else {
            loadingState.hidden = true;
        }
    }

    // 7. Render Radiologic Findings
    function renderDiagnosisResults(pred) {
        emptyState.hidden = true;
        loadingState.hidden = true;
        diagnosisContent.hidden = false;
        viewportModes.hidden = false;

        const isPneumonia = pred.is_pneumonia;

        // Findings banner
        diagnosisBanner.className = 'findings-banner ' + (isPneumonia ? 'pneumonia' : 'normal');
        diagnosisBadge.textContent = isPneumonia ? 'PATHOLOGY PRESENT' : 'NO ACUTE PATHOLOGY';
        diagnosisHeading.textContent = pred.diagnosis === 'PNEUMONIA' ? 'PNEUMONIA DETECTED' : 'CLEAR LUNG FIELDS';
        riskSubtitle.textContent = pred.risk_tier.replace(/_/g, ' ');

        // Circular DPI Gauge
        const radius = 25;
        const circumference = 2 * Math.PI * radius;
        confidenceRing.style.strokeDasharray = `${circumference} ${circumference}`;

        const conf = pred.confidence_percentage;
        confidencePercentage.textContent = `${Math.round(conf)}%`;
        const offset = circumference - (conf / 100) * circumference;
        confidenceRing.style.strokeDashoffset = offset;
        confidenceRing.style.stroke = isPneumonia ? 'var(--pathology-critical)' : 'var(--pathology-clear)';

        latencyChip.textContent = `${pred.latency_ms} ms`;
        clinicalRecommendationText.textContent = pred.clinical_recommendation;

        // Anatomical Zonation Progress
        if (pred.zonation) {
            const z = pred.zonation;
            zoneRulVal.textContent = `${z.right_upper_lobe_pct}%`;
            zoneRulFill.style.width = `${z.right_upper_lobe_pct}%`;
            zoneRllVal.textContent = `${z.right_lower_lobe_pct}%`;
            zoneRllFill.style.width = `${z.right_lower_lobe_pct}%`;
            zoneLulVal.textContent = `${z.left_upper_lobe_pct}%`;
            zoneLulFill.style.width = `${z.left_upper_lobe_pct}%`;
            zoneLllVal.textContent = `${z.left_lower_lobe_pct}%`;
            zoneLllFill.style.width = `${z.left_lower_lobe_pct}%`;
            dominantZoneChip.textContent = `Dominant Opacity: ${z.dominant_zone}`;
        }

        // Image Sources
        viewUnderlay.src = pred.gradcam_overlay_b64;
        viewOverlay.src = pred.original_image_b64;

        sideOrig.src = pred.original_image_b64;
        sideHeatmap.src = pred.gradcam_overlay_b64;

        resetSplitSlider();
        applyViewMode(currentViewMode);
        updateVisualFilters();
    }

    // 8. Interactive Split Slider
    function resetSplitSlider() { setSplitPosition(50); }

    function setSplitPosition(pct) {
        const clamped = Math.max(0, Math.min(100, pct));
        splitSliderWrapper.style.setProperty('--split-pos', `${clamped}%`);
        sliderHandle.style.left = `${clamped}%`;
    }

    function onPointerDown(e) {
        if (isLoupeActive) return; // Don't drag if loupe is active
        isDraggingSlider = true;
        updateSliderFromEvent(e);
    }

    function onPointerMove(e) {
        if (!isDraggingSlider) return;
        updateSliderFromEvent(e);
    }

    function onPointerUp() { isDraggingSlider = false; }

    function updateSliderFromEvent(e) {
        const rect = splitSliderWrapper.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const offsetX = clientX - rect.left;
        const pct = (offsetX / rect.width) * 100;
        setSplitPosition(pct);
    }

    sliderHandle.addEventListener('mousedown', onPointerDown);
    splitSliderWrapper.addEventListener('mousedown', onPointerDown);
    window.addEventListener('mousemove', onPointerMove);
    window.addEventListener('mouseup', onPointerUp);

    sliderHandle.addEventListener('touchstart', onPointerDown, { passive: true });
    splitSliderWrapper.addEventListener('touchstart', onPointerDown, { passive: true });
    window.addEventListener('touchmove', onPointerMove, { passive: true });
    window.addEventListener('touchend', onPointerUp);

    // 9. Viewport Mode Toggles
    document.querySelectorAll('#viewport-modes .view-mode-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            applyViewMode(btn.dataset.mode);
        });
    });

    function applyViewMode(mode) {
        currentViewMode = mode;
        document.querySelectorAll('#viewport-modes .view-mode-btn').forEach(b => {
            b.classList.toggle('active', b.dataset.mode === mode);
        });

        if (mode === 'split') {
            splitSliderWrapper.hidden = false;
            sideBySideWrapper.hidden = true;
            splitClipped.hidden = false;
            sliderHandle.hidden = false;
            splitClipped.style.clipPath = '';
            setSplitPosition(50);
        } else if (mode === 'side') {
            splitSliderWrapper.hidden = true;
            sideBySideWrapper.hidden = false;
        } else if (mode === 'heatmap') {
            splitSliderWrapper.hidden = false;
            sideBySideWrapper.hidden = true;
            splitClipped.hidden = true;
            sliderHandle.hidden = true;
        } else if (mode === 'original') {
            splitSliderWrapper.hidden = false;
            sideBySideWrapper.hidden = true;
            splitClipped.hidden = false;
            sliderHandle.hidden = true;
            splitClipped.style.clipPath = 'none';
        }
    }

    // Reset All Workstation Settings
    document.getElementById('reset-pacs-btn').addEventListener('click', () => {
        contrastSlider.value = 100;
        brightnessSlider.value = 100;
        isInverted = false;
        isClaheActive = false;
        isLoupeActive = false;
        loupeLens.hidden = true;
        document.getElementById('btn-invert').classList.remove('active');
        document.getElementById('btn-clahe').classList.remove('active');
        loupeToggleBtn.classList.remove('active');
        hudLoupeDisplay.textContent = 'LOUPE: OFF';
        updateVisualFilters();
        resetSplitSlider();
    });

    // 10. Official PACS Consultation Report
    openReportBtn.addEventListener('click', async () => {
        if (!currentPrediction) return;

        try {
            const reportPayload = {
                patient_id: "ALV-2026-X84",
                patient_name: "Patient Anonymous",
                diagnosis: currentPrediction.diagnosis,
                confidence_percentage: currentPrediction.confidence_percentage,
                risk_tier: currentPrediction.risk_tier,
                clinical_recommendation: currentPrediction.clinical_recommendation,
                zonation: currentPrediction.zonation,
                original_image_b64: currentPrediction.original_image_b64,
                gradcam_overlay_b64: currentPrediction.gradcam_overlay_b64
            };

            const res = await fetch('/api/v1/report', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reportPayload)
            });

            if (res.ok) {
                const data = await res.json();
                modalReportContainer.innerHTML = data.summary_html;
                reportDialog.showModal();
            }
        } catch (err) {
            console.error('Report error:', err);
        }
    });

    closeModalBtn.addEventListener('click', () => reportDialog.close());
    modalCancelBtn.addEventListener('click', () => reportDialog.close());
    modalPrintBtn.addEventListener('click', () => window.print());

    // 11. Export Radiographic Plate
    downloadOverlayBtn.addEventListener('click', () => {
        if (!currentPrediction) return;
        const a = document.createElement('a');
        a.href = currentPrediction.gradcam_overlay_b64;
        a.download = `ALVEON_${currentPrediction.diagnosis.toUpperCase()}_DICOM_PLATE.jpg`;
        a.click();
    });
});
