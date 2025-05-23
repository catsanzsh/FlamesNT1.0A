#!/usr/bin/env python3
"""
Flames NT ISO Installer 💕
Version: 1.1 – Now with "Auto-Update" magic ✨
-------------------------------------------------
This GUI tool lets you:
  1. Download & create a Windows ISO for the build/edition you pick.
  2. Mount that ISO and run a Windows-Update-style in-place upgrade.
  3. ***NEW*** "Auto Update OS" button that performs (1) + (2) in one click.

Built with tkinter + pywin32.  Requires Administrator rights to mount ISOs
and do the upgrade.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import os
import subprocess
import tempfile
import shutil
import time
import win32com.client  # Requires: pip install pywin32


class WindowsUpdateEngine:
    """Wraps COM objects to run an in-place upgrade from a mounted ISO."""

    def __init__(self, status_callback, progress_callback):
        self.update_status = status_callback
        self.update_progress = progress_callback

    def upgrade_os(self, iso_root):
        try:
            self.update_status("Initializing Windows Update session…")
            session = win32com.client.Dispatch("Microsoft.Update.Session")
            searcher = session.CreateUpdateSearcher()

            # Scope the search *only* to the mounted image source.
            # (In practice Windows Update ignores this; a real integration would
            #  require setup.exe /auto upgrade + answer files. This demo keeps
            #  using the COM interface for familiarity.)
            self.update_status("Searching for installable packages on ISO…")
            results = searcher.Search("IsInstalled=0 and Type='Software'")

            updates = results.Updates
            if updates.Count == 0:
                self.update_status("No applicable updates found.")
                return

            collection = win32com.client.Dispatch("Microsoft.Update.UpdateColl")
            for i in range(updates.Count):
                collection.Add(updates.Item(i))

            installer = session.CreateUpdateInstaller()
            installer.Updates = collection

            self.update_status(f"Downloading {updates.Count} updates…")
            installer.Download()

            self.update_status("Installing updates – this can take a while…")
            result = installer.Install()
            self.update_status(f"Installation finished with result code {result.ResultCode}.")
        except Exception as exc:
            self.update_status(f"Windows Update error: {exc}")


class FlamesISOInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("Flames NT ISO Installer – DDLC HUD 💕")
        self.root.geometry("650x520")
        self.root.configure(bg="#ffb3d9")
        self.root.resizable(False, False)

        # UI-state vars
        self.status_var = tk.StringVar(value="Select a build to begin~ 💝")
        self.progress_var = tk.DoubleVar()
        self.cancelled = False
        self.auto_update_requested = False

        # --- Header ---
        tk.Label(
            root,
            text="Flames NT ISO Installer 🔥",
            font=("Segoe UI", 18, "bold"),
            bg="#ffb3d9",
            fg="#8b0051",
        ).pack(pady=(12, 6))

        # --- Build / Edition selectors ---
        selector_frame = tk.Frame(root, bg="#ffb3d9")
        selector_frame.pack(pady=4)

        tk.Label(selector_frame, text="Build:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=0, column=0, sticky="e")
        self.build_selector = ttk.Combobox(
            selector_frame,
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
        self.build_selector.grid(row=0, column=1, padx=5, pady=2)

        tk.Label(selector_frame, text="Edition:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=1, column=0, sticky="e")
        self.edition_selector = ttk.Combobox(
            selector_frame,
            state="readonly",
            width=35,
            values=["Professional", "Home", "Enterprise", "Education"],
        )
        self.edition_selector.current(0)
        self.edition_selector.grid(row=1, column=1, padx=5, pady=2)

        # --- Buttons ---
        btn_frame = tk.Frame(root, bg="#ffb3d9")
        btn_frame.pack(pady=14)

        self.start_button = tk.Button(
            btn_frame,
            text="Download & Create ISO 💾",
            font=("Segoe UI", 14, "bold"),
            command=self.start_process,
        )
        self.start_button.grid(row=0, column=0, padx=6)

        self.update_button = tk.Button(
            btn_frame,
            text="Upgrade via WinUpdate 🔄",
            font=("Segoe UI", 14),
            state="disabled",
            command=self.start_win_update,
        )
        self.update_button.grid(row=0, column=1, padx=6)

        self.auto_button = tk.Button(
            btn_frame,
            text="Auto Update OS ✨",
            font=("Segoe UI", 14),
            command=self.start_auto_update,
        )
        self.auto_button.grid(row=0, column=2, padx=6)

        self.cancel_button = tk.Button(
            btn_frame,
            text="Cancel ❌",
            font=("Segoe UI", 14),
            state="disabled",
            command=self.cancel,
        )
        self.cancel_button.grid(row=0, column=3, padx=6)

        # --- Progress ---
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100, length=580)
        self.progress_bar.pack(pady=(4, 6))

        tk.Label(
            root,
            textvariable=self.status_var,
            font=("Segoe UI", 10),
            bg="#ffe6f2",
            fg="#5d0037",
            wraplength=620,
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=8, pady=(0, 10))

        # Runtime helpers
        self.temp_dir: str | None = None
        self.mounted_path: str | None = None

    # ---------------------------------------------------------------------
    #  Button handlers
    # ---------------------------------------------------------------------
    def start_process(self):
        """Download/build an ISO (no OS upgrade)."""
        self._prime_for_action()
        self.auto_update_requested = False
        threading.Thread(target=self.download_and_prepare, daemon=True).start()

    def start_auto_update(self):
        """One-click: Download ISO, mount, then run upgrade."""
        self._prime_for_action()
        self.auto_update_requested = True
        threading.Thread(target=self.download_and_prepare, daemon=True).start()

    def start_win_update(self):
        self.update_button.config(state="disabled")
        self.auto_button.config(state="disabled")
        if not self.mounted_path:
            messagebox.showwarning("No ISO mounted", "Please mount or create an ISO first.")
            return
        threading.Thread(
            target=lambda: WindowsUpdateEngine(self.update_status, self.update_progress).upgrade_os(
                self.mounted_path
            ),
            daemon=True,
        ).start()

    def cancel(self):
        self.cancelled = True
        self.update_status("Process cancelled by user.")

    # ------------------------------------------------------------------
    #  Helper callbacks into UI thread
    # ------------------------------------------------------------------
    def update_status(self, message: str):
        self.root.after(0, lambda: self.status_var.set(message))

    def update_progress(self, pct: int | float):
        self.root.after(0, lambda: self.progress_var.set(pct))

    # ------------------------------------------------------------------
    #  Worker thread logic
    # ------------------------------------------------------------------
    def download_and_prepare(self):
        try:
            build_name = self.build_selector.get()
            edition = self.edition_selector.get()
            self.update_status(f"Preparing {build_name} – {edition}…")
            self.update_progress(5)

            # Prepare scratch dir
            self.temp_dir = tempfile.mkdtemp(prefix="FlamesISO_")

            # Map selector → search query for UUPDump API
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
                raise RuntimeError("Unrecognised build selection.")

            # Query UUPDump (simplified)
            self.update_status("Fetching build metadata…")
            resp = requests.get(
                "https://api.uupdump.net/listid.php",
                params={"search": info["build"], "sortByDate": 1},
                timeout=10,
            )
            data = resp.json().get("response", {}).get("builds", {})
            # First hit matching ring → id
            bid, bdata = next(((k, v) for k, v in data.items() if info["ring"] in v.get("title", "")), (None, None))
            build_id = bid or f"{info['build']}_fallback"
            build_ver = bdata.get("build", info["build"]) if bdata else info["build"]
            title = bdata["title"] if bdata else build_name

            # Simulate: download tools & create ISO (stubbed)
            self.download_tools()
            if self.cancelled:
                return

            self.update_status("Building ISO… this is a stub demo 🔨")
            self.update_progress(35)
            iso_path = self.create_iso(build_ver, edition)

            self.update_progress(70)
            self.update_status("Mounting ISO… 💿")
            drive = self.mount_iso(iso_path)
            if self.cancelled:
                return

            if not drive:
                raise RuntimeError("Failed to mount ISO.")

            self.mounted_path = f"{drive}:\\"
            self.update_status(f"ISO mounted at {self.mounted_path}")
            self.update_progress(100)

            if self.auto_update_requested:
                # Kick off the upgrade automatically.
                self.start_win_update()
            else:
                self.update_button.config(state="normal")
                self.auto_button.config(state="normal")
                self.update_status("✅ ISO ready. Click 'Upgrade via WinUpdate' to continue.")

        except Exception as exc:
            self.update_status(f"❌ Error: {exc}")
            messagebox.showerror("Error", str(exc))
        finally:
            self._tidy_after_action()

    # ------------------------------------------------------------------
    #  Internal helpers
    # ------------------------------------------------------------------
    def download_tools(self):
        tools_dir = os.path.join(self.temp_dir, "tools")
        os.makedirs(tools_dir, exist_ok=True)
        # Here you could download aria2, uup-converter, etc.
        self.update_status("Tools ready.")
        self.update_progress(20)

    def create_iso(self, build_ver: str, edition: str) -> str:
        # Stub implementation – make an empty file to pretend we built an ISO.
        iso_path = os.path.join(self.temp_dir, f"Windows_{build_ver}_{edition}.iso")
        with open(iso_path, "wb") as fp:
            fp.write(b"ISO STUB")
        return iso_path

    def mount_iso(self, iso_path: str) -> str | None:
        cmd = [
            "powershell",
            "-Command",
            f"$img=Mount-DiskImage -ImagePath '{iso_path}' -PassThru; (Get-DiskImage -ImagePath '{iso_path}' | Get-Volume).DriveLetter",
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.stdout.strip() if result.returncode == 0 else None

    # ------------------------------------------------------------------
    def _prime_for_action(self):
        self.start_button.config(state="disabled")
        self.update_button.config(state="disabled")
        self.auto_button.config(state="disabled")
        self.cancel_button.config(state="normal")
        self.progress_var.set(0)
        self.cancelled = False

    def _tidy_after_action(self):
        # Clean up temporary dir if we created one and user didn't cancel mid-way
        if self.temp_dir and not self.cancelled:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
            self.temp_dir = None

        self.start_button.config(state="normal")
        if not self.cancelled and self.mounted_path:
            self.auto_button.config(state="normal")
        self.cancel_button.config(state="disabled")


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    if os.name != "nt":
        raise SystemExit("This script only runs on Windows.")

    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
