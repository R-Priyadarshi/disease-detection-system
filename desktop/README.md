# ALVEON Desktop PACS Workstation

Dedicated, cross-platform, institutional desktop application for ALVEON.

---

## 🌟 Capabilities

- **Zero-Install Offline Operation**: Runs completely self-contained on air-gapped hospital networks without internet connectivity.
- **Embedded Port 11112 DIMSE SCP**: Automatically starts the background DICOM C-STORE and C-ECHO hardware listener upon launch.
- **Embedded SQLite WAL Database**: Stores reports, caliper annotations, user accounts, and cryptographic SHA-256 audit logs locally in `data/alveon.db`.
- **Native Diagnostic Window**: Fullscreen (`F11`), distraction-free, 60 FPS HTML5 Canvas and WebGL GPU acceleration.
- **Native OS Menus**: `Cmd/Ctrl+O` to open local `.dcm` files, quick toggles between Diagnostic Workstation and Landing Page.

---

## 🚀 Quickstart (Development Mode)

### Option A: Python Launcher (Zero Extra Dependencies)
From the repository root:
```bash
python3 desktop_app.py
```
*Automatically detects system browser (Chrome/Edge/Brave) and launches a clean, frameless `--app` window.*

### Option B: Electron Workstation
From the `desktop/` directory:
```bash
cd desktop
npm install
npm start
```

---

## 📦 Building Native Installers

Generate stand-alone installers for distribution to hospitals and clinics:

### 1. Windows Installer (`.exe` / Portable)
```bash
npm run build:win
```
*Outputs `dist/ALVEON PACS Setup 5.1.0.exe` and portable executable.*

### 2. macOS Package (`.dmg` / `.zip`)
```bash
npm run build:mac
```
*Outputs `dist/ALVEON PACS-5.1.0.dmg` with Apple Silicon & Intel Universal binary support.*

### 3. Linux Package (`.AppImage` / `.deb`)
```bash
npm run build:linux
```
*Outputs standalone `dist/ALVEON PACS-5.1.0.AppImage` executable (runs on Ubuntu, Debian, RedHat, Fedora, Arch).*
