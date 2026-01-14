#!/usr/bin/env python3

import psutil
import tkinter as tk
from tkinter import ttk, font, messagebox
import subprocess
import os
import platform
import time
import shutil
from functools import lru_cache

class SystemMonitor:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("System Monitor")
        self.root.geometry("400x250")
        self.root.resizable(False, False)
        
        # Color scheme
        self.bg_color = "#2e2e2e"
        self.fg_color = "#ffffff"
        self.accent_color = "#4e79a0"
        self.status_color = "#aaaaaa"
        
        # Initialize
        self.setup_style()
        self.setup_ui()
        self.last_update_time = 0
        self.update_interval = 2000  # ms
        self.gpu_dependencies_installed = False
        self.cpu_temp_sources = self.detect_cpu_temp_sources()
        
        # Start monitoring
        self.update_status(f"Initializing on {platform.system()} {platform.release()}")
        self.update_metrics()

    def setup_style(self):
        """Configure modern UI styling"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure root background
        self.root.configure(bg=self.bg_color)
        
        # Widget styles
        style.configure("TFrame", background=self.bg_color)
        style.configure("TLabel", 
                      background=self.bg_color, 
                      foreground=self.fg_color,
                      font=('Segoe UI', 10))
        style.configure("Header.TLabel", 
                      font=('Segoe UI', 12, 'bold'),
                      foreground=self.accent_color)
        style.configure("Status.TLabel", 
                      font=('Segoe UI', 8),
                      foreground=self.status_color)
        
        # Temperature styles
        style.configure("Normal.TLabel", foreground="#4CAF50")  # Green
        style.configure("Warm.TLabel", foreground="#FFC107")   # Yellow
        style.configure("Hot.TLabel", foreground="#F44336")    # Red

    def setup_ui(self):
        """Create modern user interface"""
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header = ttk.Label(main_frame, 
                         text="SYSTEM MONITOR", 
                         style="Header.TLabel")
        header.pack(pady=(0, 15))
        
        # Metrics frame
        metrics_frame = ttk.Frame(main_frame)
        metrics_frame.pack(fill=tk.X, pady=5)
        
        # CPU display
        self.cpu_icon = tk.Label(metrics_frame, 
                                text="", 
                                font=('Segoe UI', 14), 
                                bg=self.bg_color, 
                                fg=self.fg_color)
        self.cpu_icon.grid(row=0, column=0, padx=5, sticky="w")
        self.cpu_label = ttk.Label(metrics_frame, 
                                  text="Initializing...", 
                                  style="TLabel")
        self.cpu_label.grid(row=0, column=1, sticky="w")
        
        # GPU display
        self.gpu_icon = tk.Label(metrics_frame, 
                                text="", 
                                font=('Segoe UI', 14), 
                                bg=self.bg_color, 
                                fg=self.fg_color)
        self.gpu_icon.grid(row=1, column=0, padx=5, sticky="w")
        self.gpu_label = ttk.Label(metrics_frame, 
                                  text="Initializing...", 
                                  style="TLabel")
        self.gpu_label.grid(row=1, column=1, sticky="w")
        
        # RAM display
        self.ram_icon = tk.Label(metrics_frame, 
                               text="", 
                               font=('Segoe UI', 14), 
                               bg=self.bg_color, 
                               fg=self.fg_color)
        self.ram_icon.grid(row=2, column=0, padx=5, sticky="w")
        self.ram_label = ttk.Label(metrics_frame, 
                                 text="Initializing...", 
                                 style="TLabel")
        self.ram_label.grid(row=2, column=1, sticky="w")
        
        # Status bar
        self.status_bar = ttk.Label(main_frame, 
                                  text="Initializing...", 
                                  style="Status.TLabel",
                                  relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, pady=(15, 0), anchor='s')
        
        # Context menu
        self.setup_context_menu()

    def setup_context_menu(self):
        """Create right-click context menu"""
        self.popup_menu = tk.Menu(self.root, tearoff=0, bg=self.bg_color, fg=self.fg_color)
        self.popup_menu.add_command(label="Refresh", command=self.force_update)
        self.popup_menu.add_separator()
        self.popup_menu.add_command(label="Exit", command=self.quit_app)
        self.root.bind("<Button-3>", self.show_context_menu)

    def show_context_menu(self, event):
        """Show context menu on right-click"""
        try:
            self.popup_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.popup_menu.grab_release()

    def update_status(self, message):
        """Update status bar with timestamp"""
        timestamp = time.strftime("%H:%M:%S")
        self.status_bar.config(text=f"{timestamp} - {message}")

    def force_update(self):
        """Force immediate metrics update"""
        self.last_update_time = 0
        self.update_metrics()

    def quit_app(self):
        """Exit the application"""
        self.root.destroy()

    def detect_cpu_temp_sources(self):
        """Detect available CPU temperature sources"""
        sources = []
        
        # 1. Check psutil sensors
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if any(x in entry.label.lower() for x in ['core', 'package', 'cpu', 'tctl', 'tdie']):
                            sources.append(("psutil", name, entry.label))
                            self.update_status(f"Found CPU temp source: psutil/{name}/{entry.label}")
        except Exception as e:
            self.update_status(f"psutil sensors error: {str(e)}")
        
        # 2. Check Linux thermal zones
        thermal_paths = [
            "/sys/class/thermal/thermal_zone0/temp",
            "/sys/class/thermal/thermal_zone1/temp",
            "/sys/class/hwmon/hwmon0/temp1_input",
            "/sys/class/hwmon/hwmon1/temp1_input"
        ]
        
        for path in thermal_paths:
            if os.path.exists(path):
                sources.append(("thermal", path, "thermal_zone"))
                self.update_status(f"Found CPU temp source: {path}")
        
        # 3. Check sensors command
        if shutil.which("sensors"):
            sources.append(("sensors", "lm-sensors", "sensors command"))
            self.update_status("Found CPU temp source: lm-sensors")
        
        if not sources:
            self.update_status("Warning: No CPU temperature sources found")
        
        return sources

    def get_cpu_temperature(self):
        """Get CPU temperature from best available source"""
        for source_type, source, label in self.cpu_temp_sources:
            try:
                if source_type == "psutil":
                    temps = psutil.sensors_temperatures()
                    if source in temps:
                        for entry in temps[source]:
                            if any(x in entry.label.lower() for x in ['core', 'package', 'cpu', 'tctl', 'tdie']):
                                return entry.current
                
                elif source_type == "thermal":
                    with open(source, "r") as f:
                        millidegrees = float(f.read().strip())
                        if millidegrees > 1000:  # Assume it's in millidegrees
                            return millidegrees / 1000.0
                        return millidegrees  # Already in degrees
                
                elif source_type == "sensors":
                    output = subprocess.check_output(["sensors"], stderr=subprocess.PIPE)
                    lines = output.decode("utf-8").splitlines()
                    for line in lines:
                        if any(x in line for x in ["Package id", "Tdie", "CPU Temp", "Core 0"]):
                            temp_str = line.split(":")[1].split()[0]
                            return float(temp_str.replace("+", "").replace("°C", ""))
            except Exception as e:
                self.update_status(f"Error reading {source_type}: {str(e)}")
                continue
        
        return None

    def get_gpu_info(self):
        """Get GPU temperature and usage"""
        if not self.gpu_dependencies_installed:
            self.install_gpu_dependencies()
        
        # Try NVIDIA first
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu", "--format=csv,noheader"],
                stderr=subprocess.PIPE
            )
            temp, usage = output.decode("utf-8").strip().split(",")
            return float(temp), float(usage.strip().split()[0]), "NVIDIA"
        except Exception:
            pass
        
        # Try AMD
        try:
            output = subprocess.check_output(
                ["rocm-smi", "--showtemp", "--showuse"],
                stderr=subprocess.PIPE
            )
            lines = output.decode("utf-8").splitlines()
            temp = usage = None
            for line in lines:
                if "Temperature" in line:
                    temp = float(line.split(":")[1].strip().split()[0])
                elif "GPU use" in line:
                    usage = float(line.split(":")[1].strip().split()[0])
            if temp is not None and usage is not None:
                return temp, usage, "AMD"
        except Exception:
            pass
        
        # Try Intel
        try:
            output = subprocess.check_output(["sensors"], stderr=subprocess.PIPE)
            lines = output.decode("utf-8").splitlines()
            for line in lines:
                if any(x in line for x in ["GPU Temp", "gt"]):
                    temp_str = line.split(":")[1].split()[0]
                    return float(temp_str.replace("+", "").replace("°C", "")), 0, "Intel"
        except Exception:
            pass
        
        return None, None, None

    def install_gpu_dependencies(self):
        """Install required GPU monitoring packages"""
        system = platform.system()
        if system != "Linux":
            return
            
        packages = {
            "nvidia": ["nvidia-utils"],
            "amd": ["rocm-smi"],
            "intel": ["lm-sensors"]
        }
        
        installed = False
        
        # Ubuntu/Debian
        if shutil.which("apt"):
            for pkg_type, pkgs in packages.items():
                for pkg in pkgs:
                    try:
                        subprocess.run(
                            ["sudo", "apt", "install", "-y", pkg],
                            check=True,
                            stderr=subprocess.PIPE
                        )
                        installed = True
                        self.update_status(f"Installed: {pkg}")
                    except subprocess.CalledProcessError:
                        continue
        
        # Arch Linux
        elif shutil.which("pacman"):
            for pkg_type, pkgs in packages.items():
                for pkg in pkgs:
                    try:
                        subprocess.run(
                            ["sudo", "pacman", "-S", "--noconfirm", pkg],
                            check=True,
                            stderr=subprocess.PIPE
                        )
                        installed = True
                        self.update_status(f"Installed: {pkg}")
                    except subprocess.CalledProcessError:
                        continue
        
        if installed:
            self.gpu_dependencies_installed = True

    def get_temp_style(self, temp):
        """Determine style based on temperature"""
        if temp > 80:
            return "Hot.TLabel"
        elif temp > 60:
            return "Warm.TLabel"
        return "Normal.TLabel"

    def update_metrics(self):
        """Update all system metrics"""
        try:
            current_time = time.time() * 1000
            if current_time - self.last_update_time < self.update_interval:
                self.root.after(100, self.update_metrics)
                return
                
            self.last_update_time = current_time
            
            # CPU metrics
            cpu_temp = self.get_cpu_temperature()
            cpu_usage = psutil.cpu_percent(interval=1)
            
            if cpu_temp is not None:
                temp_style = self.get_temp_style(cpu_temp)
                self.cpu_label.config(
                    text=f"CPU: {cpu_temp:.1f}°C | Usage: {cpu_usage:.1f}%",
                    style=temp_style
                )
            else:
                self.cpu_label.config(
                    text=f"CPU: Usage: {cpu_usage:.1f}% (Temp: N/A)",
                    style="TLabel"
                )
            
            # GPU metrics
            gpu_temp, gpu_usage, gpu_vendor = self.get_gpu_info()
            if all(v is not None for v in [gpu_temp, gpu_usage, gpu_vendor]):
                temp_style = self.get_temp_style(gpu_temp)
                self.gpu_label.config(
                    text=f"GPU: {gpu_temp:.1f}°C | Usage: {gpu_usage:.1f}% ({gpu_vendor})",
                    style=temp_style
                )
            else:
                self.gpu_label.config(text="GPU: Not available")
            
            # RAM metrics
            ram = psutil.virtual_memory()
            self.ram_label.config(
                text=f"RAM: {ram.used / (1024**3):.1f}GB / {ram.total / (1024**3):.1f}GB ({ram.percent:.1f}%)"
            )
            
            self.update_status("Metrics updated")
            
        except Exception as e:
            self.update_status(f"Error: {str(e)}")
        
        self.root.after(100, self.update_metrics)

if __name__ == "__main__":
    try:
        monitor = SystemMonitor()
        monitor.root.mainloop()
    except Exception as e:
        print(f"Fatal error: {str(e)}")
        raise
