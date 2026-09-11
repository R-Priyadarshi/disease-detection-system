#!/usr/bin/env python3
"""
ALVEON Desktop Application Launcher
===================================
Launches ALVEON as a dedicated, standalone, distraction-free desktop application.
Automatically manages the local FastAPI diagnostic engine and DIMSE DICOM SCP
daemon on port 11112.
"""

import os
import sys
import time
import socket
import subprocess
import threading
import webbrowser
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent
APP_PORT = int(os.environ.get("PORT", 8000))
DICOM_PORT = 11112
APP_URL = f"http://127.0.0.1:{APP_PORT}/"

def is_port_in_use(port: int) -> bool:
    """Checks if a local TCP port is already actively listening."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(('127.0.0.1', port)) == 0

def start_backend():
    """Starts the FastAPI application and DICOM listener if not already running."""
    if is_port_in_use(APP_PORT):
        print(f"  ✓ ALVEON diagnostic server is already running on port {APP_PORT}.")
        return None

    print(f"  ⚡ Starting local ALVEON diagnostic engine on port {APP_PORT}...")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT_DIR)
    
    # Use current virtual environment python if available
    python_bin = sys.executable
    cmd = [
        python_bin, "-m", "uvicorn", "api.app:app",
        "--host", "127.0.0.1",
        "--port", str(APP_PORT),
        "--log-level", "warning"
    ]
    proc = subprocess.Popen(cmd, cwd=str(ROOT_DIR), env=env)
    
    # Wait for server to become responsive
    max_wait = 15
    for _ in range(max_wait * 2):
        if is_port_in_use(APP_PORT):
            print(f"  ✓ ALVEON diagnostic server online at {APP_URL}")
            return proc
        time.sleep(0.5)

    print("  ⚠️ Server took longer than expected to initialize. Launching window...")
    return proc

def launch_native_window():
    """
    Attempts to open a dedicated native desktop window without browser URL bar
    or navigation chrome for a distraction-free radiology workstation experience.
    """
    # 1. Try pywebview if installed
    try:
        import webview
        print("  🖥️  Launching via Native PyWebView Desktop Engine...")
        webview.create_window(
            title="ALVEON — Institutional Thoracic PACS & Diagnostic AI",
            url=APP_URL,
            width=1440,
            height=900,
            min_size=(1024, 700),
            background_color="#060709"
        )
        webview.start()
        return
    except ImportError:
        pass

    # 2. Try Chrome / Edge / Brave / Chromium native app mode
    browser_candidates = [
        # Linux
        ["google-chrome", f"--app={APP_URL}", "--window-size=1440,900"],
        ["chromium-browser", f"--app={APP_URL}", "--window-size=1440,900"],
        ["chromium", f"--app={APP_URL}", "--window-size=1440,900"],
        ["brave-browser", f"--app={APP_URL}", "--window-size=1440,900"],
        ["microsoft-edge", f"--app={APP_URL}", "--window-size=1440,900"],
        # macOS
        ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", f"--app={APP_URL}", "--window-size=1440,900"],
        ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge", f"--app={APP_URL}", "--window-size=1440,900"],
        ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser", f"--app={APP_URL}", "--window-size=1440,900"],
        # Windows
        ["chrome.exe", f"--app={APP_URL}", "--window-size=1440,900"],
        ["msedge.exe", f"--app={APP_URL}", "--window-size=1440,900"]
    ]

    for candidate in browser_candidates:
        executable = candidate[0]
        try:
            # Check if binary is in PATH or exists as absolute file
            if os.path.isabs(executable):
                if not os.path.exists(executable):
                    continue
            else:
                import shutil
                if not shutil.which(executable):
                    continue

            print(f"  🖥️  Launching standalone desktop window via {executable} in --app mode...")
            proc = subprocess.Popen(candidate)
            proc.wait()
            return
        except Exception:
            continue

    # 3. Standard fallback: system default browser
    print("  🌐 Launching in default system browser...")
    webbrowser.open(APP_URL)

def main():
    print("=" * 70)
    print("🏥 ALVEON PACS — INSTITUTIONAL DESKTOP WORKSTATION LAUNCHER")
    print("=" * 70)
    
    server_proc = start_backend()
    
    try:
        launch_native_window()
    except KeyboardInterrupt:
        print("\n  🛑 Shutting down ALVEON Desktop...")
    finally:
        if server_proc:
            print("  🛑 Terminating background diagnostic server...")
            server_proc.terminate()
            server_proc.wait()
        print("  ✓ ALVEON shutdown clean. Goodbye.")

if __name__ == "__main__":
    main()
