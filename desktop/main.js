const { app, BrowserWindow, Menu, dialog, shell } = require('electron');
const path = require('path');
const http = require('http');
const { spawn } = require('child_process');

let mainWindow = null;
let pythonProcess = null;
const BACKEND_PORT = 8000;
const APP_URL = `http://127.0.0.1:${BACKEND_PORT}/`;

function checkBackendReady(timeoutMs = 15000) {
    return new Promise((resolve) => {
        const startTime = Date.now();
        const interval = setInterval(() => {
            http.get(`http://127.0.0.1:${BACKEND_PORT}/health`, (res) => {
                if (res.statusCode === 200) {
                    clearInterval(interval);
                    resolve(true);
                }
            }).on('error', () => {
                if (Date.now() - startTime > timeoutMs) {
                    clearInterval(interval);
                    resolve(false);
                }
            });
        }, 500);
    });
}

function startPythonBackend() {
    const rootDir = path.resolve(__dirname, '..');
    const pythonExecutable = process.platform === 'win32' 
        ? path.join(rootDir, '.venv', 'Scripts', 'python.exe')
        : path.join(rootDir, '.venv', 'bin', 'python');

    const cmd = require('fs').existsSync(pythonExecutable) ? pythonExecutable : 'python3';
    
    console.log(`[ALVEON Desktop] Spawning diagnostic engine via ${cmd}...`);
    pythonProcess = spawn(cmd, ['-m', 'uvicorn', 'api.app:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT), '--log-level', 'warning'], {
        cwd: rootDir,
        env: { ...process.env, PYTHONPATH: rootDir }
    });

    pythonProcess.stdout.on('data', (data) => console.log(`[Backend] ${data}`));
    pythonProcess.stderr.on('data', (data) => console.error(`[Backend ERR] ${data}`));
    pythonProcess.on('close', (code) => console.log(`[Backend] Exited with code ${code}`));
}

function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: 1440,
        height: 900,
        minWidth: 1024,
        minHeight: 700,
        title: 'ALVEON — Institutional Thoracic PACS & Diagnostic Workstation',
        backgroundColor: '#060709',
        icon: path.join(__dirname, 'icon.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js')
        }
    });

    // Load ALVEON workstation
    mainWindow.loadURL(APP_URL);

    // Build Native Menu Bar
    const template = [
        {
            label: 'File',
            submenu: [
                {
                    label: 'Open DICOM File (.dcm)...',
                    accelerator: 'CmdOrCtrl+O',
                    click: async () => {
                        const result = await dialog.showOpenDialog(mainWindow, {
                            properties: ['openFile', 'multiSelections'],
                            filters: [
                                { name: 'DICOM Studies', extensions: ['dcm', 'ima', 'dicom'] },
                                { name: 'All Files', extensions: ['*'] }
                            ]
                        });
                        if (!result.canceled && result.filePaths.length > 0) {
                            dialog.showMessageBox(mainWindow, {
                                type: 'info',
                                title: 'DICOM Ingestion',
                                message: `Selected ${result.filePaths.length} study file(s). Forwarding to local port 11112 SCP...`
                            });
                        }
                    }
                },
                { type: 'separator' },
                {
                    label: 'Launch Landing Page Overview',
                    click: () => mainWindow.loadURL(`http://127.0.0.1:${BACKEND_PORT}/landing`)
                },
                {
                    label: 'Launch Diagnostic Workstation',
                    accelerator: 'CmdOrCtrl+W',
                    click: () => mainWindow.loadURL(APP_URL)
                },
                { type: 'separator' },
                { role: 'quit' }
            ]
        },
        {
            label: 'View',
            submenu: [
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },
        {
            label: 'PACS & Help',
            submenu: [
                {
                    label: 'Interactive API Documentation',
                    click: () => shell.openExternal(`http://127.0.0.1:${BACKEND_PORT}/docs`)
                },
                {
                    label: 'Zero-Footprint OHIF Viewer',
                    click: () => shell.openExternal(`http://127.0.0.1:${BACKEND_PORT}/viewer`)
                },
                { type: 'separator' },
                {
                    label: 'About ALVEON PACS',
                    click: () => {
                        dialog.showMessageBox(mainWindow, {
                            type: 'info',
                            title: 'About ALVEON PACS',
                            message: 'ALVEON Institutional Thoracic PACS v5.1\n\nClinical Deep Learning Diagnostic Engine & Hardware DICOM SCP.\nBuilt by - R Priyadarshi\nZero Cloud Cost & Zero Setup Architecture.'
                        });
                    }
                }
            ]
        }
    ];

    const menu = Menu.buildFromTemplate(template);
    Menu.setApplicationMenu(menu);

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

app.whenReady().then(async () => {
    // 1. Check if backend is already active
    const alreadyRunning = await checkBackendReady(1000);
    if (!alreadyRunning) {
        startPythonBackend();
        const ready = await checkBackendReady(15000);
        if (!ready) {
            console.warn('[ALVEON Desktop] Warning: Backend warmup took longer than expected.');
        }
    } else {
        console.log('[ALVEON Desktop] Existing backend found active on port ' + BACKEND_PORT);
    }

    // 2. Open desktop window
    createMainWindow();

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
    });
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

app.on('will-quit', () => {
    if (pythonProcess) {
        console.log('[ALVEON Desktop] Terminating child python backend...');
        pythonProcess.kill();
        pythonProcess = null;
    }
});
