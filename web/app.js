/**
 * PneumoScan AI - Web Diagnostic Client
 * Handles file ingestion, API communications, interactive split slider,
 * radiology filters, and clinical report modal generation.
 */

document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const browseBtn = document.getElementById('browse-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analyzeSpinner = document.getElementById('analyze-spinner');
    const analyzeBtnText = document.getElementById('analyze-btn-text');

    const claheToggle = document.getElementById('clahe-toggle');
    const invertToggle = document.getElementById('invert-toggle');
    const heatmapOpacitySlider = document.getElementById('heatmap-opacity');
    const opacityValLabel = document.getElementById('opacity-val');

    const sampleNormalBtn = document.getElementById('sample-normal-btn');
    const samplePneumoniaBtn = document.getElementById('sample-pneumonia-btn');

    const emptyState = document.getElementById('empty-state');
    const loadingState = document.getElementById('loading-state');
    const diagnosisContent = document.getElementById('diagnosis-content');
    const viewToggles = document.getElementById('view-toggles');

    const diagnosisBanner = document.getElementById('diagnosis-banner');
    const diagnosisBadge = document.getElementById('diagnosis-badge');
    const diagnosisHeading = document.getElementById('diagnosis-heading');
    const riskSubtitle = document.getElementById('risk-subtitle');
    const confidencePercentage = document.getElementById('confidence-percentage');
    const confidenceRing = document.getElementById('confidence-ring');
    const latencyChip = document.getElementById('latency-chip');
    const clinicalRecommendationText = document.getElementById('clinical-recommendation-text');

    const splitSliderWrapper = document.getElementById('split-slider-wrapper');
    const splitClipped = document.getElementById('split-clipped');
    const sliderHandle = document.getElementById('slider-handle');
    const viewUnderlay = document.getElementById('view-underlay');
    const viewOverlay = document.getElementById('view-overlay');

    const sideBySideWrapper = document.getElementById('side-by-side-wrapper');
    const sideOrig = document.getElementById('side-orig');
    const sideHeatmap = document.getElementById('side-heatmap');

    const openReportBtn = document.getElementById('open-report-btn');
    const downloadOverlayBtn = document.getElementById('download-overlay-btn');
    const reportDialog = document.getElementById('report-dialog');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalPrintBtn = document.getElementById('modal-print-btn');
    const modalReportContainer = document.getElementById('modal-report-container');

    // State Variables
    let currentFile = null;
    let currentPrediction = null;
    let isDraggingSlider = false;
    let currentViewMode = 'split';

    // 1. Initial Health Check
    async function checkSystemHealth() {
        try {
            const res = await fetch('/health');
            if (res.ok) {
                const data = await res.json();
                const statusText = document.getElementById('status-text');
                statusText.textContent = `Model Online • ${data.device} • TF ${data.tensorflow_version}`;
            }
        } catch (err) {
            console.warn('Backend offline or initializing:', err);
        }
    }
    checkSystemHealth();

    // 2. File Selection & Drag-and-Drop Handlers
    browseBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        fileInput.click();
    });

    dropZone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('dragover');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelected(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelected(e.target.files[0]);
        }
    });

    function handleFileSelected(file) {
        currentFile = file;
        analyzeBtn.disabled = false;
        dropZone.querySelector('.drop-primary').textContent = `Selected: ${file.name}`;
        dropZone.querySelector('.drop-secondary').textContent = `${(file.size / 1024).toFixed(1)} KB • Ready for neural analysis`;
        dropZone.style.borderColor = 'var(--primary)';
    }

    // 3. Sample Radiograph Handlers
    async function loadSample(sampleId) {
        try {
            setLoading(true);
            const res = await fetch('/api/v1/samples');
            const data = await res.json();
            const sample = data.samples.find(s => s.id === sampleId);
            if (!sample) return;

            // Convert Base64 data URL to Blob File
            const response = await fetch(sample.image_b64);
            const blob = await response.blob();
            const file = new File([blob], `${sampleId}.jpg`, { type: 'image/jpeg' });

            handleFileSelected(file);
            await executeAnalysis();
        } catch (err) {
            console.error('Failed to load sample:', err);
            alert('Failed to load verification sample: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    sampleNormalBtn.addEventListener('click', () => loadSample('sample_normal'));
    samplePneumoniaBtn.addEventListener('click', () => loadSample('sample_pneumonia'));

    // 4. Radiology Filter Controls
    invertToggle.addEventListener('change', () => {
        const filterVal = invertToggle.checked ? 'invert(1)' : 'none';
        viewUnderlay.style.filter = filterVal;
        viewOverlay.style.filter = filterVal;
        sideOrig.style.filter = filterVal;
        sideHeatmap.style.filter = filterVal;
    });

    heatmapOpacitySlider.addEventListener('input', (e) => {
        const val = e.target.value;
        opacityValLabel.textContent = `${val}%`;
    });

    heatmapOpacitySlider.addEventListener('change', () => {
        if (currentFile && currentPrediction) {
            executeAnalysis();
        }
    });

    claheToggle.addEventListener('change', () => {
        if (currentFile && currentPrediction) {
            executeAnalysis();
        }
    });

    // 5. Analysis Execution
    analyzeBtn.addEventListener('click', executeAnalysis);

    async function executeAnalysis() {
        if (!currentFile) return;

        setLoading(true);
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('apply_clahe', claheToggle.checked);
        formData.append('heatmap_alpha', heatmapOpacitySlider.value / 100.0);

        try {
            const res = await fetch('/api/v1/predict', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Prediction failed');
            }

            const data = await res.json();
            currentPrediction = data;
            renderDiagnosisResults(data);
        } catch (err) {
            console.error('Analysis error:', err);
            alert('Analysis Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        analyzeBtn.disabled = isLoading;
        analyzeSpinner.hidden = !isLoading;
        analyzeBtnText.textContent = isLoading ? 'Processing Neural Scan...' : 'Execute Diagnostic Neural Scan';

        if (isLoading) {
            emptyState.hidden = true;
            diagnosisContent.hidden = true;
            loadingState.hidden = false;
        } else {
            loadingState.hidden = true;
        }
    }

    // 6. Render Diagnosis Results
    function renderDiagnosisResults(pred) {
        emptyState.hidden = true;
        loadingState.hidden = true;
        diagnosisContent.hidden = false;
        viewToggles.hidden = false;

        const isPneumonia = pred.is_pneumonia;

        // Banner styling
        diagnosisBanner.className = 'diagnosis-banner ' + (isPneumonia ? 'pneumonia' : 'normal');
        diagnosisBadge.textContent = isPneumonia ? 'POSITIVE' : 'NEGATIVE';
        diagnosisHeading.textContent = pred.diagnosis === 'PNEUMONIA' ? 'PNEUMONIA DETECTED' : 'CLEAR LUNG FIELDS';
        riskSubtitle.textContent = pred.risk_tier.replace(/_/g, ' ');

        // Animated Confidence Circle Ring
        const radius = 28;
        const circumference = 2 * Math.PI * radius;
        confidenceRing.style.strokeDasharray = `${circumference} ${circumference}`;

        const conf = pred.confidence_percentage;
        confidencePercentage.textContent = `${Math.round(conf)}%`;
        const offset = circumference - (conf / 100) * circumference;
        confidenceRing.style.strokeDashoffset = offset;
        confidenceRing.style.stroke = isPneumonia ? 'var(--status-pneumonia)' : 'var(--status-normal)';

        latencyChip.textContent = `${pred.latency_ms}ms`;
        clinicalRecommendationText.textContent = pred.clinical_recommendation;

        // Image Viewer Sources
        // Underlay: Grad-CAM Overlay; Overlay: Raw Radiograph (clipped by split wipe)
        viewUnderlay.src = pred.gradcam_overlay_b64;
        viewOverlay.src = pred.original_image_b64;

        sideOrig.src = pred.original_image_b64;
        sideHeatmap.src = pred.gradcam_overlay_b64;

        resetSplitSlider();
        applyViewMode(currentViewMode);
    }

    // 7. Interactive Split Slider Logic
    function resetSplitSlider() {
        setSplitPosition(50);
    }

    function setSplitPosition(percentage) {
        const clamped = Math.max(5, Math.min(95, percentage));
        splitClipped.style.width = `${clamped}%`;
        sliderHandle.style.left = `${clamped}%`;
    }

    function onPointerDown(e) {
        isDraggingSlider = true;
        updateSliderFromEvent(e);
    }

    function onPointerMove(e) {
        if (!isDraggingSlider) return;
        updateSliderFromEvent(e);
    }

    function onPointerUp() {
        isDraggingSlider = false;
    }

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

    // 8. View Mode Toggles
    const toggleButtons = viewToggles.querySelectorAll('.toggle-btn');
    toggleButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            toggleButtons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentViewMode = btn.dataset.view;
            applyViewMode(currentViewMode);
        });
    });

    function applyViewMode(mode) {
        if (mode === 'split') {
            splitSliderWrapper.hidden = false;
            sideBySideWrapper.hidden = true;
            splitClipped.hidden = false;
            sliderHandle.hidden = false;
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
            splitClipped.style.width = '100%';
        }
    }

    // 9. Clinical Consultation Report Modal
    openReportBtn.addEventListener('click', async () => {
        if (!currentPrediction) return;

        try {
            const reportPayload = {
                diagnosis: currentPrediction.diagnosis,
                confidence_percentage: currentPrediction.confidence_percentage,
                risk_tier: currentPrediction.risk_tier,
                clinical_recommendation: currentPrediction.clinical_recommendation,
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
            console.error('Failed to generate report:', err);
        }
    });

    closeModalBtn.addEventListener('click', () => reportDialog.close());
    modalCancelBtn.addEventListener('click', () => reportDialog.close());
    modalPrintBtn.addEventListener('click', () => window.print());

    // 10. Download Overlay Image
    downloadOverlayBtn.addEventListener('click', () => {
        if (!currentPrediction) return;
        const link = document.createElement('a');
        link.href = currentPrediction.gradcam_overlay_b64;
        link.download = `gradcam_${currentPrediction.diagnosis.toLowerCase()}_xray.jpg`;
        link.click();
    });
});
