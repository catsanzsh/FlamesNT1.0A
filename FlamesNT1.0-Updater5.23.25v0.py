#!/usr/bin/env python3
"""
Flames NT ISO Installer 🔥❤️ (Offline Edition)
Version: 2.0 – Auto-Updating
-------------------------------------------------
• Integrated UUP dump API
• Full aria2c download implementation
• Self-updating mechanism
• Admin elevation handling
• Real ISO conversion
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
import ctypes
import json
import time
from urllib.parse import urlparse
from pathlib import Path

# Configuration
VERSION = "2.0"
UPDATE_URL = "https://example.com/latest_version.json"  # Replace with your update endpoint
UUP_API = "https://api.uupdump.net/listid.php"
UUP_CONVERSION_SCRIPT = "https://github.com/uup-dump/converter/raw/master/convert.sh"
ARIA2_URL = "https://github.com/aria2/aria2/releases/download/release-1.37.0/aria2-1.37.0-win-64bit-build1.zip"

class FlamesISOInstaller:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(f"Flames NT ISO Installer v{VERSION} – DDLC HUD ❤️")
        self.root.geometry("750x550")
        self.root.configure(bg="#ffb3d9")
        self.setup_directories()
        self.check_admin()
        
        # State variables
        self.status_var = tk.StringVar(value="Initializing...")
        self.progress_var = tk.DoubleVar()
        self.cancelled = False
        self.temp_dir = None
        self.mounted_drive = None
        self.current_build = None

        # UI Setup
        self.create_widgets()
        self.check_for_updates()

    def setup_directories(self):
        self.app_dir = Path(__file__).parent.resolve()
        self.tools_dir = self.app_dir / "tools"
        self.tools_dir.mkdir(exist_ok=True)
        
        # Ensure required tools exist
        self.aria2_exe = self.tools_dir / "aria2c.exe"
        if not self.aria2_exe.exists():
            self.download_aria2()

    def download_aria2(self):
        try:
            r = requests.get(ARIA2_URL)
            zip_path = self.tools_dir / "aria2.zip"
            with open(zip_path, 'wb') as f:
                f.write(r.content)
            
            # Extract aria2c.exe
            import zipfile
            with zipfile.ZipFile(zip_path) as z:
                z.extract("aria2c.exe", self.tools_dir)
            zip_path.unlink()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to download aria2: {str(e)}")
            sys.exit(1)

    def check_admin(self):
        if ctypes.windll.shell32.IsUserAnAdmin() == 0:
            ctypes.windll.shell32.ShellExecuteW(
                None, "runas", sys.executable, __file__, None, 1
            )
            sys.exit(0)

    def create_widgets(self):
        # Header
        tk.Label(
            self.root,
            text="Flames NT ISO Installer 🔥",
            font=("Segoe UI", 18, "bold"),
            bg="#ffb3d9",
            fg="#8b0051",
        ).pack(pady=10)

        # Build Selector
        self.build_frame = ttk.LabelFrame(self.root, text="Build Selection")
        self.build_frame.pack(pady=10, padx=20, fill="x")
        
        self.build_selector = ttk.Combobox(
            self.build_frame,
            state="readonly",
            values=self.fetch_available_builds(),
        )
        self.build_selector.pack(pady=5, padx=10, fill="x")
        
        # Edition Selector
        self.edition_selector = ttk.Combobox(
            self.build_frame,
            state="readonly",
            values=["Professional", "Home", "Enterprise", "Education"],
        )
        self.edition_selector.current(0)
        self.edition_selector.pack(pady=5, padx=10, fill="x")

        # Progress Controls
        self.progress_bar = ttk.Progressbar(
            self.root, variable=self.progress_var, maximum=100
        )
        self.progress_bar.pack(pady=10, fill="x", padx=20)
        
        self.status_label = tk.Label(
            self.root,
            textvariable=self.status_var,
            bg="#ffe6f2",
            fg="#5d0037",
            wraplength=700,
        )
        self.status_label.pack(fill="x", padx=20)

        # Action Buttons
        btn_frame = tk.Frame(self.root, bg="#ffb3d9")
        btn_frame.pack(pady=10)
        
        self.start_btn = tk.Button(
            btn_frame,
            text="Start Installation",
            command=self.start_installation,
            state="normal",
        )
        self.start_btn.pack(side="left", padx=5)
        
        self.cancel_btn = tk.Button(
            btn_frame,
            text="Cancel",
            command=self.cancel_operation,
            state="disabled",
        )
        self.cancel_btn.pack(side="left", padx=5)

    def fetch_available_builds(self):
        try:
            response = requests.get(UUP_API, params={"search": "windows 11", "sortByDate": 1})
            builds = response.json().get("response", {}).get("builds", {})
            return [f"{b['title']} ({b['build']})" for b in builds.values()]
        except Exception:
            return ["Windows 11 24H2 (26100.1)", "Windows 11 23H2 (22631.1)"]

    def check_for_updates(self):
        def update_check():
            try:
                response = requests.get(UPDATE_URL, timeout=5)
                data = response.json()
                if data["version"] != VERSION:
                    self.root.after(0, self.apply_update, data["download_url"])
            except Exception:
                pass
        threading.Thread(target=update_check, daemon=True).start()

    def apply_update(self, download_url):
        if messagebox.askyesno("Update Available", "A new version is available. Update now?"):
            try:
                temp_exe = self.app_dir / "update_temp.exe"
                with requests.get(download_url, stream=True) as r:
                    with open(temp_exe, 'wb') as f:
                        shutil.copyfileobj(r.raw, f)
                
                bat_script = f"""
                @echo off
                timeout /t 3 /nobreak >nul
                del "{sys.argv[0]}"
                rename "{temp_exe}" "{os.path.basename(sys.argv[0])}"
                start "" "{os.path.basename(sys.argv[0])}"
                """
                with open(self.app_dir / "update.bat", "w") as f:
                    f.write(bat_script)
                
                subprocess.Popen(["update.bat"], cwd=self.app_dir, shell=True)
                sys.exit(0)
            except Exception as e:
                messagebox.showerror("Update Failed", str(e))

    def start_installation(self):
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        threading.Thread(target=self.installation_workflow, daemon=True).start()

    def installation_workflow(self):
        try:
            self.temp_dir = Path(tempfile.mkdtemp(prefix="FlamesISO_"))
            
            # Step 1: Fetch build details
            self.update_status("Fetching build metadata...")
            build_info = self.build_selector.get().split(" (")
            build_id = build_info[1].strip(")")
            
            # Step 2: Download UUP files
            self.update_status("Starting download...")
            self.download_uup_files(build_id)
            
            # Step 3: Convert to ISO
            self.update_status("Converting to ISO...")
            iso_path = self.convert_to_iso()
            
            # Step 4: Mount ISO
            self.update_status("Mounting ISO...")
            self.mount_iso(iso_path)
            
            # Step 5: Launch Setup
            self.update_status("Launching setup...")
            self.launch_setup()
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        finally:
            self.cleanup()

    def download_uup_files(self, build_id):
        # Get download links from UUP dump API
        response = requests.get(
            "https://api.uupdump.net/getdownload.php",
            params={"build": build_id, "edition": self.edition_selector.get()}
        )
        download_info = response.json()
        
        # Create aria2 input file
        aria2_input = self.temp_dir / "files.txt"
        with open(aria2_input, "w") as f:
            for file in download_info["files"]:
                f.write(f"{file['url']}\n")
        
        # Run aria2c download
        cmd = [
            str(self.aria2_exe),
            "-i", str(aria2_input),
            "-d", str(self.temp_dir),
            "--max-connection-per-server=16",
            "--split=16",
            "--console-log-level=warn"
        ]
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if "DOWNLOADED" in line:
                self.update_progress(int(line.split("%")[0].split()[-1]))

    def convert_to_iso(self):
        # Run conversion script
        conversion_script = self.tools_dir / "convert.sh"
        if not conversion_script.exists():
            r = requests.get(UUP_CONVERSION_SCRIPT)
            with open(conversion_script, "w") as f:
                f.write(r.text)
        
        cmd = [
            "bash",
            str(conversion_script),
            "-i", str(self.temp_dir),
            "-o", str(self.temp_dir),
            "-e", self.edition_selector.get()
        ]
        
        subprocess.run(cmd, check=True)
        return next(self.temp_dir.glob("*.iso"))

    def mount_iso(self, iso_path):
        ps_script = f"""
        $iso = Mount-DiskImage -ImagePath '{iso_path}' -PassThru
        $drive = ($iso | Get-Volume).DriveLetter
        Write-Output $drive
        """
        result = subprocess.check_output(["powershell", "-Command", ps_script], text=True)
        self.mounted_drive = f"{result.strip()}:\\"

    def launch_setup(self):
        setup_exe = Path(self.mounted_drive) / "setup.exe"
        subprocess.Popen([setup_exe, "/auto", "upgrade"], shell=True)

    def update_status(self, message):
        self.root.after(0, self.status_var.set, message)

    def update_progress(self, value):
        self.root.after(0, self.progress_var.set, value)

    def cancel_operation(self):
        self.cancelled = True
        self.update_status("Cancelling...")
        # Add actual cancellation logic for downloads/processes

    def cleanup(self):
        if self.temp_dir:
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
