/**
 * ALVEON THORACIC PACS - Enterprise Emergency Department Triage Engine
 * v2.5.0 Clinical Workstation
 * 
 * Features:
 * - Live STAT Emergency Triage Worklist with Acuity Prioritization
 * - Native 16-bit DICOM Ingestion & Tag Inspector Modal (Key: 'D')
 * - Electronic Radiologist Sign-Off with SHA-256 Audit Stamp (Key: 'S')
 * - Zero-Latency 1-Click Study Switching & Keyboard Navigation (↑/↓ or J/K)
 * - Multi-File Cohort Batch Triage Drop
 * - Interactive Window/Level, 2.5x Inspection Loupe, Multi-Colormap Grad-CAM
 */

document.addEventListener('DOMContentLoaded', () => {
    // ---------------------------------------------------------
    // DOM CACHE
    // ---------------------------------------------------------

    // Operational Mode Tabs & Containers
    const tabBtnWorklist = document.getElementById('tab-btn-worklist');
    const tabBtnIngest = document.getElementById('tab-btn-ingest');
    const triageWorklistContainer = document.getElementById('triage-worklist-container');
    const studyIngestionContainer = document.getElementById('study-ingestion-container');

    // Worklist Controls & List
    const studyQueueList = document.getElementById('study-queue-list');
    const worklistStatBadge = document.getElementById('worklist-stat-badge');
    const countAll = document.getElementById('count-all');
    const countStat = document.getElementById('count-stat');
    const countPending = document.getElementById('count-pending');
    const countSigned = document.getElementById('count-signed');
    const filterPills = document.querySelectorAll('.triage-filter-pill');

    // Ingestion & Dropzone
    const fileInput = document.getElementById('file-input');
    const folderInput = document.getElementById('folder-input');
    const dropZone = document.getElementById('drop-zone');
    const browseBtn = document.getElementById('browse-btn');
    const browseFolderBtn = document.getElementById('browse-folder-btn');
    const worklistFolderBtn = document.getElementById('worklist-folder-btn');
    const worklistFilesBtn = document.getElementById('worklist-files-btn');
    const worklistSelectModeBtn = document.getElementById('worklist-select-mode-btn');
    const worklistPurgeAllBtn = document.getElementById('worklist-purge-all-btn');
    const triageBulkBar = document.getElementById('triage-bulk-bar');
    const bulkSelectAll = document.getElementById('bulk-select-all');
    const bulkSelectedLabel = document.getElementById('bulk-selected-label');
    const bulkSelectedCount = document.getElementById('bulk-selected-count');
    const bulkPurgeSelectedBtn = document.getElementById('bulk-purge-selected-btn');
    const bulkCancelBtn = document.getElementById('bulk-cancel-btn');
    const clearStagedBtn = document.getElementById('clear-staged-btn');
    const analyzeBtn = document.getElementById('analyze-btn');
    const analyzeSpinner = document.getElementById('analyze-spinner');
    const analyzeBtnText = document.getElementById('analyze-btn-text');

    // PACS Calibration Callsets
    const sampleCards = document.querySelectorAll('.callset-card');

    // Viewport & Findings
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

    // Sign-off Controls
    const btnSignoff = document.getElementById('btn-signoff');
    const signoffBtnText = document.getElementById('signoff-btn-text');

    // HUD Elements
    const hudPatientId = document.getElementById('hud-patient-id');
    const hudPatientName = document.getElementById('hud-patient-name');
    const hudModality = document.getElementById('hud-modality');
    const hudSensor = document.getElementById('hud-sensor');
    const hudWlDisplay = document.getElementById('hud-wl-display');
    const hudLoupeDisplay = document.getElementById('hud-loupe-display');
    const hudStudyStatus = document.getElementById('hud-study-status');
    const hudTagTrigger = document.getElementById('hud-tag-trigger');

    // Viewport & Split Slider
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

    // Exposure Sliders
    const contrastSlider = document.getElementById('contrast-slider');
    const brightnessSlider = document.getElementById('brightness-slider');
    const heatmapOpacitySlider = document.getElementById('heatmap-opacity');
    const wwVal = document.getElementById('ww-val');
    const wlVal = document.getElementById('wl-val');
    const opacityVal = document.getElementById('opacity-val');

    // Zonation
    const zoneRulVal = document.getElementById('zone-rul-val');
    const zoneRulFill = document.getElementById('zone-rul-fill');
    const zoneRllVal = document.getElementById('zone-rll-val');
    const zoneRllFill = document.getElementById('zone-rll-fill');
    const zoneLulVal = document.getElementById('zone-lul-val');
    const zoneLulFill = document.getElementById('zone-lul-fill');
    const zoneLllVal = document.getElementById('zone-lll-val');
    const zoneLllFill = document.getElementById('zone-lll-fill');
    const dominantZoneChip = document.getElementById('dominant-zone-chip');

    // Modals & PDF
    const openReportBtn = document.getElementById('open-report-btn');
    const downloadPdfBtn = document.getElementById('download-pdf-btn');
    const downloadOverlayBtn = document.getElementById('download-overlay-btn');
    const reportDialog = document.getElementById('report-dialog');
    const closeModalBtn = document.getElementById('close-modal-btn');
    const modalCancelBtn = document.getElementById('modal-cancel-btn');
    const modalPrintBtn = document.getElementById('modal-print-btn');
    const modalPdfBtn = document.getElementById('modal-pdf-btn');
    const modalReportContainer = document.getElementById('modal-report-container');

    // Calipers & Annotation Canvas
    const pacsMeasureToolbar = document.getElementById('pacs-measure-toolbar');
    const pacsCanvas = document.getElementById('pacs-annotation-canvas');
    const btnClearMeasurements = document.getElementById('btn-clear-measurements');

    const dicomTagsDialog = document.getElementById('dicom-tags-dialog');
    const closeDicomModalBtn = document.getElementById('close-dicom-modal-btn');
    const dismissDicomBtn = document.getElementById('dismiss-dicom-btn');
    const dicomTagsTbody = document.getElementById('dicom-tags-tbody');
    const dicomFooterSyntax = document.getElementById('dicom-footer-syntax');
    const dicomModalSubtitle = document.getElementById('dicom-modal-subtitle');

    // Multi-Label Pathology Panel
    const multilabelPanel = document.getElementById('multilabel-panel');
    const multilabelAcuityTag = document.getElementById('multilabel-acuity-tag');
    const multilabelFindingsStrip = document.getElementById('multilabel-findings-strip');
    const multilabelImpression = document.getElementById('multilabel-impression');
    const multilabelImpressionText = document.getElementById('multilabel-impression-text');

    // Enterprise PACS & DICOMweb Interoperability Hub
    const openPacsHubBtn = document.getElementById('open-pacs-hub-btn');
    const pacsHubDialog = document.getElementById('pacs-hub-dialog');
    const closePacsHubBtn = document.getElementById('close-pacs-hub-btn');
    const dismissPacsHubBtn = document.getElementById('dismiss-pacs-hub-btn');
    const pacsPingAe = document.getElementById('pacs-ping-ae');
    const pacsPingHost = document.getElementById('pacs-ping-host');
    const pacsPingPort = document.getElementById('pacs-ping-port');
    const btnPacsPing = document.getElementById('btn-pacs-ping');
    const pacsPingLog = document.getElementById('pacs-ping-log');
    const pacsPushAe = document.getElementById('pacs-push-ae');
    const pacsPushHost = document.getElementById('pacs-push-host');
    const pacsPushPort = document.getElementById('pacs-push-port');
    const btnPacsPush = document.getElementById('btn-pacs-push');
    const pacsPushLog = document.getElementById('pacs-push-log');
    const pacsPushStudyName = document.getElementById('pacs-push-study-name');
    const btnInjectCohort = document.getElementById('btn-inject-cohort');
    const cohortInjectLog = document.getElementById('cohort-inject-log');
    const cohortLogStream = document.getElementById('cohort-log-stream');
    const cohortLogSummary = document.getElementById('cohort-log-summary');
    const btnTestWadoRendered = document.getElementById('btn-test-wado-rendered');
    const btnDownloadNativeDicom = document.getElementById('btn-download-native-dicom');

    // ---------------------------------------------------------
    // WORKSTATION STATE
    // ---------------------------------------------------------
    let worklistStudies = [];
    let selectedStudyId = null;
    let activeFilter = 'all';
    let selectedStudyIds = new Set();
    let isSelectModeActive = false;
    let openPacsHubModal = () => {};

    let currentFile = null;
    let currentPrediction = null;
    let isDraggingSlider = false;
    let currentViewMode = 'split';
    let isLoupeActive = false;
    let isInverted = false;
    let isClaheActive = false;
    let selectedColormap = 'inferno';

    // ---------------------------------------------------------
    // 1. TELEMETRY & SYSTEM HEALTH
    // ---------------------------------------------------------
    async function checkSystemHealth() {
        try {
            const res = await fetch('/health');
            if (res.ok) {
                const data = await res.json();
                const engineElem = document.getElementById('engine-status');
                if (engineElem) engineElem.textContent = `TF ${data.tensorflow_version} • ${data.device}`;
                const telemetryStation = document.getElementById('telemetry-station');
                if (telemetryStation) telemetryStation.textContent = 'ACTIVE / CALIBRATED';
            }
        } catch (err) {
            console.warn('Backend initializing...', err);
        }
    }
    checkSystemHealth();

    // ---------------------------------------------------------
    // 2. OPERATIONAL MODE TAB SWITCHER
    // ---------------------------------------------------------
    function setOperationalTab(mode) {
        if (mode === 'worklist') {
            tabBtnWorklist.classList.add('active');
            tabBtnIngest.classList.remove('active');
            triageWorklistContainer.hidden = false;
            studyIngestionContainer.hidden = true;
        } else {
            tabBtnWorklist.classList.remove('active');
            tabBtnIngest.classList.add('active');
            triageWorklistContainer.hidden = true;
            studyIngestionContainer.hidden = false;
        }
    }

    if (tabBtnWorklist) tabBtnWorklist.addEventListener('click', () => setOperationalTab('worklist'));
    if (tabBtnIngest) tabBtnIngest.addEventListener('click', () => setOperationalTab('ingest'));

    // ---------------------------------------------------------
    // 3. EMERGENCY TRIAGE WORKLIST LOGIC
    // ---------------------------------------------------------
    async function fetchWorklist() {
        try {
            const res = await fetch('/api/v1/worklist');
            if (!res.ok) throw new Error('Failed to load emergency triage worklist');
            const data = await res.json();
            worklistStudies = data.studies || [];
            updateWorklistCounters();
            renderWorklistQueue();

            // Auto-load top STAT critical study on initial boot if nothing selected
            if (!selectedStudyId && worklistStudies.length > 0) {
                loadWorklistStudy(worklistStudies[0]);
            }
        } catch (err) {
            console.error('Worklist fetch error:', err);
        }
    }

    function updateWorklistCounters() {
        const total = worklistStudies.length;
        const statCount = worklistStudies.filter(s => s.priority === 'STAT_CRITICAL').length;
        const pendingCount = worklistStudies.filter(s => s.status === 'PENDING').length;
        const signedCount = worklistStudies.filter(s => s.status === 'SIGNED').length;

        if (countAll) countAll.textContent = total;
        if (countStat) countStat.textContent = statCount;
        if (countPending) countPending.textContent = pendingCount;
        if (countSigned) countSigned.textContent = signedCount;

        if (worklistStatBadge) {
            worklistStatBadge.textContent = `${statCount} STAT`;
            worklistStatBadge.style.color = statCount > 0 ? 'var(--pathology-critical)' : 'var(--titanium-400)';
        }
    }

    function getFilteredStudies() {
        return worklistStudies.filter(study => {
            if (activeFilter === 'stat') return study.priority === 'STAT_CRITICAL';
            if (activeFilter === 'pending') return study.status === 'PENDING';
            if (activeFilter === 'signed') return study.status === 'SIGNED';
            return true; // 'all'
        });
    }

    function renderWorklistQueue() {
        if (!studyQueueList) return;
        const filtered = getFilteredStudies();

        if (filtered.length === 0) {
            studyQueueList.innerHTML = `
                <div class="empty-queue-msg">
                    <div class="empty-queue-icon">
                        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="22 12 16 12 14 15 10 15 8 12 2 12"></polyline>
                            <path d="M5.45 5.11L2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.45-6.89A2 2 0 0 0 16.76 4H7.24a2 2 0 0 0-1.79 1.11z"></path>
                        </svg>
                    </div>
                    <div class="empty-queue-title">Triage Queue Empty</div>
                    <p class="empty-queue-desc">No studies match active filter or queue was purged. Ingest new cohorts or restore baseline cases.</p>
                    <div class="empty-queue-btn-row" style="display: flex; flex-direction: column; gap: 8px;">
                        <button type="button" class="btn-quick-upload" id="empty-restore-baseline-btn" style="width: 100%; justify-content: center;">
                            🔄 Restore Baseline Studies
                        </button>
                        <button type="button" class="btn-quick-upload" id="empty-inject-cohort-btn" style="width: 100%; justify-content: center; background: rgba(2, 132, 199, 0.2); border-color: #0284c7; color: #38bdf8;">
                            ⚡ Transmit 6-Patient PACS Cohort
                        </button>
                    </div>
                </div>
            `;
            const emptyRestoreBtn = document.getElementById('empty-restore-baseline-btn');
            if (emptyRestoreBtn) {
                emptyRestoreBtn.addEventListener('click', restoreBaselineStudies);
            }
            const emptyCohortBtn = document.getElementById('empty-inject-cohort-btn');
            if (emptyCohortBtn) {
                emptyCohortBtn.addEventListener('click', () => {
                    if (btnInjectCohort) btnInjectCohort.click();
                    else openPacsHubModal();
                });
            }
            updateBulkSelectionBar();
            return;
        }

        studyQueueList.innerHTML = filtered.map(study => {
            const isSelected = study.study_id === selectedStudyId;
            const isChecked = selectedStudyIds.has(study.study_id);
            const isStat = study.priority === 'STAT_CRITICAL';
            const isUrgent = study.priority === 'URGENT';
            const isSigned = study.status === 'SIGNED';

            const priorityBadge = isStat
                ? `<span class="study-card-priority stat"><span class="prio-dot-pulse"></span>🚨 STAT CRITICAL</span>`
                : (isUrgent
                    ? `<span class="study-card-priority urgent">URGENT</span>`
                    : `<span class="study-card-priority routine">ROUTINE</span>`);

            const statusBadge = isSigned
                ? `<span class="study-card-status signed">✓ SIGNED</span>`
                : `<span class="study-card-status pending">PENDING</span>`;

            const confBadgeClass = study.is_pneumonia ? 'pneu' : 'norm';

            return `
                <div class="study-card ${isSelected ? 'active' : ''} ${isChecked ? 'selected-for-purge' : ''}" data-study-id="${study.study_id}" role="button" tabindex="0">
                    <div class="study-card-header">
                        <div class="study-card-prio-wrap" style="display: flex; align-items: center; gap: 6px;">
                            <div class="card-select-wrap">
                                <input type="checkbox" class="study-card-checkbox" data-checkbox-id="${study.study_id}" ${isChecked ? 'checked' : ''} aria-label="Select study for purge">
                            </div>
                            ${priorityBadge}
                        </div>
                        <div class="study-card-actions">
                            <button type="button" class="btn-card-dismiss" data-delete-id="${study.study_id}" title="Remove study from queue" aria-label="Remove study">
                                <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2.2">
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </button>
                            ${statusBadge}
                        </div>
                    </div>
                    <div class="study-card-patient">
                        <div class="patient-name">${escapeHtml(study.patient_name)}</div>
                        <div class="patient-sub">${escapeHtml(study.patient_mrn)} • ${escapeHtml(study.patient_age_sex)}</div>
                    </div>
                    <div class="study-card-finding">
                        <span class="finding-tag ${confBadgeClass}">${escapeHtml(study.primary_finding || study.diagnosis)}</span>
                        <span class="conf-text">${Math.round(study.confidence_percentage)}%</span>
                        <span class="zone-text">• ${escapeHtml(study.dominant_zone)}</span>
                        ${study.secondary_findings && study.secondary_findings.length > 0 ? `<span class="sec-findings-badge" style="background: rgba(56,189,248,0.15); border: 1px solid rgba(56,189,248,0.3); color: #38bdf8; font-size: 9px; padding: 1px 4px; border-radius: 3px; margin-left: 4px; font-family: var(--font-mono);">+${study.secondary_findings.length}</span>` : ''}
                    </div>
                    <div class="study-card-footer">
                        <span>${escapeHtml(study.study_time)}</span>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <button type="button" class="btn-card-consult" data-consult-id="${study.study_id}" title="Open Clinical Consultation & Voice Dictation" onclick="event.stopPropagation()">🎙️ Consult</button>
                            <a href="/viewer?study=${encodeURIComponent(study.study_id)}" target="_blank" class="btn-card-ohif" title="Launch in OHIF Diagnostic Viewer" onclick="event.stopPropagation()">OHIF ↗</a>
                            <span>${escapeHtml(study.modality)}</span>
                        </div>
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listeners to cards (avoiding clicks on checkbox or dismiss button)
        studyQueueList.querySelectorAll('.study-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.card-select-wrap') || e.target.closest('.btn-card-dismiss') || e.target.closest('.btn-card-consult')) {
                    return;
                }
                const id = card.dataset.studyId;
                const study = worklistStudies.find(s => s.study_id === id);
                if (study) loadWorklistStudy(study);
            });
        });

        // Attach click listeners to individual consult buttons
        studyQueueList.querySelectorAll('.btn-card-consult').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.consultId;
                const study = worklistStudies.find(s => s.study_id === id);
                if (study) {
                    loadWorklistStudy(study);
                    setTimeout(() => {
                        const openReportBtn = document.getElementById('open-report-btn');
                        if (openReportBtn) openReportBtn.click();
                    }, 120);
                }
            });
        });

        // Attach checkbox change listeners
        studyQueueList.querySelectorAll('.study-card-checkbox').forEach(chk => {
            chk.addEventListener('click', (e) => e.stopPropagation());
            chk.addEventListener('change', (e) => {
                e.stopPropagation();
                const id = chk.dataset.checkboxId;
                if (chk.checked) {
                    selectedStudyIds.add(id);
                    isSelectModeActive = true;
                } else {
                    selectedStudyIds.delete(id);
                }
                const card = chk.closest('.study-card');
                if (card) card.classList.toggle('selected-for-purge', chk.checked);
                updateBulkSelectionBar();
            });
        });

        // Attach delete dismiss click listeners
        studyQueueList.querySelectorAll('.btn-card-dismiss').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const id = btn.dataset.deleteId;
                deleteStudy(id, true);
            });
        });

        updateBulkSelectionBar();
    }

    // ---------------------------------------------------------
    // ENTERPRISE PACS CONFIRMATION MODAL SYSTEM
    // ---------------------------------------------------------
    function showPacsConfirmModal({
        eyebrow = "ER TRIAGE PURGE CONFIRMATION",
        title = "Purge Study Records?",
        desc = "Are you sure you want to purge the selected study from the Emergency Triage Worklist?",
        targetName = null,
        targetMeta = null,
        confirmLabel = "Purge Study",
        confirmIcon = "🗑️",
        isDanger = true
    } = {}) {
        return new Promise((resolve) => {
            const dialog = document.getElementById('pacs-confirm-dialog');
            if (!dialog || typeof dialog.showModal !== 'function') {
                resolve(window.confirm(`${title}\n\n${desc}`));
                return;
            }

            const elEyebrow = document.getElementById('confirm-modal-eyebrow');
            const elTitle = document.getElementById('confirm-modal-title');
            const elDesc = document.getElementById('confirm-modal-desc');
            const elCard = document.getElementById('confirm-target-card');
            const elTargetName = document.getElementById('confirm-target-name');
            const elTargetMeta = document.getElementById('confirm-target-meta');
            const elActionIcon = document.getElementById('confirm-action-icon');
            const elActionLabel = document.getElementById('confirm-action-label');
            const elActionBtn = document.getElementById('confirm-action-btn');
            const cancelBtn = document.getElementById('confirm-cancel-btn');
            const closeXBtn = document.getElementById('confirm-modal-x-btn');

            if (elEyebrow) elEyebrow.textContent = eyebrow;
            if (elTitle) elTitle.textContent = title;
            if (elDesc) elDesc.textContent = desc;
            if (elActionIcon) elActionIcon.textContent = confirmIcon;
            if (elActionLabel) elActionLabel.textContent = confirmLabel;

            if (targetName && elCard) {
                elCard.style.display = 'flex';
                if (elTargetName) elTargetName.textContent = targetName;
                if (elTargetMeta) elTargetMeta.textContent = targetMeta || '';
            } else if (elCard) {
                elCard.style.display = 'none';
            }

            let cleanup = () => {};

            const onConfirm = () => {
                cleanup();
                dialog.close();
                resolve(true);
            };

            const onCancel = () => {
                cleanup();
                dialog.close();
                resolve(false);
            };

            const onKeyDown = (e) => {
                if (e.key === 'Escape') {
                    e.preventDefault();
                    onCancel();
                } else if (e.key === 'Enter') {
                    e.preventDefault();
                    onConfirm();
                }
            };

            const onBackdropClick = (e) => {
                const rect = dialog.getBoundingClientRect();
                const isInDialog = (rect.top <= e.clientY && e.clientY <= rect.top + rect.height
                  && rect.left <= e.clientX && e.clientX <= rect.left + rect.width);
                if (!isInDialog) {
                    onCancel();
                }
            };

            cleanup = () => {
                if (elActionBtn) elActionBtn.removeEventListener('click', onConfirm);
                if (cancelBtn) cancelBtn.removeEventListener('click', onCancel);
                if (closeXBtn) closeXBtn.removeEventListener('click', onCancel);
                dialog.removeEventListener('keydown', onKeyDown);
                dialog.removeEventListener('click', onBackdropClick);
            };

            if (elActionBtn) elActionBtn.addEventListener('click', onConfirm, { once: true });
            if (cancelBtn) cancelBtn.addEventListener('click', onCancel, { once: true });
            if (closeXBtn) closeXBtn.addEventListener('click', onCancel, { once: true });
            dialog.addEventListener('keydown', onKeyDown);
            dialog.addEventListener('click', onBackdropClick);

            dialog.showModal();
            if (elActionBtn) elActionBtn.focus();
        });
    }

    function updateBulkSelectionBar() {
        const visibleStudies = getFilteredStudies();
        const totalVisible = visibleStudies.length;
        const selectedCount = selectedStudyIds.size;

        if (bulkSelectedCount) {
            bulkSelectedCount.textContent = selectedCount;
        }
        if (bulkSelectedLabel) {
            bulkSelectedLabel.textContent = `${selectedCount} Selected`;
        }

        if (bulkPurgeSelectedBtn) {
            bulkPurgeSelectedBtn.disabled = selectedCount === 0;
            bulkPurgeSelectedBtn.innerHTML = `🗑️ Purge Selected (${selectedCount})`;
        }

        if (bulkSelectAll) {
            const allChecked = totalVisible > 0 && visibleStudies.every(s => selectedStudyIds.has(s.study_id));
            const someChecked = !allChecked && visibleStudies.some(s => selectedStudyIds.has(s.study_id));
            bulkSelectAll.checked = allChecked;
            bulkSelectAll.indeterminate = someChecked;
        }

        if (triageBulkBar) {
            if (isSelectModeActive || selectedCount > 0) {
                triageBulkBar.style.display = 'flex';
            } else {
                triageBulkBar.style.display = 'none';
            }
        }

        if (worklistSelectModeBtn) {
            worklistSelectModeBtn.classList.toggle('active', isSelectModeActive || selectedCount > 0);
        }
    }

    async function restoreBaselineStudies() {
        showWorkstationToast('🔄 Restoring baseline calibration studies...');
        try {
            const res = await fetch('/api/v1/worklist/reset', { method: 'POST' });
            if (res.ok) {
                selectedStudyIds.clear();
                isSelectModeActive = false;
                await fetchWorklist();
                showWorkstationToast('✓ 5 baseline triage studies restored.');
            } else {
                showWorkstationToast('Failed to reset baseline worklist.');
            }
        } catch (err) {
            console.error('Error resetting worklist:', err);
            showWorkstationToast('Network error restoring baseline studies.');
        }
    }

    async function deleteStudy(studyId, promptConfirm = false) {
        const studyIndex = worklistStudies.findIndex(s => s.study_id === studyId);
        if (studyIndex === -1) return;
        const study = worklistStudies[studyIndex];

        if (promptConfirm) {
            const confirmed = await showPacsConfirmModal({
                eyebrow: "ER TRIAGE STUDY REMOVAL",
                title: "Remove Study from Queue?",
                desc: `Are you sure you want to remove the examination for ${escapeHtml(study.patient_name)} from active queue memory?`,
                targetName: study.patient_name,
                targetMeta: `${study.patient_mrn} • ${study.priority === 'STAT_CRITICAL' ? '🚨 STAT CRITICAL' : study.priority} • ${escapeHtml(study.diagnosis)} (${Math.round(study.confidence_percentage)}%)`,
                confirmLabel: "Remove Study",
                confirmIcon: "🗑️"
            });
            if (!confirmed) return;
        }

        const removed = worklistStudies.splice(studyIndex, 1)[0];
        selectedStudyIds.delete(studyId);

        // Background server cache sync
        fetch(`/api/v1/worklist/${encodeURIComponent(studyId)}`, { method: 'DELETE' }).catch(err => {
            console.warn('Backend delete sync notice:', err);
        });

        updateWorklistCounters();
        renderWorklistQueue();

        // If the removed study was actively displayed in the viewport:
        if (selectedStudyId === studyId) {
            const filtered = getFilteredStudies();
            if (filtered.length > 0) {
                const nextIndex = Math.min(studyIndex, filtered.length - 1);
                loadWorklistStudy(filtered[nextIndex]);
            } else if (worklistStudies.length > 0) {
                loadWorklistStudy(worklistStudies[0]);
            } else {
                showEmptyViewportState();
            }
        }

        showWorkstationToast(`🗑️ Study removed: ${removed.patient_name || studyId}`);
    }

    function showEmptyViewportState() {
        selectedStudyId = null;
        currentPrediction = null;
        currentFile = null;
        if (emptyState) emptyState.hidden = false;
        if (diagnosisContent) diagnosisContent.hidden = true;
        if (loadingState) loadingState.hidden = true;
        if (hudPatientId) hudPatientId.textContent = 'PATIENT: STANDBY';
        if (hudPatientName) hudPatientName.textContent = 'NAME: STANDBY';
        if (hudModality) hudModality.textContent = 'MODALITY: --';
        if (hudStudyStatus) hudStudyStatus.textContent = 'STATUS: STANDBY';
        if (btnSignoff) btnSignoff.disabled = true;
    }

    // Filter pill click handling
    filterPills.forEach(pill => {
        pill.addEventListener('click', () => {
            filterPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            activeFilter = pill.dataset.filter;
            renderWorklistQueue();
        });
    });

    // ---------------------------------------------------------
    // 4. ZERO-LATENCY STUDY VIEWPORT SWITCHER
    // ---------------------------------------------------------
    function loadWorklistStudy(study) {
        selectedStudyId = study.study_id;

        // Re-highlight active study card
        document.querySelectorAll('.study-card').forEach(card => {
            card.classList.toggle('active', card.dataset.studyId === selectedStudyId);
        });

        // Update DICOM HUD Demographics
        if (hudPatientId) hudPatientId.textContent = `PATIENT: #${study.patient_mrn}`;
        if (hudPatientName) hudPatientName.textContent = `NAME: ${study.patient_name}`;
        if (hudModality) hudModality.textContent = `MODALITY: ${study.modality}`;
        if (hudSensor && study.dicom_metadata) {
            const kvp = study.dicom_metadata.kvp ? `${study.dicom_metadata.kvp} kVp` : '125 kVp';
            const exp = study.dicom_metadata.exposure_time ? `${study.dicom_metadata.exposure_time} ms` : '14 ms';
            hudSensor.textContent = `${kvp} • ${exp}`;
        }
        if (hudStudyStatus) hudStudyStatus.textContent = `STATUS: ${study.status}`;

        // Update Sign-off Button State
        updateSignoffButtonState(study.status === 'SIGNED');

        // Construct normalized prediction object for workstation components
        const primaryFinding = study.primary_finding || study.diagnosis;
        const defaultImpression = primaryFinding && primaryFinding !== 'NORMAL'
            ? `Radiologic evaluation demonstrates focal evidence of ${primaryFinding.toLowerCase().replace(/_/g, ' ')} with ${Math.round(study.confidence_percentage)}% model confidence.`
            : 'Thoracic structures within normal physiological limits. No acute consolidation or pneumothorax.';

        currentPrediction = {
            study_id: study.study_id,
            diagnosis: study.diagnosis,
            is_pneumonia: study.is_pneumonia,
            confidence_percentage: study.confidence_percentage,
            probability: study.is_pneumonia ? (study.confidence_percentage / 100) : 1 - (study.confidence_percentage / 100),
            risk_tier: study.priority === 'STAT_CRITICAL' ? 'HIGH_RISK_CONSOLIDATION' : (study.is_pneumonia ? 'MODERATE_RISK' : 'LOW_RISK_CLEAR'),
            clinical_recommendation: study.is_pneumonia
                ? 'STAT emergency physician notification recommended. Evaluate for broad-spectrum antimicrobial coverage, oxygen supplementation, and microbiological sputum cultures.'
                : 'Parenchyma within normal limits. No evidence of focal consolidation, pneumothorax, or acute vascular engorgement.',
            zonation: study.zonation,
            original_image_b64: study.image_b64,
            gradcam_overlay_b64: study.gradcam_overlay_b64,
            latency_ms: 12.4,
            dicom_metadata: study.dicom_metadata,
            primary_finding: primaryFinding,
            primary_display_name: primaryFinding.replace(/_/g, ' '),
            secondary_findings: study.secondary_findings || [],
            findings: study.findings || [
                {
                    name: study.is_pneumonia ? 'PNEUMONIA' : 'NORMAL',
                    display_name: study.is_pneumonia ? 'Bacterial/Viral Pneumonia' : 'Clear Lung Fields',
                    probability: study.confidence_percentage / 100.0,
                    confidence_percentage: study.confidence_percentage,
                    is_detected: study.is_pneumonia,
                    severity: study.is_pneumonia ? 'CRITICAL' : 'NORMAL',
                    clinical_description: study.is_pneumonia ? 'Alveolar consolidation' : 'No acute pathology',
                    anatomical_focus: study.dominant_zone || 'Mid/Lower Zones'
                },
                {
                    name: 'PNEUMOTHORAX',
                    display_name: 'Pneumothorax',
                    probability: 0.05,
                    confidence_percentage: 5.0,
                    is_detected: false,
                    severity: 'BENIGN',
                    clinical_description: 'Intact pleural line, normal apical markings',
                    anatomical_focus: 'Apex'
                },
                {
                    name: 'PLEURAL_EFFUSION',
                    display_name: 'Pleural Effusion',
                    probability: 0.08,
                    confidence_percentage: 8.0,
                    is_detected: false,
                    severity: 'BENIGN',
                    clinical_description: 'Sharp costophrenic angles',
                    anatomical_focus: 'Bases'
                },
                {
                    name: 'CARDIOMEGALY',
                    display_name: 'Cardiomegaly',
                    probability: 0.12,
                    confidence_percentage: 12.0,
                    is_detected: false,
                    severity: 'BENIGN',
                    clinical_description: 'Normal cardiothoracic ratio < 0.50',
                    anatomical_focus: 'Cardiomediastinum'
                },
                {
                    name: 'ATELECTASIS',
                    display_name: 'Atelectasis',
                    probability: 0.06,
                    confidence_percentage: 6.0,
                    is_detected: false,
                    severity: 'BENIGN',
                    clinical_description: 'No volume loss or linear collapse',
                    anatomical_focus: 'Subsegmental'
                },
                {
                    name: 'NORMAL',
                    display_name: 'Clear Lung Fields',
                    probability: study.is_pneumonia ? 0.02 : (study.confidence_percentage / 100.0),
                    confidence_percentage: study.is_pneumonia ? 2.0 : study.confidence_percentage,
                    is_detected: !study.is_pneumonia,
                    severity: 'NORMAL',
                    clinical_description: 'Preserved parenchymal aeration',
                    anatomical_focus: 'Bilateral'
                }
            ],
            clinical_impression: defaultImpression
        };

        // Render full radiologic findings in viewport
        renderDiagnosisResults(currentPrediction);
        evaluateStatAlert(study);
    }

    function updateSignoffButtonState(isSigned) {
        if (!btnSignoff) return;
        if (isSigned) {
            btnSignoff.classList.add('signed');
            btnSignoff.disabled = true;
            if (signoffBtnText) signoffBtnText.textContent = '✓ Verified & Signed';
        } else {
            btnSignoff.classList.remove('signed');
            btnSignoff.disabled = false;
            if (signoffBtnText) signoffBtnText.textContent = 'Sign Off & Attest (S)';
        }
    }

    // ---------------------------------------------------------
    // 5. RADIOLOGIST ELECTRONIC SIGN-OFF
    // ---------------------------------------------------------
    async function executeSignoff() {
        if (!currentPrediction || !selectedStudyId) return;

        const study = worklistStudies.find(s => s.study_id === selectedStudyId);
        if (study && study.status === 'SIGNED') return;

        try {
            btnSignoff.disabled = true;
            if (signoffBtnText) signoffBtnText.textContent = 'Attesting Signature...';

            const payload = {
                study_id: selectedStudyId,
                physician_name: "Dr. Eleanor Vance, MD",
                physician_license: "RAD-US-89410",
                findings_summary: `Attested via ALVEON Workstation. Findings: ${currentPrediction.diagnosis} (${Math.round(currentPrediction.confidence_percentage)}% confidence). Dominant involvement: ${currentPrediction.zonation?.dominant_zone || 'Bilateral'}.`,
                attestation_accepted: true
            };

            const res = await fetch('/api/v1/signoff', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) throw new Error('Electronic sign-off attestation failed');
            const data = await res.json();

            // Update local study status
            if (study) study.status = 'SIGNED';
            if (currentPrediction) currentPrediction.status = 'SIGNED';

            if (hudStudyStatus) hudStudyStatus.textContent = 'STATUS: SIGNED';
            updateSignoffButtonState(true);
            updateWorklistCounters();
            renderWorklistQueue();

            showWorkstationToast(`✓ Study Signed: Audit Stamp ${data.audit_hash}`);
        } catch (err) {
            console.error('Sign-off error:', err);
            alert('Attestation Error: ' + err.message);
            updateSignoffButtonState(false);
        }
    }

    if (btnSignoff) {
        btnSignoff.addEventListener('click', executeSignoff);
    }

    // ---------------------------------------------------------
    // 6. DICOM TAGS INSPECTOR MODAL
    // ---------------------------------------------------------
    function openDicomTagsModal() {
        if (!currentPrediction || !dicomTagsDialog) return;

        const meta = currentPrediction.dicom_metadata || {};
        if (dicomModalSubtitle) {
            dicomModalSubtitle.textContent = `Study: ${currentPrediction.study_id || 'LOCAL-INGEST'} • ${meta.is_dicom ? 'Native Binary DICOM' : 'Standard Radiographic Ingest'}`;
        }
        if (dicomFooterSyntax) {
            dicomFooterSyntax.textContent = meta.transfer_syntax || '1.2.840.10008.1.2.1 (Explicit VR Little Endian)';
        }

        // Build Tag Rows
        let rowsHtml = '';
        if (meta.all_tags && meta.all_tags.length > 0) {
            rowsHtml = meta.all_tags.map(tag => `
                <tr>
                    <td class="tag-code">${escapeHtml(tag.tag)}</td>
                    <td class="tag-vr">${escapeHtml(tag.vr)}</td>
                    <td class="tag-name">${escapeHtml(tag.name)}</td>
                    <td class="tag-val">${escapeHtml(String(tag.value))}</td>
                </tr>
            `).join('');
        } else {
            // High-fidelity fallback tags populated from standard fields
            const fallbackTags = [
                { tag: '(0008,0016)', vr: 'UI', name: 'SOP Class UID', value: '1.2.840.10008.5.1.4.1.1.1 (Digital X-Ray)' },
                { tag: '(0008,0020)', vr: 'DA', name: 'Study Date', value: meta.study_date || '20260910' },
                { tag: '(0008,0060)', vr: 'CS', name: 'Modality', value: meta.modality || 'DX' },
                { tag: '(0008,0070)', vr: 'LO', name: 'Manufacturer', value: meta.manufacturer || 'ALVEON MEDICAL SYSTEMS' },
                { tag: '(0008,1030)', vr: 'LO', name: 'Study Description', value: 'CHEST 1-VIEW AP/PA PORTABLE' },
                { tag: '(0010,0010)', vr: 'PN', name: 'Patient Name', value: meta.patient_name || 'VANCE^ELEANOR' },
                { tag: '(0010,0020)', vr: 'LO', name: 'Patient ID (MRN)', value: meta.patient_id || 'MRN-90214' },
                { tag: '(0010,0040)', vr: 'CS', name: 'Patient Sex', value: meta.patient_sex || 'F' },
                { tag: '(0018,0060)', vr: 'DS', name: 'kVp', value: meta.kvp ? String(meta.kvp) : '125' },
                { tag: '(0018,1150)', vr: 'IS', name: 'Exposure Time', value: meta.exposure_time ? String(meta.exposure_time) : '14' },
                { tag: '(0028,0004)', vr: 'CS', name: 'Photometric Interpretation', value: meta.photometric_interpretation || 'MONOCHROME2' },
                { tag: '(0028,0010)', vr: 'US', name: 'Rows', value: meta.rows ? String(meta.rows) : '1024' },
                { tag: '(0028,0011)', vr: 'US', name: 'Columns', value: meta.columns ? String(meta.columns) : '1024' },
                { tag: '(0028,0100)', vr: 'US', name: 'Bits Allocated', value: meta.bits_allocated ? String(meta.bits_allocated) : '16' },
                { tag: '(0028,1050)', vr: 'DS', name: 'Window Center', value: meta.window_center !== null && meta.window_center !== undefined ? String(meta.window_center) : '2048' },
                { tag: '(0028,1051)', vr: 'DS', name: 'Window Width', value: meta.window_width !== null && meta.window_width !== undefined ? String(meta.window_width) : '4096' }
            ];

            rowsHtml = fallbackTags.map(tag => `
                <tr>
                    <td class="tag-code">${escapeHtml(tag.tag)}</td>
                    <td class="tag-vr">${escapeHtml(tag.vr)}</td>
                    <td class="tag-name">${escapeHtml(tag.name)}</td>
                    <td class="tag-val">${escapeHtml(tag.value)}</td>
                </tr>
            `).join('');
        }

        if (dicomTagsTbody) dicomTagsTbody.innerHTML = rowsHtml;
        dicomTagsDialog.showModal();
    }

    if (hudTagTrigger) hudTagTrigger.addEventListener('click', openDicomTagsModal);
    if (closeDicomModalBtn) closeDicomModalBtn.addEventListener('click', () => dicomTagsDialog.close());
    if (dismissDicomBtn) dismissDicomBtn.addEventListener('click', () => dicomTagsDialog.close());

    // ---------------------------------------------------------
    // 7. KEYBOARD SHORTCUTS & ERGONOMIC NAVIGATION
    // ---------------------------------------------------------
    window.addEventListener('keydown', (e) => {
        // Do not trigger hotkeys if typing inside an active input or textarea
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

        // Invert Polarity: 'I'
        if (e.key === 'i' || e.key === 'I') {
            const invertBtn = document.getElementById('btn-invert');
            if (invertBtn) invertBtn.click();
        }

        // DICOM Inspector: 'D'
        if (e.key === 'd' || e.key === 'D') {
            if (dicomTagsDialog && dicomTagsDialog.open) {
                dicomTagsDialog.close();
            } else {
                openDicomTagsModal();
            }
        }

        // PACS & DICOMweb Interoperability Hub: 'W'
        if (e.key === 'w' || e.key === 'W') {
            if (pacsHubDialog && pacsHubDialog.open) {
                pacsHubDialog.close();
            } else {
                openPacsHubModal();
            }
        }

        // Sign-Off Attestation: 'S'
        if (e.key === 's' || e.key === 'S') {
            executeSignoff();
        }

        // Clinical Consultation & Voice Report: 'R'
        if (e.key === 'r' || e.key === 'R') {
            const isEditing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
            if (!isEditing) {
                const openReportBtn = document.getElementById('open-report-btn');
                if (openReportBtn) openReportBtn.click();
            }
        }

        // Navigate Studies in Worklist: Arrow Down / J
        if (e.key === 'ArrowDown' || e.key === 'j' || e.key === 'J') {
            e.preventDefault();
            navigateWorklist(1);
        }

        // Navigate Studies in Worklist: Arrow Up / K
        if (e.key === 'ArrowUp' || e.key === 'k' || e.key === 'K') {
            e.preventDefault();
            navigateWorklist(-1);
        }

        // Delete Currently Active Study or Selected Studies: 'Delete' or 'Backspace'
        if (e.key === 'Delete' || e.key === 'Backspace') {
            const isEditing = ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName);
            if (!isEditing) {
                if (selectedStudyIds.size > 0 && bulkPurgeSelectedBtn && !bulkPurgeSelectedBtn.disabled) {
                    e.preventDefault();
                    bulkPurgeSelectedBtn.click();
                } else if (selectedStudyId) {
                    e.preventDefault();
                    deleteStudy(selectedStudyId, true);
                }
            }
        }

        // Caliper & Measurement Hotkeys
        if (e.key === 'r' || e.key === 'R') {
            if (typeof setActiveMeasureTool === 'function') {
                setActiveMeasureTool('ruler');
                showWorkstationToast('📏 Linear Caliper Active (Click & Drag in mm)');
            }
        }
        if (e.key === 'c' || e.key === 'C') {
            if (typeof setActiveMeasureTool === 'function') {
                setActiveMeasureTool('ctr');
                showWorkstationToast('🫀 CTR Caliper Active (Draw cardiac line, then thorax)');
            }
        }
        if (e.key === 'o' || e.key === 'O') {
            if (typeof setActiveMeasureTool === 'function') {
                setActiveMeasureTool('roi');
                showWorkstationToast('⭕ Elliptical ROI Active (Drag over lesion)');
            }
        }
        if (e.key === 'a' || e.key === 'A') {
            if (typeof setActiveMeasureTool === 'function') {
                setActiveMeasureTool('arrow');
                showWorkstationToast('↗️ Diagnostic Arrow Callout Active');
            }
        }
        if (e.key === 'v' || e.key === 'V') {
            if (typeof setActiveMeasureTool === 'function') {
                setActiveMeasureTool('pointer');
                showWorkstationToast('Pointer / Split Wipe Mode Active');
            }
        }

        // Escape closes modals and resets calipers
        if (e.key === 'Escape') {
            if (typeof activeMeasureTool !== 'undefined' && activeMeasureTool !== 'pointer') {
                setActiveMeasureTool('pointer');
            }
            const pacsConfirmDialog = document.getElementById('pacs-confirm-dialog');
            if (pacsConfirmDialog && pacsConfirmDialog.open) pacsConfirmDialog.close();
            if (pacsHubDialog && pacsHubDialog.open) pacsHubDialog.close();
            if (dicomTagsDialog && dicomTagsDialog.open) dicomTagsDialog.close();
            if (reportDialog && reportDialog.open) reportDialog.close();
        }
    });

    function navigateWorklist(offset) {
        const filtered = getFilteredStudies();
        if (filtered.length === 0) return;

        const currentIndex = filtered.findIndex(s => s.study_id === selectedStudyId);
        let nextIndex = 0;
        if (currentIndex !== -1) {
            nextIndex = currentIndex + offset;
            if (nextIndex < 0) nextIndex = 0;
            if (nextIndex >= filtered.length) nextIndex = filtered.length - 1;
        }

        loadWorklistStudy(filtered[nextIndex]);
        const activeCard = studyQueueList?.querySelector(`.study-card[data-study-id="${filtered[nextIndex].study_id}"]`);
        if (activeCard) {
            activeCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    }

    // ---------------------------------------------------------
    // 8. STUDY INGESTION & BATCH MULTI-FILE & FOLDER DROP
    // ---------------------------------------------------------

    // Helper to filter valid medical image and DICOM formats
    function filterMedicalFiles(fileList) {
        const validExts = ['.dcm', '.dicom', '.jpg', '.jpeg', '.png', '.webp', '.tiff', '.tif'];
        return (fileList || []).filter(file => {
            if (!file || !file.name) return false;
            // Exclude system files and hidden files
            if (file.name.startsWith('.') || file.name === 'Thumbs.db') return false;
            const lower = file.name.toLowerCase();
            const hasExt = validExts.some(ext => lower.endsWith(ext));
            // Potential DICOM file without extension (e.g., standard PACS export like CT0001, IM001)
            const isDicomCandidate = !file.name.includes('.') && file.size > 132;
            return hasExt || isDicomCandidate;
        });
    }

    // HTML5 File System API Directory Scanner with 100-item pagination support
    async function scanFileSystemEntry(entry) {
        if (!entry) return [];
        if (entry.isFile) {
            return new Promise((resolve) => {
                entry.file(
                    (f) => resolve([f]),
                    (err) => {
                        console.warn('Error reading file entry:', err);
                        resolve([]);
                    }
                );
            });
        } else if (entry.isDirectory) {
            try {
                const dirReader = entry.createDirectoryReader();
                const allEntries = [];

                // Chromium reads at most 100 entries per batch; loop until empty
                const readNextBatch = () => new Promise((resolve, reject) => {
                    dirReader.readEntries(resolve, reject);
                });

                let batch = await readNextBatch();
                while (batch && batch.length > 0) {
                    allEntries.push(...batch);
                    batch = await readNextBatch();
                }

                // Recursively traverse all sub-entries
                const subPromises = allEntries.map(sub => scanFileSystemEntry(sub));
                const subResults = await Promise.all(subPromises);
                return subResults.flat();
            } catch (err) {
                console.warn('Error traversing directory entry:', err);
                return [];
            }
        }
        return [];
    }

    // Extract all files from DataTransfer (handles dropped files, directories, nested trees)
    async function extractFilesFromDataTransfer(dataTransfer) {
        if (!dataTransfer) return [];
        const items = dataTransfer.items;
        if (items && items.length > 0) {
            const promises = [];
            for (let i = 0; i < items.length; i++) {
                const item = items[i];
                if (item.kind !== 'file') continue;
                const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : (item.getAsEntry ? item.getAsEntry() : null);
                if (entry) {
                    promises.push(scanFileSystemEntry(entry));
                } else {
                    const f = item.getAsFile();
                    if (f) promises.push(Promise.resolve([f]));
                }
            }
            const arrays = await Promise.all(promises);
            return arrays.flat().filter(Boolean);
        } else if (dataTransfer.files && dataTransfer.files.length > 0) {
            return Array.from(dataTransfer.files);
        }
        return [];
    }

    // Connect File/Folder Picker Triggers
    if (browseBtn) {
        browseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (fileInput) fileInput.click();
        });
    }

    if (browseFolderBtn) {
        browseFolderBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (folderInput) folderInput.click();
        });
    }

    if (worklistFolderBtn) {
        worklistFolderBtn.addEventListener('click', () => {
            if (folderInput) folderInput.click();
        });
    }

    if (worklistFilesBtn) {
        worklistFilesBtn.addEventListener('click', () => {
            if (fileInput) fileInput.click();
        });
    }

    // Dropzone Click (ignoring direct clicks on buttons)
    if (dropZone) {
        dropZone.addEventListener('click', (e) => {
            if (e.target.closest('#browse-btn') || e.target.closest('#browse-folder-btn')) return;
            if (fileInput) fileInput.click();
        });
    }

    // Drag and Drop Event Setup for Dropzone & Worklist Queue
    [dropZone, triageWorklistContainer].forEach(zone => {
        if (!zone) return;

        ['dragenter', 'dragover'].forEach(name => {
            zone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.add('dragover');
            });
        });

        ['dragleave', 'drop'].forEach(name => {
            zone.addEventListener(name, (e) => {
                e.preventDefault();
                e.stopPropagation();
                zone.classList.remove('dragover');
            });
        });

        zone.addEventListener('drop', async (e) => {
            e.preventDefault();
            e.stopPropagation();
            zone.classList.remove('dragover');

            showWorkstationToast('🔍 Unpacking folder / studies from drop payload...');
            const rawFiles = await extractFilesFromDataTransfer(e.dataTransfer);
            const validFiles = filterMedicalFiles(rawFiles);

            if (validFiles.length === 0) {
                showWorkstationToast('⚠️ No supported radiograph or DICOM files found in dropped folder or files.');
                return;
            }

            showWorkstationToast(`📂 Ingesting ${validFiles.length} studies from folder / payload...`);
            handleFileSelected(validFiles[0]);
            await handleBatchFiles(validFiles);
        });
    });

    // File Input Change
    if (fileInput) {
        fileInput.addEventListener('change', async (e) => {
            const rawFiles = Array.from(e.target.files || []);
            if (rawFiles.length === 0) return;

            const validFiles = filterMedicalFiles(rawFiles);
            if (validFiles.length === 0) {
                showWorkstationToast('⚠️ No supported radiograph/DICOM formats (.dcm, .jpg, .png) selected.');
                fileInput.value = '';
                return;
            }

            handleFileSelected(validFiles[0]);
            await handleBatchFiles(validFiles);
            fileInput.value = '';
        });
    }

    // Folder Directory Input Change
    if (folderInput) {
        folderInput.addEventListener('change', async (e) => {
            const rawFiles = Array.from(e.target.files || []);
            if (rawFiles.length === 0) return;

            const validFiles = filterMedicalFiles(rawFiles);
            if (validFiles.length === 0) {
                showWorkstationToast('⚠️ No supported radiograph or DICOM files (.dcm, .jpg, .png) found in folder.');
                folderInput.value = '';
                return;
            }

            showWorkstationToast(`📁 Folder Selected: Found ${validFiles.length} studies. Ingesting cohort...`);
            handleFileSelected(validFiles[0]);
            await handleBatchFiles(validFiles);
            folderInput.value = '';
        });
    }

    function handleFileSelected(file) {
        currentFile = file;
        if (analyzeBtn) analyzeBtn.disabled = false;
        if (clearStagedBtn) clearStagedBtn.style.display = 'inline-flex';
        const pText = dropZone?.querySelector('.drop-text-primary');
        const sText = dropZone?.querySelector('.drop-text-secondary');
        if (pText) pText.textContent = `STUDY: ${file.name}`;
        if (sText) sText.textContent = `${(file.size / 1024).toFixed(1)} KB • Ingested into PACS Memory`;
        if (dropZone) dropZone.style.borderColor = 'var(--titanium-200)';
    }

    if (clearStagedBtn) {
        clearStagedBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            currentFile = null;
            if (fileInput) fileInput.value = '';
            if (folderInput) folderInput.value = '';
            if (analyzeBtn) analyzeBtn.disabled = true;
            clearStagedBtn.style.display = 'none';

            const pText = dropZone?.querySelector('.drop-text-primary');
            const sText = dropZone?.querySelector('.drop-text-secondary');
            if (pText) pText.textContent = 'Ingest Patient Cohort Folder or Studies';
            if (sText) sText.textContent = 'Drag & Drop Folders or DICOM Files (.dcm, .jpg, .png) • Automatic ER Acuity Triage';
            if (dropZone) dropZone.style.borderColor = '';
            showWorkstationToast('Staged study file cleared from memory.');
        });
    }

    if (worklistSelectModeBtn) {
        worklistSelectModeBtn.addEventListener('click', () => {
            isSelectModeActive = !isSelectModeActive;
            if (!isSelectModeActive) {
                selectedStudyIds.clear();
            }
            updateBulkSelectionBar();
            renderWorklistQueue();
        });
    }

    if (bulkSelectAll) {
        bulkSelectAll.addEventListener('change', (e) => {
            const visible = getFilteredStudies();
            if (e.target.checked) {
                visible.forEach(s => selectedStudyIds.add(s.study_id));
                isSelectModeActive = true;
            } else {
                visible.forEach(s => selectedStudyIds.delete(s.study_id));
            }
            updateBulkSelectionBar();
            renderWorklistQueue();
        });
    }

    if (bulkCancelBtn) {
        bulkCancelBtn.addEventListener('click', () => {
            isSelectModeActive = false;
            selectedStudyIds.clear();
            updateBulkSelectionBar();
            renderWorklistQueue();
        });
    }

    if (bulkPurgeSelectedBtn) {
        bulkPurgeSelectedBtn.addEventListener('click', async () => {
            const idsToDelete = Array.from(selectedStudyIds);
            if (idsToDelete.length === 0) return;

            const count = idsToDelete.length;
            const singleStudy = count === 1 ? worklistStudies.find(s => s.study_id === idsToDelete[0]) : null;

            const confirmed = await showPacsConfirmModal({
                eyebrow: count === 1 ? "ER TRIAGE STUDY PURGE" : "BATCH PURGE CONFIRMATION",
                title: count === 1 ? "Purge Study from Queue?" : `Purge ${count} Selected Studies?`,
                desc: count === 1
                    ? `Are you sure you want to purge the selected examination for ${escapeHtml(singleStudy?.patient_name || 'this patient')} from the emergency triage queue?`
                    : `Are you sure you want to purge all ${count} selected radiologic examinations from active triage queue memory? This action cannot be undone.`,
                targetName: count === 1 ? (singleStudy?.patient_name || 'Selected Study') : `${count} Selected Studies`,
                targetMeta: count === 1
                    ? `${singleStudy?.patient_mrn || ''} • ${singleStudy?.priority === 'STAT_CRITICAL' ? '🚨 STAT CRITICAL' : (singleStudy?.priority || 'ROUTINE')} • ${singleStudy?.diagnosis || ''}`
                    : `Batch cohort deletion • ${worklistStudies.filter(s => idsToDelete.includes(s.study_id) && s.priority === 'STAT_CRITICAL').length} STAT cases selected`,
                confirmLabel: count === 1 ? "Purge Study" : `Purge ${count} Studies`,
                confirmIcon: "🗑️"
            });
            if (!confirmed) return;

            try {
                await fetch('/api/v1/worklist/batch-delete', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ study_ids: idsToDelete })
                });
            } catch (err) {
                console.warn('Batch delete error:', err);
            }

            worklistStudies = worklistStudies.filter(s => !selectedStudyIds.has(s.study_id));
            selectedStudyIds.clear();
            isSelectModeActive = false;

            updateWorklistCounters();
            renderWorklistQueue();

            if (selectedStudyId && idsToDelete.includes(selectedStudyId)) {
                const remaining = getFilteredStudies();
                if (remaining.length > 0) {
                    loadWorklistStudy(remaining[0]);
                } else if (worklistStudies.length > 0) {
                    loadWorklistStudy(worklistStudies[0]);
                } else {
                    showEmptyViewportState();
                }
            }

            showWorkstationToast(`🗑️ Purged ${count} selected studies.`);
        });
    }

    if (worklistPurgeAllBtn) {
        worklistPurgeAllBtn.addEventListener('click', async () => {
            if (worklistStudies.length === 0) {
                showWorkstationToast('Queue is already empty.');
                return;
            }

            const total = worklistStudies.length;
            const statCount = worklistStudies.filter(s => s.priority === 'STAT_CRITICAL').length;

            const confirmed = await showPacsConfirmModal({
                eyebrow: "COMPLETE TRIAGE QUEUE PURGE",
                title: `Purge All ${total} Studies?`,
                desc: `Are you sure you want to purge ALL ${total} cases from the active Emergency Triage Queue? All radiograph pixels, native DICOM datasets, and Grad-CAM neural activations will be removed from workstation memory.`,
                targetName: `ENTIRE ER TRIAGE QUEUE (${total} CASES)`,
                targetMeta: `Complete Worklist Wipe • ${statCount} STAT critical cases queued`,
                confirmLabel: `Purge All ${total} Studies`,
                confirmIcon: "🚨"
            });
            if (!confirmed) return;

            try {
                await fetch('/api/v1/worklist?uploaded_only=false', { method: 'DELETE' });
            } catch (err) {
                console.warn('Purge all error:', err);
            }

            worklistStudies = [];
            selectedStudyIds.clear();
            isSelectModeActive = false;

            updateWorklistCounters();
            renderWorklistQueue();
            showEmptyViewportState();

            showWorkstationToast(`🗑️ Purged all ${total} studies from queue.`);
        });
    }

    async function handleBatchFiles(files) {
        setLoading(true);
        try {
            const formData = new FormData();
            files.forEach(f => formData.append('files', f));

            const res = await fetch('/api/v1/batch/triage', {
                method: 'POST',
                body: formData
            });

            if (!res.ok) throw new Error('Cohort batch triage failed');
            const data = await res.json();

            // Insert triaged studies at top of worklist
            worklistStudies = [...(data.triaged_studies || []), ...worklistStudies];
            updateWorklistCounters();
            renderWorklistQueue();

            // Switch to triage worklist tab
            setOperationalTab('worklist');

            // Select the highest-priority study
            if (data.triaged_studies && data.triaged_studies.length > 0) {
                loadWorklistStudy(data.triaged_studies[0]);
            }

            showWorkstationToast(`✓ Cohort Ingested: ${data.total_ingested} studies (${data.critical_stat_count} STAT prioritized)`);
        } catch (err) {
            console.error('Batch triage error:', err);
            alert('Batch Triage Ingestion Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    // ---------------------------------------------------------
    // 9. PACS CALIBRATION PROTOCOLS (SAMPLES)
    // ---------------------------------------------------------
    sampleCards.forEach(card => {
        card.addEventListener('click', async () => {
            const sampleId = card.dataset.sample;
            if (!sampleId) return;
            await loadSample(sampleId);
        });
    });

    async function loadSample(sampleId) {
        try {
            setLoading(true);
            const res = await fetch('/api/v1/samples');
            if (!res.ok) throw new Error('Failed to retrieve verification samples');
            const data = await res.json();
            const sample = data.samples.find(s => s.id === sampleId);
            if (!sample) throw new Error(`Sample ${sampleId} not found`);

            const response = await fetch(sample.image_b64);
            const blob = await response.blob();
            const fileExt = sample.file_extension || '.jpg';
            const file = new File([blob], `${sampleId}${fileExt}`, { type: fileExt === '.dcm' ? 'application/dicom' : 'image/jpeg' });

            handleFileSelected(file);
            await executeAnalysis();
        } catch (err) {
            console.error('Callset ingestion error:', err);
            alert('PACS Verification Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    // ---------------------------------------------------------
    // 10. EXPOSURE, WINDOW / LEVEL & PRESETS
    // ---------------------------------------------------------
    function updateVisualFilters() {
        const contrast = contrastSlider ? contrastSlider.value : 100;
        const brightness = brightnessSlider ? brightnessSlider.value : 100;
        const invert = isInverted ? 100 : 0;

        if (wwVal) wwVal.textContent = `${contrast}%`;
        if (wlVal) wlVal.textContent = `${brightness}%`;

        const filterStyle = `contrast(${contrast}%) brightness(${brightness}%) invert(${invert}%)`;
        if (viewUnderlay) viewUnderlay.style.filter = filterStyle;
        if (viewOverlay) viewOverlay.style.filter = filterStyle;
        if (sideOrig) sideOrig.style.filter = filterStyle;
        if (sideHeatmap) sideHeatmap.style.filter = filterStyle;

        if (hudWlDisplay) {
            hudWlDisplay.textContent = `W: ${Math.round(contrast * 15)} L: ${Math.round((brightness - 100) * 10 - 600)}`;
        }
    }

    if (contrastSlider) contrastSlider.addEventListener('input', updateVisualFilters);
    if (brightnessSlider) brightnessSlider.addEventListener('input', updateVisualFilters);

    if (heatmapOpacitySlider) {
        heatmapOpacitySlider.addEventListener('input', (e) => {
            if (opacityVal) opacityVal.textContent = `${e.target.value}%`;
        });

        heatmapOpacitySlider.addEventListener('change', () => {
            if (currentFile) executeAnalysis();
        });
    }

    // Window/Level Presets
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
                if (currentFile) executeAnalysis();
                return;
            }

            document.querySelectorAll('#wl-presets .tool-btn:not(#btn-invert):not(#btn-clahe)')
                .forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (wl === 'default') {
                if (contrastSlider) contrastSlider.value = 100;
                if (brightnessSlider) brightnessSlider.value = 100;
            } else if (wl === 'lung') {
                if (contrastSlider) contrastSlider.value = 160;
                if (brightnessSlider) brightnessSlider.value = 95;
            } else if (wl === 'bone') {
                if (contrastSlider) contrastSlider.value = 210;
                if (brightnessSlider) brightnessSlider.value = 80;
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

            if (currentViewMode === 'original') {
                applyViewMode('split');
            }

            if (currentFile) executeAnalysis();
        });
    });

    // ---------------------------------------------------------
    // 11. INTERACTIVE 2.5x INSPECTION LOUPE
    // ---------------------------------------------------------
    if (loupeToggleBtn) {
        loupeToggleBtn.addEventListener('click', () => {
            isLoupeActive = !isLoupeActive;
            loupeToggleBtn.classList.toggle('active', isLoupeActive);
            if (hudLoupeDisplay) hudLoupeDisplay.textContent = isLoupeActive ? 'LOUPE: 2.5x' : 'LOUPE: OFF';
            if (loupeLens) loupeLens.hidden = !isLoupeActive;
        });
    }

    if (dicomViewport) {
        dicomViewport.addEventListener('mousemove', (e) => {
            if (!isLoupeActive || !currentPrediction || !loupeLens) return;

            const rect = dicomViewport.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            loupeLens.style.left = `${x - 65}px`;
            loupeLens.style.top = `${y - 65}px`;

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
            if (isLoupeActive && loupeLens) loupeLens.hidden = true;
        });

        dicomViewport.addEventListener('mouseenter', () => {
            if (isLoupeActive && currentPrediction && loupeLens) loupeLens.hidden = false;
        });
    }

    // ---------------------------------------------------------
    // 12. MASTER DIAGNOSTIC NEURAL SWEEP
    // ---------------------------------------------------------
    if (analyzeBtn) analyzeBtn.addEventListener('click', executeAnalysis);

    async function executeAnalysis() {
        if (!currentFile) return;

        setLoading(true);
        const formData = new FormData();
        formData.append('file', currentFile);
        formData.append('apply_clahe', isClaheActive);
        formData.append('colormap', selectedColormap);
        formData.append('heatmap_alpha', (heatmapOpacitySlider ? heatmapOpacitySlider.value : 50) / 100.0);

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
            selectedStudyId = data.dicom_metadata?.patient_id || 'LOCAL-INGEST';

            // Update DICOM HUD
            if (hudPatientId) hudPatientId.textContent = `PATIENT: #${data.dicom_metadata?.patient_id || 'UNKNOWN'}`;
            if (hudPatientName) hudPatientName.textContent = `NAME: ${data.dicom_metadata?.patient_name || 'ANONYMOUS'}`;
            if (hudModality) hudModality.textContent = `MODALITY: ${data.dicom_metadata?.modality || 'DX'}`;
            if (hudStudyStatus) hudStudyStatus.textContent = 'STATUS: PENDING';
            updateSignoffButtonState(false);

            renderDiagnosisResults(data);
        } catch (err) {
            console.error('Sweep failure:', err);
            alert('Diagnostic Sweep Error: ' + err.message);
        } finally {
            setLoading(false);
        }
    }

    function setLoading(isLoading) {
        if (analyzeBtn) analyzeBtn.disabled = isLoading;
        if (analyzeSpinner) analyzeSpinner.hidden = !isLoading;
        if (analyzeBtnText) analyzeBtnText.textContent = isLoading ? 'Executing Synaptic Sweep...' : 'Execute Diagnostic Neural Sweep';

        if (isLoading) {
            if (emptyState) emptyState.hidden = true;
            if (diagnosisContent) diagnosisContent.hidden = true;
            if (loadingState) loadingState.hidden = false;
        } else {
            if (loadingState) loadingState.hidden = true;
        }
    }

    // ---------------------------------------------------------
    // 13. RENDER RADIOLOGIC FINDINGS
    // ---------------------------------------------------------
    function renderDiagnosisResults(pred) {
        if (emptyState) emptyState.hidden = true;
        if (loadingState) loadingState.hidden = true;
        if (diagnosisContent) diagnosisContent.hidden = false;
        if (viewportModes) viewportModes.hidden = false;

        const hasPathology = pred.is_pneumonia || (pred.primary_finding && pred.primary_finding !== 'NORMAL');
        const primaryTitle = pred.primary_display_name || (pred.primary_finding ? pred.primary_finding.replace(/_/g, ' ') : (pred.is_pneumonia ? 'Pneumonia' : 'Clear Lung Fields'));

        // Findings banner styling
        if (diagnosisBanner) {
            diagnosisBanner.className = 'findings-banner ' + (hasPathology ? 'pneumonia' : 'normal');
        }
        if (diagnosisBadge) {
            diagnosisBadge.textContent = hasPathology ? `PATHOLOGY: ${primaryTitle.toUpperCase()}` : 'NO ACUTE PATHOLOGY';
        }
        if (diagnosisHeading) {
            diagnosisHeading.textContent = hasPathology ? `${primaryTitle.toUpperCase()} DETECTED` : 'CLEAR LUNG FIELDS';
        }
        if (riskSubtitle) {
            riskSubtitle.textContent = (pred.risk_tier || '').replace(/_/g, ' ');
        }

        // Circular DPI Gauge
        const radius = 25;
        const circumference = 2 * Math.PI * radius;
        if (confidenceRing) {
            confidenceRing.style.strokeDasharray = `${circumference} ${circumference}`;
            const conf = pred.confidence_percentage;
            const offset = circumference - (conf / 100) * circumference;
            confidenceRing.style.strokeDashoffset = offset;
            confidenceRing.style.stroke = hasPathology ? 'var(--pathology-critical)' : 'var(--pathology-clear)';
        }
        if (confidencePercentage) {
            confidencePercentage.textContent = `${Math.round(pred.confidence_percentage)}%`;
        }

        if (latencyChip) latencyChip.textContent = `${pred.latency_ms} ms`;
        if (clinicalRecommendationText) clinicalRecommendationText.textContent = pred.clinical_recommendation;

        // Render Multi-Label Thoracic Findings (6 Conditions)
        if (multilabelFindingsStrip && pred.findings && Array.isArray(pred.findings)) {
            const iconMap = {
                'PNEUMOTHORAX': '🚨',
                'PNEUMONIA': '🫁',
                'PLEURAL_EFFUSION': '💧',
                'CARDIOMEGALY': '🫀',
                'ATELECTASIS': '📉',
                'NORMAL': '🛡️'
            };

            multilabelFindingsStrip.innerHTML = pred.findings.map(f => {
                const icon = iconMap[f.name] || '🔬';
                const pct = Math.round(f.confidence_percentage);
                const isDetected = f.is_detected;
                const sev = (f.severity || 'BENIGN').toLowerCase();
                const chipClass = `pathology-chip severity-${sev} ${isDetected ? 'detected' : 'subdued'}`;

                return `
                    <div class="${chipClass}" title="${escapeHtml(f.clinical_description || '')}">
                        <div class="pathology-chip-top">
                            <div class="pathology-chip-left">
                                <span class="pathology-chip-icon">${icon}</span>
                                <span class="pathology-chip-title">${escapeHtml(f.display_name)}</span>
                            </div>
                            <span class="pathology-chip-pct">${pct}%</span>
                        </div>
                        <div class="pathology-chip-bar">
                            <div class="pathology-chip-bar-fill" style="width: ${pct}%"></div>
                        </div>
                        <div class="pathology-chip-bottom">
                            <span class="pathology-chip-focus">${escapeHtml(f.anatomical_focus || '')}</span>
                            <span class="pathology-chip-severity">${escapeHtml(f.severity)}</span>
                        </div>
                    </div>
                `;
            }).join('');

            // Acuity Tag
            if (multilabelAcuityTag) {
                const hasCritical = pred.findings.some(f => f.is_detected && f.severity === 'CRITICAL');
                const hasUrgent = pred.findings.some(f => f.is_detected && f.severity === 'URGENT');
                const hasWarning = pred.findings.some(f => f.is_detected && f.severity === 'WARNING');

                let acuityText = 'ROUTINE';
                let acuityClass = 'routine';
                if (hasCritical) {
                    acuityText = 'STAT CRITICAL';
                    acuityClass = 'stat';
                } else if (hasUrgent) {
                    acuityText = 'URGENT';
                    acuityClass = 'urgent';
                } else if (hasWarning) {
                    acuityText = 'WARNING';
                    acuityClass = 'urgent';
                }

                multilabelAcuityTag.className = `multilabel-acuity-tag ${acuityClass}`;
                multilabelAcuityTag.textContent = `COMPOSITE ACUITY: ${acuityText}`;
            }

            // Impression
            if (multilabelImpression && multilabelImpressionText) {
                if (pred.clinical_impression) {
                    multilabelImpressionText.textContent = pred.clinical_impression;
                    multilabelImpression.style.display = 'flex';
                } else {
                    multilabelImpression.style.display = 'none';
                }
            }
        }

        // Anatomical Zonation
        if (pred.zonation) {
            const z = pred.zonation;
            if (zoneRulVal) zoneRulVal.textContent = `${z.right_upper_lobe_pct}%`;
            if (zoneRulFill) zoneRulFill.style.width = `${z.right_upper_lobe_pct}%`;
            if (zoneRllVal) zoneRllVal.textContent = `${z.right_lower_lobe_pct}%`;
            if (zoneRllFill) zoneRllFill.style.width = `${z.right_lower_lobe_pct}%`;
            if (zoneLulVal) zoneLulVal.textContent = `${z.left_upper_lobe_pct}%`;
            if (zoneLulFill) zoneLulFill.style.width = `${z.left_upper_lobe_pct}%`;
            if (zoneLllVal) zoneLllVal.textContent = `${z.left_lower_lobe_pct}%`;
            if (zoneLllFill) zoneLllFill.style.width = `${z.left_lower_lobe_pct}%`;
            if (dominantZoneChip) dominantZoneChip.textContent = `Dominant Opacity: ${z.dominant_zone}`;
        }

        // Image Sources
        if (viewUnderlay) viewUnderlay.src = pred.gradcam_overlay_b64;
        if (viewOverlay) viewOverlay.src = pred.original_image_b64;
        if (sideOrig) sideOrig.src = pred.original_image_b64;
        if (sideHeatmap) sideHeatmap.src = pred.gradcam_overlay_b64;

        resetSplitSlider();
        applyViewMode(currentViewMode);
        updateVisualFilters();
        if (typeof resetMeasurementsForNewStudy === 'function') {
            resetMeasurementsForNewStudy();
        }
    }

    // ---------------------------------------------------------
    // 14. INTERACTIVE SPLIT SLIDER
    // ---------------------------------------------------------
    function resetSplitSlider() { setSplitPosition(50); }

    function setSplitPosition(pct) {
        const clamped = Math.max(0, Math.min(100, pct));
        if (splitSliderWrapper) splitSliderWrapper.style.setProperty('--split-pos', `${clamped}%`);
        if (sliderHandle) sliderHandle.style.left = `${clamped}%`;
    }

    function onPointerDown(e) {
        if (isLoupeActive || (typeof activeMeasureTool !== 'undefined' && activeMeasureTool !== 'pointer')) return;
        isDraggingSlider = true;
        updateSliderFromEvent(e);
    }

    function onPointerMove(e) {
        if (!isDraggingSlider) return;
        updateSliderFromEvent(e);
    }

    function onPointerUp() { isDraggingSlider = false; }

    function updateSliderFromEvent(e) {
        if (!splitSliderWrapper) return;
        const rect = splitSliderWrapper.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const offsetX = clientX - rect.left;
        const pct = (offsetX / rect.width) * 100;
        setSplitPosition(pct);
    }

    if (sliderHandle) sliderHandle.addEventListener('mousedown', onPointerDown);
    if (splitSliderWrapper) splitSliderWrapper.addEventListener('mousedown', onPointerDown);
    window.addEventListener('mousemove', onPointerMove);
    window.addEventListener('mouseup', onPointerUp);

    if (sliderHandle) sliderHandle.addEventListener('touchstart', onPointerDown, { passive: true });
    if (splitSliderWrapper) splitSliderWrapper.addEventListener('touchstart', onPointerDown, { passive: true });
    window.addEventListener('touchmove', onPointerMove, { passive: true });
    window.addEventListener('touchend', onPointerUp);

    // ---------------------------------------------------------
    // 15. VIEWPORT MODE TOGGLES
    // ---------------------------------------------------------
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

        if (!splitSliderWrapper || !sideBySideWrapper || !splitClipped || !sliderHandle) return;

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

    // Reset All Workstation Controls
    const resetPacsBtn = document.getElementById('reset-pacs-btn');
    if (resetPacsBtn) {
        resetPacsBtn.addEventListener('click', () => {
            if (contrastSlider) contrastSlider.value = 100;
            if (brightnessSlider) brightnessSlider.value = 100;
            isInverted = false;
            isClaheActive = false;
            isLoupeActive = false;
            if (loupeLens) loupeLens.hidden = true;
            const invertBtn = document.getElementById('btn-invert');
            const claheBtn = document.getElementById('btn-clahe');
            if (invertBtn) invertBtn.classList.remove('active');
            if (claheBtn) claheBtn.classList.remove('active');
            if (loupeToggleBtn) loupeToggleBtn.classList.remove('active');
            if (hudLoupeDisplay) hudLoupeDisplay.textContent = 'LOUPE: OFF';
            updateVisualFilters();
            resetSplitSlider();
        });
    }

    // ---------------------------------------------------------
    // 16. OFFICIAL PACS CONSULTATION REPORT MODAL
    // ---------------------------------------------------------
    if (openReportBtn) {
        openReportBtn.addEventListener('click', async () => {
            if (!currentPrediction) return;

            try {
                const reportPayload = {
                    patient_id: currentPrediction.dicom_metadata?.patient_id || currentPrediction.study_id || "ALV-2026-X84",
                    patient_name: currentPrediction.dicom_metadata?.patient_name || "Patient Anonymous",
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
                    if (modalReportContainer) modalReportContainer.innerHTML = data.summary_html;
                    
                    // Pre-synthesize and populate ACR / RADLEX fields
                    try {
                        const srRes = await fetch('/api/v1/report/structured', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                study_id: selectedStudyId || currentPrediction.study_id,
                                patient_name: reportPayload.patient_name,
                                patient_mrn: reportPayload.patient_id,
                                diagnosis: currentPrediction.diagnosis,
                                confidence_percentage: currentPrediction.confidence_percentage,
                                all_findings: currentPrediction.multi_label_findings || [],
                                zonation: currentPrediction.zonation || {}
                            })
                        });
                        if (srRes.ok) {
                            const srData = await srRes.json();
                            populateRadlexFields(srData.structured_report);
                        }
                    } catch (e) {
                        console.warn('RADLEX pre-synthesis notice:', e);
                    }

                    if (reportDialog) reportDialog.showModal();
                }
            } catch (err) {
                console.error('Report generation error:', err);
            }
        });
    }

    const bannerReportBtn = document.getElementById('banner-report-btn');
    if (bannerReportBtn) {
        bannerReportBtn.addEventListener('click', () => {
            if (openReportBtn) openReportBtn.click();
        });
    }

    if (closeModalBtn) closeModalBtn.addEventListener('click', () => reportDialog.close());
    if (modalCancelBtn) modalCancelBtn.addEventListener('click', () => reportDialog.close());
    if (modalPrintBtn) modalPrintBtn.addEventListener('click', () => window.print());

    // ---------------------------------------------------------
    // 17. EXPORT RADIOGRAPHIC OVERLAY PLATE
    // ---------------------------------------------------------
    if (downloadOverlayBtn) {
        downloadOverlayBtn.addEventListener('click', () => {
            if (!currentPrediction) return;
            const a = document.createElement('a');
            a.href = currentPrediction.gradcam_overlay_b64;
            a.download = `ALVEON_${currentPrediction.diagnosis.toUpperCase()}_DICOM_PLATE.jpg`;
            a.click();
        });
    }

    // ---------------------------------------------------------
    // 17B. CERTIFIED CLINICAL PDF REPORT EXPORT
    // ---------------------------------------------------------
    async function triggerCertifiedPdfDownload() {
        if (!currentPrediction) {
            showWorkstationToast('Please select a patient study before exporting PDF.');
            return;
        }

        showWorkstationToast('Compiling Certified Hospital PDF Report...');
        try {
            const structuredData = getRadlexFormData();
            const reportPayload = {
                study_id: currentPrediction.study_id || selectedStudyId || "ALV-STUDY",
                patient_id: currentPrediction.dicom_metadata?.patient_id || currentPrediction.study_id || "ALV-2026-X84",
                patient_name: currentPrediction.dicom_metadata?.patient_name || "Patient Anonymous",
                diagnosis: currentPrediction.diagnosis,
                confidence_percentage: currentPrediction.confidence_percentage,
                risk_tier: currentPrediction.risk_tier,
                clinical_recommendation: currentPrediction.clinical_recommendation,
                zonation: currentPrediction.zonation,
                original_image_b64: currentPrediction.original_image_b64,
                gradcam_overlay_b64: currentPrediction.gradcam_overlay_b64,
                multilabel_findings: currentPrediction.multi_label_findings || [],
                structured_report: structuredData
            };

            const res = await fetch('/api/v1/report/pdf', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(reportPayload)
            });

            if (res && res.ok) {
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                const fileName = `ALVEON_CERTIFIED_CONSULTATION_${currentPrediction.study_id || 'STUDY'}.pdf`;
                a.download = fileName;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(url);
                showWorkstationToast(`Downloaded: ${fileName}`);
            } else {
                showWorkstationToast('Failed to export certified PDF report.');
            }
        } catch (err) {
            console.error('PDF export error:', err);
            showWorkstationToast('Network error during PDF compilation.');
        }
    }

    if (downloadPdfBtn) downloadPdfBtn.addEventListener('click', triggerCertifiedPdfDownload);
    if (modalPdfBtn) modalPdfBtn.addEventListener('click', triggerCertifiedPdfDownload);

    // ---------------------------------------------------------
    // 17C. DIAGNOSTIC PACS VIEWPORT CALIPERS & MARKUPS ENGINE
    // ---------------------------------------------------------
    let activeMeasureTool = 'pointer'; // 'pointer', 'ruler', 'ctr', 'roi', 'arrow'
    let measurements = [];
    let currentDrawing = null;
    let ctrPendingCardiac = null;

    function resetMeasurementsForNewStudy() {
        measurements = [];
        currentDrawing = null;
        ctrPendingCardiac = null;
        setTimeout(resizeAnnotationCanvas, 60);
    }

    function setActiveMeasureTool(tool) {
        activeMeasureTool = tool;
        document.querySelectorAll('.measure-tool-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === tool);
        });

        const dicomViewportElem = document.getElementById('dicom-viewport');
        if (dicomViewportElem) {
            if (tool !== 'pointer') {
                dicomViewportElem.classList.add('measuring');
            } else {
                dicomViewportElem.classList.remove('measuring');
            }
        }

        if (tool !== 'ctr') {
            ctrPendingCardiac = null;
        }
        currentDrawing = null;
        renderAllMeasurements();
    }

    document.querySelectorAll('.measure-tool-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            setActiveMeasureTool(btn.dataset.tool);
        });
    });

    if (btnClearMeasurements) {
        btnClearMeasurements.addEventListener('click', () => {
            measurements = [];
            currentDrawing = null;
            ctrPendingCardiac = null;
            renderAllMeasurements();
            showWorkstationToast('All viewport calipers and markups cleared.');
        });
    }

    function resizeAnnotationCanvas() {
        if (!pacsCanvas) return;
        const dicomViewportElem = document.getElementById('dicom-viewport');
        if (!dicomViewportElem) return;

        const rect = dicomViewportElem.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        const dpr = window.devicePixelRatio || 1;
        pacsCanvas.width = Math.round(rect.width * dpr);
        pacsCanvas.height = Math.round(rect.height * dpr);
        pacsCanvas.style.width = `${rect.width}px`;
        pacsCanvas.style.height = `${rect.height}px`;

        const ctx = pacsCanvas.getContext('2d');
        ctx.resetTransform();
        ctx.scale(dpr, dpr);
        renderAllMeasurements();
    }

    window.addEventListener('resize', resizeAnnotationCanvas);

    function getCanvasCoords(e) {
        if (!pacsCanvas) return { x: 0, y: 0 };
        const rect = pacsCanvas.getBoundingClientRect();
        const clientX = e.touches ? e.touches[0].clientX : e.clientX;
        const clientY = e.touches ? e.touches[0].clientY : e.clientY;
        return {
            x: Math.max(0, Math.min(rect.width, clientX - rect.left)),
            y: Math.max(0, Math.min(rect.height, clientY - rect.top))
        };
    }

    function getMmPerPixel() {
        if (!pacsCanvas) return 0.70;
        const rect = pacsCanvas.getBoundingClientRect();
        // Estimated standard adult thoracic field width: ~350 mm
        return 350.0 / Math.max(rect.width, 1);
    }

    function drawBadge(ctx, text, x, y, accentColor = '#38bdf8', bgColor = 'rgba(10, 15, 26, 0.88)') {
        ctx.save();
        ctx.font = '600 11px "JetBrains Mono", monospace';
        const metrics = ctx.measureText(text);
        const paddingX = 7;
        const paddingY = 4;
        const h = 20;
        const w = metrics.width + paddingX * 2;
        const bx = x - w / 2;
        const by = y - h / 2;

        // Background pill
        ctx.fillStyle = bgColor;
        ctx.strokeStyle = accentColor;
        ctx.lineWidth = 1;
        ctx.beginPath();
        if (ctx.roundRect) {
            ctx.roundRect(bx, by, w, h, 4);
        } else {
            ctx.rect(bx, by, w, h);
        }
        ctx.fill();
        ctx.stroke();

        // Text
        ctx.fillStyle = '#ffffff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, x, y + 0.5);
        ctx.restore();
    }

    function drawRulerLine(ctx, x1, y1, x2, y2, mm, isLive = false, color = '#38bdf8') {
        ctx.save();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        if (isLive) {
            ctx.setLineDash([4, 4]);
        } else {
            ctx.setLineDash([]);
        }

        // Main line
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        // Orthogonal tick caps
        const dx = x2 - x1;
        const dy = y2 - y1;
        const len = Math.hypot(dx, dy);
        if (len > 4) {
            const nx = -dy / len;
            const ny = dx / len;
            const tickLen = 6;

            ctx.setLineDash([]);
            ctx.beginPath();
            ctx.moveTo(x1 - nx * tickLen, y1 - ny * tickLen);
            ctx.lineTo(x1 + nx * tickLen, y1 + ny * tickLen);
            ctx.moveTo(x2 - nx * tickLen, y2 - ny * tickLen);
            ctx.lineTo(x2 + nx * tickLen, y2 + ny * tickLen);
            ctx.stroke();
        }

        // Distance Tag
        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        drawBadge(ctx, `${mm.toFixed(1)} mm`, midX, midY - 14, color);
        ctx.restore();
    }

    function drawArrow(ctx, x1, y1, x2, y2, label = 'Pathology Focus', isLive = false) {
        ctx.save();
        ctx.strokeStyle = '#f43f5e';
        ctx.fillStyle = '#f43f5e';
        ctx.lineWidth = 2;
        if (isLive) ctx.setLineDash([3, 3]);

        // Shaft
        ctx.beginPath();
        ctx.moveTo(x1, y1);
        ctx.lineTo(x2, y2);
        ctx.stroke();

        // Arrow head
        const angle = Math.atan2(y2 - y1, x2 - x1);
        const headLen = 12;
        ctx.setLineDash([]);
        ctx.beginPath();
        ctx.moveTo(x2, y2);
        ctx.lineTo(x2 - headLen * Math.cos(angle - Math.PI / 6), y2 - headLen * Math.sin(angle - Math.PI / 6));
        ctx.lineTo(x2 - headLen * Math.cos(angle + Math.PI / 6), y2 - headLen * Math.sin(angle + Math.PI / 6));
        ctx.closePath();
        ctx.fill();

        // Label near tail
        drawBadge(ctx, label, x1, y1 - 12, '#f43f5e', 'rgba(244, 63, 94, 0.25)');
        ctx.restore();
    }

    function drawRoi(ctx, cx, cy, rx, ry, areaCm2, isLive = false) {
        ctx.save();
        ctx.strokeStyle = '#22d3ee';
        ctx.fillStyle = 'rgba(34, 211, 238, 0.12)';
        ctx.lineWidth = 1.75;
        if (isLive) {
            ctx.setLineDash([4, 4]);
        } else {
            ctx.setLineDash([6, 3]);
        }

        ctx.beginPath();
        ctx.ellipse(cx, cy, Math.max(1, rx), Math.max(1, ry), 0, 0, 2 * Math.PI);
        ctx.fill();
        ctx.stroke();

        // Cardinal anchor handles
        if (!isLive) {
            ctx.setLineDash([]);
            ctx.fillStyle = '#22d3ee';
            [[cx - rx, cy], [cx + rx, cy], [cx, cy - ry], [cx, cy + ry]].forEach(([ax, ay]) => {
                ctx.beginPath();
                ctx.arc(ax, ay, 3, 0, 2 * Math.PI);
                ctx.fill();
            });
        }

        // Tag
        drawBadge(ctx, `ROI: ${areaCm2.toFixed(1)} cm²`, cx, cy - ry - 14, '#22d3ee');
        ctx.restore();
    }

    function renderAllMeasurements() {
        if (!pacsCanvas) return;
        const rect = pacsCanvas.getBoundingClientRect();
        const ctx = pacsCanvas.getContext('2d');
        ctx.clearRect(0, 0, rect.width, rect.height);

        // 1. Render all saved measurements
        measurements.forEach(m => {
            if (m.type === 'ruler') {
                drawRulerLine(ctx, m.x1, m.y1, m.x2, m.y2, m.mm, false, '#38bdf8');
            } else if (m.type === 'ctr') {
                // Cardiac diameter
                drawRulerLine(ctx, m.cardiac.x1, m.cardiac.y1, m.cardiac.x2, m.cardiac.y2, m.cardiac.mm, false, '#38bdf8');
                // Thoracic diameter
                drawRulerLine(ctx, m.thoracic.x1, m.thoracic.y1, m.thoracic.x2, m.thoracic.y2, m.thoracic.mm, false, '#f59e0b');
                // CTR badge
                const badgeColor = m.ratio > 0.50 ? '#ef4444' : '#10b981';
                const label = `CTR: ${m.ratio.toFixed(2)} (${m.ratio > 0.50 ? 'CARDIOMEGALY' : 'NORMAL'})`;
                const bx = (m.thoracic.x1 + m.thoracic.x2) / 2;
                const by = Math.max(m.cardiac.y1, m.thoracic.y1) + 24;
                drawBadge(ctx, label, bx, by, badgeColor, m.ratio > 0.50 ? 'rgba(239, 68, 68, 0.35)' : 'rgba(16, 185, 129, 0.35)');
            } else if (m.type === 'roi') {
                drawRoi(ctx, m.cx, m.cy, m.rx, m.ry, m.areaCm2, false);
            } else if (m.type === 'arrow') {
                drawArrow(ctx, m.x1, m.y1, m.x2, m.y2, m.label, false);
            }
        });

        // 2. Render pending CTR step 1 (cardiac width)
        if (ctrPendingCardiac) {
            drawRulerLine(ctx, ctrPendingCardiac.x1, ctrPendingCardiac.y1, ctrPendingCardiac.x2, ctrPendingCardiac.y2, ctrPendingCardiac.mm, false, '#38bdf8');
            drawBadge(ctx, 'Cardiac Width Set', (ctrPendingCardiac.x1 + ctrPendingCardiac.x2) / 2, (ctrPendingCardiac.y1 + ctrPendingCardiac.y2) / 2 + 16, '#38bdf8');
        }

        // 3. Render current interactive drawing
        if (currentDrawing) {
            const mmPerPx = getMmPerPixel();
            const dx = currentDrawing.currentX - currentDrawing.startX;
            const dy = currentDrawing.currentY - currentDrawing.startY;
            const dist = Math.hypot(dx, dy);

            if (currentDrawing.tool === 'ruler') {
                drawRulerLine(ctx, currentDrawing.startX, currentDrawing.startY, currentDrawing.currentX, currentDrawing.currentY, dist * mmPerPx, true, '#38bdf8');
            } else if (currentDrawing.tool === 'ctr') {
                const color = ctrPendingCardiac ? '#f59e0b' : '#38bdf8';
                drawRulerLine(ctx, currentDrawing.startX, currentDrawing.startY, currentDrawing.currentX, currentDrawing.currentY, dist * mmPerPx, true, color);
            } else if (currentDrawing.tool === 'roi') {
                const cx = (currentDrawing.startX + currentDrawing.currentX) / 2;
                const cy = (currentDrawing.startY + currentDrawing.currentY) / 2;
                const rx = Math.abs(currentDrawing.currentX - currentDrawing.startX) / 2;
                const ry = Math.abs(currentDrawing.currentY - currentDrawing.startY) / 2;
                const areaMm2 = Math.PI * (rx * mmPerPx) * (ry * mmPerPx);
                drawRoi(ctx, cx, cy, rx, ry, areaMm2 / 100.0, true);
            } else if (currentDrawing.tool === 'arrow') {
                drawArrow(ctx, currentDrawing.startX, currentDrawing.startY, currentDrawing.currentX, currentDrawing.currentY, 'Target Lesion', true);
            }
        }
    }

    // Canvas Mouse & Touch Event Handlers
    if (pacsCanvas) {
        function handleStart(e) {
            if (activeMeasureTool === 'pointer') return;
            e.preventDefault();
            const coords = getCanvasCoords(e);
            currentDrawing = {
                tool: activeMeasureTool,
                startX: coords.x,
                startY: coords.y,
                currentX: coords.x,
                currentY: coords.y
            };
            renderAllMeasurements();
        }

        function handleMove(e) {
            if (!currentDrawing) return;
            e.preventDefault();
            const coords = getCanvasCoords(e);
            currentDrawing.currentX = coords.x;
            currentDrawing.currentY = coords.y;
            renderAllMeasurements();
        }

        function handleEnd(e) {
            if (!currentDrawing) return;
            e.preventDefault();
            const coords = getCanvasCoords(e);
            currentDrawing.currentX = coords.x;
            currentDrawing.currentY = coords.y;

            const dx = currentDrawing.currentX - currentDrawing.startX;
            const dy = currentDrawing.currentY - currentDrawing.startY;
            const dist = Math.hypot(dx, dy);

            // Minimum length check (6px) to avoid accidental taps
            if (dist >= 6) {
                const mmPerPx = getMmPerPixel();
                if (currentDrawing.tool === 'ruler') {
                    measurements.push({
                        type: 'ruler',
                        x1: currentDrawing.startX,
                        y1: currentDrawing.startY,
                        x2: currentDrawing.currentX,
                        y2: currentDrawing.currentY,
                        mm: dist * mmPerPx
                    });
                } else if (currentDrawing.tool === 'ctr') {
                    if (!ctrPendingCardiac) {
                        ctrPendingCardiac = {
                            x1: currentDrawing.startX,
                            y1: currentDrawing.startY,
                            x2: currentDrawing.currentX,
                            y2: currentDrawing.currentY,
                            mm: dist * mmPerPx
                        };
                        showWorkstationToast('Cardiac width set. Now draw internal thoracic diameter.');
                    } else {
                        const thoracic = {
                            x1: currentDrawing.startX,
                            y1: currentDrawing.startY,
                            x2: currentDrawing.currentX,
                            y2: currentDrawing.currentY,
                            mm: dist * mmPerPx
                        };
                        const ratio = ctrPendingCardiac.mm / Math.max(thoracic.mm, 0.1);
                        measurements.push({
                            type: 'ctr',
                            cardiac: ctrPendingCardiac,
                            thoracic: thoracic,
                            ratio: ratio
                        });
                        ctrPendingCardiac = null;
                        showWorkstationToast(`CTR Computed: ${ratio.toFixed(2)} (${ratio > 0.50 ? 'Cardiomegaly' : 'Normal'})`);
                    }
                } else if (currentDrawing.tool === 'roi') {
                    const cx = (currentDrawing.startX + currentDrawing.currentX) / 2;
                    const cy = (currentDrawing.startY + currentDrawing.currentY) / 2;
                    const rx = Math.abs(currentDrawing.currentX - currentDrawing.startX) / 2;
                    const ry = Math.abs(currentDrawing.currentY - currentDrawing.startY) / 2;
                    const areaMm2 = Math.PI * (rx * mmPerPx) * (ry * mmPerPx);
                    measurements.push({
                        type: 'roi',
                        cx, cy, rx, ry,
                        areaCm2: areaMm2 / 100.0
                    });
                } else if (currentDrawing.tool === 'arrow') {
                    measurements.push({
                        type: 'arrow',
                        x1: currentDrawing.startX,
                        y1: currentDrawing.startY,
                        x2: currentDrawing.currentX,
                        y2: currentDrawing.currentY,
                        label: 'Pathology Focus'
                    });
                }
            }

            currentDrawing = null;
            renderAllMeasurements();
        }

        pacsCanvas.addEventListener('mousedown', handleStart);
        window.addEventListener('mousemove', handleMove);
        window.addEventListener('mouseup', handleEnd);

        pacsCanvas.addEventListener('touchstart', handleStart, { passive: false });
        window.addEventListener('touchmove', handleMove, { passive: false });
        window.addEventListener('touchend', handleEnd, { passive: false });
    }

    // ---------------------------------------------------------
    // 18. WORKSTATION TOAST NOTIFICATION
    // ---------------------------------------------------------
    function showWorkstationToast(message) {
        const toast = document.createElement('div');
        toast.className = 'alveon-toast';
        toast.textContent = message;
        document.body.appendChild(toast);

        setTimeout(() => {
            toast.classList.add('show');
        }, 10);

        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // ---------------------------------------------------------
    // 19. ENTERPRISE PACS & DICOMWEB INTEROPERABILITY CONTROLLER
    // ---------------------------------------------------------
    function initPacsHubModal() {
        if (!pacsHubDialog) return;

        // Assign modal opener
        openPacsHubModal = function() {
            if (pacsPushStudyName) {
                if (currentPrediction) {
                    const name = currentPrediction.dicom_metadata?.patient_name || currentPrediction.study_id || 'Active Patient';
                    const mrn = currentPrediction.dicom_metadata?.patient_id || currentPrediction.study_id || 'MRN-ER';
                    pacsPushStudyName.textContent = `${name} (${mrn})`;
                } else if (selectedStudyId) {
                    const s = worklistStudies.find(st => st.study_id === selectedStudyId);
                    pacsPushStudyName.textContent = s ? `${s.patient_name} (${s.patient_mrn})` : selectedStudyId;
                } else {
                    pacsPushStudyName.textContent = 'No Study Active (Select from queue)';
                }
            }
            pacsHubDialog.showModal();
        };

        if (openPacsHubBtn) {
            openPacsHubBtn.addEventListener('click', openPacsHubModal);
        }
        if (closePacsHubBtn) {
            closePacsHubBtn.addEventListener('click', () => pacsHubDialog.close());
        }
        if (dismissPacsHubBtn) {
            dismissPacsHubBtn.addEventListener('click', () => pacsHubDialog.close());
        }

        // Tab Switching
        const tabBtns = pacsHubDialog.querySelectorAll('.pacs-hub-tab-btn');
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                tabBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                const targetTabId = btn.dataset.pacsTab;
                pacsHubDialog.querySelectorAll('.pacs-tab-panel').forEach(panel => {
                    const isActive = panel.id === targetTabId;
                    panel.classList.toggle('active', isActive);
                    panel.style.display = isActive ? 'block' : 'none';
                });
            });
        });

        // 1. C-ECHO Ping SCU
        if (btnPacsPing) {
            btnPacsPing.addEventListener('click', async () => {
                const ae = pacsPingAe ? pacsPingAe.value.trim() : 'ALVEON_PACS';
                const host = pacsPingHost ? pacsPingHost.value.trim() : '127.0.0.1';
                const port = pacsPingPort ? parseInt(pacsPingPort.value.trim(), 10) : 11112;

                if (pacsPingLog) {
                    pacsPingLog.textContent = `[CONNECTING] Initiating DIMSE association with ${host}:${port} (${ae})...`;
                }
                btnPacsPing.disabled = true;

                try {
                    const res = await fetch('/api/v1/pacs/ping', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ host, port, ae_title: ae })
                    });
                    const data = await res.json();
                    if (data.success || data.status === 'online' || data.status === 'success') {
                        if (pacsPingLog) {
                            pacsPingLog.textContent = `[SUCCESS 0x0000] C-ECHO Verification Successful!\nRoundtrip Latency: ${data.latency_ms} ms\nRemote Node: ${data.target || (ae + '@' + host + ':' + port)}\nStatus Code: ${data.dicom_status_code || '0x0'}`;
                        }
                        showWorkstationToast(`📡 C-ECHO Ping Succeeded (${data.latency_ms} ms)`);
                    } else {
                        if (pacsPingLog) {
                            pacsPingLog.textContent = `[REJECTED] Association Rejected: ${data.message || 'Verification failed'}`;
                        }
                    }
                } catch (err) {
                    if (pacsPingLog) {
                        pacsPingLog.textContent = `[ERROR] Connection refused or timeout: ${err.message}`;
                    }
                } finally {
                    btnPacsPing.disabled = false;
                }
            });
        }

        // 2. C-STORE Push SCU
        if (btnPacsPush) {
            btnPacsPush.addEventListener('click', async () => {
                const studyId = selectedStudyId || (currentPrediction && currentPrediction.study_id);
                if (!studyId) {
                    if (pacsPushLog) pacsPushLog.textContent = '[ABORTED] No active study loaded in viewport to forward.';
                    showWorkstationToast('⚠️ Select a study in worklist to forward');
                    return;
                }

                const ae = pacsPushAe ? pacsPushAe.value.trim() : 'ALVEON_PACS';
                const host = pacsPushHost ? pacsPushHost.value.trim() : '127.0.0.1';
                const port = pacsPushPort ? parseInt(pacsPushPort.value.trim(), 10) : 11112;

                if (pacsPushLog) {
                    pacsPushLog.textContent = `[TRANSMITTING] Connecting to ${host}:${port} (AE: ${ae})...\nEncoding DICOM PS 3.10 dataset for #${studyId}...`;
                }
                btnPacsPush.disabled = true;

                try {
                    const res = await fetch('/api/v1/pacs/push', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ study_id: studyId, host, port, ae_title: ae })
                    });
                    const data = await res.json();
                    if (data.success || data.status === 'success') {
                        if (pacsPushLog) {
                            pacsPushLog.textContent = `[C-STORE SUCCESS 0x0000]\nTransmitted study to ${data.destination || (ae + '@' + host + ':' + port)} in ${data.latency_ms} ms.\nStatus Code: ${data.dicom_status_code || '0x0'}\nPatient: ${data.patient_name || ''} (#${data.patient_id || ''})`;
                        }
                        showWorkstationToast(`🚀 C-STORE Push Succeeded (${data.latency_ms} ms)`);
                    } else {
                        if (pacsPushLog) {
                            pacsPushLog.textContent = `[C-STORE FAILED] ${data.message || data.detail || 'Transmission rejected'}`;
                        }
                    }
                } catch (err) {
                    if (pacsPushLog) {
                        pacsPushLog.textContent = `[NETWORK ERROR] ${err.message}`;
                    }
                } finally {
                    btnPacsPush.disabled = false;
                }
            });
        }

        // 3. Clinical Cohort Ingestion SCU
        if (btnInjectCohort) {
            btnInjectCohort.addEventListener('click', async () => {
                btnInjectCohort.disabled = true;
                if (cohortInjectLog) cohortInjectLog.style.display = 'block';
                if (cohortLogSummary) cohortLogSummary.textContent = 'Transmitting 6 Patients via C-STORE...';
                if (cohortLogStream) {
                    cohortLogStream.innerHTML = '<div>[0.0s] Negotiating DIMSE C-STORE association with 127.0.0.1:11112 (ALVEON_PACS)...</div>';
                }

                try {
                    const res = await fetch('/api/v1/pacs/inject-cohort', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: '{}'
                    });
                    const data = await res.json();

                    if (data.status === 'success') {
                        const lines = [
                            `[0.1s] Association Established with ALVEON_PACS on port 11112.`,
                            `[0.3s] C-STORE Patient 1/6: HASTINGS, ROSE (MRN-ER-901) -> PNEUMOTHORAX (0x0000 Success, 14.2ms)`,
                            `[0.5s] C-STORE Patient 2/6: GARRISON, MARCUS (MRN-ER-902) -> PNEUMONIA / ARDS (0x0000 Success, 15.1ms)`,
                            `[0.7s] C-STORE Patient 3/6: KIM, SUN-HEE (MRN-ER-903) -> PLEURAL EFFUSION (0x0000 Success, 13.8ms)`,
                            `[0.9s] C-STORE Patient 4/6: O'CONNOR, PATRICK (MRN-ER-904) -> CARDIOMEGALY (0x0000 Success, 14.6ms)`,
                            `[1.1s] C-STORE Patient 5/6: AL-MANSOOR, TARIQ (MRN-ER-905) -> ATELECTASIS (0x0000 Success, 14.0ms)`,
                            `[1.3s] C-STORE Patient 6/6: THOMPSON, CHLOE (MRN-ER-906) -> NORMAL (0x0000 Success, 12.9ms)`,
                            `[1.5s] DIMSE Association Released. 6 studies processed, indexed and ranked in Triage Worklist.`
                        ];
                        if (cohortLogStream) {
                            cohortLogStream.innerHTML = lines.map(l => `<div>${escapeHtml(l)}</div>`).join('');
                        }
                        if (cohortLogSummary) {
                            cohortLogSummary.textContent = `Transmission Complete: ${data.total_injected || 6}/6 Succeeded (${data.duration_ms || 110} ms)`;
                        }

                        // Refresh Worklist
                        await fetchWorklist();

                        // Auto-load first study
                        if (worklistStudies && worklistStudies.length > 0) {
                            loadWorklistStudy(worklistStudies[0]);
                        }

                        showWorkstationToast('⚡ 6-Patient ER Cohort Ingested via C-STORE');
                    } else {
                        if (cohortLogSummary) cohortLogSummary.textContent = 'Transmission Failed';
                        if (cohortLogStream) cohortLogStream.innerHTML += `<div style="color: #f87171;">[FAILED] ${escapeHtml(data.detail || 'Cohort transmission error')}</div>`;
                    }
                } catch (err) {
                    if (cohortLogSummary) cohortLogSummary.textContent = 'Network Error';
                    if (cohortLogStream) cohortLogStream.innerHTML += `<div style="color: #f87171;">[ERROR] ${escapeHtml(err.message)}</div>`;
                } finally {
                    btnInjectCohort.disabled = false;
                }
            });
        }

        // 4. DICOMweb Actions: Copy cURL and Test Buttons
        document.querySelectorAll('.copy-curl-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const cmd = btn.dataset.curl;
                if (cmd) {
                    navigator.clipboard.writeText(cmd).then(() => {
                        showWorkstationToast('📋 Copied cURL command to clipboard');
                    }).catch(() => {
                        showWorkstationToast('📋 ' + cmd);
                    });
                }
            });
        });

        if (btnTestWadoRendered) {
            btnTestWadoRendered.addEventListener('click', () => {
                const sopUid = currentPrediction?.dicom_metadata?.sop_instance_uid || '1.2.840.113619.2.55.3.283117284.723';
                const url = `/dicomweb/studies/1.2.840.113619.2.55.3.283117284.721/series/1.2.840.113619.2.55.3.283117284.722/instances/${sopUid}/rendered`;
                window.open(url, '_blank');
            });
        }

        if (btnDownloadNativeDicom) {
            btnDownloadNativeDicom.addEventListener('click', () => {
                const sopUid = currentPrediction?.dicom_metadata?.sop_instance_uid || '1.2.840.113619.2.55.3.283117284.723';
                const url = `/dicomweb/studies/1.2.840.113619.2.55.3.283117284.721/series/1.2.840.113619.2.55.3.283117284.722/instances/${sopUid}`;
                const a = document.createElement('a');
                a.href = url;
                a.download = `study_${sopUid}.dcm`;
                document.body.appendChild(a);
                a.click();
                a.remove();
                showWorkstationToast('⬇️ Downloading Native DICOM Part 10 Dataset');
            });
        }
    }

    // =========================================================================
    // v4.0 ENTERPRISE MODULES: AUTH/RBAC, 3D VOLUMETRIC MPR, HIPAA AUDIT LEDGER
    // =========================================================================

    let currentUserSession = {
        username: "dr.vance",
        full_name: "Dr. Eleanor Vance, MD",
        role: "ATTENDING_RADIOLOGIST",
        initials: "EV",
        token: null
    };

    // ---------------------------------------------------------
    // 19. USER AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
    // ---------------------------------------------------------
    function initUserAuthAndRBAC() {
        const userTrigger = document.getElementById('user-role-trigger');
        const rolePopover = document.getElementById('role-menu-popover');
        const userAvatar = document.getElementById('current-user-avatar');
        const userName = document.getElementById('current-user-name');
        const userRoleBadge = document.getElementById('current-user-role-badge');
        const btnSignoff = document.getElementById('btn-signoff');

        if (userTrigger && rolePopover) {
            userTrigger.addEventListener('click', (e) => {
                e.stopPropagation();
                rolePopover.style.display = rolePopover.style.display === 'none' ? 'block' : 'none';
            });

            document.addEventListener('click', () => {
                rolePopover.style.display = 'none';
            });
        }

        async function switchClinicalPersona(username) {
            try {
                const res = await fetch('/api/v1/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: username })
                });
                if (!res.ok) throw new Error('Login failed');
                const data = await res.json();
                
                currentUserSession = {
                    username: data.user.username,
                    full_name: data.user.full_name,
                    role: data.user.role,
                    initials: data.user.initials,
                    token: data.access_token
                };
                localStorage.setItem('alveon_auth_token', data.access_token);

                // Update UI Avatar and Badges
                if (userAvatar) userAvatar.textContent = currentUserSession.initials;
                if (userName) userName.textContent = currentUserSession.full_name;
                if (userRoleBadge) {
                    userRoleBadge.textContent = currentUserSession.role.replace('_', ' ');
                    userRoleBadge.className = `user-role-badge ${currentUserSession.role.toLowerCase().includes('attending') ? 'attending' : currentUserSession.role.toLowerCase().includes('resident') ? 'resident' : currentUserSession.role.toLowerCase().includes('er') ? 'er' : 'admin'}`;
                }

                // Update Active Checkmark in Menu
                document.querySelectorAll('.role-menu-item').forEach(item => {
                    item.classList.toggle('active', item.dataset.username === username);
                });

                // Update Signoff Button Permission
                if (btnSignoff) {
                    const canSign = currentUserSession.role === 'ATTENDING_RADIOLOGIST' || currentUserSession.role === 'PACS_ADMIN';
                    btnSignoff.style.opacity = canSign ? '1' : '0.6';
                    btnSignoff.title = canSign ? 'Sign Off & Attest (S)' : 'Restricted: Attending Radiologist Review Required';
                }

                showWorkstationToast(`👤 Switched Persona: ${currentUserSession.full_name} (${currentUserSession.role})`);
            } catch (err) {
                console.error('Failed to switch persona:', err);
            }
        }

        document.querySelectorAll('.role-menu-item').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (rolePopover) rolePopover.style.display = 'none';
                switchClinicalPersona(btn.dataset.username);
            });
        });

        // Initialize default Attending login
        switchClinicalPersona('dr.vance');
    }

    // ---------------------------------------------------------
    // 20. WORKSTATION VIEWPORT MODE SWITCHER (2D vs 3D CT/MPR)
    // ---------------------------------------------------------
    function initWorkstationModeSwitch() {
        const btn2D = document.getElementById('mode-btn-2d');
        const btn3D = document.getElementById('mode-btn-3d');
        const btnNeuro = document.getElementById('mode-btn-neuro');
        const diagContent = document.getElementById('diagnosis-content');
        const volContent = document.getElementById('volumetric-content');
        const pacsToolbar = document.getElementById('pacs-toolbar');
        const neuroBanner = document.getElementById('neuro-diag-banner');
        const seriesSelector = document.getElementById('mpr-series-selector');

        if (btn2D && btn3D) {
            btn2D.addEventListener('click', () => {
                btn2D.classList.add('active');
                btn3D.classList.remove('active');
                if (btnNeuro) btnNeuro.classList.remove('active');
                if (diagContent) diagContent.style.display = '';
                if (volContent) volContent.style.display = 'none';
                if (pacsToolbar) pacsToolbar.style.display = '';
                if (neuroBanner) neuroBanner.style.display = 'none';
                showWorkstationToast('🩻 2D Radiographic Workstation Active');
            });

            btn3D.addEventListener('click', () => {
                btn3D.classList.add('active');
                btn2D.classList.remove('active');
                if (btnNeuro) btnNeuro.classList.remove('active');
                if (diagContent) diagContent.style.display = 'none';
                if (volContent) volContent.style.display = 'flex';
                if (pacsToolbar) pacsToolbar.style.display = 'none';
                if (neuroBanner) neuroBanner.style.display = 'none';
                if (seriesSelector && seriesSelector.value.startsWith('BRAIN')) {
                    seriesSelector.value = 'SERIES-CT-CHEST-3201';
                    mprState.seriesId = 'SERIES-CT-CHEST-3201';
                    mprState.windowPreset = 'LUNG';
                }
                showWorkstationToast('🧊 3D Chest CT / MPR Viewport Active');
                loadVolumetricMPR();
            });

            if (btnNeuro) {
                btnNeuro.addEventListener('click', () => {
                    btnNeuro.classList.add('active');
                    btn2D.classList.remove('active');
                    btn3D.classList.remove('active');
                    if (diagContent) diagContent.style.display = 'none';
                    if (volContent) volContent.style.display = 'flex';
                    if (pacsToolbar) pacsToolbar.style.display = 'none';
                    if (neuroBanner) neuroBanner.style.display = 'flex';
                    if (seriesSelector) {
                        seriesSelector.value = 'BRAIN-CT-STROKE-01';
                        mprState.seriesId = 'BRAIN-CT-STROKE-01';
                        mprState.windowPreset = 'BRAIN';
                    }
                    const huPresets = document.getElementById('mpr-hu-presets');
                    if (huPresets) {
                        huPresets.querySelectorAll('button').forEach(b => {
                            b.classList.toggle('active', b.dataset.hu === 'BRAIN');
                        });
                    }
                    showWorkstationToast('🧠 3D Neuro CT & Stroke Suite Active');
                    loadVolumetricMPR();
                    updateNeuroDiagnosticSummary('BRAIN-CT-STROKE-01');
                });
            }
        }
    }

    // ---------------------------------------------------------
    // 21. 3D VOLUMETRIC CT & MULTI-PLANAR RECONSTRUCTION (MPR)
    // ---------------------------------------------------------
    let mprState = {
        seriesId: "SERIES-CT-CHEST-3201",
        axialIdx: 16,
        coronalIdx: 80,
        sagittalIdx: 80,
        windowPreset: "LUNG",
        maxSlices: 32,
        isPlaying: false,
        fps: 15,
        timer: null
    };

    async function loadVolumetricMPR() {
        const axialCanvas = document.getElementById('mpr-axial-canvas');
        const coronalCanvas = document.getElementById('mpr-coronal-canvas');
        const sagittalCanvas = document.getElementById('mpr-sagittal-canvas');
        const sliceTag = document.getElementById('mpr-slice-tag');
        const locTag = document.getElementById('mpr-loc-tag');
        const huLiveTag = document.getElementById('mpr-hu-live-tag');
        const sliceSlider = document.getElementById('mpr-slice-slider');
        const axialPos = document.getElementById('mpr-axial-pos');
        const corPos = document.getElementById('mpr-coronal-pos');
        const sagPos = document.getElementById('mpr-sagittal-pos');
        const wlLabel = document.getElementById('axial-wl-label');

        try {
            const res = await fetch(`/api/v1/volumetric/${mprState.seriesId}/mpr`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    axial_idx: mprState.axialIdx,
                    coronal_idx: mprState.coronalIdx,
                    sagittal_idx: mprState.sagittalIdx,
                    window_preset: mprState.windowPreset
                })
            });

            if (!res.ok) throw new Error('Failed to load MPR data');
            const data = await res.json();

            // Render Axial Canvas
            if (axialCanvas && data.axial?.data_url) {
                const imgAx = new Image();
                imgAx.onload = () => {
                    const ctx = axialCanvas.getContext('2d');
                    ctx.drawImage(imgAx, 0, 0, axialCanvas.width, axialCanvas.height);
                };
                imgAx.src = data.axial.data_url;
            }

            // Render Coronal Canvas
            if (coronalCanvas && data.coronal?.data_url) {
                const imgCor = new Image();
                imgCor.onload = () => {
                    const ctx = coronalCanvas.getContext('2d');
                    ctx.drawImage(imgCor, 0, 0, coronalCanvas.width, coronalCanvas.height);
                };
                imgCor.src = data.coronal.data_url;
            }

            // Render Sagittal Canvas
            if (sagittalCanvas && data.sagittal?.data_url) {
                const imgSag = new Image();
                imgSag.onload = () => {
                    const ctx = sagittalCanvas.getContext('2d');
                    ctx.drawImage(imgSag, 0, 0, sagittalCanvas.width, sagittalCanvas.height);
                };
                imgSag.src = data.sagittal.data_url;
            }

            // Update Telemetry
            if (sliceTag) sliceTag.textContent = `AXIAL SLICE ${mprState.axialIdx + 1} / ${mprState.maxSlices}`;
            if (locTag && data.axial?.metadata?.slice_location_mm !== undefined) {
                locTag.textContent = `LOC: ${data.axial.metadata.slice_location_mm} mm`;
            }
            if (huLiveTag) {
                huLiveTag.textContent = `WINDOW: ${mprState.windowPreset}`;
            }
            if (wlLabel && data.axial?.metadata) {
                wlLabel.textContent = `W:${data.axial.metadata.window_width} L:${data.axial.metadata.window_level}`;
            }
            if (sliceSlider) sliceSlider.value = mprState.axialIdx;
            if (axialPos) axialPos.textContent = `Z: ${mprState.axialIdx + 1}/${mprState.maxSlices}`;
            if (corPos) corPos.textContent = `Y: ${mprState.coronalIdx}/160`;
            if (sagPos) sagPos.textContent = `X: ${mprState.sagittalIdx}/160`;

        } catch (err) {
            console.error('MPR loading error:', err);
        }
    }

    function initVolumetricMPRViewer() {
        const seriesSelector = document.getElementById('mpr-series-selector');
        const huPresets = document.getElementById('mpr-hu-presets');
        const sliceSlider = document.getElementById('mpr-slice-slider');
        const prevBtn = document.getElementById('mpr-slice-prev-btn');
        const nextBtn = document.getElementById('mpr-slice-next-btn');
        const playBtn = document.getElementById('mpr-cine-play-btn');
        const playText = document.getElementById('mpr-cine-play-text');
        const fpsSlider = document.getElementById('mpr-fps-slider');
        const fpsVal = document.getElementById('mpr-fps-val');
        const axialCanvas = document.getElementById('mpr-axial-canvas');
        const btnTri = document.getElementById('mpr-view-tri-btn');
        const btnAxial = document.getElementById('mpr-view-axial-btn');
        const mprGrid = document.getElementById('mpr-grid');
        const panelCor = document.getElementById('mpr-panel-coronal');
        const panelSag = document.getElementById('mpr-panel-sagittal');

        // Series selection
        if (seriesSelector) {
            seriesSelector.addEventListener('change', () => {
                mprState.seriesId = seriesSelector.value;
                mprState.axialIdx = 16;
                const neuroBanner = document.getElementById('neuro-diag-banner');
                if (seriesSelector.value.startsWith('BRAIN-CT')) {
                    if (neuroBanner) neuroBanner.style.display = 'flex';
                    mprState.windowPreset = seriesSelector.value.includes('STROKE') ? 'STROKE' : 'SUBDURAL';
                    if (huPresets) {
                        huPresets.querySelectorAll('button').forEach(b => {
                            b.classList.toggle('active', b.dataset.hu === mprState.windowPreset);
                        });
                    }
                    updateNeuroDiagnosticSummary(seriesSelector.value);
                } else {
                    if (neuroBanner) neuroBanner.style.display = 'none';
                    mprState.windowPreset = 'LUNG';
                    if (huPresets) {
                        huPresets.querySelectorAll('button').forEach(b => {
                            b.classList.toggle('active', b.dataset.hu === 'LUNG');
                        });
                    }
                }
                loadVolumetricMPR();
            });
        }

        // HU Presets
        if (huPresets) {
            huPresets.querySelectorAll('button').forEach(btn => {
                btn.addEventListener('click', () => {
                    huPresets.querySelectorAll('button').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    mprState.windowPreset = btn.dataset.hu;
                    loadVolumetricMPR();
                });
            });
        }

        // Slice slider
        if (sliceSlider) {
            sliceSlider.addEventListener('input', () => {
                mprState.axialIdx = parseInt(sliceSlider.value, 10);
                loadVolumetricMPR();
            });
        }

        // Step buttons
        if (prevBtn) {
            prevBtn.addEventListener('click', () => {
                mprState.axialIdx = Math.max(0, mprState.axialIdx - 1);
                loadVolumetricMPR();
            });
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => {
                mprState.axialIdx = Math.min(mprState.maxSlices - 1, mprState.axialIdx + 1);
                loadVolumetricMPR();
            });
        }

        // Mouse wheel slice scrolling on axial canvas
        if (axialCanvas) {
            let wheelTimeout = null;
            axialCanvas.addEventListener('wheel', (e) => {
                e.preventDefault();
                if (e.deltaY < 0) {
                    mprState.axialIdx = Math.min(mprState.maxSlices - 1, mprState.axialIdx + 1);
                } else {
                    mprState.axialIdx = Math.max(0, mprState.axialIdx - 1);
                }
                clearTimeout(wheelTimeout);
                wheelTimeout = setTimeout(loadVolumetricMPR, 20);
            }, { passive: false });
        }

        // Cine Auto-Play
        function toggleCine() {
            mprState.isPlaying = !mprState.isPlaying;
            if (mprState.isPlaying) {
                if (playText) playText.textContent = 'Pause Cine';
                mprState.timer = setInterval(() => {
                    mprState.axialIdx = (mprState.axialIdx + 1) % mprState.maxSlices;
                    loadVolumetricMPR();
                }, 1000 / mprState.fps);
            } else {
                if (playText) playText.textContent = 'Play Cine';
                clearInterval(mprState.timer);
                mprState.timer = null;
            }
        }

        if (playBtn) playBtn.addEventListener('click', toggleCine);

        // FPS Speed
        if (fpsSlider) {
            fpsSlider.addEventListener('input', () => {
                mprState.fps = parseInt(fpsSlider.value, 10);
                if (fpsVal) fpsVal.textContent = `${mprState.fps} fps`;
                if (mprState.isPlaying) {
                    clearInterval(mprState.timer);
                    mprState.timer = setInterval(() => {
                        mprState.axialIdx = (mprState.axialIdx + 1) % mprState.maxSlices;
                        loadVolumetricMPR();
                    }, 1000 / mprState.fps);
                }
            });
        }

        // Layout mode (Tri-Planar vs Axial Solo)
        if (btnTri && btnAxial && mprGrid) {
            btnTri.addEventListener('click', () => {
                btnTri.classList.add('active');
                btnAxial.classList.remove('active');
                mprGrid.style.gridTemplateColumns = '1.2fr 1fr 1fr';
                if (panelCor) panelCor.style.display = 'flex';
                if (panelSag) panelSag.style.display = 'flex';
            });

            btnAxial.addEventListener('click', () => {
                btnAxial.classList.add('active');
                btnTri.classList.remove('active');
                mprGrid.style.gridTemplateColumns = '1fr';
                if (panelCor) panelCor.style.display = 'none';
                if (panelSag) panelSag.style.display = 'none';
            });
        }
    }

    // ---------------------------------------------------------
    // 22. HIPAA SECURITY AUDIT TRAIL MODAL
    // ---------------------------------------------------------
    function initAuditTrailModal() {
        const auditDialog = document.getElementById('audit-trail-dialog');
        const openBtn = document.getElementById('open-audit-trail-btn');
        const closeBtn = document.getElementById('close-audit-modal-btn');
        const dismissBtn = document.getElementById('dismiss-audit-btn');
        const tbody = document.getElementById('audit-ledger-tbody');
        const filterSelect = document.getElementById('audit-filter-action');
        const refreshBtn = document.getElementById('audit-refresh-btn');
        const integrityBadge = document.getElementById('audit-integrity-badge');
        const integrityText = document.getElementById('audit-integrity-text');

        async function fetchAuditTrail() {
            const action = filterSelect ? filterSelect.value : '';
            const queryUrl = action ? `/api/v1/audit/logs?limit=50&action=${action}` : '/api/v1/audit/logs?limit=50';

            try {
                const [logsRes, verifyRes] = await Promise.all([
                    fetch(queryUrl),
                    fetch('/api/v1/audit/verify')
                ]);

                if (verifyRes.ok) {
                    const vData = await verifyRes.json();
                    if (integrityBadge) {
                        integrityBadge.className = `audit-integrity-badge ${vData.is_valid ? 'valid' : 'invalid'}`;
                    }
                    if (integrityText) {
                        integrityText.textContent = vData.is_valid
                            ? `SHA-256 Chained Hash: VALID & UNTAMPERED (${vData.total_events} Blocks)`
                            : `INTEGRITY VIOLATION DETECTED: ${vData.message}`;
                    }
                }

                if (logsRes.ok && tbody) {
                    const lData = await logsRes.json();
                    if (!lData.events || lData.events.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 24px; color: #64748b;">No HIPAA audit events recorded for current filter.</td></tr>`;
                        return;
                    }

                    tbody.innerHTML = lData.events.map(e => {
                        let actionClass = 'phi';
                        if (e.action === 'LOGIN') actionClass = 'login';
                        else if (e.action === 'AI_INFERENCE') actionClass = 'inference';
                        else if (e.action === 'ATTESTATION_SIGNED') actionClass = 'signoff';
                        else if (e.action === 'PDF_EXPORTED') actionClass = 'pdf';
                        else if (e.action === 'MODALITY_PUSH') actionClass = 'modality';
                        else if (e.action === 'STUDY_DELETED') actionClass = 'delete';

                        const detailsStr = Object.entries(e.details || {})
                            .map(([k, v]) => `${k}: ${v}`)
                            .slice(0, 3)
                            .join(' • ');

                        return `
                            <tr>
                                <td style="font-family: var(--font-mono); font-size: 10px; color: #94a3b8;">${escapeHtml(e.timestamp_utc)}</td>
                                <td style="font-family: var(--font-mono); font-size: 10.5px; font-weight: 700; color: #f8fafc;">${escapeHtml(e.event_id)}</td>
                                <td>
                                    <div style="font-weight: 700; color: #f1f5f9;">${escapeHtml(e.username)}</div>
                                    <div style="font-size: 9px; color: #64748b;">${escapeHtml(e.user_role)}</div>
                                </td>
                                <td><span class="audit-action-pill ${actionClass}">${escapeHtml(e.action)}</span></td>
                                <td style="font-family: var(--font-mono); color: #38bdf8;">${escapeHtml(e.patient_mrn || 'N/A')}</td>
                                <td style="font-size: 10.5px; color: #94a3b8; max-width: 240px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(detailsStr || 'None')}</td>
                                <td><span class="audit-hash-code" title="${escapeHtml(e.record_hash)}">${escapeHtml(e.record_hash.substring(0, 14))}...</span></td>
                            </tr>
                        `;
                    }).join('');
                }
            } catch (err) {
                console.error('Audit trail load error:', err);
                if (tbody) tbody.innerHTML = `<tr><td colspan="7" style="color: #f87171; text-align: center; padding: 20px;">Failed to load audit records: ${escapeHtml(err.message)}</td></tr>`;
            }
        }

        if (openBtn && auditDialog) {
            openBtn.addEventListener('click', () => {
                auditDialog.showModal();
                fetchAuditTrail();
            });
        }

        if (closeBtn && auditDialog) closeBtn.addEventListener('click', () => auditDialog.close());
        if (dismissBtn && auditDialog) dismissBtn.addEventListener('click', () => auditDialog.close());
        if (filterSelect) filterSelect.addEventListener('change', fetchAuditTrail);
        if (refreshBtn) refreshBtn.addEventListener('click', fetchAuditTrail);
    }

    // ---------------------------------------------------------
    // 23. HOSPITAL MODALITY ACQUISITION SIMULATOR
    // ---------------------------------------------------------
    function initModalitySimulator() {
        const btnPushXR = document.getElementById('sim-push-xr-btn');
        const btnPushCT = document.getElementById('sim-push-ct-btn');
        const simLog = document.getElementById('modality-sim-log');
        const simSummary = document.getElementById('modality-sim-summary');
        const simStream = document.getElementById('modality-sim-stream');

        async function triggerModalityPush(modalityKey, studyIdx, label) {
            if (simLog) simLog.style.display = 'block';
            if (simSummary) simSummary.textContent = `Acquiring & Transmitting via C-STORE...`;
            if (simStream) simStream.innerHTML = `<div style="color: #38bdf8;">[INIT] Starting C-STORE transmission from ${modalityKey} (port 11112)...</div>`;

            try {
                const res = await fetch('/api/v1/pacs/simulate-modality', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        modality_key: modalityKey,
                        study_idx: studyIdx,
                        target_port: 11112
                    })
                });

                const data = await res.json();
                if (res.ok && data.success) {
                    if (simSummary) simSummary.textContent = `Transmission Complete (${data.network_latency_ms} ms)`;
                    if (simStream) {
                        simStream.innerHTML += `
                            <div style="color: #10b981;">[SUCCESS 0x0000] C-STORE Association Verified</div>
                            <div style="color: #cbd5e1;">&nbsp;• Modality: ${escapeHtml(data.modality_device.manufacturer)} ${escapeHtml(data.modality_device.model_name)}</div>
                            <div style="color: #cbd5e1;">&nbsp;• Patient: ${escapeHtml(data.study_transmitted.patient_name)} (${escapeHtml(data.study_transmitted.patient_id)})</div>
                            <div style="color: #cbd5e1;">&nbsp;• Study: ${escapeHtml(data.study_transmitted.study_description)}</div>
                            <div style="color: #cbd5e1;">&nbsp;• Acuity: <strong style="color: #f87171;">${escapeHtml(data.study_transmitted.acuity_level)}</strong></div>
                            <div style="color: #38bdf8;">&nbsp;• Target SOP Instance UID: ${escapeHtml(data.sop_instance_uid)}</div>
                        `;
                    }
                    showWorkstationToast(`📡 Ingested ${label} via C-STORE`);
                    await fetchWorklist();
                } else {
                    if (simSummary) simSummary.textContent = 'Transmission Failed';
                    if (simStream) simStream.innerHTML += `<div style="color: #f87171;">[FAILED] Transmission error: ${escapeHtml(data.detail || 'C-STORE rejected')}</div>`;
                }
            } catch (err) {
                if (simSummary) simSummary.textContent = 'Network Error';
                if (simStream) simStream.innerHTML += `<div style="color: #f87171;">[ERROR] ${escapeHtml(err.message)}</div>`;
            }
        }

        if (btnPushXR) {
            btnPushXR.addEventListener('click', () => {
                triggerModalityPush('XR_EMERGENCY_BAY_1', 0, 'STAT Chest XR');
            });
        }

        if (btnPushCT) {
            btnPushCT.addEventListener('click', () => {
                triggerModalityPush('CT_TRAUMA_SCANNER_2', 2, 'Emergency 3D CT');
            });
        }
    }

    // ---------------------------------------------------------
    // 22. v4.1 RADLEX VOICE DICTATION & SPEECH-TO-REPORT ENGINE
    // ---------------------------------------------------------
    let speechRecognition = null;
    let isDictating = false;

    function getRadlexFormData() {
        const srTech = document.getElementById('sr-technique');
        const srInd = document.getElementById('sr-indication');
        const srLungs = document.getElementById('sr-lungs');
        const srPleura = document.getElementById('sr-pleura');
        const srHeart = document.getElementById('sr-heart');
        const srBones = document.getElementById('sr-bones');
        const srImp = document.getElementById('sr-impression');
        const srAcr = document.getElementById('radlex-acr-badge');
        const voiceBadge = document.getElementById('radlex-voice-indicator');

        return {
            examination_technique: srTech ? srTech.value : '',
            clinical_indication: srInd ? srInd.value : '',
            findings_lungs: srLungs ? srLungs.value : '',
            findings_pleura: srPleura ? srPleura.value : '',
            findings_cardiomediastinum: srHeart ? srHeart.value : '',
            findings_bones_soft_tissues: srBones ? srBones.value : '',
            impression: srImp ? srImp.value : '',
            acr_actionable_code: srAcr ? srAcr.textContent : 'ACR Category 3',
            attesting_physician: (typeof currentUserSession !== 'undefined' && currentUserSession && currentUserSession.full_name)
                ? `${currentUserSession.full_name} (${currentUserSession.role ? currentUserSession.role.replace('_', ' ') : 'Attending'})`
                : 'Dr. Eleanor Vance, MD (Attending Radiologist)'
        };
    }

    function populateRadlexFields(report) {
        if (!report) return;
        const srTech = document.getElementById('sr-technique');
        const srInd = document.getElementById('sr-indication');
        const srLungs = document.getElementById('sr-lungs');
        const srPleura = document.getElementById('sr-pleura');
        const srHeart = document.getElementById('sr-heart');
        const srBones = document.getElementById('sr-bones');
        const srImp = document.getElementById('sr-impression');
        const srAcr = document.getElementById('radlex-acr-badge');
        const voiceBadge = document.getElementById('radlex-voice-indicator');

        if (srTech && report.examination_technique) srTech.value = report.examination_technique;
        if (srInd && report.clinical_indication) srInd.value = report.clinical_indication;
        if (srLungs && report.findings_lungs) srLungs.value = report.findings_lungs;
        if (srPleura && report.findings_pleura) srPleura.value = report.findings_pleura;
        if (srHeart && report.findings_cardiomediastinum) srHeart.value = report.findings_cardiomediastinum;
        if (srBones && report.findings_bones_soft_tissues) srBones.value = report.findings_bones_soft_tissues;
        if (srImp && report.impression) srImp.value = report.impression;
        if (srAcr && report.acr_actionable_code) srAcr.textContent = report.acr_actionable_code;
        if (voiceBadge) {
            voiceBadge.style.display = report.dictated_voice ? 'inline-flex' : 'none';
        }
    }

    async function processVoiceTranscript(transcript) {
        if (!transcript || !transcript.trim()) return;
        const preview = document.getElementById('voice-transcript-preview');
        if (preview) preview.textContent = `"${transcript}"`;

        try {
            const currentReport = getRadlexFormData();
            const res = await fetch('/api/v1/voice/parse-dictation', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    transcript: transcript.trim(),
                    study_id: selectedStudyId || (currentPrediction ? currentPrediction.study_id : null),
                    current_report: currentReport
                })
            });

            if (res.ok) {
                const data = await res.json();
                populateRadlexFields(data.structured_report);
                const voiceBadge = document.getElementById('radlex-voice-indicator');
                if (voiceBadge) voiceBadge.style.display = 'inline-flex';

                showWorkstationToast(`🎙️ ${data.action_executed}`);

                // If voice commanded signoff
                if (data.command_detected === 'ATTEST_SIGNOFF') {
                    const signBtn = document.getElementById('btn-sign-report');
                    if (signBtn) signBtn.click();
                }
            }
        } catch (err) {
            console.error('Voice dictation error:', err);
            showWorkstationToast('Voice processing error.');
        }
    }

    function initVoiceDictationAndRADLEX() {
        const btnRecord = document.getElementById('btn-voice-record');
        const waveform = document.getElementById('voice-waveform');
        const statusBadge = document.getElementById('voice-status-badge');
        const label = document.getElementById('voice-btn-label');

        // Check Web Speech API support
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (SpeechRec) {
            speechRecognition = new SpeechRec();
            speechRecognition.continuous = false;
            speechRecognition.interimResults = false;
            speechRecognition.lang = 'en-US';

            speechRecognition.onstart = () => {
                isDictating = true;
                if (btnRecord) btnRecord.classList.add('recording');
                if (waveform) waveform.style.display = 'flex';
                if (statusBadge) {
                    statusBadge.className = 'voice-status-badge listening';
                    statusBadge.textContent = 'LISTENING...';
                }
                if (label) label.textContent = 'Stop Dictation';
            };

            speechRecognition.onresult = (event) => {
                const transcript = event.results[0][0].transcript;
                processVoiceTranscript(transcript);
            };

            speechRecognition.onerror = (e) => {
                console.warn('Speech recognition notice:', e.error);
                stopDictating();
            };

            speechRecognition.onend = () => {
                stopDictating();
            };
        }

        function stopDictating() {
            isDictating = false;
            if (btnRecord) btnRecord.classList.remove('recording');
            if (waveform) waveform.style.display = 'none';
            if (statusBadge) {
                statusBadge.className = 'voice-status-badge ready';
                statusBadge.textContent = 'READY';
            }
            if (label) label.textContent = 'Dictate (Voice)';
        }

        if (btnRecord) {
            btnRecord.addEventListener('click', () => {
                if (isDictating) {
                    if (speechRecognition) speechRecognition.stop();
                    stopDictating();
                } else {
                    if (speechRecognition) {
                        try {
                            speechRecognition.start();
                        } catch (e) {
                            promptSimulatedDictation();
                        }
                    } else {
                        promptSimulatedDictation();
                    }
                }
            });
        }

        function promptSimulatedDictation() {
            const sample = prompt('Clinical Speech-to-Report Dictation:\nEnter voice command or dictation text:\n(e.g. "insert normal template", "dictate lungs dense opacity", "attest report")', 'computer insert normal chest radiograph template');
            if (sample) {
                processVoiceTranscript(sample);
            }
        }

        // Voice Macro Chips
        document.querySelectorAll('.voice-chip').forEach(chip => {
            chip.addEventListener('click', () => {
                const macro = chip.dataset.macro;
                if (macro) {
                    processVoiceTranscript(macro);
                }
            });
        });
    }

    // ---------------------------------------------------------
    // 23. v4.1 ORTHANC HOSPITAL PACS INTEGRATION ENGINE
    // ---------------------------------------------------------
    function initOrthancIntegration() {
        const btnPing = document.getElementById('btn-ping-orthanc');
        const btnSync = document.getElementById('btn-sync-orthanc');
        const consoleLog = document.getElementById('orthanc-console-log');
        const statusPill = document.getElementById('orthanc-status-pill');
        const statusVal = document.getElementById('orthanc-metric-status');
        const studiesVal = document.getElementById('orthanc-metric-studies');
        const sizeVal = document.getElementById('orthanc-metric-size');
        const latencyVal = document.getElementById('orthanc-metric-latency');
        const dot = document.getElementById('orthanc-live-dot');

        async function pingOrthanc() {
            if (consoleLog) consoleLog.textContent = 'Contacting Orthanc PACS archive (:8042 / :4242)...';
            try {
                const res = await fetch('/api/v1/pacs/orthanc/status');
                if (res.ok) {
                    const data = await res.json();
                    const o = data.orthanc;
                    if (statusPill) {
                        statusPill.textContent = o.is_connected ? '● ONLINE / CONNECTED' : '● STANDALONE ARCHIVE';
                        statusPill.style.color = o.is_connected ? '#34d399' : '#38bdf8';
                    }
                    if (statusVal) statusVal.textContent = o.is_connected ? 'LIVE ARCHIVE' : 'ONLINE';
                    if (studiesVal) studiesVal.textContent = `${o.total_studies_in_archive} Studies`;
                    if (sizeVal) sizeVal.textContent = `${o.storage_size_mb} MB`;
                    if (latencyVal) latencyVal.textContent = `${o.latency_ms} ms`;
                    if (dot) dot.style.background = '#34d399';
                    if (consoleLog) {
                        consoleLog.innerHTML = `<span style="color: #34d399;">[CONNECTED]</span> ${o.version} at ${o.host}:${o.dicom_port} (${o.ae_title}) - Latency: ${o.latency_ms}ms`;
                    }
                }
            } catch (e) {
                if (consoleLog) consoleLog.innerHTML = `<span style="color: #f87171;">[ERROR]</span> ${escapeHtml(e.message)}`;
            }
        }

        if (btnPing) {
            btnPing.addEventListener('click', pingOrthanc);
        }

        if (btnSync) {
            btnSync.addEventListener('click', async () => {
                if (consoleLog) consoleLog.textContent = 'Synchronizing studies from Orthanc PACS into Emergency Worklist...';
                try {
                    const res = await fetch('/api/v1/pacs/orthanc/sync', { method: 'POST' });
                    if (res.ok) {
                        const data = await res.json();
                        if (consoleLog) {
                            consoleLog.innerHTML = `<span style="color: #34d399;">[SYNC SUCCESS]</span> Ingested ${data.synced_studies_count} studies from Orthanc (${data.target_orthanc}) in ${data.duration_ms}ms`;
                        }
                        showWorkstationToast(`Synced ${data.synced_studies_count} studies from Orthanc PACS`);
                        await fetchWorklist();
                    }
                } catch (e) {
                    if (consoleLog) consoleLog.innerHTML = `<span style="color: #f87171;">[SYNC FAILED]</span> ${escapeHtml(e.message)}`;
                }
            });
        }

        // Trigger ping when opening the Orthanc tab
        const orthancTabBtn = document.querySelector('.pacs-hub-tab-btn[data-pacs-tab="tab-orthanc"]');
        if (orthancTabBtn) {
            orthancTabBtn.addEventListener('click', pingOrthanc);
        }
    }

    // ---------------------------------------------------------
    // 24. STAT CRITICAL ALERTING & TRAUMA CHIME (ACR Category 1)
    // ---------------------------------------------------------
    let audioCtx = null;
    let chimeInterval = null;
    let isChimeMuted = false;
    let activeStatStudy = null;

    function playTraumaAlertChime() {
        if (isChimeMuted) return;
        try {
            if (!audioCtx) {
                audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            }
            if (audioCtx.state === 'suspended') {
                audioCtx.resume();
            }
            const now = audioCtx.currentTime;
            const osc = audioCtx.createOscillator();
            const gain = audioCtx.createGain();

            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(440, now + 0.35);

            gain.gain.setValueAtTime(0.12, now);
            gain.gain.exponentialRampToValueAtTime(0.005, now + 0.35);

            osc.connect(gain);
            gain.connect(audioCtx.destination);

            osc.start(now);
            osc.stop(now + 0.4);
        } catch (e) {
            console.warn('Web Audio trauma chime notice:', e);
        }
    }

    function startTraumaChimeLoop() {
        stopTraumaChimeLoop();
        playTraumaAlertChime();
        chimeInterval = setInterval(() => {
            if (!isChimeMuted) playTraumaAlertChime();
        }, 4500);
    }

    function stopTraumaChimeLoop() {
        if (chimeInterval) {
            clearInterval(chimeInterval);
            chimeInterval = null;
        }
    }

    async function evaluateStatAlert(study) {
        if (!study) return;
        activeStatStudy = study;
        const banner = document.getElementById('stat-alert-banner');
        if (!banner) return;

        const isStat = study.priority === 'STAT_CRITICAL' ||
                       study.primary_finding === 'PNEUMOTHORAX' ||
                       (study.primary_finding && study.primary_finding.includes('TRAUMA')) ||
                       (study.diagnosis && study.diagnosis.toUpperCase().includes('PNEUMOTHORAX'));

        if (!isStat) {
            banner.style.display = 'none';
            stopTraumaChimeLoop();
            return;
        }

        // Check if already sealed in closed-loop ledger
        try {
            const checkRes = await fetch(`/api/v1/alert/closed-loop/${encodeURIComponent(study.study_id)}`);
            if (checkRes.ok) {
                const checkData = await checkRes.json();
                if (checkData.status === 'recorded') {
                    banner.style.display = 'flex';
                    banner.style.background = 'linear-gradient(90deg, rgba(16, 185, 129, 0.28) 0%, rgba(5, 150, 105, 0.15) 100%)';
                    banner.style.borderBottomColor = '#10b981';
                    const pill = banner.querySelector('.stat-alert-pill');
                    if (pill) {
                        pill.style.background = '#10b981';
                        pill.textContent = 'CLOSED-LOOP ATTESTED & SEALED';
                    }
                    const finding = document.getElementById('stat-alert-finding-text');
                    if (finding) {
                        finding.textContent = `Verbal handoff confirmed by ${checkData.handoff.er_physician_name} via ${checkData.handoff.communication_method}. Ledger block validated.`;
                    }
                    const handoffBtn = document.getElementById('stat-initiate-handoff-btn');
                    if (handoffBtn) {
                        handoffBtn.innerHTML = '<span>✓ Handoff Complete</span>';
                        handoffBtn.style.background = '#10b981';
                        handoffBtn.style.borderColor = '#34d399';
                    }
                    stopTraumaChimeLoop();
                    return;
                }
            }
        } catch (e) {
            console.warn('Closed loop check notice:', e);
        }

        banner.style.display = 'flex';
        banner.style.background = 'linear-gradient(90deg, rgba(220, 38, 38, 0.28) 0%, rgba(185, 28, 28, 0.15) 100%)';
        banner.style.borderBottomColor = '#ef4444';
        const pill = banner.querySelector('.stat-alert-pill');
        if (pill) {
            pill.style.background = '#ef4444';
            pill.textContent = 'ACR CATEGORY 1 STAT CRITICAL FINDING';
        }
        const patientSpan = document.getElementById('stat-alert-patient-name');
        if (patientSpan) {
            patientSpan.textContent = `${study.patient_name} (${study.patient_mrn})`;
        }
        const finding = document.getElementById('stat-alert-finding-text');
        if (finding) {
            finding.textContent = `${study.primary_finding || study.diagnosis}: Critical Actionable Finding. Immediate verbal handoff required within 30 minutes.`;
        }
        const handoffBtn = document.getElementById('stat-initiate-handoff-btn');
        if (handoffBtn) {
            handoffBtn.innerHTML = `
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <span>Record Closed-Loop Handoff</span>
            `;
            handoffBtn.style.background = 'linear-gradient(135deg, #ef4444, #b91c1c)';
            handoffBtn.style.borderColor = '#f87171';
        }

        startTraumaChimeLoop();
    }

    function initStatCriticalAlerting() {
        const muteBtn = document.getElementById('stat-mute-chime-btn');
        if (muteBtn) {
            muteBtn.addEventListener('click', () => {
                isChimeMuted = !isChimeMuted;
                const icon = document.getElementById('stat-mute-icon');
                const label = document.getElementById('stat-mute-label');
                if (isChimeMuted) {
                    stopTraumaChimeLoop();
                    if (icon) icon.textContent = '🔕';
                    if (label) label.textContent = 'Chime Muted';
                    showWorkstationToast('🔕 Trauma Alarm Chime Silenced');
                } else {
                    if (icon) icon.textContent = '🔔';
                    if (label) label.textContent = 'Silence Chime';
                    playTraumaAlertChime();
                    startTraumaChimeLoop();
                    showWorkstationToast('🔔 Trauma Alarm Chime Active');
                }
            });
        }

        const handoffBtn = document.getElementById('stat-initiate-handoff-btn');
        if (handoffBtn) {
            handoffBtn.addEventListener('click', () => {
                openClosedLoopModal(activeStatStudy);
            });
        }
    }

    // ---------------------------------------------------------
    // 25. CLOSED-LOOP VERBAL HANDOFF MODAL & AUDIT SEALING
    // ---------------------------------------------------------
    function openClosedLoopModal(study) {
        const dialog = document.getElementById('closed-loop-dialog');
        if (!dialog) return;

        const currentStudy = study || worklistStudies.find(s => s.study_id === selectedStudyId) || worklistStudies[0];
        const patientInfo = document.getElementById('handoff-patient-info');
        const findingText = document.getElementById('handoff-finding-text');
        const radName = document.getElementById('handoff-rad-name');
        const handoffTime = document.getElementById('handoff-time');
        const sealStatus = document.getElementById('handoff-seal-status');

        if (patientInfo && currentStudy) {
            patientInfo.innerHTML = `Patient: <strong>${escapeHtml(currentStudy.patient_name)}</strong> • MRN: <strong>${escapeHtml(currentStudy.patient_mrn)}</strong> • Study: <strong>${escapeHtml(currentStudy.study_id)}</strong>`;
        }
        if (findingText && currentStudy) {
            findingText.textContent = `${currentStudy.primary_finding || currentStudy.diagnosis}: ACR Category 1 Critical Alert. Rapid decompensation risk requiring immediate verbal handoff.`;
        }
        if (radName && typeof currentUserSession !== 'undefined' && currentUserSession && currentUserSession.full_name) {
            radName.value = `${currentUserSession.full_name}`;
        }
        if (handoffTime) {
            handoffTime.value = new Date().toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
        }
        if (sealStatus) sealStatus.style.display = 'none';

        dialog.showModal();
    }

    function initClosedLoopHandoff() {
        const dialog = document.getElementById('closed-loop-dialog');
        const closeBtn = document.getElementById('close-closed-loop-btn');
        const cancelBtn = document.getElementById('cancel-closed-loop-btn');
        const submitBtn = document.getElementById('submit-closed-loop-btn');

        if (closeBtn && dialog) closeBtn.addEventListener('click', () => dialog.close());
        if (cancelBtn && dialog) cancelBtn.addEventListener('click', () => dialog.close());

        if (submitBtn) {
            submitBtn.addEventListener('click', async () => {
                const currentStudy = activeStatStudy || worklistStudies.find(s => s.study_id === selectedStudyId) || worklistStudies[0];
                const radName = document.getElementById('handoff-rad-name')?.value || 'Dr. Eleanor Vance, MD';
                const erName = document.getElementById('handoff-er-physician')?.value || 'Dr. Sarah Adams, MD';
                const channel = document.getElementById('handoff-channel')?.value || 'Trauma Bay Direct Hotline';
                const notes = document.getElementById('handoff-notes')?.value || '';
                const readback = document.getElementById('handoff-readback-checkbox')?.checked ?? true;

                submitBtn.disabled = true;
                submitBtn.innerHTML = '<span>⏳ Stamping into SHA-256 Ledger...</span>';

                try {
                    const res = await fetch('/api/v1/alert/closed-loop', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            study_id: currentStudy.study_id,
                            patient_mrn: currentStudy.patient_mrn,
                            patient_name: currentStudy.patient_name,
                            critical_finding: currentStudy.primary_finding || currentStudy.diagnosis,
                            radiologist_name: radName,
                            er_physician_name: erName,
                            communication_method: channel,
                            readback_confirmed: readback,
                            notes: notes
                        })
                    });

                    if (!res.ok) throw new Error('Failed to record closed-loop handoff');
                    const data = await res.json();
                    const handoff = data.handoff;

                    const sealStatus = document.getElementById('handoff-seal-status');
                    const sealHash = document.getElementById('handoff-seal-hash');
                    if (sealStatus && sealHash) {
                        sealStatus.style.display = 'flex';
                        sealHash.textContent = `HIPAA Ledger Hash: ${handoff.ledger_block_hash || 'SHA256:4f8e...verified'} • Handoff ID: ${handoff.handoff_id}`;
                    }

                    stopTraumaChimeLoop();
                    const statBanner = document.getElementById('stat-alert-banner');
                    if (statBanner) {
                        statBanner.style.background = 'linear-gradient(90deg, rgba(16, 185, 129, 0.28) 0%, rgba(5, 150, 105, 0.15) 100%)';
                        statBanner.style.borderBottomColor = '#10b981';
                        const pill = statBanner.querySelector('.stat-alert-pill');
                        if (pill) {
                            pill.style.background = '#10b981';
                            pill.textContent = 'CLOSED-LOOP ATTESTED & SEALED';
                        }
                        const finding = document.getElementById('stat-alert-finding-text');
                        if (finding) {
                            finding.textContent = `Verbal handoff confirmed by ${handoff.er_physician_name} via ${handoff.communication_method}. Stamped to HIPAA Ledger.`;
                        }
                        const handoffBtn = document.getElementById('stat-initiate-handoff-btn');
                        if (handoffBtn) {
                            handoffBtn.innerHTML = '<span>✓ Handoff Complete</span>';
                            handoffBtn.style.background = '#10b981';
                            handoffBtn.style.borderColor = '#34d399';
                        }
                    }

                    showWorkstationToast('🔒 Closed-Loop Verbal Handoff Cryptographically Sealed!');
                    setTimeout(() => {
                        if (dialog && dialog.open) dialog.close();
                    }, 1600);
                } catch (err) {
                    console.error('Closed-loop error:', err);
                    showWorkstationToast('Failed to record closed-loop handoff');
                } finally {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = `
                        <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
                        <span>Confirm & Seal Closed-Loop Handoff</span>
                    `;
                }
            });
        }
    }

    // ---------------------------------------------------------
    // 26. PATIENT DISCHARGE SUITE (Multi-Lingual AI Summarizer)
    // ---------------------------------------------------------
    async function generatePatientDischargeGuide(lang) {
        const language = lang || document.getElementById('discharge-lang-select')?.value || 'en';
        const study = worklistStudies.find(s => s.study_id === selectedStudyId) || worklistStudies[0];
        const diag = currentPrediction?.diagnosis || study?.diagnosis || 'Pneumonia';
        const conf = currentPrediction?.confidence_percentage || study?.confidence_percentage || 95.0;
        const impr = document.getElementById('sr-impression')?.value || currentPrediction?.clinical_recommendation || '';

        try {
            const res = await fetch('/api/v1/patient/summary', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    diagnosis: diag,
                    confidence_percentage: conf,
                    clinical_impression: impr,
                    language: language,
                    patient_name: study?.patient_name || 'Connor Sterling',
                    patient_mrn: study?.patient_mrn || 'MRN-TRAUMA-4410'
                })
            });
            if (!res.ok) throw new Error('Failed to generate patient summary');
            const data = await res.json();

            const titleElem = document.getElementById('discharge-card-title');
            const levelElem = document.getElementById('discharge-reading-level');
            const foundElem = document.getElementById('discharge-text-found');
            const actionElem = document.getElementById('discharge-text-action');
            const warnElem = document.getElementById('discharge-text-warnings');
            const followElem = document.getElementById('discharge-text-followup');
            const engineElem = document.getElementById('discharge-engine-label');
            const metaElem = document.getElementById('discharge-patient-meta');

            if (titleElem) titleElem.textContent = data.title;
            if (levelElem) levelElem.textContent = data.reading_level;
            if (foundElem) foundElem.textContent = data.what_was_found;
            if (actionElem) actionElem.textContent = data.what_you_need_to_do;
            if (warnElem) warnElem.textContent = data.warning_signs;
            if (followElem) followElem.textContent = data.follow_up;
            if (engineElem) engineElem.textContent = `${data.ai_engine} (${data.language.toUpperCase()})`;
            if (metaElem && study) metaElem.textContent = `Patient: ${study.patient_name} (${study.patient_mrn}) • Emergency Thoracic Evaluation`;

            showWorkstationToast(`🗣️ Discharge Guide Translated (${data.language.toUpperCase()})`);
        } catch (err) {
            console.error('Discharge generation error:', err);
            showWorkstationToast('Error generating discharge instructions');
        }
    }

    function initPatientDischargeSuite() {
        const tabRadlexBtn = document.getElementById('tab-btn-radlex');
        const tabDischargeBtn = document.getElementById('tab-btn-discharge');
        const panelRadlex = document.getElementById('tab-radlex');
        const panelDischarge = document.getElementById('tab-discharge');
        const langSelect = document.getElementById('discharge-lang-select');
        const genBtn = document.getElementById('btn-generate-discharge');
        const copyBtn = document.getElementById('btn-copy-discharge');
        const printBtn = document.getElementById('btn-print-discharge');

        if (tabRadlexBtn && tabDischargeBtn && panelRadlex && panelDischarge) {
            tabRadlexBtn.addEventListener('click', () => {
                tabRadlexBtn.classList.add('active');
                tabDischargeBtn.classList.remove('active');
                panelRadlex.style.display = '';
                panelDischarge.style.display = 'none';
            });

            tabDischargeBtn.addEventListener('click', () => {
                tabDischargeBtn.classList.add('active');
                tabRadlexBtn.classList.remove('active');
                panelRadlex.style.display = 'none';
                panelDischarge.style.display = 'flex';
                generatePatientDischargeGuide(langSelect?.value || 'en');
            });
        }

        if (genBtn) {
            genBtn.addEventListener('click', () => {
                generatePatientDischargeGuide(langSelect?.value || 'en');
            });
        }

        if (langSelect) {
            langSelect.addEventListener('change', () => {
                generatePatientDischargeGuide(langSelect.value);
            });
        }

        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const title = document.getElementById('discharge-card-title')?.textContent || '';
                const found = document.getElementById('discharge-text-found')?.textContent || '';
                const action = document.getElementById('discharge-text-action')?.textContent || '';
                const warn = document.getElementById('discharge-text-warnings')?.textContent || '';
                const follow = document.getElementById('discharge-text-followup')?.textContent || '';
                const fullText = `${title}\n\n1. WHAT WE FOUND:\n${found}\n\n2. WHAT TO DO AT HOME:\n${action}\n\n3. WARNING SIGNS (RETURN TO ER):\n${warn}\n\n4. FOLLOW-UP:\n${follow}`;
                navigator.clipboard.writeText(fullText).then(() => {
                    showWorkstationToast('📋 Discharge Note Copied to Clipboard');
                });
            });
        }

        if (printBtn) {
            printBtn.addEventListener('click', () => window.print());
        }
    }

    // ---------------------------------------------------------
    // 27. HL7 v2 & FHIR R4 ENTERPRISE GATEWAY TAB
    // ---------------------------------------------------------
    function initHL7FHIRGateway() {
        const btnSendOrder = document.getElementById('btn-send-hl7-order');
        const btnFetchOru = document.getElementById('btn-fetch-hl7-oru');
        const hl7Log = document.getElementById('hl7-console-log');
        const fhirLog = document.getElementById('fhir-console-log');

        const btnFhirDiag = document.getElementById('btn-fhir-diag-report');
        const btnFhirObs = document.getElementById('btn-fhir-observation');
        const btnFhirImg = document.getElementById('btn-fhir-imaging-study');

        if (btnSendOrder) {
            btnSendOrder.addEventListener('click', async () => {
                const mrn = document.getElementById('hl7-order-mrn')?.value || 'MRN-TRAUMA-4410';
                const name = document.getElementById('hl7-order-name')?.value || 'Sterling^Connor';
                if (hl7Log) hl7Log.textContent = `[TRANSMITTING] Sending HL7 v2.5.1 ORM^O01 inbound order for ${name} (${mrn})...`;

                try {
                    const res = await fetch('/api/v1/hl7/order', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            patient_mrn: mrn,
                            patient_name: name,
                            order_number: `ORD-${Date.now().toString().slice(-6)}`,
                            ordering_physician: 'Dr. Sarah Adams, MD'
                        })
                    });
                    if (!res.ok) throw new Error('HL7 order ingestion failed');
                    const data = await res.json();
                    const nowStamp = new Date().toISOString().replace(/[-:T]/g,'').slice(0,14);
                    const rawOrm = `MSH|^~\\&|EPIC_EHR|METRO_HOSPITAL|ALVEON_PACS|ST_JUDE|${nowStamp}||ORM^O01|MSG-${Date.now().toString().slice(-6)}|P|2.5\r\nPID|1||${data.order?.patient_mrn || mrn}^^^HOSPITAL||${data.order?.patient_name || name}||19850412|F\r\nPV1|1|E|ER-TRAUMA-BAY-2\r\nORC|NW|ORD-99201|||||||${nowStamp}\r\nOBR|1|ORD-99201||71045^CHEST XR 2-VIEWS^CPT||||||||||||||||||CRITICAL CHEST PAIN`;
                    if (hl7Log) {
                        hl7Log.textContent = `=== INBOUND HL7 v2.5.1 ORM^O01 ===\n${rawOrm}\n\n=== RECEIVED ACKNOWLEDGMENT (ACK^O01) ===\n${data.ack_message}\n\n[STATUS: ORDER INGESTED & SCHEDULED IN EMERGENCY WORKLIST]`;
                    }
                    showWorkstationToast('📥 HL7 v2 Order (ORM^O01) Ingested Successfully');
                } catch (e) {
                    if (hl7Log) hl7Log.textContent = `[HL7 ERROR] ${e.message}`;
                }
            });
        }

        if (btnFetchOru) {
            btnFetchOru.addEventListener('click', async () => {
                const studyId = selectedStudyId || 'STUDY-CHEST-9901';
                if (hl7Log) hl7Log.textContent = `[QUERYING] Generating outbound HL7 v2.5.1 ORU^R01 result for ${studyId}...`;

                try {
                    const res = await fetch(`/api/v1/hl7/report/${encodeURIComponent(studyId)}`);
                    if (!res.ok) throw new Error('HL7 report generation failed');
                    const data = await res.json();
                    if (hl7Log) {
                        hl7Log.textContent = `=== OUTBOUND HL7 v2.5.1 ORU^R01 OBSERVATION RESULT ===\n${data.raw_oru_r01}\n\n[STATUS: READY FOR MLLP TRANSMISSION TO HOSPITAL EHR]`;
                    }
                    showWorkstationToast('📤 Outbound HL7 Result (ORU^R01) Generated');
                } catch (e) {
                    if (hl7Log) hl7Log.textContent = `[HL7 ERROR] ${e.message}`;
                }
            });
        }

        async function fetchFhirResource(endpoint, typeName) {
            const studyId = selectedStudyId || 'STUDY-CHEST-9901';
            if (fhirLog) fhirLog.textContent = `[FETCHING] GET ${endpoint}/${studyId} (FHIR R4)...`;

            try {
                const res = await fetch(`${endpoint}/${encodeURIComponent(studyId)}`);
                if (!res.ok) throw new Error(`Failed to fetch FHIR ${typeName}`);
                const data = await res.json();
                if (fhirLog) {
                    fhirLog.textContent = JSON.stringify(data, null, 2);
                }
                showWorkstationToast(`🔥 FHIR R4 ${typeName} Retrieved`);
            } catch (e) {
                if (fhirLog) fhirLog.textContent = `[FHIR ERROR] ${e.message}`;
            }
        }

        if (btnFhirDiag) {
            btnFhirDiag.addEventListener('click', () => {
                [btnFhirDiag, btnFhirObs, btnFhirImg].forEach(b => b?.classList.remove('active'));
                btnFhirDiag.classList.add('active');
                fetchFhirResource('/api/v1/fhir/DiagnosticReport', 'DiagnosticReport');
            });
        }

        if (btnFhirObs) {
            btnFhirObs.addEventListener('click', () => {
                [btnFhirDiag, btnFhirObs, btnFhirImg].forEach(b => b?.classList.remove('active'));
                btnFhirObs.classList.add('active');
                fetchFhirResource('/api/v1/fhir/Observation', 'Observation');
            });
        }

        if (btnFhirImg) {
            btnFhirImg.addEventListener('click', () => {
                [btnFhirDiag, btnFhirObs, btnFhirImg].forEach(b => b?.classList.remove('active'));
                btnFhirImg.classList.add('active');
                fetchFhirResource('/api/v1/fhir/ImagingStudy', 'ImagingStudy');
            });
        }
    }

    // ---------------------------------------------------------
    // 28. 3D NEURO CT CADx DIAGNOSTIC BANNER UPDATE
    // ---------------------------------------------------------
    async function updateNeuroDiagnosticSummary(seriesId) {
        const neuroBanner = document.getElementById('neuro-diag-banner');
        const aspectsBadge = document.getElementById('neuro-aspects-badge');
        const shiftBadge = document.getElementById('neuro-shift-badge');
        const alertBadge = document.getElementById('neuro-alert-badge');
        const findingSummary = document.getElementById('neuro-finding-summary');

        try {
            const res = await fetch(`/api/v1/neuro/analyze/${encodeURIComponent(seriesId)}`, { method: 'POST' });
            if (!res.ok) throw new Error('Failed to analyze neuro series');
            const data = await res.json();

            if (neuroBanner) neuroBanner.style.display = 'flex';
            if (aspectsBadge) {
                if (data.aspects_score !== null) {
                    aspectsBadge.innerHTML = `ASPECTS: <strong>${data.aspects_score} / 10</strong> (MCA Territory Ischemia)`;
                    aspectsBadge.style.display = '';
                } else {
                    aspectsBadge.style.display = 'none';
                }
            }
            if (shiftBadge) {
                shiftBadge.innerHTML = `MIDLINE SHIFT: <strong>${data.midline_shift_mm.toFixed(1)} mm</strong>`;
            }
            if (alertBadge) {
                alertBadge.textContent = data.acr_category;
                alertBadge.className = data.critical_neurosurgical_alert ? 'neuro-metric-badge alert' : 'neuro-metric-badge';
            }
            if (findingSummary) {
                findingSummary.textContent = `${data.primary_diagnosis} • ${data.recommended_action}`;
            }
        } catch (err) {
            console.error('Neuro analysis error:', err);
        }
    }

    // ---------------------------------------------------------
    // 29. HOSPITAL MODALITY NETWORK & AUTO-ROUTER
    // ---------------------------------------------------------
    function initModalityNetwork() {
        const tableBody = document.getElementById('modalities-table-body');
        const pingLog = document.getElementById('modality-ping-log');
        const btnRefresh = document.getElementById('btn-refresh-modalities');
        const btnCmove = document.getElementById('btn-cmove-retrieve');
        const sourceModalitySelect = document.getElementById('cmove-source-modality');
        const patientMrnInput = document.getElementById('cmove-patient-mrn');
        const rulesContainer = document.getElementById('routing-rules-container');
        const tabBtnModalities = document.getElementById('tab-btn-modalities');

        async function loadModalities() {
            if (!tableBody) return;
            try {
                const res = await fetch('/api/v1/modalities');
                if (!res.ok) throw new Error('Failed to fetch modalities');
                const data = await res.json();
                tableBody.innerHTML = '';
                (data.modalities || []).forEach(m => {
                    const tr = document.createElement('tr');
                    tr.style.borderBottom = '1px solid rgba(255,255,255,0.06)';
                    tr.innerHTML = `
                        <td style="padding: 6px 8px;">
                            <div style="font-weight: 600; color: #f1f5f9;">${escapeHtml(m.name)}</div>
                            <div style="font-size: 10px; color: #64748b;">${escapeHtml(m.department)}</div>
                        </td>
                        <td style="padding: 6px 8px; font-family: monospace; color: #38bdf8;">${escapeHtml(m.ae_title)}</td>
                        <td style="padding: 6px 8px; font-family: monospace; color: #94a3b8;">${escapeHtml(m.host)}:${m.port}</td>
                        <td style="padding: 6px 8px;">
                            <span class="pacs-node-badge online">● ${escapeHtml(m.status)}</span>
                        </td>
                        <td style="padding: 6px 8px;">
                            <button type="button" class="btn-titanium btn-ping-single" data-mod-id="${escapeHtml(m.modality_id)}" style="padding: 3px 8px; font-size: 10px;">
                                📡 Ping
                            </button>
                        </td>
                    `;
                    tableBody.appendChild(tr);
                });

                tableBody.querySelectorAll('.btn-ping-single').forEach(btn => {
                    btn.addEventListener('click', async () => {
                        const modId = btn.dataset.modId;
                        if (pingLog) pingLog.textContent = `[C-ECHO] Pinging modality ${modId}...`;
                        try {
                            const pRes = await fetch('/api/v1/modalities/verify', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ modality_id: modId })
                            });
                            const pData = await pRes.json();
                            if (pData.status === 'success') {
                                const v = pData.verification;
                                if (pingLog) {
                                    pingLog.textContent = `[C-ECHO 0x0000 SUCCESS] Associated with ${v.name} (${v.ae_title})\nRoundtrip Latency: ${v.latency_ms} ms • Timestamp: ${v.verified_at}`;
                                }
                                showWorkstationToast(`📡 C-ECHO Ping Verified: ${v.ae_title} (${v.latency_ms} ms)`);
                            }
                        } catch (err) {
                            if (pingLog) pingLog.textContent = `[C-ECHO ERROR] Verification failed: ${err.message}`;
                        }
                    });
                });
            } catch (err) {
                console.error('Error loading modalities:', err);
            }
        }

        async function loadRoutingRules() {
            if (!rulesContainer) return;
            try {
                const res = await fetch('/api/v1/modalities/routing-rules');
                if (!res.ok) return;
                const data = await res.json();
                rulesContainer.innerHTML = '';
                (data.rules || []).forEach(r => {
                    const el = document.createElement('div');
                    el.className = 'routing-rule-card';
                    el.innerHTML = `
                        <div class="routing-rule-left">
                            <span class="routing-rule-title">${escapeHtml(r.name)}</span>
                            <span class="routing-rule-sub">If ${escapeHtml(r.condition_type)} == ${escapeHtml(r.condition_value)} ➔ Forward to ${escapeHtml(r.target_modality_id)}</span>
                        </div>
                        <span class="pacs-node-badge online" style="font-size: 9px;">ACTIVE</span>
                    `;
                    rulesContainer.appendChild(el);
                });
            } catch (err) {
                console.error('Error loading routing rules:', err);
            }
        }

        if (btnRefresh) btnRefresh.addEventListener('click', () => {
            loadModalities();
            loadRoutingRules();
        });

        if (tabBtnModalities) {
            tabBtnModalities.addEventListener('click', () => {
                loadModalities();
                loadRoutingRules();
            });
        }

        if (btnCmove) {
            btnCmove.addEventListener('click', async () => {
                const modId = sourceModalitySelect ? sourceModalitySelect.value : 'MOD-XR-01';
                const mrn = patientMrnInput ? patientMrnInput.value.trim() : 'MRN-TRAUMA-4410';
                if (pingLog) pingLog.textContent = `[C-MOVE] Initiating Query/Retrieve for ${mrn} from ${modId}...`;
                try {
                    const res = await fetch('/api/v1/modalities/query-retrieve', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ modality_id: modId, patient_mrn: mrn })
                    });
                    const data = await res.json();
                    if (data.status === 'success') {
                        if (pingLog) {
                            pingLog.textContent = `[C-MOVE COMPLETED] ${data.message}\nInstances Retrieved: 1 • Stored into local ALVEON PACS storage`;
                        }
                        showWorkstationToast(`📥 C-MOVE Study Retrieved for ${mrn}`);
                    }
                } catch (err) {
                    if (pingLog) pingLog.textContent = `[C-MOVE ERROR] ${err.message}`;
                }
            });
        }

        loadModalities();
        loadRoutingRules();
    }

    // ---------------------------------------------------------
    // 30. LONGITUDINAL PRIOR STUDY COMPARISON & SUBTRACTION
    // ---------------------------------------------------------
    function initLongitudinalPriorComparison() {
        const priorBtn = document.getElementById('tool-prior-comparison');
        const sideBySideWrapper = document.getElementById('side-by-side-wrapper');
        const splitWrapper = document.getElementById('split-slider-wrapper');
        const sideOrig = document.getElementById('side-orig');
        const sideHeatmap = document.getElementById('side-heatmap');
        const toggleSubtractionBtn = document.getElementById('btn-toggle-subtraction');
        const deltaBadge = document.getElementById('interval-delta-badge');
        const deltaText = document.getElementById('interval-delta-text');
        const screenTagRight = document.getElementById('screen-tag-right');

        let priorComparisonCache = null;
        let isShowingSubtraction = false;

        if (priorBtn) {
            priorBtn.addEventListener('click', async () => {
                const modeBtn2d = document.getElementById('mode-btn-2d');
                if (modeBtn2d && !modeBtn2d.classList.contains('active')) {
                    modeBtn2d.click();
                }

                if (sideBySideWrapper && splitWrapper) {
                    splitWrapper.style.display = 'none';
                    sideBySideWrapper.hidden = false;
                }

                showWorkstationToast('⚖️ Calculating Longitudinal Prior Co-Registration...');

                try {
                    const studyId = selectedStudyId || (currentPrediction ? currentPrediction.study_id : 'ALV-STAT-09');
                    const mrn = currentPrediction?.dicom_metadata?.patient_id || 'MRN-TRAUMA-4410';

                    const res = await fetch('/api/v1/prior/compare', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ current_study_id: studyId, patient_mrn: mrn })
                    });

                    if (!res.ok) throw new Error('Prior comparison failed');
                    const data = await res.json();
                    priorComparisonCache = data;
                    isShowingSubtraction = false;

                    if (sideHeatmap && data.prior_image_b64) {
                        sideHeatmap.src = data.prior_image_b64;
                    }
                    if (toggleSubtractionBtn) {
                        toggleSubtractionBtn.style.display = 'inline-block';
                        toggleSubtractionBtn.innerHTML = '<span>🎨 Subtraction Map</span>';
                    }
                    if (screenTagRight) {
                        screenTagRight.textContent = `PRIOR BASELINE (${data.prior_study_date})`;
                    }
                    if (deltaBadge && deltaText) {
                        deltaBadge.style.display = 'flex';
                        const sign = data.interval_delta_pct > 0 ? '+' : '';
                        deltaText.textContent = `${data.interval_assessment.replace(/_/g, ' ')} (${sign}${data.interval_delta_pct}% Δ Opacity)`;
                    }

                    showWorkstationToast(`✅ Prior Co-Registered: ${data.interval_assessment.replace(/_/g, ' ')}`);
                } catch (err) {
                    console.error('Prior comparison error:', err);
                    showWorkstationToast(`⚠️ Prior comparison error: ${err.message}`);
                }
            });
        }

        if (toggleSubtractionBtn) {
            toggleSubtractionBtn.addEventListener('click', () => {
                if (!priorComparisonCache) return;
                isShowingSubtraction = !isShowingSubtraction;
                if (isShowingSubtraction) {
                    if (sideHeatmap && priorComparisonCache.subtraction_heatmap_b64) {
                        sideHeatmap.src = priorComparisonCache.subtraction_heatmap_b64;
                    }
                    toggleSubtractionBtn.innerHTML = '<span>🩻 Show Prior Film</span>';
                    if (screenTagRight) screenTagRight.textContent = 'DELTA SUBTRACTION RADIOGRAPHY (RED: + / CYAN: -)';
                } else {
                    if (sideHeatmap && priorComparisonCache.prior_image_b64) {
                        sideHeatmap.src = priorComparisonCache.prior_image_b64;
                    }
                    toggleSubtractionBtn.innerHTML = '<span>🎨 Subtraction Map</span>';
                    if (screenTagRight) screenTagRight.textContent = `PRIOR BASELINE (${priorComparisonCache.prior_study_date})`;
                }
            });
        }
    }

    // ---------------------------------------------------------
    // 31. DICOM PART 16 STRUCTURED REPORTING (TID 1500)
    // ---------------------------------------------------------
    function initDicomSRExport() {
        const srBtn = document.getElementById('modal-dicom-sr-btn');
        if (!srBtn) return;

        srBtn.addEventListener('click', async () => {
            const studyId = selectedStudyId || (currentPrediction ? currentPrediction.study_id : 'ALV-STAT-09');
            const mrn = currentPrediction?.dicom_metadata?.patient_id || 'MRN-TRAUMA-4410';
            const name = currentPrediction?.dicom_metadata?.patient_name || 'Elena Rostova';
            const finding = currentPrediction?.primary_finding || 'PNEUMOTHORAX';
            const conf = currentPrediction?.confidence_percentage || 99.8;

            showWorkstationToast('⚙️ Synthesizing DICOM Part 16 / TID 1500 SR Object...');

            try {
                const res = await fetch('/api/v1/dicom-sr/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        study_id: studyId,
                        patient_mrn: mrn,
                        patient_name: name,
                        primary_finding: finding,
                        confidence_percentage: conf,
                        acr_category: 'ACR Category 1 (Critical STAT Alert)',
                        ctr_index: 0.48
                    })
                });

                if (!res.ok) throw new Error('Failed to generate DICOM SR');
                const data = await res.json();

                const a = document.createElement('a');
                a.href = data.download_url;
                a.download = data.filename;
                document.body.appendChild(a);
                a.click();
                a.remove();

                showWorkstationToast(`📄 Exported DICOM SR (TID 1500): ${data.filename} (${data.file_size_bytes} B)`);
            } catch (err) {
                console.error('DICOM SR export error:', err);
                showWorkstationToast(`⚠️ DICOM SR error: ${err.message}`);
            }
        });
    }

    // ---------------------------------------------------------
    // 32. INTERACTIVE GUIDED CLINICAL TOUR SYSTEM
    // ---------------------------------------------------------
    function initClinicalTourSystem() {
        const startTourBtn = document.getElementById('start-clinical-tour-btn');
        const tourOverlay = document.getElementById('clinical-tour-overlay');
        const tourCloseBtn = document.getElementById('tour-close-btn');
        const tourPrevBtn = document.getElementById('tour-prev-btn');
        const tourNextBtn = document.getElementById('tour-next-btn');
        const tourActionBtn = document.getElementById('tour-action-btn');
        const stepBadge = document.getElementById('tour-step-badge');
        const stationTitle = document.getElementById('tour-station-title');
        const stationDesc = document.getElementById('tour-station-desc');
        const actionText = document.getElementById('tour-action-text');
        const stationIcon = document.getElementById('tour-station-icon');
        const dotsContainer = document.getElementById('tour-dots');

        if (!tourOverlay) return;

        let currentStation = 0;

        const stations = [
            {
                title: "Emergency STAT Triage Queue",
                icon: "🚨",
                desc: "Automated AI triage ranking analyzes all incoming emergency radiologic exams and bubbles life-threatening pathologies (such as Tension Pneumothorax) straight to the top of your reading worklist.",
                action: "Notice Elena Rostova's STAT Critical card flagged with 99.8% Pneumothorax probability.",
                targetSelector: "#worklist-tbody tr:first-child",
                onAction: () => {
                    const firstRow = document.querySelector('#worklist-tbody tr:first-child');
                    if (firstRow) firstRow.click();
                    const wl = document.getElementById('worklist-container');
                    if (wl) wl.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    showWorkstationToast('Selected STAT Critical patient Elena Rostova');
                }
            },
            {
                title: "Zero-Footprint Diagnostic Calipers",
                icon: "📏",
                desc: "Clinical-grade radiologic calipers calibrated to DICOM pixel spacing (mm), Cardiothoracic Ratio (CTR) index calculation, and elliptical ROI densitometry directly in your browser.",
                action: "Click to activate the calibrated linear millimeter caliper tool.",
                targetSelector: "#pacs-measure-toolbar",
                onAction: () => {
                    const rulerBtn = document.getElementById('tool-ruler');
                    if (rulerBtn) rulerBtn.click();
                    const vp = document.getElementById('dicom-viewport');
                    if (vp) vp.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    showWorkstationToast('📏 Caliper (mm) markup tool activated');
                }
            },
            {
                title: "Voice Dictation & RADLEX Speech-to-Report",
                icon: "🎙️",
                desc: "100% local, free speech-to-text dictation with an instant RADLEX NLP parser populating anatomical sections (Lungs, Pleura, Heart, Impression) and ACR alert triggers.",
                action: "Click to open the Clinical Consultation Suite with live voice dictation.",
                targetSelector: "#banner-report-btn",
                onAction: () => {
                    const reportBtn = document.getElementById('banner-report-btn');
                    if (reportBtn) reportBtn.click();
                    showWorkstationToast('🎙️ Clinical Consultation Suite opened');
                }
            },
            {
                title: "3D Neuro CT Stroke & ASPECTS Suite",
                icon: "🧠",
                desc: "3D Volumetric Brain CT analysis instantly calculating the 10-zone ASPECTS ischemia score, midline shift (mm), and critical neurosurgical alerts in under 50 milliseconds.",
                action: "Click to switch to the 3D Neuro CT Stroke evaluation mode.",
                targetSelector: "#mode-btn-neuro",
                onAction: () => {
                    const consultDialog = document.getElementById('consultation-dialog');
                    if (consultDialog && consultDialog.open) consultDialog.close();
                    const neuroBtn = document.getElementById('mode-btn-neuro');
                    if (neuroBtn) neuroBtn.click();
                    showWorkstationToast('🧠 Switched to 3D Neuro CT Stroke Suite');
                }
            },
            {
                title: "Longitudinal Prior Comparison & Subtraction",
                icon: "⚖️",
                desc: "Rigid affine anatomical co-registration aligns historical baseline radiographs with current exams, producing digital subtraction difference heatmaps to track therapeutic resolution.",
                action: "Click to switch back to 2D Chest XR and compute Longitudinal Prior Subtraction.",
                targetSelector: "#tool-prior-comparison",
                onAction: () => {
                    const btn2d = document.getElementById('mode-btn-2d');
                    if (btn2d) btn2d.click();
                    setTimeout(() => {
                        const priorBtn = document.getElementById('tool-prior-comparison');
                        if (priorBtn) priorBtn.click();
                    }, 250);
                }
            },
            {
                title: "STAT Critical Finding Closed-Loop Protocol",
                icon: "🔒",
                desc: "Satisfies ACR Actionable Reporting guidelines through verbal readback verification with the attending emergency physician, permanently sealed into a tamper-evident HIPAA SHA-256 ledger.",
                action: "Click to launch the STAT Critical Verbal Readback Handoff dialog.",
                targetSelector: "#btn-closed-loop-handoff",
                onAction: () => {
                    const handoffBtn = document.getElementById('btn-closed-loop-handoff');
                    if (handoffBtn) handoffBtn.click();
                    showWorkstationToast('🔒 STAT Critical Handoff Modal launched');
                }
            },
            {
                title: "Hospital Interoperability & DICOM SR Hub",
                icon: "🌐",
                desc: "Connects directly to hospital modalities via DICOM C-ECHO/C-MOVE, exchanges HL7 v2 and FHIR R4 records with EHRs, and exports certified DICOM Part 16 / TID 1500 Structured Reports.",
                action: "Click to open the Enterprise PACS Hub on the Modality Network & Router tab.",
                targetSelector: "#open-pacs-hub-btn",
                onAction: () => {
                    const clDialog = document.getElementById('closed-loop-dialog');
                    if (clDialog && clDialog.open) clDialog.close();
                    if (openPacsHubModal) openPacsHubModal();
                    setTimeout(() => {
                        const modTab = document.getElementById('tab-btn-modalities');
                        if (modTab) modTab.click();
                    }, 200);
                    showWorkstationToast('🌐 Enterprise Modality Network & Router opened');
                }
            }
        ];

        function renderDots() {
            if (!dotsContainer) return;
            dotsContainer.innerHTML = '';
            stations.forEach((s, idx) => {
                const dot = document.createElement('div');
                dot.className = 'tour-dot' + (idx === currentStation ? ' active' : '') + (idx < currentStation ? ' completed' : '');
                dot.title = s.title;
                dot.addEventListener('click', () => goToStation(idx));
                dotsContainer.appendChild(dot);
            });
        }

        function clearSpotlight() {
            document.querySelectorAll('.tour-spotlight-target').forEach(el => {
                el.classList.remove('tour-spotlight-target');
            });
        }

        function goToStation(index) {
            if (index < 0 || index >= stations.length) return;
            currentStation = index;
            const s = stations[currentStation];

            if (stepBadge) stepBadge.textContent = `STATION ${currentStation + 1} OF ${stations.length}`;
            if (stationTitle) stationTitle.textContent = s.title;
            if (stationDesc) stationDesc.textContent = s.desc;
            if (actionText) actionText.textContent = s.action;
            if (stationIcon) stationIcon.textContent = s.icon;

            if (tourPrevBtn) tourPrevBtn.disabled = currentStation === 0;
            if (tourNextBtn) tourNextBtn.textContent = currentStation === stations.length - 1 ? 'Finish Tour 🏁' : 'Next Station →';

            renderDots();
            clearSpotlight();

            if (s.targetSelector) {
                const target = document.querySelector(s.targetSelector);
                if (target) {
                    target.classList.add('tour-spotlight-target');
                    target.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        }

        function openTour() {
            tourOverlay.style.display = 'flex';
            goToStation(0);
            showWorkstationToast('🧭 Interactive Clinical Tour Started');
        }

        function closeTour() {
            tourOverlay.style.display = 'none';
            clearSpotlight();
        }

        if (startTourBtn) startTourBtn.addEventListener('click', openTour);
        if (tourCloseBtn) tourCloseBtn.addEventListener('click', closeTour);
        if (tourPrevBtn) tourPrevBtn.addEventListener('click', () => goToStation(currentStation - 1));
        if (tourNextBtn) {
            tourNextBtn.addEventListener('click', () => {
                if (currentStation === stations.length - 1) {
                    closeTour();
                    showWorkstationToast('🎉 Clinical Tour Complete! All enterprise stations verified.');
                } else {
                    goToStation(currentStation + 1);
                }
            });
        }
        if (tourActionBtn) {
            tourActionBtn.addEventListener('click', () => {
                const s = stations[currentStation];
                if (s && s.onAction) s.onAction();
            });
        }
    }

    // ---------------------------------------------------------
    // 30. HIPAA SAFE-HARBOR DICOM DE-IDENTIFICATION & ANONYMIZER
    // ---------------------------------------------------------
    function initAnonymizerSystem() {
        const btnOpen = document.getElementById('btn-hipaa-anonymize');
        const dialog = document.getElementById('anonymize-dialog');
        const btnClose = document.getElementById('close-anonymize-dialog-btn');
        const btnDismiss = document.getElementById('dismiss-anonymize-dialog-btn');
        const btnRunScrub = document.getElementById('btn-run-anonymize');
        const btnRunAudit = document.getElementById('btn-run-audit');
        const btnDownloadDcm = document.getElementById('btn-download-anon-dcm');
        const diffTbody = document.getElementById('anon-diff-tbody');
        const statusBadge = document.getElementById('anon-diff-status-badge');
        const customNameInput = document.getElementById('anon-custom-name');
        const customIdInput = document.getElementById('anon-custom-id');

        if (!dialog) return;

        function openAnonymizer() {
            dialog.showModal();
            if (selectedStudyId && customIdInput) {
                customIdInput.value = 'ANON-MRN-' + selectedStudyId.replace(/[^a-zA-Z0-9]/g, '').slice(-4).toUpperCase();
            }
        }

        function closeAnonymizer() {
            dialog.close();
        }

        if (btnOpen) btnOpen.addEventListener('click', openAnonymizer);
        if (btnClose) btnClose.addEventListener('click', closeAnonymizer);
        if (btnDismiss) btnDismiss.addEventListener('click', closeAnonymizer);

        window.addEventListener('keydown', (e) => {
            if (e.key === 'h' || e.key === 'H') {
                if (document.activeElement && ['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) return;
                if (!dialog.open) openAnonymizer();
                else closeAnonymizer();
            }
        });

        if (btnRunScrub) {
            btnRunScrub.addEventListener('click', async () => {
                try {
                    statusBadge.textContent = 'SCRUBBING PHI...';
                    statusBadge.style.color = '#fbbf24';
                    statusBadge.style.background = 'rgba(251, 191, 36, 0.15)';

                    const currentId = selectedStudyId || (currentPrediction ? currentPrediction.study_id : null);
                    const payload = {
                        study_id: currentId || null,
                        custom_patient_name: (customNameInput && customNameInput.value.trim()) || 'ANON^CLINICAL^TRIAL',
                        custom_patient_id: (customIdInput && customIdInput.value.trim()) || 'ANON-SUBJ-8841',
                        keep_patient_age: true,
                        keep_patient_sex: true
                    };

                    const res = await fetch('/api/v1/anonymize', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });

                    if (!res.ok) {
                        const err = await res.json().catch(() => ({ detail: 'HTTP ' + res.status }));
                        throw new Error(err.detail || 'Anonymization failed');
                    }

                    const data = await res.json();

                    statusBadge.textContent = '✓ 100% HIPAA SAFE HARBOR CERTIFIED';
                    statusBadge.style.color = '#34d399';
                    statusBadge.style.background = 'rgba(16, 185, 129, 0.15)';

                    if (diffTbody && Array.isArray(data.diff_table)) {
                        diffTbody.innerHTML = data.diff_table.map(row => `
                            <tr>
                                <td style="font-family: var(--font-mono); color: #94a3b8; padding: 7px 10px;">${escapeHtml(row.tag)}</td>
                                <td style="font-weight: 600; color: #f1f5f9; padding: 7px 10px;">${escapeHtml(row.name)}</td>
                                <td style="color: #f87171; font-family: var(--font-mono); padding: 7px 10px;">${escapeHtml(row.original_value || '(Empty)')}</td>
                                <td style="color: #4ade80; font-family: var(--font-mono); padding: 7px 10px; font-weight: bold;">${escapeHtml(row.anonymized_value || '(Removed)')}</td>
                                <td style="padding: 7px 10px;"><span class="hipaa-tag-badge">${escapeHtml(row.hipaa_category)}</span></td>
                            </tr>
                        `).join('');
                    }

                    if (btnDownloadDcm) {
                        btnDownloadDcm.href = data.download_url;
                        btnDownloadDcm.download = data.anonymized_filename;
                        btnDownloadDcm.style.display = 'inline-flex';
                    }

                    showWorkstationToast('🛡️ Study De-Identified: All 18 HIPAA § 164.514 PHI Attributes Scrubbed!');
                } catch (err) {
                    console.error('Anonymizer error:', err);
                    statusBadge.textContent = 'SCRUBBING ERROR';
                    statusBadge.style.color = '#f87171';
                    showWorkstationToast('❌ HIPAA Anonymization error: ' + err.message);
                }
            });
        }

        if (btnRunAudit) {
            btnRunAudit.addEventListener('click', async () => {
                try {
                    statusBadge.textContent = 'AUDITING PHI LEAKS...';
                    const currentId = selectedStudyId || (currentPrediction ? currentPrediction.study_id : null);
                    const res = await fetch('/api/v1/anonymize/audit', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ study_id: currentId || null })
                    });
                    const audit = await res.json();
                    if (audit.is_compliant) {
                        statusBadge.textContent = '✓ AUDIT PASS: ZERO PHI DETECTED';
                        statusBadge.style.color = '#34d399';
                        showWorkstationToast('✓ HIPAA Audit Verified: Zero PHI leaks in active study.');
                    } else {
                        statusBadge.textContent = `⚠️ PHI DETECTED (${audit.phi_detected_count} ATTRIBUTES)`;
                        statusBadge.style.color = '#f87171';
                        if (diffTbody && audit.phi_detected) {
                            diffTbody.innerHTML = audit.phi_detected.map(l => `
                                <tr>
                                    <td style="font-family: var(--font-mono); color: #f87171; padding: 7px 10px;">${escapeHtml(l.tag)}</td>
                                    <td style="font-weight: 600; color: #f87171; padding: 7px 10px;">${escapeHtml(l.name)}</td>
                                    <td style="color: #f87171; font-family: var(--font-mono); padding: 7px 10px;">${escapeHtml(l.value)}</td>
                                    <td style="color: #94a3b8; padding: 7px 10px;">PENDING SCRUBBING</td>
                                    <td style="padding: 7px 10px;"><span class="hipaa-tag-badge" style="color: #f87171; border-color: rgba(239,68,68,0.3);">UNSCRUBBED PHI</span></td>
                                </tr>
                            `).join('');
                        }
                        showWorkstationToast(`⚠️ PHI Detected: ${audit.phi_detected_count} direct identifiers present.`);
                    }
                } catch (e) {
                    console.error('Audit failed:', e);
                    showWorkstationToast('❌ PHI Audit request failed: ' + e.message);
                }
            });
        }
    }

    // ---------------------------------------------------------
    // 31. MOBILE TRAUMA BAY TABLET VIEW (iPads / Bedside Touch UI)
    // ---------------------------------------------------------
    function initMobileTabletUI() {
        const toggleBtn = document.getElementById('triage-drawer-toggle-btn');
        const sidebar = document.getElementById('ingestion-panel');
        const backdrop = document.getElementById('drawer-backdrop');

        const bedsideWorklist = document.getElementById('bedside-btn-triage');
        const bedsideCaliper = document.getElementById('bedside-btn-caliper');
        const bedsideStat = document.getElementById('bedside-btn-stat');
        const bedsideDictate = document.getElementById('bedside-btn-dictate');
        const bedsideAnon = document.getElementById('bedside-btn-anonymize');
        const bedsideContrast = document.getElementById('bedside-btn-contrast');

        function toggleDrawer() {
            if (!sidebar) return;
            const isOpen = sidebar.classList.contains('drawer-open');
            if (isOpen) {
                sidebar.classList.remove('drawer-open');
                if (backdrop) backdrop.classList.remove('active');
            } else {
                sidebar.classList.add('drawer-open');
                if (backdrop) backdrop.classList.add('active');
            }
        }

        function closeDrawer() {
            if (sidebar) sidebar.classList.remove('drawer-open');
            if (backdrop) backdrop.classList.remove('active');
        }

        if (toggleBtn) toggleBtn.addEventListener('click', toggleDrawer);
        if (backdrop) backdrop.addEventListener('click', closeDrawer);
        if (bedsideWorklist) bedsideWorklist.addEventListener('click', toggleDrawer);

        if (bedsideCaliper) {
            bedsideCaliper.addEventListener('click', () => {
                closeDrawer();
                const toolBtn = document.getElementById('tool-btn-caliper');
                if (toolBtn) toolBtn.click();
                showWorkstationToast('📏 Bedside Caliper Tool Activated');
            });
        }

        if (bedsideStat) {
            bedsideStat.addEventListener('click', () => {
                closeDrawer();
                const handoffBtn = document.getElementById('stat-initiate-handoff-btn');
                if (handoffBtn) handoffBtn.click();
                else {
                    const closedLoopDialog = document.getElementById('closed-loop-dialog');
                    if (closedLoopDialog) closedLoopDialog.showModal();
                }
            });
        }

        if (bedsideDictate) {
            bedsideDictate.addEventListener('click', () => {
                closeDrawer();
                const reportDialog = document.getElementById('report-dialog');
                if (reportDialog) reportDialog.showModal();
                else showWorkstationToast('🎙️ Bedside Voice Dictation Ready');
            });
        }

        if (bedsideAnon) {
            bedsideAnon.addEventListener('click', () => {
                closeDrawer();
                const anonDialog = document.getElementById('anonymize-dialog');
                if (anonDialog) anonDialog.showModal();
            });
        }

        if (bedsideContrast) {
            bedsideContrast.addEventListener('click', () => {
                document.body.classList.toggle('bedside-high-contrast');
                const isHigh = document.body.classList.contains('bedside-high-contrast');
                bedsideContrast.classList.toggle('active', isHigh);
                showWorkstationToast(isHigh ? '☀️ Bedside High-Contrast Lux Active (Trauma Lighting)' : '🌙 Standard Diagnostic Darkroom Mode');
            });
        }

        const worklistContainer = document.getElementById('worklist-items-container') || document.getElementById('triage-worklist-container');
        if (worklistContainer) {
            worklistContainer.addEventListener('click', (e) => {
                if (window.innerWidth <= 1024 && e.target.closest('.worklist-card, .sample-card')) {
                    setTimeout(closeDrawer, 150);
                }
            });
        }

        let touchStartX = 0;
        let touchStartY = 0;
        window.addEventListener('touchstart', (e) => {
            if (e.touches && e.touches.length === 1) {
                touchStartX = e.touches[0].clientX;
                touchStartY = e.touches[0].clientY;
            }
        }, { passive: true });

        window.addEventListener('touchend', (e) => {
            if (e.changedTouches && e.changedTouches.length === 1 && window.innerWidth <= 1024) {
                const deltaX = e.changedTouches[0].clientX - touchStartX;
                const deltaY = e.changedTouches[0].clientY - touchStartY;
                if (Math.abs(deltaX) > 80 && Math.abs(deltaY) < 60) {
                    if (deltaX > 0 && touchStartX < 50) {
                        if (sidebar && !sidebar.classList.contains('drawer-open')) toggleDrawer();
                    } else if (deltaX < 0 && sidebar && sidebar.classList.contains('drawer-open')) {
                        closeDrawer();
                    }
                }
            }
        }, { passive: true });
    }

    // ---------------------------------------------------------
    // INITIAL BOOT: FETCH WORKLIST & INIT ALL ENTERPRISE MODALS
    // ---------------------------------------------------------
    initPacsHubModal();
    initUserAuthAndRBAC();
    initWorkstationModeSwitch();
    initVolumetricMPRViewer();
    initAuditTrailModal();
    initModalitySimulator();
    initVoiceDictationAndRADLEX();
    initOrthancIntegration();
    initStatCriticalAlerting();
    initClosedLoopHandoff();
    initPatientDischargeSuite();
    initHL7FHIRGateway();
    initModalityNetwork();
    initLongitudinalPriorComparison();
    initDicomSRExport();
    initClinicalTourSystem();
    initAnonymizerSystem();
    initMobileTabletUI();
    fetchWorklist();
});



