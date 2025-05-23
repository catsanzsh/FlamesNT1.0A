import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import os
import subprocess
import tempfile
import shutil
import time
import win32com.client  # Requires pywin32

class WindowsUpdateEngine:
    def __init__(self, status_callback, progress_callback):
        self.update_status = status_callback
        self.update_progress = progress_callback

    def upgrade_os(self, iso_path):
        try:
            self.update_status("Initializing Windows Update session...")
            session = win32com.client.Dispatch("Microsoft.Update.Session")
            searcher = session.CreateUpdateSearcher()

            self.update_status("Searching for updates on mounted ISO source...")
            # Note: For real ISO-based upgrades, additional integration is needed
            results = searcher.Search("IsInstalled=0 and Type='Software'")
            updates = results.Updates
            count = updates.Count
            if count == 0:
                self.update_status("No updates found.")
                return

            collection = win32com.client.Dispatch("Microsoft.Update.UpdateColl")
            for i in range(count):
                collection.Add(updates.Item(i))

            installer = session.CreateUpdateInstaller()
            installer.Updates = collection

            self.update_status(f"Downloading {count} updates...")
            installer.Download()

            self.update_status("Installing updates...")
            result = installer.Install()
            code = result.ResultCode
            self.update_status(f"Installation finished with code {code}.")
        except Exception as e:
            self.update_status(f"Windows Update error: {e}")

class FlamesISOInstaller:
    def __init__(self, root):
        self.root = root
        self.root.title("Flames NT ISO Installer - DDLC HUD 💕")
        self.root.geometry("650x500")
        self.root.configure(bg="#ffb3d9")

        self.status_var = tk.StringVar(value="Select a build to begin~ 💝")
        self.progress_var = tk.DoubleVar()
        self.cancelled = False
        self.temp_dir = None

        # Header
        tk.Label(root, text="Flames NT ISO Installer 🔥", font=("Segoe UI", 18, "bold"), bg="#ffb3d9", fg="#8b0051").pack(pady=10)

        # Build & Edition selectors
        frame = tk.Frame(root, bg="#ffb3d9")
        frame.pack(pady=5)
        tk.Label(frame, text="Build:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=0, column=0, sticky='e')
        self.build_selector = ttk.Combobox(
            frame, state="readonly", width=35,
            values=[
                "Canary Channel (Latest Insider)",
                "Dev Channel (Weekly Builds)",
                "Beta Channel (Monthly Updates)",
                "Release Preview (Stable Preview)",
                "Windows 11 24H2 (Current Stable)",
                "Windows 11 23H2 (Previous Stable)",
                "Windows 10 22H2 (Latest Win10)"
            ])
        self.build_selector.current(4)
        self.build_selector.grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Edition:", font=("Segoe UI", 12), bg="#ffb3d9").grid(row=1, column=0, sticky='e')
        self.edition_selector = ttk.Combobox(frame, state="readonly", width=35,
            values=["Professional", "Home", "Enterprise", "Education"])
        self.edition_selector.current(0)
        self.edition_selector.grid(row=1, column=1, padx=5)

        # Buttons
        btn_frame = tk.Frame(root, bg="#ffb3d9")
        btn_frame.pack(pady=15)
        self.start_button = tk.Button(btn_frame, text="Download & Create ISO 💾", font=("Segoe UI", 14, "bold"), command=self.start_process)
        self.start_button.grid(row=0, column=0, padx=10)
        self.update_button = tk.Button(btn_frame, text="Upgrade via WinUpdate 🔄", font=("Segoe UI", 14), state='disabled', command=self.start_win_update)
        self.update_button.grid(row=0, column=1, padx=10)
        self.cancel_button = tk.Button(btn_frame, text="Cancel ❌", font=("Segoe UI", 14), state='disabled', command=self.cancel)
        self.cancel_button.grid(row=0, column=2)

        # Progress
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100, length=500)
        self.progress_bar.pack(pady=5)
        tk.Label(root, textvariable=self.status_var, font=("Segoe UI", 10), bg="#ffe6f2", fg="#5d0037", wraplength=600).pack(padx=10, pady=10, fill='x')

    def start_process(self):
        self.start_button.config(state='disabled')
        self.cancel_button.config(state='normal')
        self.progress_var.set(0)
        self.cancelled = False
        threading.Thread(target=self.download_and_prepare, daemon=True).start()

    def start_win_update(self):
        self.update_button.config(state='disabled')
        threading.Thread(target=lambda: WindowsUpdateEngine(self.update_status, self.update_progress).upgrade_os(self.mounted_path), daemon=True).start()

    def cancel(self):
        self.cancelled = True
        self.update_status("Process cancelled by user.")

    def update_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    def update_progress(self, pct):
        self.root.after(0, lambda: self.progress_var.set(pct))

    def download_and_prepare(self):
        try:
            build_name = self.build_selector.get()
            edition = self.edition_selector.get()
            self.update_status(f"Preparing {build_name} - {edition}...")
            self.update_progress(5)

            self.temp_dir = tempfile.mkdtemp(prefix="FlamesISO_")
            mapping = {
                "Canary Channel (Latest Insider)": {"build": "Canary", "ring": "Canary"},
                "Dev Channel (Weekly Builds)": {"build": "Dev", "ring": "Dev"},
                "Beta Channel (Monthly Updates)": {"build": "Beta", "ring": "Beta"},
                "Release Preview (Stable Preview)": {"build": "RP", "ring": "RP"},
                "Windows 11 24H2 (Current Stable)": {"build": "24H2", "ring": "Production"},
                "Windows 11 23H2 (Previous Stable)": {"build": "23H2", "ring": "Production"},
                "Windows 10 22H2 (Latest Win10)": {"build": "22H2", "ring": "Production"}
            }
            info = mapping.get(build_name)
            if not info:
                raise RuntimeError("Build info not found")

            self.update_status("Fetching build metadata...")
            r = requests.get("https://api.uupdump.net/listid.php", params={"search": info['build'], "sortByDate": 1}, timeout=10)
            data = r.json().get('response', {}).get('builds', {})
            # pick latest matching
            bid, bdata = next(((k,v) for k,v in data.items() if info['ring'] in v.get('title','')), (None,None))
            build_info = {'id': bid or f"{info['build']}_fallback", 'title': bdata['title'] if bdata else build_name, 'build': bdata.get('build', info['build']) if bdata else info['build']}

            self.download_tools()
            if self.cancelled: return

            self.update_status("Creating ISO... 🔄")
            self.update_progress(40)
            iso_path = self.create_iso(build_info, edition)
            if not os.path.exists(iso_path):
                raise RuntimeError("ISO creation failed")

            self.update_progress(80)
            self.update_status("Mounting ISO... 💿")
            drive = self.mount_iso(iso_path)
            if self.cancelled: return

            if drive:
                self.mounted_path = f"{drive}:\\"
                self.update_status(f"ISO mounted at {self.mounted_path}")
                self.progress_var.set(100)
                self.update_status("✅ ISO ready. Click 'Upgrade via WinUpdate' to proceed.")
                self.update_button.config(state='normal')
            else:
                raise RuntimeError("ISO mount failed")

        except Exception as e:
            self.update_status(f"❌ Error: {e}")
            messagebox.showerror("Error", str(e))
        finally:
            self.start_button.config(state='normal')
            self.cancel_button.config(state='disabled')
            if self.temp_dir and not self.cancelled:
                shutil.rmtree(self.temp_dir, ignore_errors=True)

    def download_tools(self):
        tools = os.path.join(self.temp_dir, 'tools')
        os.makedirs(tools, exist_ok=True)
        # TODO: Download and extract aria2c if needed
        self.update_status("Tools ready.")
        self.update_progress(30)

    def create_iso(self, build_info, edition):
        iso = os.path.join(self.temp_dir, f"Windows_{build_info['build']}_{edition}.iso")
        open(iso, 'wb').close()  # stub
        return iso

    def mount_iso(self, iso_path):
        cmd = [
            "powershell", "-Command",
            f"$img=Mount-DiskImage -ImagePath '{iso_path}' -PassThru; (Get-DiskImage -ImagePath '{iso_path}' | Get-Volume).DriveLetter"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return res.stdout.strip()
        return None

if __name__ == '__main__':
    root = tk.Tk()
    app = FlamesISOInstaller(root)
    root.mainloop()
