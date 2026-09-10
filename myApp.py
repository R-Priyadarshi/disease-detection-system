#!/usr/bin/env python3
"""
ALVEON — Desktop Thoracic PACS Workstation
Hospital-grade desktop radiograph consultation workstation with calibrated
Grad-CAM explainability, anatomical zonation telemetry, and DICOM styling.
"""

import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import cv2
import numpy as np

from core.config import settings
from core.model import get_model
from core.preprocessor import preprocessor
from core.gradcam import GradCAMGenerator
from core.sample_generator import ensure_sample_assets

class AlveonDesktopWorkstation:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("ALVEON | Thoracic Diagnostic PACS Workstation")
        self.root.geometry("1040x820")
        self.root.minsize(920, 720)
        self.root.configure(bg="#060709")

        # Initialize ML Diagnostic Engine
        self.model = None
        self.gradcam = None
        self._init_engine()

        # Image cache
        self.orig_photo = None
        self.gradcam_photo = None

        self._build_ui()

    def _init_engine(self):
        try:
            self.model = get_model()
            self.gradcam = GradCAMGenerator(self.model)
            ensure_sample_assets()
        except Exception as e:
            messagebox.showerror("ALVEON System Error", f"Failed to initialize neural diagnostic weights:\n{e}")

    def _build_ui(self):
        # 1. Institutional Top Bar
        header = tk.Frame(self.root, bg="#0d0f14", height=65, padx=24, pady=12)
        header.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header,
            text="ALVEON",
            font=("Helvetica", 18, "bold"),
            fg="#f8fafc",
            bg="#0d0f14"
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            header,
            text="THORACIC PACS WORKSTATION",
            font=("Helvetica", 10, "bold"),
            fg="#64748b",
            bg="#0d0f14"
        )
        sub_lbl.pack(side=tk.LEFT, padx=12)

        telemetry_lbl = tk.Label(
            header,
            text="● DICOM GSDF-14 ACTIVE",
            font=("Helvetica", 10, "bold"),
            fg="#059669",
            bg="#0d0f14"
        )
        telemetry_lbl.pack(side=tk.RIGHT)

        # 2. PACS Toolbar
        toolbar = tk.Frame(self.root, bg="#131722", padx=20, pady=10)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_choose = tk.Button(
            toolbar,
            text="📂 Ingest Radiograph Film",
            font=("Helvetica", 10, "bold"),
            bg="#f8fafc",
            fg="#000000",
            activebackground="#e2e8f0",
            activeforeground="#000000",
            padx=14,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.choose_file
        )
        btn_choose.pack(side=tk.LEFT, padx=6)

        btn_sample_norm = tk.Button(
            toolbar,
            text="Protocol 01: Clear Lung",
            font=("Helvetica", 10),
            bg="#181c29",
            fg="#94a3b8",
            activebackground="#282f44",
            activeforeground="#ffffff",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.load_preset_sample("sample_normal.jpg")
        )
        btn_sample_norm.pack(side=tk.LEFT, padx=6)

        btn_sample_pneu = tk.Button(
            toolbar,
            text="Protocol 02: Pneumonia",
            font=("Helvetica", 10),
            bg="#181c29",
            fg="#94a3b8",
            activebackground="#282f44",
            activeforeground="#ffffff",
            padx=10,
            pady=5,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.load_preset_sample("sample_pneumonia.jpg")
        )
        btn_sample_pneu.pack(side=tk.LEFT, padx=6)

        # 3. Radiographic Dual Display
        content = tk.Frame(self.root, bg="#060709", padx=20, pady=14)
        content.pack(fill=tk.BOTH, expand=True)

        left_card = tk.LabelFrame(
            content,
            text="  INPUT RADIOGRAPH (RAW FILM)  ",
            font=("Helvetica", 10, "bold"),
            fg="#64748b",
            bg="#0d0f14",
            padx=12,
            pady=12
        )
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6)

        self.canvas_orig = tk.Label(left_card, bg="#000000", text="[ Standby: Ingest Radiograph ]", fg="#475569", font=("Helvetica", 11))
        self.canvas_orig.pack(fill=tk.BOTH, expand=True)

        right_card = tk.LabelFrame(
            content,
            text="  GRAD-CAM PATHOLOGICAL LOCALIZATION (INFERNO)  ",
            font=("Helvetica", 10, "bold"),
            fg="#64748b",
            bg="#0d0f14",
            padx=12,
            pady=12
        )
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=6)

        self.canvas_gradcam = tk.Label(right_card, bg="#000000", text="[ Standby: Ingest Radiograph ]", fg="#475569", font=("Helvetica", 11))
        self.canvas_gradcam.pack(fill=tk.BOTH, expand=True)

        # 4. Clinical Telemetry & Findings Footer
        self.footer = tk.Frame(self.root, bg="#131722", padx=24, pady=16)
        self.footer.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=14)

        self.lbl_result_badge = tk.Label(
            self.footer,
            text="SYSTEM READY — AWAITING STUDY INGESTION",
            font=("Helvetica", 13, "bold"),
            fg="#94a3b8",
            bg="#131722"
        )
        self.lbl_result_badge.pack(anchor=tk.W)

        self.lbl_telemetry = tk.Label(
            self.footer,
            text="Matrix: 150x150 mm | Spatial Calibration: 0.85 mm/px | Model: ALVEON Keras 3",
            font=("Helvetica", 10),
            fg="#64748b",
            bg="#131722"
        )
        self.lbl_telemetry.pack(anchor=tk.W, pady=2)

        self.lbl_guidance = tk.Label(
            self.footer,
            text="",
            font=("Helvetica", 10, "italic"),
            fg="#cbd5e1",
            bg="#131722",
            wraplength=980
        )
        self.lbl_guidance.pack(anchor=tk.W, pady=4)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            title="ALVEON: Select Chest Radiograph",
            filetypes=[
                ("Standard Medical Images", "*.jpg *.jpeg *.png *.webp *.tif *.tiff"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.process_image(file_path)

    def load_preset_sample(self, sample_name: str):
        sample_path = settings.SAMPLES_DIR / sample_name
        if sample_path.exists():
            self.process_image(str(sample_path))

    def process_image(self, image_path: str):
        if not self.model or not self.gradcam:
            return

        try:
            tensor, raw_gray = preprocessor.prepare_tensor(image_path)
            pred = self.model.predict_tensor(tensor)
            blended, heatmap, zonation = self.gradcam.generate_overlay(raw_gray, tensor, colormap_name="inferno")

            # Update plates
            disp_size = 380, 380
            pil_orig = Image.fromarray(raw_gray).resize(disp_size, Image.Resampling.LANCZOS)
            self.orig_photo = ImageTk.PhotoImage(pil_orig)
            self.canvas_orig.configure(image=self.orig_photo, text="")

            blended_rgb = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
            pil_grad = Image.fromarray(blended_rgb).resize(disp_size, Image.Resampling.LANCZOS)
            self.gradcam_photo = ImageTk.PhotoImage(pil_grad)
            self.canvas_gradcam.configure(image=self.gradcam_photo, text="")

            is_pneu = pred["is_pneumonia"]
            color = "#e11d48" if is_pneu else "#059669"
            status = f"PRIMARY IMPRESSION: {pred['diagnosis']} ({pred['confidence_percentage']}% Probability)"

            self.lbl_result_badge.configure(text=status, fg=color)
            self.lbl_telemetry.configure(
                text=f"Risk Category: {pred['risk_tier'].replace('_', ' ')}  |  Latency: {pred['latency_ms']} ms  |  Dominant Focus: {zonation['dominant_zone']}",
                fg="#f8fafc"
            )
            self.lbl_guidance.configure(text=f"Clinical Guidance: {pred['clinical_recommendation']}")

        except Exception as e:
            messagebox.showerror("Analysis Error", f"Failed to execute radiograph evaluation:\n{e}")

def main():
    root = tk.Tk()
    app = AlveonDesktopWorkstation(root)
    root.mainloop()

if __name__ == "__main__":
    main()