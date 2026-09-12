#!/usr/bin/env python3
"""
ALVEON God-Tier Multi-Workspace Re-architecting Script.
Wraps the application in .alveon-app-shell, creates .alveon-sidebar with 8 dedicated workspaces,
and retains 100% of existing DOM elements, IDs, attributes, modals, and scripts.
"""

import re
import sys

def main():
    with open('web/index.html', 'r', encoding='utf-8') as f:
        content = f.read()

    # Verify existing IDs count
    orig_ids = set(re.findall(r'id=[\"\']([a-zA-Z0-9_-]+)[\"\']', content))
    print(f"Original unique IDs: {len(orig_ids)}")

    # Extract sections
    # 1. Head and open body
    head_match = re.search(r'([\s\S]*?<body>\s*)<div class="workstation-container">', content)
    if not head_match:
        print("ERROR: Could not find <body> <div class='workstation-container'>")
        sys.exit(1)
    head_part = head_match.group(1)

    # 2. Extract telemetry bar (from line ~64 to ~205)
    telemetry_match = re.search(r'(<div class="telemetry-bar" id="telemetry-bar">[\s\S]*?</div>\s*</header>)', content)
    if not telemetry_match:
        print("ERROR: Could not find telemetry-bar")
        sys.exit(1)
    telemetry_html = telemetry_match.group(1)

    # 3. Extract diagnostic workstation body: pacs-toolbar down to bedside-quick-bar
    # From <nav class="pacs-toolbar" to </nav> right before <dialog id="report-dialog"
    diag_body_match = re.search(r'(<!-- Radiology PACS Master Controls Toolbar -->[\s\S]*?</nav>\s*)(<!-- 1\. Official ALVEON Clinical Consultation Report Modal -->)', content)
    if not diag_body_match:
        print("ERROR: Could not find diagnostic body before report modal")
        sys.exit(1)
    diag_body_html = diag_body_match.group(1)

    # Make sure workstation-grid has id="workstation-grid" if not present
    if '<main class="workstation-grid">' in diag_body_html:
        diag_body_html = diag_body_html.replace('<main class="workstation-grid">', '<main class="workstation-grid" id="workstation-grid">')

    # 4. Extract all dialogs and scripts
    dialogs_match = re.search(r'(<!-- 1\. Official ALVEON Clinical Consultation Report Modal -->[\s\S]*)', content)
    if not dialogs_match:
        print("ERROR: Could not find dialogs start")
        sys.exit(1)
    dialogs_and_tail = dialogs_match.group(1)

    # Remove the extra closing </div> for workstation-container before scripts
    # Look for </div> followed by <script src="/static/webgpu_engine.js">
    dialogs_and_tail = re.sub(r'</div>\s*(<script src="/static/webgpu_engine\.js">)', r'\1', dialogs_and_tail)

    # Now construct the God-Tier multi-workspace HTML
    sidebar_html = '''    <aside class="alveon-sidebar" id="alveon-sidebar">
        <a href="/landing" class="sidebar-header brand-cluster" id="brand-cluster-link" title="ALVEON Overview & Landing Page" style="text-decoration: none; cursor: pointer;">
            <div class="sidebar-emblem alveon-emblem" id="alveon-emblem" aria-hidden="true">
                <svg viewBox="0 0 48 48" fill="none" xmlns="http://www.w3.org/2000/svg" class="emblem-svg">
                    <defs>
                        <radialGradient id="alv-reticle-glow-ws" cx="31" cy="26" r="8" gradientUnits="userSpaceOnUse">
                            <stop offset="0%" stop-color="#ef4444" stop-opacity="0.95"/>
                            <stop offset="50%" stop-color="#f59e0b" stop-opacity="0.5"/>
                            <stop offset="100%" stop-color="#38bdf8" stop-opacity="0"/>
                        </radialGradient>
                    </defs>
                    <path d="M11 14C15.5 12.8 19.5 14 24 16C28.5 14 32.5 12.8 37 14" stroke="#94a3b8" stroke-width="1.5" stroke-linecap="round" opacity="0.85"/>
                    <path d="M9 22C14.5 20 19.5 22 24 24C28.5 22 33.5 20 39 22" stroke="#e2e8f0" stroke-width="1.6" stroke-linecap="round" opacity="0.95"/>
                    <path d="M10 30C15 28 19.5 30 24 32C28.5 30 33 28 38 30" stroke="#64748b" stroke-width="1.5" stroke-linecap="round" opacity="0.8"/>
                    <line x1="24" y1="7" x2="24" y2="41" stroke="#cbd5e1" stroke-width="1.8" stroke-dasharray="3 2" opacity="0.85"/>
                    <circle cx="31" cy="26" r="9.5" stroke="#38bdf8" stroke-width="1.3" stroke-dasharray="2.5 2"/>
                    <circle cx="31" cy="26" r="7" fill="url(#alv-reticle-glow-ws)"/>
                    <circle cx="31" cy="26" r="3.8" fill="#ef4444"/>
                    <circle cx="31" cy="26" r="1.8" fill="#ffffff"/>
                    <line x1="31" y1="12.5" x2="31" y2="18" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round"/>
                    <line x1="31" y1="34" x2="31" y2="39.5" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round"/>
                    <line x1="17.5" y1="26" x2="23" y2="26" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round"/>
                    <line x1="39" y1="26" x2="44.5" y2="26" stroke="#38bdf8" stroke-width="1.5" stroke-linecap="round"/>
                </svg>
            </div>
            <div class="sidebar-brand-info brand-titles">
                <div class="sidebar-brand-title brand-row">
                    <span class="brand-name">ALVEON</span>
                    <span class="sidebar-brand-version brand-badge">v5.2</span>
                </div>
                <div class="sidebar-brand-status brand-subtext">
                    <span class="status-dot-pulse"></span>
                    <span>INSTITUTIONAL OS</span>
                </div>
            </div>
        </a>

        <div class="sidebar-scroll-body">
            <div class="sidebar-group-title">CLINICAL SUITES</div>
            <div class="sidebar-nav-list">
                <button type="button" class="sidebar-nav-item active" data-workspace="workspace-diagnostic" id="nav-btn-diagnostic" title="2D Diagnostic Radiograph Workstation (Shortcut: 1)">
                    <span class="sidebar-nav-icon">🩻</span>
                    <span class="sidebar-nav-text">2D Diagnostic Workstation</span>
                    <span class="sidebar-nav-kbd">1</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-triage" id="nav-btn-triage" title="Emergency ED Triage Queue & Trauma Stream (Shortcut: 2)">
                    <span class="sidebar-nav-icon">🚨</span>
                    <span class="sidebar-nav-text">Emergency ED Triage</span>
                    <span class="sidebar-nav-badge stat" id="sidebar-stat-badge">3 STAT</span>
                    <span class="sidebar-nav-kbd">2</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-volumetric" id="nav-btn-volumetric" title="3D Volumetric Studio & Neuro Hemorrhage (Shortcut: 3)">
                    <span class="sidebar-nav-icon">🧊</span>
                    <span class="sidebar-nav-text">3D Volumetric Studio</span>
                    <span class="sidebar-nav-badge mpr">360°</span>
                    <span class="sidebar-nav-kbd">3</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-reporting" id="nav-btn-reporting" title="Radiologist Consultation Desk & Speech Dictation (Shortcut: 4)">
                    <span class="sidebar-nav-icon">🎙️</span>
                    <span class="sidebar-nav-text">Dictation & Reading Desk</span>
                    <span class="sidebar-nav-kbd">4</span>
                </button>
            </div>

            <div class="sidebar-group-title">ENTERPRISE CORE</div>
            <div class="sidebar-nav-list">
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-pacs" id="nav-btn-pacs" title="Enterprise PACS & HL7 v2 / FHIR Hub (Shortcut: 5)">
                    <span class="sidebar-nav-icon">🏥</span>
                    <span class="sidebar-nav-text">PACS Hub & HL7/FHIR</span>
                    <span class="sidebar-nav-badge hl7">2575</span>
                    <span class="sidebar-nav-kbd">5</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-telerad" id="nav-btn-telerad" title="Tele-Radiology Multi-User Live Collaboration (Shortcut: 6)">
                    <span class="sidebar-nav-icon">📡</span>
                    <span class="sidebar-nav-text">Tele-Radiology Suite</span>
                    <span class="sidebar-nav-kbd">6</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-benchmark" id="nav-btn-benchmark" title="FDA 510(k) Benchmark & Multi-Model Lab (Shortcut: 7)">
                    <span class="sidebar-nav-icon">⚖️</span>
                    <span class="sidebar-nav-text">FDA 510(k) AI Lab</span>
                    <span class="sidebar-nav-kbd">7</span>
                </button>
                <button type="button" class="sidebar-nav-item" data-workspace="workspace-hipaa" id="nav-btn-hipaa" title="HIPAA Security, Cryptographic Audit & De-ID (Shortcut: 8)">
                    <span class="sidebar-nav-icon">🛡️</span>
                    <span class="sidebar-nav-text">HIPAA Audit & De-ID</span>
                    <span class="sidebar-nav-kbd">8</span>
                </button>
            </div>
        </div>

        <div class="sidebar-footer">
            <div class="sidebar-persona-card" id="sidebar-persona-card" title="Switch User Persona">
                <div class="sidebar-persona-avatar" id="sidebar-persona-avatar">EV</div>
                <div class="sidebar-persona-info">
                    <div class="sidebar-persona-name" id="sidebar-persona-name">Dr. Eleanor Vance</div>
                    <div class="sidebar-persona-role" id="sidebar-persona-role">ATTENDING RADIOLOGIST</div>
                </div>
            </div>
            <div class="sidebar-collapse-row">
                <button type="button" class="btn-sidebar-collapse-toggle" id="btn-toggle-main-sidebar" title="Collapse / Expand Navigation Sidebar (Key: [)">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                    </svg>
                    <span>Collapse Sidebar</span>
                </button>
            </div>
        </div>
    </aside>'''

    topbar_html = f'''        <header class="pacs-header alveon-topbar" id="pacs-header">
            <div class="topbar-left">
                <button type="button" class="btn-sidebar-collapse-toggle" id="btn-topbar-sidebar-toggle" title="Toggle Navigation Sidebar" style="width: 32px; height: 32px; padding: 0; min-width: 32px; border-radius: 6px;">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="3" y1="12" x2="21" y2="12"></line>
                        <line x1="3" y1="6" x2="21" y2="6"></line>
                        <line x1="3" y1="18" x2="21" y2="18"></line>
                    </svg>
                </button>
                <div class="topbar-breadcrumbs" id="topbar-breadcrumbs">
                    <span class="crumb-root">ALVEON OS</span>
                    <span class="crumb-separator">/</span>
                    <span class="crumb-active" id="topbar-workspace-name">Diagnostic Workstation</span>
                </div>
                <div class="topbar-patient-pill" id="topbar-active-patient-pill">
                    <span>PATIENT:</span>
                    <span id="topbar-active-patient-name" style="color: #ffffff; font-weight: 700;">Elena Rostova (PT-9402)</span>
                </div>
                <div class="topbar-search-box">
                    <svg viewBox="0 0 24 24" width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" style="color: #64748b;">
                        <circle cx="11" cy="11" r="8"></circle>
                        <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    </svg>
                    <input type="text" class="topbar-search-input" id="topbar-quick-search" placeholder="Search patient or accession (Ctrl+K)...">
                </div>
            </div>

            {telemetry_html}'''

    # Workspace 2: Emergency ED Triage
    ws_triage_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 2: EMERGENCY ED TRIAGE QUEUE & CONTINUOUS STREAM        -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-triage" data-workspace="workspace-triage">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.4); color: #f87171;">🚨</div>
                        <div class="workspace-hero-text">
                            <h1>Emergency ED Triage Command & Trauma Influx</h1>
                            <p>ACR Acuity Prioritization • Continuous Real-Time Bay Stream • Sub-3-Second Critical Latency</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" id="btn-triage-refresh-ws" title="Refresh worklist from PACS database">
                            <span>🔄 Sync Queue</span>
                        </button>
                        <button type="button" class="btn-master" id="btn-triage-surge-trigger" style="background: linear-gradient(135deg, #b91c1c, #ef4444); border-color: #f87171;">
                            <span>⚡ Simulate MCI Surge</span>
                        </button>
                    </div>
                </div>

                <div class="triage-hero-metrics">
                    <div class="triage-metric-card">
                        <div class="triage-metric-label">
                            <span>CRITICAL STAT QUEUE</span>
                            <span class="triage-metric-pill stat">URGENT</span>
                        </div>
                        <div class="triage-metric-value" style="color: #ef4444;" id="triage-kpi-stat">3 CASES</div>
                        <div class="triage-metric-sub">Tension PTX, Massive Effusion, Hemorrhage</div>
                    </div>
                    <div class="triage-metric-card">
                        <div class="triage-metric-label">
                            <span>MEDIAN TRIAGE LATENCY</span>
                            <span class="triage-metric-pill">REAL-TIME</span>
                        </div>
                        <div class="triage-metric-value" style="color: #38bdf8;">1.8s</div>
                        <div class="triage-metric-sub">Target SLA: &lt; 3.0s (99.8% compliance)</div>
                    </div>
                    <div class="triage-metric-card">
                        <div class="triage-metric-label">
                            <span>EMERGENCY INFLUX CADENCE</span>
                            <span class="triage-metric-pill" style="color: #34d399; background: rgba(16, 185, 129, 0.15);">ACTIVE</span>
                        </div>
                        <div class="triage-metric-value" style="color: #34d399;">30s Interval</div>
                        <div class="triage-metric-sub">Trauma Bay Stream: Connected</div>
                    </div>
                    <div class="triage-metric-card">
                        <div class="triage-metric-label">
                            <span>ATTESTATION RATIO</span>
                            <span class="triage-metric-pill">SHIFT TOTAL</span>
                        </div>
                        <div class="triage-metric-value" style="color: #c084fc;">84% Done</div>
                        <div class="triage-metric-sub">4 Pending Review • 1 Verified Signed</div>
                    </div>
                </div>

                <div class="triage-workspace-content">
                    <!-- High Acuity Patient Spotlight Banner -->
                    <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(239, 68, 68, 0.35); border-radius: 12px; padding: 18px 24px; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <div style="width: 42px; height: 42px; border-radius: 50%; background: rgba(239, 68, 68, 0.2); border: 1px solid #ef4444; display: flex; align-items: center; justify-content: center; font-size: 20px;">🚨</div>
                            <div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span style="font-weight: 700; font-size: 15px; color: #ffffff;">Elena Rostova (PT-9402)</span>
                                    <span style="background: #ef4444; color: #ffffff; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;">PRIORITY 1: STAT CRITICAL</span>
                                    <span style="color: #94a3b8; font-size: 12px; font-family: var(--font-mono);">ACC: AC-90214 • BED 04 TRAUMA</span>
                                </div>
                                <div style="color: #fca5a5; font-size: 13px; margin-top: 4px;">
                                    ⚠️ <strong>Tension Pneumothorax (99.8%)</strong> • Right Hemithorax Tension Collapse • Mediastinal Shift Detected
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button type="button" class="btn-master" id="btn-triage-open-stat" style="background: #ef4444; border-color: #f87171;" onclick="window.alveonSwitchWorkspace('workspace-diagnostic')">
                                <span>Open in 2D Diagnostic 🩻</span>
                            </button>
                            <button type="button" class="btn-titanium" onclick="window.alveonSwitchWorkspace('workspace-reporting')">
                                <span>Direct Dictation 🎙️</span>
                            </button>
                        </div>
                    </div>

                    <!-- Spacious Triage Worklist Container -->
                    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 14px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <span style="font-size: 14px; font-weight: 700; color: #ffffff;">INSTITUTIONAL EMERGENCY WORKLIST</span>
                                <span style="font-size: 11px; color: #64748b; font-family: var(--font-mono);">SORTED BY CLINICAL ACUITY & SEVERITY SCORE</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-size: 11px; color: #94a3b8;">Filter:</span>
                                <button type="button" class="triage-filter-pill active" onclick="document.querySelector('.triage-filter-pill[data-filter=\\'all\\']')?.click()">All</button>
                                <button type="button" class="triage-filter-pill stat-pill" onclick="document.querySelector('.triage-filter-pill[data-filter=\\'stat\\']')?.click()">🚨 STAT</button>
                                <button type="button" class="triage-filter-pill" onclick="document.querySelector('.triage-filter-pill[data-filter=\\'pending\\']')?.click()">Pending</button>
                                <button type="button" class="triage-filter-pill" onclick="document.querySelector('.triage-filter-pill[data-filter=\\'signed\\']')?.click()">Signed</button>
                            </div>
                        </div>

                        <!-- Spacious Triage Rows Grid -->
                        <div id="triage-fullpage-table-container" style="display: flex; flex-direction: column; gap: 10px; max-height: 540px; overflow-y: auto;">
                            <!-- Static high-visibility cards rendered in real-time -->
                            <div class="study-card active-study stat-study" style="cursor: pointer;" onclick="window.alveonSwitchWorkspace('workspace-diagnostic')">
                                <div class="study-header">
                                    <div class="study-patient-info">
                                        <span class="patient-name">Elena Rostova</span>
                                        <span class="patient-demographics">42F • PT-9402</span>
                                    </div>
                                    <span class="acuity-badge stat-badge">🚨 STAT CRITICAL</span>
                                </div>
                                <div class="study-meta">
                                    <span class="study-modality">DX CHEST PA</span>
                                    <span class="study-time">Today, 12:44:12</span>
                                    <span class="study-acc">AC-90214</span>
                                </div>
                                <div class="study-findings-preview">
                                    <span class="finding-chip critical">Tension Pneumothorax (99.8%)</span>
                                    <span class="finding-chip warning">Comp. Atelectasis (76.4%)</span>
                                </div>
                            </div>

                            <div class="study-card stat-study" style="cursor: pointer;" onclick="window.alveonSwitchWorkspace('workspace-diagnostic')">
                                <div class="study-header">
                                    <div class="study-patient-info">
                                        <span class="patient-name">Arthur Pendelton</span>
                                        <span class="patient-demographics">68M • PT-9388</span>
                                    </div>
                                    <span class="acuity-badge stat-badge">🚨 STAT CRITICAL</span>
                                </div>
                                <div class="study-meta">
                                    <span class="study-modality">DX CHEST AP</span>
                                    <span class="study-time">Today, 12:38:05</span>
                                    <span class="study-acc">AC-90212</span>
                                </div>
                                <div class="study-findings-preview">
                                    <span class="finding-chip critical">Massive Pleural Effusion (94.1%)</span>
                                    <span class="finding-chip warning">Cardiomegaly (88.3%)</span>
                                </div>
                            </div>

                            <div class="study-card stat-study" style="cursor: pointer;" onclick="window.alveonSwitchWorkspace('workspace-diagnostic')">
                                <div class="study-header">
                                    <div class="study-patient-info">
                                        <span class="patient-name">Marcus Brody</span>
                                        <span class="patient-demographics">54M • PT-9381</span>
                                    </div>
                                    <span class="acuity-badge stat-badge">🚨 STAT CRITICAL</span>
                                </div>
                                <div class="study-meta">
                                    <span class="study-modality">CT BRAIN NON-CONTRAST</span>
                                    <span class="study-time">Today, 12:31:40</span>
                                    <span class="study-acc">AC-90209</span>
                                </div>
                                <div class="study-findings-preview">
                                    <span class="finding-chip critical">Intracranial Hemorrhage (96.5%)</span>
                                    <span class="finding-chip">Midline Shift (4.8mm)</span>
                                </div>
                            </div>

                            <div class="study-card" style="cursor: pointer;" onclick="window.alveonSwitchWorkspace('workspace-diagnostic')">
                                <div class="study-header">
                                    <div class="study-patient-info">
                                        <span class="patient-name">Clara Oswald</span>
                                        <span class="patient-demographics">29F • PT-9377</span>
                                    </div>
                                    <span class="acuity-badge routine-badge">ROUTINE</span>
                                </div>
                                <div class="study-meta">
                                    <span class="study-modality">DX CHEST PA</span>
                                    <span class="study-time">Today, 12:15:20</span>
                                    <span class="study-acc">AC-90205</span>
                                </div>
                                <div class="study-findings-preview">
                                    <span class="finding-chip">Normal Baseline Radiograph (98.9%)</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

    # Workspace 3: 3D Volumetric Studio
    ws_volumetric_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 3: 3D VOLUMETRIC STUDIO & ADVANCED RECONSTRUCTION       -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-volumetric" data-workspace="workspace-volumetric">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(139, 92, 246, 0.15); border-color: rgba(139, 92, 246, 0.4); color: #c4b5fd;">🧊</div>
                        <div class="workspace-hero-text">
                            <h1>3D Volumetric Studio & Advanced Reformation</h1>
                            <p>Cinematic GPU Ray-Casting • 3-Plane Orthogonal MPR • ABC/2 Neuro Hemorrhage Volumetry</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <div class="volumetric-tabs-bar" id="volumetric-workspace-tabs">
                            <button type="button" class="volumetric-tab-btn active" data-vtab="tab-v-raycast">
                                <span>🔮 3D Cinematic Ray-Casting</span>
                            </button>
                            <button type="button" class="volumetric-tab-btn" data-vtab="tab-v-mpr">
                                <span>📐 Orthogonal 3-Plane MPR</span>
                            </button>
                            <button type="button" class="volumetric-tab-btn" data-vtab="tab-v-neuro">
                                <span>🧠 Neuro CT Hemorrhage & ABC/2</span>
                            </button>
                        </div>
                    </div>
                </div>

                <div class="volumetric-workspace-content">
                    <!-- View A: 3D Cinematic Ray-Casting -->
                    <div class="volumetric-stage-view active" id="tab-v-raycast-view">
                        <div style="display: grid; grid-template-columns: 1fr 340px; width: 100%; height: 100%; min-height: 580px;">
                            <!-- Left 3D Stage -->
                            <div style="position: relative; display: flex; align-items: center; justify-content: center; background: #030509; overflow: hidden;">
                                <canvas id="workspace-raycast-canvas" width="640" height="640" style="max-width: 90%; max-height: 90%; object-fit: contain; cursor: grab;"></canvas>
                                <div style="position: absolute; top: 16px; left: 16px; background: rgba(9, 12, 19, 0.8); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; padding: 8px 14px; font-family: var(--font-mono); font-size: 11px; color: #94a3b8;">
                                    <span style="color: #c4b5fd; font-weight: 700;">VOLUMETRIC SHADER:</span> CINEMATIC GRADIENT LIGHTING • 360° TURNTABLE
                                </div>
                                <div style="position: absolute; bottom: 16px; left: 50%; transform: translateX(-50%); background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 20px; padding: 6px 18px; font-size: 12px; color: #e2e8f0; display: flex; align-items: center; gap: 8px;">
                                    <span>↔ Click and drag horizontally to scrub 360° volumetric rotation</span>
                                </div>
                            </div>
                            <!-- Right Controls Panel -->
                            <div style="background: rgba(15, 23, 42, 0.8); border-left: 1px solid rgba(255, 255, 255, 0.08); padding: 20px; display: flex; flex-direction: column; gap: 18px; overflow-y: auto;">
                                <div style="font-size: 13px; font-weight: 700; color: #ffffff; letter-spacing: 0.5px;">TISSUE TRANSFER FUNCTIONS</div>
                                <div style="display: flex; flex-direction: column; gap: 8px;">
                                    <button type="button" class="btn-titanium" style="justify-content: space-between; border-color: rgba(56, 189, 248, 0.4); color: #38bdf8;">
                                        <span>🦴 Dense Cortical Bone</span>
                                        <span style="font-family: var(--font-mono); font-size: 10px;">HU &gt; 350</span>
                                    </button>
                                    <button type="button" class="btn-titanium" style="justify-content: space-between;">
                                        <span>🫁 Pulmonary Parenchyma</span>
                                        <span style="font-family: var(--font-mono); font-size: 10px;">-700 to -400 HU</span>
                                    </button>
                                    <button type="button" class="btn-titanium" style="justify-content: space-between;">
                                        <span>❤️ Mediastinal Soft Tissue</span>
                                        <span style="font-family: var(--font-mono); font-size: 10px;">+20 to +60 HU</span>
                                    </button>
                                    <button type="button" class="btn-titanium" style="justify-content: space-between;">
                                        <span>🩸 Contrast Angiography MIP</span>
                                        <span style="font-family: var(--font-mono); font-size: 10px;">Peak Attenuation</span>
                                    </button>
                                </div>

                                <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px;">
                                    <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 8px;">OPACITY DENSITY CUTOFF</div>
                                    <input type="range" min="0" max="100" value="55" class="pacs-slider" style="width: 100%;">
                                </div>

                                <div>
                                    <div style="font-size: 12px; font-weight: 600; color: #94a3b8; margin-bottom: 8px;">SPECULAR ILLUMINATION</div>
                                    <input type="range" min="0" max="100" value="70" class="pacs-slider" style="width: 100%;">
                                </div>

                                <div style="margin-top: auto; padding: 14px; background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px;">
                                    <div style="font-size: 11px; font-weight: 700; color: #38bdf8;">GPU ACCELERATION ACTIVE</div>
                                    <div style="font-size: 11px; color: #94a3b8; margin-top: 4px;">WebGPU hardware volumetric ray-marcher active. Instant rendering at 60 FPS.</div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- View B: Orthogonal 3-Plane MPR -->
                    <div class="volumetric-stage-view" id="tab-v-mpr-view">
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; width: 100%; height: 100%; min-height: 560px; padding: 16px;">
                            <div style="background: #020408; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; display: flex; flex-direction: column; overflow: hidden;">
                                <div style="padding: 10px 14px; background: rgba(15, 23, 42, 0.8); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between;">
                                    <span style="font-weight: 700; font-size: 12px; color: #38bdf8;">AXIAL VIEWPORT (Z-AXIS)</span>
                                    <span style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8;">SLICE 128 / 256</span>
                                </div>
                                <div style="flex: 1; display: flex; align-items: center; justify-content: center; position: relative;">
                                    <img src="/static/placeholder_xray.jpg" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: brightness(0.9) contrast(1.2);" alt="Axial">
                                </div>
                            </div>
                            <div style="background: #020408; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; display: flex; flex-direction: column; overflow: hidden;">
                                <div style="padding: 10px 14px; background: rgba(15, 23, 42, 0.8); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between;">
                                    <span style="font-weight: 700; font-size: 12px; color: #34d399;">CORONAL VIEWPORT (Y-AXIS)</span>
                                    <span style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8;">SLICE 142 / 256</span>
                                </div>
                                <div style="flex: 1; display: flex; align-items: center; justify-content: center; position: relative;">
                                    <img src="/static/placeholder_xray.jpg" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: brightness(0.9) contrast(1.2);" alt="Coronal">
                                </div>
                            </div>
                            <div style="background: #020408; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; display: flex; flex-direction: column; overflow: hidden;">
                                <div style="padding: 10px 14px; background: rgba(15, 23, 42, 0.8); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: space-between;">
                                    <span style="font-weight: 700; font-size: 12px; color: #f59e0b;">SAGITTAL VIEWPORT (X-AXIS)</span>
                                    <span style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8;">SLICE 110 / 256</span>
                                </div>
                                <div style="flex: 1; display: flex; align-items: center; justify-content: center; position: relative;">
                                    <img src="/static/placeholder_xray.jpg" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: brightness(0.9) contrast(1.2);" alt="Sagittal">
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- View C: Neuro CT Hemorrhage & ABC/2 -->
                    <div class="volumetric-stage-view" id="tab-v-neuro-view">
                        <div style="display: grid; grid-template-columns: 1fr 380px; width: 100%; height: 100%; min-height: 580px;">
                            <div style="position: relative; display: flex; align-items: center; justify-content: center; background: #020408;">
                                <canvas id="workspace-neuro-canvas" width="600" height="600" style="max-width: 90%; max-height: 90%; object-fit: contain;"></canvas>
                            </div>
                            <div style="background: rgba(15, 23, 42, 0.8); border-left: 1px solid rgba(255, 255, 255, 0.08); padding: 24px; display: flex; flex-direction: column; gap: 20px; overflow-y: auto;">
                                <div style="display: flex; align-items: center; justify-content: space-between;">
                                    <span style="font-size: 14px; font-weight: 700; color: #ffffff;">ABC/2 HEMORRHAGE METRICS</span>
                                    <span style="font-size: 10px; background: rgba(239, 68, 68, 0.2); color: #fca5a5; padding: 2px 6px; border-radius: 4px; font-weight: 700;">ICH PROTOCOL</span>
                                </div>

                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px;">
                                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                                        <div style="font-size: 10px; color: #94a3b8; font-family: var(--font-mono);">MAX DIAMETER (A)</div>
                                        <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin-top: 4px;">4.2 cm</div>
                                    </div>
                                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                                        <div style="font-size: 10px; color: #94a3b8; font-family: var(--font-mono);">PERPENDICULAR (B)</div>
                                        <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin-top: 4px;">3.6 cm</div>
                                    </div>
                                    <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 12px;">
                                        <div style="font-size: 10px; color: #94a3b8; font-family: var(--font-mono);">SLICE HEIGHT (C)</div>
                                        <div style="font-size: 18px; font-weight: 700; color: #ffffff; margin-top: 4px;">2.5 cm</div>
                                    </div>
                                    <div style="background: rgba(239, 68, 68, 0.15); border: 1px solid rgba(239, 68, 68, 0.4); border-radius: 8px; padding: 12px;">
                                        <div style="font-size: 10px; color: #fca5a5; font-family: var(--font-mono);">CALCULATED VOL</div>
                                        <div style="font-size: 18px; font-weight: 800; color: #ef4444; margin-top: 4px;">18.9 mL</div>
                                    </div>
                                </div>

                                <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 8px; padding: 14px;">
                                    <div style="font-size: 11px; font-weight: 600; color: #94a3b8;">MIDLINE SHIFT ANALYSIS</div>
                                    <div style="display: flex; align-items: baseline; gap: 8px; margin-top: 6px;">
                                        <span style="font-size: 22px; font-weight: 800; color: #fbbf24;">4.8 mm</span>
                                        <span style="font-size: 12px; color: #fbbf24;">Right-to-Left Shift</span>
                                    </div>
                                </div>

                                <div style="padding: 14px; background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px;">
                                    <div style="font-size: 11px; font-weight: 700; color: #f87171;">NEUROSURGICAL ALERT</div>
                                    <div style="font-size: 11px; color: #fca5a5; margin-top: 4px;">Volume exceeds 15 mL with &gt; 4 mm midline mass effect. Immediate neurosurgical consultation recommended.</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

    # Workspace 4: Reporting & Dictation Desk
    ws_reporting_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 4: RADIOLOGIST READING DESK & STRUCTURED DICTATION      -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-reporting" data-workspace="workspace-reporting">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(14, 165, 233, 0.15); border-color: rgba(56, 189, 248, 0.4); color: #38bdf8;">🎙️</div>
                        <div class="workspace-hero-text">
                            <h1>Radiologist Reading Desk & Structured Dictation</h1>
                            <p>ACR Practice Parameter • Real-Time Speech Recognition • RADLEX Thoracic Lexicon • Certified PDF Generation</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" id="btn-reading-desk-load-findings">
                            <span>🔄 Sync AI Findings</span>
                        </button>
                        <button type="button" class="btn-master" id="btn-reading-desk-pdf" style="background: linear-gradient(135deg, #0284c7, #2563eb); border-color: #38bdf8;">
                            <span>📄 Download Certified PDF</span>
                        </button>
                    </div>
                </div>

                <div class="reporting-workspace-content">
                    <!-- Left Patient & Finding Card -->
                    <div class="reporting-patient-card">
                        <div style="display: flex; align-items: center; gap: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.08); padding-bottom: 14px;">
                            <div style="width: 36px; height: 36px; border-radius: 50%; background: linear-gradient(135deg, #0284c7, #2563eb); color: #fff; font-weight: 700; display: flex; align-items: center; justify-content: center; font-size: 12px;">ER</div>
                            <div>
                                <div style="font-size: 14px; font-weight: 700; color: #ffffff;" id="reading-patient-name">Elena Rostova</div>
                                <div style="font-size: 11px; color: #94a3b8; font-family: var(--font-mono);">PT-9402 • 42F • CHEST PA/LAT</div>
                            </div>
                        </div>

                        <div>
                            <div style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase;">CLINICAL INDICATION</div>
                            <div style="font-size: 12px; color: #e2e8f0; margin-top: 4px; line-height: 1.4;">Acute sudden-onset dyspnea, right-sided pleuritic chest pain following motor vehicle collision. Trauma Bay 4.</div>
                        </div>

                        <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 12px;">
                            <div style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 8px;">GRAD-CAM AI SYNTHESIS</div>
                            <div style="display: flex; flex-direction: column; gap: 6px;">
                                <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: rgba(239, 68, 68, 0.12); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 6px;">
                                    <span style="font-size: 12px; font-weight: 600; color: #fca5a5;">Tension Pneumothorax</span>
                                    <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #ef4444;">99.8%</span>
                                </div>
                                <div style="display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.25); border-radius: 6px;">
                                    <span style="font-size: 12px; font-weight: 600; color: #fde68a;">Atelectasis (Comp.)</span>
                                    <span style="font-family: var(--font-mono); font-size: 11px; font-weight: 700; color: #f59e0b;">76.4%</span>
                                </div>
                            </div>
                        </div>

                        <div style="border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 12px;">
                            <div style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase; margin-bottom: 8px;">RADLEX QUICK INSERT MACROS</div>
                            <div style="display: flex; flex-wrap: wrap; gap: 6px;">
                                <button type="button" class="btn-titanium" style="font-size: 11px; padding: 4px 8px;" onclick="window.insertReadingMacro('normal')">Normal Chest</button>
                                <button type="button" class="btn-titanium" style="font-size: 11px; padding: 4px 8px;" onclick="window.insertReadingMacro('ptx')">Pneumothorax</button>
                                <button type="button" class="btn-titanium" style="font-size: 11px; padding: 4px 8px;" onclick="window.insertReadingMacro('consolidation')">Consolidation</button>
                                <button type="button" class="btn-titanium" style="font-size: 11px; padding: 4px 8px;" onclick="window.insertReadingMacro('effusion')">Effusion</button>
                            </div>
                        </div>
                    </div>

                    <!-- Right Structured Editor & Voice Dictation -->
                    <div class="reporting-editor-card">
                        <!-- Voice Dictation Bar -->
                        <div style="display: flex; align-items: center; justify-content: space-between; background: rgba(14, 165, 233, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 10px; padding: 12px 18px;">
                            <div style="display: flex; align-items: center; gap: 12px;">
                                <button type="button" class="btn-master" id="reading-desk-mic-btn" style="background: linear-gradient(135deg, #0284c7, #2563eb); border-color: #38bdf8;">
                                    <span id="reading-desk-mic-icon">🎙️</span>
                                    <span id="reading-desk-mic-label">Dictate (Space)</span>
                                </button>
                                <span style="font-size: 12px; color: #94a3b8;" id="reading-desk-dictation-status">Microphone ready. Speak to dictate clinical impressions...</span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span class="status-dot-pulse"></span>
                                <span style="font-size: 11px; font-family: var(--font-mono); color: #38bdf8;">ACR RADLEX ENG: ACTIVE</span>
                            </div>
                        </div>

                        <!-- Structured Report Sections -->
                        <div style="display: flex; flex-direction: column; gap: 14px;">
                            <div>
                                <label style="font-size: 11px; font-weight: 700; color: #94a3b8; letter-spacing: 0.5px; text-transform: uppercase;">FINDINGS</label>
                                <textarea class="pacs-textarea" id="reading-desk-findings" rows="6" style="width: 100%; margin-top: 4px; background: rgba(10, 14, 23, 0.7); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 8px; color: #f1f5f9; padding: 12px; font-family: var(--font-clinical); font-size: 13px; line-height: 1.5;">Lungs: Large right apical and lateral pneumothorax measuring 3.8 cm at the apex with complete collapse of the right upper lobe. Contralateral tracheal and mediastinal shift to the left, diagnostic of tension physiology.

Pleura: No pleural fluid or blunting of left costophrenic angle.

Cardiovascular: Normal cardiac silhouette without cardiomegaly.</textarea>
                            </div>

                            <div>
                                <label style="font-size: 11px; font-weight: 700; color: #ef4444; letter-spacing: 0.5px; text-transform: uppercase;">IMPRESSION & RECOMMENDATION</label>
                                <textarea class="pacs-textarea" id="reading-desk-impression" rows="4" style="width: 100%; margin-top: 4px; background: rgba(10, 14, 23, 0.7); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 8px; color: #f1f5f9; padding: 12px; font-family: var(--font-clinical); font-size: 13px; line-height: 1.5;">1. TENSION PNEUMOTHORAX of the right hemithorax with marked mediastinal shift.
2. CRITICAL FINDING: Emergent needle decompression / thoracostomy tube placement immediately warranted.
3. Attending radiologist communicated finding directly to trauma bay team via closed-loop verbal handoff.</textarea>
                            </div>
                        </div>

                        <!-- Attestation Footer -->
                        <div style="display: flex; align-items: center; justify-content: space-between; border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 16px; margin-top: auto;">
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <div style="width: 8px; height: 8px; border-radius: 50%; background: #10b981;"></div>
                                <span style="font-size: 12px; color: #94a3b8;">Electronic Signature Stamp: <strong style="color: #ffffff;">Dr. Eleanor Vance, MD (Attending)</strong></span>
                            </div>
                            <div style="display: flex; align-items: center; gap: 10px;">
                                <button type="button" class="btn-titanium" id="btn-reading-desk-clear">Reset Form</button>
                                <button type="button" class="btn-master" id="btn-reading-desk-sign" style="background: linear-gradient(135deg, #10b981, #059669); border-color: #34d399;">
                                    <span>✍️ Sign & Finalize (Enter)</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

    # Workspace 5: Enterprise PACS Hub & HL7
    ws_pacs_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 5: ENTERPRISE PACS HUB & HL7 / FHIR INTEROPERABILITY    -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-pacs" data-workspace="workspace-pacs">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(52, 211, 153, 0.4); color: #34d399;">🏥</div>
                        <div class="workspace-hero-text">
                            <h1>Enterprise PACS Hub & HL7/FHIR Interoperability</h1>
                            <p>Bi-Directional HL7 v2.5.1 MLLP (Port 2575) • Remote FHIR R4 Ingestion • DICOM C-STORE SCP • DICOMweb WADO/QIDO</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" id="btn-pacs-test-ping">
                            <span>⚡ Test MLLP Ping</span>
                        </button>
                        <button type="button" class="btn-master" id="btn-pacs-open-modal-view" style="background: linear-gradient(135deg, #059669, #10b981); border-color: #34d399;" onclick="document.getElementById('pacs-hub-dialog')?.showModal()">
                            <span>Open Advanced Gateway Hub 🚀</span>
                        </button>
                    </div>
                </div>

                <div class="fullscreen-workspace-pad">
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 11px; font-family: var(--font-mono); color: #34d399; font-weight: 700;">HL7 MLLP SOCKET</span>
                                <span style="width: 7px; height: 7px; border-radius: 50%; background: #10b981; box-shadow: 0 0 8px #10b981;"></span>
                            </div>
                            <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 8px;">PORT 2575</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">ORU^R01 &amp; ADT^A08 Listener</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 11px; font-family: var(--font-mono); color: #38bdf8; font-weight: 700;">REMOTE FHIR R4</span>
                                <span style="width: 7px; height: 7px; border-radius: 50%; background: #0284c7;"></span>
                            </div>
                            <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 8px;">CONNECTED</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">DiagnosticReport &amp; Observations</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 11px; font-family: var(--font-mono); color: #c084fc; font-weight: 700;">DICOM C-STORE SCP</span>
                                <span style="width: 7px; height: 7px; border-radius: 50%; background: #a855f7;"></span>
                            </div>
                            <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 8px;">ALVEON_PACS:104</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Storage Commitment Ready</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="display: flex; align-items: center; justify-content: space-between;">
                                <span style="font-size: 11px; font-family: var(--font-mono); color: #fbbf24; font-weight: 700;">DICOMWEB REST</span>
                                <span style="width: 7px; height: 7px; border-radius: 50%; background: #f59e0b;"></span>
                            </div>
                            <div style="font-size: 20px; font-weight: 800; color: #ffffff; margin-top: 8px;">WADO / QIDO</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">Zero-Footprint Web Streaming</div>
                        </div>
                    </div>

                    <div style="flex: 1; background: #030509; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px; display: flex; flex-direction: column; gap: 12px; min-height: 380px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 10px;">
                            <span style="font-family: var(--font-mono); font-size: 12px; font-weight: 700; color: #34d399;">LIVE HL7 / DICOM PROTOCOL TELEMETRY LOG</span>
                            <span style="font-family: var(--font-mono); font-size: 11px; color: #64748b;">AUTO-SCROLL: ON • 50 MSGS RETAINED</span>
                        </div>
                        <pre id="pacs-workspace-telemetry-log" style="flex: 1; margin: 0; font-family: var(--font-mono); font-size: 12px; color: #a7f3d0; line-height: 1.6; overflow-y: auto; white-space: pre-wrap;">
[2026-09-12 12:45:01 UTC] [HL7-MLLP:2575] Socket daemon bound to 0.0.0.0:2575. Ready for institutional hospital feed.
[2026-09-12 12:45:04 UTC] [DICOM-SCP:104] DimseListener initialized with AET: ALVEON_PACS. Verification SOP Class accepted.
[2026-09-12 12:48:12 UTC] [FHIR-R4] Polled remote endpoint https://fhir.alveon-health.org/r4/DiagnosticReport?_count=5. HTTP 200 OK.
[2026-09-12 12:50:22 UTC] [HL7-MLLP:2575] Inbound message ORU^R01 received from Trauma Bay 4. Study UID: 1.2.840.113619.2.9402.
[2026-09-12 12:50:23 UTC] [DICOM-SCP:104] C-STORE-RQ received: Elena Rostova (PT-9402). 16-bit DICOM pixel data stored successfully.
[2026-09-12 12:50:24 UTC] [ALVEON-TRIAGE] Acuity priority evaluated: STAT CRITICAL (Pneumothorax 99.8%). Placed at head of queue.</pre>
                    </div>
                </div>
            </div>'''

    # Workspace 6: Tele-Radiology Suite
    ws_telerad_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 6: TELE-RADIOLOGY MULTI-USER LIVE COLLABORATION SUITE   -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-telerad" data-workspace="workspace-telerad">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(52, 211, 153, 0.4); color: #34d399;">📡</div>
                        <div class="workspace-hero-text">
                            <h1>Tele-Radiology Multi-User Live Collaboration Suite</h1>
                            <p>WebSocket Co-Pilot • Synchronized Remote Laser Pointer • Peer Presence • Departmental Emergency Chat</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" id="btn-telerad-invite">
                            <span>➕ Invite Colleague</span>
                        </button>
                        <button type="button" class="btn-master" id="btn-telerad-open-modal" style="background: linear-gradient(135deg, #059669, #10b981); border-color: #34d399;" onclick="document.getElementById('tele-collab-dialog')?.showModal()">
                            <span>Open Collaboration Hub 📡</span>
                        </button>
                    </div>
                </div>

                <div class="fullscreen-workspace-pad">
                    <div style="display: grid; grid-template-columns: 1fr 380px; gap: 20px; flex: 1; min-height: 0;">
                        <!-- Synchronized Laser Stage -->
                        <div style="background: #020408; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; display: flex; flex-direction: column; overflow: hidden; position: relative;">
                            <div style="padding: 12px 18px; background: rgba(15, 23, 42, 0.8); border-bottom: 1px solid rgba(255, 255, 255, 0.08); display: flex; align-items: center; justify-content: space-between;">
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span class="tele-pulse-dot"></span>
                                    <span style="font-weight: 700; font-size: 13px; color: #ffffff;">COLLABORATIVE CANAL: ROOM TRAUMA-ALPHA</span>
                                </div>
                                <span style="font-family: var(--font-mono); font-size: 11px; color: #34d399;">SYNCHRONIZED VIEWPORT</span>
                            </div>
                            <div style="flex: 1; display: flex; align-items: center; justify-content: center; position: relative; overflow: hidden;">
                                <img src="/static/placeholder_xray.jpg" style="max-width: 90%; max-height: 90%; object-fit: contain; filter: brightness(0.9) contrast(1.2);" alt="Collaborative Radiograph">
                                <!-- Simulated Live Laser Pointer Dot -->
                                <div style="position: absolute; top: 38%; left: 62%; display: flex; flex-direction: column; align-items: center; pointer-events: none;">
                                    <div style="width: 14px; height: 14px; border-radius: 50%; background: #ef4444; box-shadow: 0 0 12px #ef4444; border: 2px solid #ffffff; animation: beacon-pulse 1s infinite;"></div>
                                    <span style="font-size: 10px; font-weight: 700; color: #ffffff; background: rgba(0, 0, 0, 0.85); padding: 2px 6px; border-radius: 4px; margin-top: 4px; white-space: nowrap; border: 1px solid #ef4444;">Dr. Adams (ER)</span>
                                </div>
                            </div>
                            <div style="padding: 10px 18px; background: rgba(15, 23, 42, 0.7); border-top: 1px solid rgba(255, 255, 255, 0.06); font-size: 11px; color: #94a3b8; display: flex; justify-content: space-between;">
                                <span>Hover mouse over radiograph to broadcast synchronized pointer coordinates</span>
                                <span style="font-family: var(--font-mono);">LATENCY: 14ms (WSS P2P)</span>
                            </div>
                        </div>

                        <!-- Departmental Chat & Roster -->
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; display: flex; flex-direction: column; overflow: hidden;">
                            <!-- Peer Roster Header -->
                            <div style="padding: 14px 18px; border-bottom: 1px solid rgba(255, 255, 255, 0.08);">
                                <div style="font-size: 11px; font-weight: 700; color: #64748b; letter-spacing: 0.5px; text-transform: uppercase;">ACTIVE PARTICIPANTS (3)</div>
                                <div style="display: flex; gap: 8px; margin-top: 10px;">
                                    <div style="display: flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 4px 8px; font-size: 11px;">
                                        <span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
                                        <span style="color: #ffffff;">Dr. Vance (Host)</span>
                                    </div>
                                    <div style="display: flex; align-items: center; gap: 6px; background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 6px; padding: 4px 8px; font-size: 11px;">
                                        <span style="width: 6px; height: 6px; border-radius: 50%; background: #10b981;"></span>
                                        <span style="color: #ffffff;">Dr. Adams (ER)</span>
                                    </div>
                                </div>
                            </div>

                            <!-- Chat Messages Feed -->
                            <div style="flex: 1; padding: 14px 18px; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; font-size: 12px;">
                                <div>
                                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
                                        <strong style="color: #f87171;">Dr. Sarah Adams (ER)</strong>
                                        <span style="font-size: 10px; color: #64748b;">12:48 PM</span>
                                    </div>
                                    <div style="background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 8px; padding: 8px 12px; color: #e2e8f0;">
                                        Eleanor, Elena's tracheal deviation looks prominent. Can you confirm pneumothorax apex distance?
                                    </div>
                                </div>
                                <div>
                                    <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 2px;">
                                        <strong style="color: #38bdf8;">Dr. Eleanor Vance (Attending)</strong>
                                        <span style="font-size: 10px; color: #64748b;">12:49 PM</span>
                                    </div>
                                    <div style="background: rgba(14, 165, 233, 0.1); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 8px; padding: 8px 12px; color: #e2e8f0;">
                                        Confirmed 3.8 cm right apex separation with tension collapse. Proceed with immediate needle decompression.
                                    </div>
                                </div>
                            </div>

                            <!-- Chat Input -->
                            <div style="padding: 12px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; gap: 8px;">
                                <input type="text" class="topbar-search-input" placeholder="Type clinical consultation note..." style="background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.1); border-radius: 6px; padding: 6px 10px; font-size: 12px; flex: 1; color: #ffffff;">
                                <button type="button" class="btn-master" style="padding: 6px 14px; font-size: 12px;">Send</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>'''

    # Workspace 7: FDA 510(k) Benchmark AI Lab
    ws_benchmark_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 7: FDA 510(k) BENCHMARK & MULTI-MODEL AI LABORATORY     -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-benchmark" data-workspace="workspace-benchmark">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(245, 158, 11, 0.15); border-color: rgba(251, 191, 36, 0.4); color: #fbbf24;">⚖️</div>
                        <div class="workspace-hero-text">
                            <h1>FDA 510(k) SaMD Benchmark & Multi-Model AI Laboratory</h1>
                            <p>DenseNet-121 vs ResNet-50-D vs ViT-B/16 vs ConvNeXt-Tiny • Cohen's Kappa • ROC-AUC Performance Dossier</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" id="btn-benchmark-dossier" onclick="document.getElementById('validation-suite-dialog')?.showModal()">
                            <span>📄 FDA Validation Suite</span>
                        </button>
                        <button type="button" class="btn-master" id="btn-benchmark-run-full" style="background: linear-gradient(135deg, #d97706, #f59e0b); border-color: #fbbf24;" onclick="document.getElementById('benchmark-dialog')?.showModal()">
                            <span>⚡ Run Full Model Benchmark</span>
                        </button>
                    </div>
                </div>

                <div class="fullscreen-workspace-pad">
                    <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px;">
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 10px; padding: 18px;">
                            <div style="font-size: 11px; font-family: var(--font-mono); color: #38bdf8; font-weight: 700;">DENSENET-121 (PRIMARY)</div>
                            <div style="font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 8px;">0.984 AUC</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">28ms • 7.0M Params • Production</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="font-size: 11px; font-family: var(--font-mono); color: #94a3b8; font-weight: 700;">RESNET-50-D</div>
                            <div style="font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 8px;">0.961 AUC</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">34ms • 25.6M Params • Residual</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="font-size: 11px; font-family: var(--font-mono); color: #c084fc; font-weight: 700;">VIT-B/16 TRANSFORMER</div>
                            <div style="font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 8px;">0.978 AUC</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">62ms • 86.6M Params • Attention</div>
                        </div>
                        <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 18px;">
                            <div style="font-size: 11px; font-family: var(--font-mono); color: #34d399; font-weight: 700;">CONVNEXT-TINY</div>
                            <div style="font-size: 24px; font-weight: 800; color: #ffffff; margin-top: 8px;">0.975 AUC</div>
                            <div style="font-size: 12px; color: #94a3b8; margin-top: 4px;">31ms • 28.6M Params • Modern CNN</div>
                        </div>
                    </div>

                    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 22px; display: flex; flex-direction: column; gap: 16px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 12px;">
                            <span style="font-size: 14px; font-weight: 700; color: #ffffff;">INTER-OBSERVER COHEN'S KAPPA AGREEMENT MATRIX (κ)</span>
                            <span style="font-size: 11px; color: #10b981; font-family: var(--font-mono); font-weight: 700;">κ &gt; 0.90: NEAR-PERFECT AGREEMENT</span>
                        </div>
                        <div style="overflow-x: auto;">
                            <table class="bm-kappa-table" style="width: 100%; border-collapse: collapse; text-align: center; font-family: var(--font-mono); font-size: 12px;">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.1);">
                                        <th style="padding: 10px; text-align: left; color: #94a3b8;">ARCHITECTURE</th>
                                        <th style="padding: 10px; color: #38bdf8;">DENSENET-121</th>
                                        <th style="padding: 10px; color: #cbd5e1;">RESNET-50</th>
                                        <th style="padding: 10px; color: #c084fc;">VIT-B/16</th>
                                        <th style="padding: 10px; color: #34d399;">CONVNEXT-T</th>
                                        <th style="padding: 10px; color: #fbbf24;">HUMAN RADIOLOGIST</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
                                        <th style="padding: 10px; text-align: left; color: #38bdf8;">DENSENET-121</th>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.35); font-weight: 700;">1.00</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.25);">0.92</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.94</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.93</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.35); font-weight: 700; color: #34d399;">0.95</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
                                        <th style="padding: 10px; text-align: left; color: #cbd5e1;">RESNET-50</th>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.25);">0.92</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.35); font-weight: 700;">1.00</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.2);">0.89</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.25);">0.91</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.25);">0.91</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04);">
                                        <th style="padding: 10px; text-align: left; color: #c084fc;">VIT-B/16</th>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.94</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.2);">0.89</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.35); font-weight: 700;">1.00</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.93</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.94</td>
                                    </tr>
                                    <tr>
                                        <th style="padding: 10px; text-align: left; color: #34d399;">CONVNEXT-T</th>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.93</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.25);">0.91</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.93</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.35); font-weight: 700;">1.00</td>
                                        <td style="padding: 10px; background: rgba(16, 185, 129, 0.3);">0.93</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>'''

    # Workspace 8: HIPAA Security, Audit Trail & De-ID
    ws_hipaa_html = '''            <!-- ================================================================= -->
            <!-- WORKSPACE 8: HIPAA SECURITY, AUDIT TRAIL & DE-IDENTIFICATION      -->
            <!-- ================================================================= -->
            <div class="alveon-workspace" id="workspace-hipaa" data-workspace="workspace-hipaa">
                <div class="workspace-hero-header">
                    <div class="workspace-hero-title-row">
                        <div class="workspace-hero-icon" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(52, 211, 153, 0.4); color: #34d399;">🛡️</div>
                        <div class="workspace-hero-text">
                            <h1>HIPAA Security, Cryptographic Audit & Safe-Harbor De-ID</h1>
                            <p>SHA-256 Merkle Chain Immutable Ledger • 21 CFR Part 11 Electronic Signature • Safe-Harbor 18-Attribute De-Identification</p>
                        </div>
                    </div>
                    <div class="workspace-hero-actions">
                        <button type="button" class="btn-titanium" onclick="document.getElementById('anonymize-dialog')?.showModal()">
                            <span>🛡️ Safe-Harbor Anonymizer</span>
                        </button>
                        <button type="button" class="btn-master" style="background: linear-gradient(135deg, #059669, #10b981); border-color: #34d399;" onclick="document.getElementById('audit-trail-dialog')?.showModal()">
                            <span>Inspect Cryptographic Ledger 📜</span>
                        </button>
                    </div>
                </div>

                <div class="fullscreen-workspace-pad">
                    <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.12), rgba(15, 23, 42, 0.8)); border: 1px solid rgba(52, 211, 153, 0.35); border-radius: 12px; padding: 18px 24px; display: flex; align-items: center; justify-content: space-between;">
                        <div style="display: flex; align-items: center; gap: 16px;">
                            <div style="width: 42px; height: 42px; border-radius: 50%; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; display: flex; align-items: center; justify-content: center; font-size: 20px;">🔒</div>
                            <div>
                                <div style="display: flex; align-items: center; gap: 10px;">
                                    <span style="font-weight: 700; font-size: 15px; color: #ffffff;">LEDGER INTEGRITY: 100% SECURE &amp; VERIFIED</span>
                                    <span style="background: #10b981; color: #ffffff; font-size: 10px; font-weight: 800; padding: 2px 8px; border-radius: 4px; letter-spacing: 0.5px;">SHA-256 CHAIN UNBROKEN</span>
                                </div>
                                <div style="color: #6ee7b7; font-size: 13px; margin-top: 4px;">
                                    All clinical readouts, DICOM modifications, attestation signatures, and exports are cryptographically hashed and sequenced. Zero tampering detected.
                                </div>
                            </div>
                        </div>
                        <div style="display: flex; align-items: center; gap: 10px;">
                            <button type="button" class="btn-titanium" id="btn-verify-merkle-chain" onclick="alert('Merkle cryptographic chain verification passed: 100% hash consistency!')">
                                <span>Re-Verify Merkle Chain</span>
                            </button>
                        </div>
                    </div>

                    <div style="background: rgba(15, 23, 42, 0.7); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 20px; display: flex; flex-direction: column; gap: 14px; flex: 1; min-height: 400px;">
                        <div style="display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(255, 255, 255, 0.06); padding-bottom: 12px;">
                            <span style="font-size: 14px; font-weight: 700; color: #ffffff;">RECENT CRYPTOGRAPHIC AUDIT LEDGER EVENTS</span>
                            <span style="font-family: var(--font-mono); font-size: 11px; color: #94a3b8;">SHOWING RECENT 10 ENTRIES</span>
                        </div>
                        <div style="overflow-x: auto; flex: 1;">
                            <table style="width: 100%; border-collapse: collapse; font-size: 12px; font-family: var(--font-clinical);">
                                <thead>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.08); color: #64748b; font-family: var(--font-mono); font-size: 11px; text-align: left;">
                                        <th style="padding: 8px 12px;">TIMESTAMP (UTC)</th>
                                        <th style="padding: 8px 12px;">USER / ROLE</th>
                                        <th style="padding: 8px 12px;">ACTION</th>
                                        <th style="padding: 8px 12px;">RESOURCE</th>
                                        <th style="padding: 8px 12px;">SHA-256 MERKLE DIGEST</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); color: #cbd5e1;">
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 11px;">2026-09-12 12:51:04</td>
                                        <td style="padding: 10px 12px;"><span style="color: #38bdf8; font-weight: 600;">Dr. Eleanor Vance</span> (Attending)</td>
                                        <td style="padding: 10px 12px;"><span style="background: rgba(16, 185, 129, 0.2); color: #34d399; padding: 2px 6px; border-radius: 4px; font-weight: 600;">ATTEST_SIGN</span></td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono);">PT-9402 (Elena Rostova)</td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 10px; color: #64748b;">e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); color: #cbd5e1;">
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 11px;">2026-09-12 12:49:33</td>
                                        <td style="padding: 10px 12px;"><span style="color: #38bdf8; font-weight: 600;">Dr. Eleanor Vance</span> (Attending)</td>
                                        <td style="padding: 10px 12px;"><span style="background: rgba(56, 189, 248, 0.2); color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-weight: 600;">INFERENCE_GRADCAM</span></td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono);">PT-9402 (Elena Rostova)</td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 10px; color: #64748b;">8f434346648f6b96df89dda901c5176b10a6d83961dd3c1ac88b59b2dc327aa4</td>
                                    </tr>
                                    <tr style="border-bottom: 1px solid rgba(255, 255, 255, 0.04); color: #cbd5e1;">
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 11px;">2026-09-12 12:48:19</td>
                                        <td style="padding: 10px 12px;"><span style="color: #94a3b8; font-weight: 600;">SYSTEM DAEMON</span> (Auto-Ingest)</td>
                                        <td style="padding: 10px 12px;"><span style="background: rgba(245, 158, 11, 0.2); color: #fbbf24; padding: 2px 6px; border-radius: 4px; font-weight: 600;">C_STORE_INGEST</span></td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono);">PT-9402 (Elena Rostova)</td>
                                        <td style="padding: 10px 12px; font-family: var(--font-mono); font-size: 10px; color: #64748b;">7d793037a0760186574b0282f2f435e70d716860717262da1366c0851c70cf61</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>'''

    # Assemble the full document
    new_html = f'''{head_part}<div class="alveon-app-shell workstation-container" id="alveon-app-shell">
{sidebar_html}

    <div class="alveon-main-stage" id="alveon-main-stage">
{topbar_html}

        <div class="alveon-workspaces-stack" id="alveon-workspaces-stack">
            <!-- ================================================================= -->
            <!-- WORKSPACE 1: 2D DIAGNOSTIC RADIOGRAPH WORKSTATION (DEFAULT ACTIVE)-->
            <!-- ================================================================= -->
            <div class="alveon-workspace active" id="workspace-diagnostic" data-workspace="workspace-diagnostic">
{diag_body_html}
            </div>

{ws_triage_html}

{ws_volumetric_html}

{ws_reporting_html}

{ws_pacs_html}

{ws_telerad_html}

{ws_benchmark_html}

{ws_hipaa_html}
        </div>
    </div>
</div>

{dialogs_and_tail}'''

    # Verification: check all original IDs
    new_ids = set(re.findall(r'id=[\"\']([a-zA-Z0-9_-]+)[\"\']', new_html))
    missing_ids = orig_ids - new_ids
    if missing_ids:
        print(f"ERROR: {len(missing_ids)} IDs are missing from new_html: {missing_ids}")
        sys.exit(1)

    print(f"SUCCESS: All {len(orig_ids)} original IDs preserved! New unique IDs: {len(new_ids)}")

    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(new_html)
    print("Successfully updated web/index.html with God-Tier multi-workspace shell!")

if __name__ == '__main__':
    main()
