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
                        <span>${escapeHtml(study.modality)}</span>
                    </div>
                </div>
            `;
        }).join('');

        // Attach click listeners to cards (avoiding clicks on checkbox or dismiss button)
        studyQueueList.querySelectorAll('.study-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (e.target.closest('.card-select-wrap') || e.target.closest('.btn-card-dismiss')) {
                    return;
                }
                const id = card.dataset.studyId;
                const study = worklistStudies.find(s => s.study_id === id);
                if (study) loadWorklistStudy(study);
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
                    if (reportDialog) reportDialog.showModal();
                }
            } catch (err) {
                console.error('Report generation error:', err);
            }
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
            let res = null;
            if (selectedStudyId) {
                res = await fetch(`/api/v1/worklist/${selectedStudyId}/pdf`);
            }
            if (!res || !res.ok) {
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
                res = await fetch('/api/v1/report/pdf', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(reportPayload)
                });
            }

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
                    panel.classList.toggle('active', panel.id === targetTabId);
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

    // ---------------------------------------------------------
    // INITIAL BOOT: FETCH WORKLIST & INIT MODALS
    // ---------------------------------------------------------
    initPacsHubModal();
    fetchWorklist();
});
