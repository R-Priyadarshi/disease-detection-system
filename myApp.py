#!/usr/bin/env python3
"""
PneumoScan AI - Desktop Radiology Consultation Workstation
Upgraded Tkinter application featuring image previews, Grad-CAM visualization,
confidence metrics, and crash-resilient file dialogs.
"""

import sys
import os
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import cv2
import numpy as np

from core.config import settings
from core.model import get_model
from core.preprocessor import preprocessor
from core.gradcam import GradCAMGenerator
from core.sample_generator import ensure_sample_assets

class PneumoScanDesktopApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("PneumoScan AI - Chest Radiograph Diagnostic Workstation")
        self.root.geometry("980x780")
        self.root.minsize(860, 680)
        self.root.configure(bg="#090d16")

        # Initialize ML engine
        self.model = None
        self.gradcam = None
        self._init_engine()

        # Cached image references for Tkinter garbage collector prevention
        self.orig_photo = None
        self.gradcam_photo = None

        self._build_ui()

    def _init_engine(self):
        try:
            self.model = get_model()
            self.gradcam = GradCAMGenerator(self.model)
            ensure_sample_assets()
        except Exception as e:
            messagebox.showerror("Model Load Error", f"Failed to load neural network weights:\n{e}")

    def _build_ui(self):
        # 1. Header Bar
        header_frame = tk.Frame(self.root, bg="#0e1424", height=70, padx=24, pady=14)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame,
            text="PneumoScan AI Workstation",
            font=("Helvetica", 18, "bold"),
            fg="#f8fafc",
            bg="#0e1424"
        )
        title_lbl.pack(side=tk.LEFT)

        subtitle_lbl = tk.Label(
            header_frame,
            text="Deep Convolutional Pulmonary Classifier • Grad-CAM XAI",
            font=("Helvetica", 11),
            fg="#06b6d4",
            bg="#0e1424"
        )
        subtitle_lbl.pack(side=tk.LEFT, padx=16)

        status_lbl = tk.Label(
            header_frame,
            text="● Engine Active",
            font=("Helvetica", 10, "bold"),
            fg="#10b981",
            bg="#0e1424"
        )
        status_lbl.pack(side=tk.RIGHT)

        # 2. Controls Toolbar
        toolbar = tk.Frame(self.root, bg="#162035", padx=20, pady=12)
        toolbar.pack(fill=tk.X, side=tk.TOP)

        btn_choose = tk.Button(
            toolbar,
            text="📁 Choose X-Ray Image",
            font=("Helvetica", 11, "bold"),
            bg="#06b6d4",
            fg="#ffffff",
            activebackground="#0891b2",
            activeforeground="#ffffff",
            padx=14,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
            command=self.choose_file
        )
        btn_choose.pack(side=tk.LEFT, padx=6)

        btn_sample_norm = tk.Button(
            toolbar,
            text="Verify Normal Sample",
            font=("Helvetica", 10),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=10,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.load_preset_sample("sample_normal.jpg")
        )
        btn_sample_norm.pack(side=tk.LEFT, padx=6)

        btn_sample_pneu = tk.Button(
            toolbar,
            text="Verify Pneumonia Sample",
            font=("Helvetica", 10),
            bg="#1e293b",
            fg="#94a3b8",
            activebackground="#334155",
            activeforeground="#ffffff",
            padx=10,
            pady=6,
            relief=tk.FLAT,
            cursor="hand2",
            command=lambda: self.load_preset_sample("sample_pneumonia.jpg")
        )
        btn_sample_pneu.pack(side=tk.LEFT, padx=6)

        # 3. Main Split Content Area
        content_frame = tk.Frame(self.root, bg="#090d16", padx=20, pady=16)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # Left Display Card: Original Radiograph
        left_card = tk.LabelFrame(
            content_frame,
            text="  Input Chest Radiograph  ",
            font=("Helvetica", 11, "bold"),
            fg="#94a3b8",
            bg="#0e1424",
            padx=14,
            pady=14
        )
        left_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)

        self.canvas_orig = tk.Label(left_card, bg="#000000", text="[ Awaiting Image ]", fg="#64748b", font=("Helvetica", 12))
        self.canvas_orig.pack(fill=tk.BOTH, expand=True)

        # Right Display Card: Grad-CAM Explainability
        right_card = tk.LabelFrame(
            content_frame,
            text="  Grad-CAM Activation Heatmap  ",
            font=("Helvetica", 11, "bold"),
            fg="#94a3b8",
            bg="#0e1424",
            padx=14,
            pady=14
        )
        right_card.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=8)

        self.canvas_gradcam = tk.Label(right_card, bg="#000000", text="[ Awaiting Ingestion ]", fg="#64748b", font=("Helvetica", 12))
        self.canvas_gradcam.pack(fill=tk.BOTH, expand=True)

        # 4. Results Banner / Bottom Card
        self.result_frame = tk.Frame(self.root, bg="#162035", padx=24, pady=16)
        self.result_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=20, pady=16)

        self.lbl_result_badge = tk.Label(
            self.result_frame,
            text="STATUS: READY",
            font=("Helvetica", 14, "bold"),
            fg="#94a3b8",
            bg="#162035"
        )
        self.lbl_result_badge.pack(anchor=tk.W)

        self.lbl_confidence = tk.Label(
            self.result_frame,
            text="Awaiting chest radiograph upload to commence diagnostic neural pass...",
            font=("Helvetica", 11),
            fg="#64748b",
            bg="#162035"
        )
        self.lbl_confidence.pack(anchor=tk.W, pady=4)

        self.lbl_clinical = tk.Label(
            self.result_frame,
            text="",
            font=("Helvetica", 10, "italic"),
            fg="#cbd5e1",
            bg="#162035",
            wraplength=900
        )
        self.lbl_clinical.pack(anchor=tk.W)

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Chest Radiograph Image",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.webp *.tif *.tiff"),
                ("JPEG Images", "*.jpg *.jpeg"),
                ("PNG Images", "*.png"),
                ("All Files", "*.*")
            ]
        )
        if file_path:
            self.process_image(file_path)

    def load_preset_sample(self, sample_name: str):
        sample_path = settings.SAMPLES_DIR / sample_name
        if sample_path.exists():
            self.process_image(str(sample_path))
        else:
            messagebox.showwarning("Sample Not Found", f"Sample {sample_name} not found.")

    def process_image(self, image_path: str):
        if not self.model or not self.gradcam:
            messagebox.showerror("Error", "Model is not initialized.")
            return

        try:
            tensor, raw_gray = preprocessor.prepare_tensor(image_path)
            pred = self.model.predict_tensor(tensor)
            blended, heatmap = self.gradcam.generate_overlay(raw_gray, tensor)

            # Update previews
            h_disp, w_disp = 360, 360
            pil_orig = Image.fromarray(raw_gray).resize((w_disp, h_disp), Image.Resampling.LANCZOS)
            self.orig_photo = ImageTk.PhotoImage(pil_orig)
            self.canvas_orig.configure(image=self.orig_photo, text="")

            # Convert BGR blended to RGB for PIL
            blended_rgb = cv2.cvtColor(blended, cv2.COLOR_BGR2RGB)
            pil_grad = Image.fromarray(blended_rgb).resize((w_disp, h_disp), Image.Resampling.LANCZOS)
            self.gradcam_photo = ImageTk.PhotoImage(pil_grad)
            self.canvas_gradcam.configure(image=self.gradcam_photo, text="")

            # Update Diagnostics
            is_pneu = pred["is_pneumonia"]
            color = "#f43f5e" if is_pneu else "#10b981"
            status_text = f"DIAGNOSIS: {pred['diagnosis']} ({pred['confidence_percentage']}% Confidence)"

            self.lbl_result_badge.configure(text=status_text, fg=color)
            self.lbl_confidence.configure(
                text=f"Risk Tier: {pred['risk_tier'].replace('_', ' ')}  |  Latency: {pred['latency_ms']} ms  |  Source: {Path(image_path).name}",
                fg="#f8fafc"
            )
            self.lbl_clinical.configure(text=f"Clinical Guidance: {pred['clinical_recommendation']}")

        except Exception as e:
            messagebox.showerror("Processing Failure", f"Failed to analyze radiograph:\n{e}")

def main():
    root = tk.Tk()
    app = PneumoScanDesktopApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()