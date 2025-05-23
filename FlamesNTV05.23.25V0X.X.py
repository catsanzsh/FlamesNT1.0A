#!/usr/bin/env python3
"""
Flames NT ISO Installer 🔥❤️ (Offline Edition)
Version: 1.4 – No‑WU
-------------------------------------------------
• Fetches latest Insider / Production builds
• Converts UUP to ISO (stubbed)
• Mounts ISO automatically
• Launches setup.exe with `/auto upgrade` so the install
  runs completely offline (no Windows Update COM API required)

Requirements:
• Windows 10/11 with PowerShell 5+
• Administrator privileges (for Mount‑DiskImage)
• ~20 GB free space for temp files & ISO

NOTE: UUP conversion & aria2 download are still stubbed; replace
`download_tools()` and `create_iso()` with your real logic.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import os
import subprocess
import tempfile
import shutil
import sys

# ---------------------------- GUI Class ---------------------------- #
class FlamesISOInstaller:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Flames NT ISO Installer – DDLC HUD ❤️")
        self.root.geometry("650x500")
        self.root.configure(bg="#ffb3d9")

        self.status_var = tk.StringVar(value="Select a build to begin~ 💕")
        self.progress_var = tk.DoubleVar()
        self.cancelled = False
        self.temp_dir = None
        self.mounted_drive = None

        # Header
        tk.Label(
            root,
            text="Flames NT ISO Installer 🔥",
            font=("Segoe UI", 18, "bold"),
            bg="#ffb3d9",
            fg="#8b0051",
        ).pack(pady=10)

        # --- Build & Edition selectors --- #
        frame = tk.Frame(root, bg="#ffb3d9")
        frame.pack(pady=5)
        tk.Label(frame, text="Build:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=0, column=0, sticky="e")

        self.build_selector = ttk.Combobox(
            frame,
            state="readonly",
            width=35,
            values=[
                "Canary Channel (Latest Insider)",
                "Dev Channel (Weekly Builds)",
                "Beta Channel (Monthly Updates)",
                "Release Preview (Stable Preview)",
                "Windows 11 24H2 (Current Stable)",
                "Windows 11 23H2 (Previous Stable)",
                "Windows 10 22H2 (Latest Win10)",
            ],
        )
        self.build_selector.current(4)
        self.build_selector.grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Edition:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=1, column=0, sticky="e")
        self.edition_selector = ttk.Combobox(
            frame,
            state="readonly",
            width=35,
            values=["Professional", "Home", "Enterprise", "Education"],
        )
        self.edition_selector.current(0)
        self.edition_selector.grid(row=1, column=1, padx=5)

        # --- Buttons --- #
        btn_frame = tk.Frame(root, bg="#ffb3d9")
        btn_frame.pack(pady=15)
        self.start_button = tk.Button(
            btn_frame,
            text="Download & Create ISO 💾",
            font=("Segoe UI", 14, "bold"),
            command=self.start_process,
        )
        self.start_button.grid(row=0, column=0, padx=10)

        self.setup_button = tk.Button(
            btn_frame,
            text="Run Setup Upgrade 🔄",
            font=("Segoe UI", 14),
            state="disabled",
            command=self.start_setup,
        )
        self.setup_button.grid(row=0, column=1, padx=10)

        self.cancel_button = tk.Button(
            btn_frame,
            text="Cancel ❌",
            font=("Segoe UI", 14),
            state="disabled",
            command=self.cancel,
        )
        self.cancel_button.grid(row=0, column=2)

        # Progress
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.pack(pady=5)
        tk.Label(
            root,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg="#ffe6f2",
            fg="#5d0037",
            wraplength=600,
        ).pack(padx=10, pady=10, fill="x")

    # ---------------------------- Top‑Level Actions ---------------------------- #
    def start_process(self):
        """Kick off background download & ISO creation."""
        self.start_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress_var.set(0)
        self.cancelled = False
        threading.Thread(target=self.download_and_prepare, daemon=True).start()

    def start_setup(self):
        """Launch setup.exe for in‑place upgrade (offline)."""
        self.setup_button.config(state="disabled")
        threading.Thread(target=self.run_setup, daemon=True).start()

    def cancel(self):
        self.cancelled = True
        self.update_status("Process cancelled by user.")

    # ---------------------------- Status Helpers ---------------------------- #
    def update_status(self, msg: str):
        self.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, pct: int | float):
        self.root.after(0, lambda: self.progress_var.set(pct))

    # ---------------------------- Core Workflow ---------------------------- #
    def download_and_prepare(self):
        try:
            build_name = self.build_selector.get()
            edition = self.edition_selector.get()
            self.update_status(f"Preparing {build_name} – {edition}…")
            self.update_progress(5)

            # --- Create temp workspace --- #
            self.temp_dir = tempfile.mkdtemp(prefix="FlamesISO_")

            # --- Resolve build metadata (naive) --- #
            mapping = {
                "Canary Channel (Latest Insider)": {"build": "Canary", "ring": "Canary"},
                "Dev Channel (Weekly Builds)": {"build": "Dev", "ring": "Dev"},
                "Beta Channel (Monthly Updates)": {"build": "Beta", "ring": "Beta"},
                "Release Preview (Stable Preview)": {"build": "RP", "ring": "RP"},
                "Windows 11 24H2 (Current Stable)": {"build": "24H2", "ring": "Production"},
                "Windows 11 23H2 (Previous Stable)": {"build": "23H2", "ring": "Production"},
                "Windows 10 22H2 (Latest Win10)": {"build": "22H2", "ring": "Production"},
            }
            info = mapping.get(build_name)
            if not info:
                raise RuntimeError("Build mapping not found.")

            self.update_status("Fetching build metadata…")
            try:
                r = requests.get(
                    "https://api.uupdump.net/listid.php",
                    params={"search": info["build"], "sortByDate": 1},
                    timeout=10,
                )
                data = r.json().get("response", {}).get("builds", {})
                latest = next(iter(data.values())) if data else None
            except Exception:
                latest = None  # fallback

            build_tag = latest.get("title", build_name) if latest else build_name
            self.update_status(f"Latest found: {build_tag}")

            # --- Stub: Download UUP & convert to ISO --- #
            self.download_tools()
            if self.cancelled:
                return

            self.update_status("Creating ISO… 🔄")
            self.update_progress(40)
            iso_path = self.create_iso(build_tag, edition)
            if not os.path.exists(iso_path):
                raise RuntimeError("ISO creation failed.")

            # --- Mount ISO --- #
            self.update_progress(80)
            self.update_status("Mounting ISO… 💽")
            drive = self.mount_iso(iso_path)
            if self.cancelled:
                return

            if drive:
                self.mounted_drive = f"{drive}:"
                self.update_status(f"ISO mounted as {self.mounted_drive} Ready for offline setup.")
                self.update_progress(95)
                self.setup_button.config(state="normal")
            else:
                raise RuntimeError("Failed to mount ISO.")

        except Exception as ex:
            self.update_status(f"Error: {ex}")
        finally:
            self.start_button.config(state="normal")
            self.cancel_button.config(state="disabled")

    # ---------------------------- Stub Methods ---------------------------- #
    def download_tools(self):
        """
        Stub: Download UUP (simulate network + file download)
        Replace with your logic.
        """
        import time
        for i in range(6, 40, 2):
            if self.cancelled:
                return
            self.update_status(f"Downloading UUP files… ({i}% done)")
            self.update_progress(i)
            time.sleep(0.2)

    def create_iso(self, build_tag, edition):
        """
        Stub: Create ISO (simulate build)
        Replace with your real UUP -> ISO logic.
        """
        import time
        iso_path = os.path.join(self.temp_dir, f"{build_tag}_{edition}.iso")
        for i in range(40, 80, 5):
            if self.cancelled:
                return iso_path
            self.update_status(f"Building ISO: {build_tag} [{edition}]… ({i}%)")
            self.update_progress(i)
            time.sleep(0.25)
        # Fake create the file
        with open(iso_path, "wb") as f:
            f.write(os.urandom(1024))  # Just a dummy ISO
        return iso_path

    def mount_iso(self, iso_path):
        """
        Mount ISO using PowerShell (requires admin)
        Returns the drive letter if successful.
        """
        try:
            powershell = ["powershell", "-NoProfile", "-Command"]
            script = f"$iso = Mount-DiskImage -ImagePath '{iso_path}' -PassThru; ($iso | Get-Volume).DriveLetter"
            result = subprocess.check_output(powershell + [script], stderr=subprocess.STDOUT, text=True)
            drive_letter = result.strip().splitlines()[-1].strip()
            if drive_letter:
                return drive_letter
        except Exception as ex:
            self.update_status(f"Mount failed: {ex}")
        return None

    def run_setup(self):
        """
        Launch setup.exe from mounted ISO for offline upgrade.
        """
        try:
            if not self.mounted_drive:
                self.update_status("No mounted drive found.")
                return
            setup_path = os.path.join(f"{self.mounted_drive}", "setup.exe")
            if not os.path.exists(setup_path):
                self.update_status(f"setup.exe not found at {setup_path}")
                return
            self.update_status("Launching Windows Setup… 🪄")
            self.update_progress(100)
            subprocess.Popen([setup_path, "/auto", "upgrade"], shell=True)
        except Exception as ex:
            self.update_status(f"Setup launch failed: {ex}")
        finally:
            self.setup_button.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
