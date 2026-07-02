#!/usr/bin/env python3

import customtkinter as ctk
import psutil
import platform
import subprocess
import os
import shutil
import tkinter as tk

# --- 1. BACKEND LOGIK (Hardware auslesen) ---
class HardwareMonitor:
    def __init__(self):
        self.cpu_name = self.detect_cpu_name()
        self.cpu_temp_sources = self.detect_cpu_temp_sources()

    def detect_cpu_name(self):
        """Erkennt den CPU Namen (optimiert für Linux & Windows)"""
        try:
            # Linux: /proc/cpuinfo auslesen
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo", "r") as f:
                    for line in f:
                        if "model name" in line:
                            model_name = line.split(":")[1].strip()
                            if "Intel" in model_name: return "INTEL"
                            if "AMD" in model_name: return "AMD"
                            if "ARM" in model_name: return "ARM"
                            return model_name.split()[0].upper()
            
            # Windows/Fallback
            proc_name = platform.processor()
            if "Intel" in proc_name: return "INTEL"
            if "AMD" in proc_name: return "AMD"
        except:
            pass
        return platform.system().upper() # Fallback z.B. "LINUX"

    def detect_cpu_temp_sources(self):
        """Findet Temperatursensoren"""
        sources = []
        try:
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        if any(x in entry.label.lower() for x in ['core', 'package', 'cpu', 'tctl', 'tdie']):
                            sources.append(("psutil", name, entry.label))
        except: pass
        
        # Manuelle Linux Pfade prüfen
        thermal_paths = ["/sys/class/thermal/thermal_zone0/temp", "/sys/class/hwmon/hwmon0/temp1_input"]
        for path in thermal_paths:
            if os.path.exists(path): sources.append(("thermal", path, "thermal_zone"))
        return sources

    def get_cpu_data(self):
        usage = psutil.cpu_percent(interval=0)
        temp = 0
        found = False
        for s_type, source, label in self.cpu_temp_sources:
            try:
                if s_type == "psutil":
                    for entry in psutil.sensors_temperatures()[source]:
                        if entry.label == label: temp = entry.current; found=True; break
                elif s_type == "thermal":
                    with open(source, "r") as f: 
                        val = float(f.read().strip())
                        temp = val/1000.0 if val > 1000 else val
                        found=True
            except: continue
            if found: break
        return usage, temp if found else None

    def get_gpu_data(self):
        temp, usage, vendor = None, None, "GPU"
        try:
            if shutil.which("nvidia-smi"):
                out = subprocess.check_output(["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu", "--format=csv,noheader"]).decode().split(",")
                return float(out[0]), float(out[1].split()[0]), "NVIDIA"
        except: pass
        return temp, usage, vendor

    def get_ram_data(self):
        ram = psutil.virtual_memory()
        return ram.percent, ram.used / (1024**3), ram.total / (1024**3)

# --- 2. UI KOMPONENTE (Eine einzelne Karte) ---
class CompactCard(ctk.CTkFrame):
    def __init__(self, master, vendor_name, icon="🔹"):
        super().__init__(master, fg_color="#1f1f1f", corner_radius=10, border_width=1, border_color="#333333")
        
        # Grid Setup
        self.grid_columnconfigure(1, weight=1)
        
        # Zeile 1: Name & Temp
        self.vendor_label = ctk.CTkLabel(self, text=f"{icon} {vendor_name}", font=("Arial", 11, "bold"), text_color="#888888", anchor="w")
        self.vendor_label.grid(row=0, column=0, padx=10, pady=(5,0), sticky="w")
        
        self.temp_label = ctk.CTkLabel(self, text="--°C", font=("Arial", 11), text_color="#aaaaaa", anchor="e")
        self.temp_label.grid(row=0, column=1, padx=10, pady=(5,0), sticky="e")

        # Zeile 2: Großer Prozentwert
        self.value_label = ctk.CTkLabel(self, text="0%", font=("Arial", 24, "bold"), text_color="#ffffff")
        self.value_label.grid(row=1, column=0, columnspan=2, padx=10, pady=(0,5), sticky="w")

        # Zeile 3: Ladebalken
        self.progress = ctk.CTkProgressBar(self, height=8)
        self.progress.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="ew")
        self.progress.set(0)

    def update_view(self, percent, temp_val=None, sub_text=None, vendor_update=None):
        # Dynamische Farbe (Ampel-System)
        color = "#3B8ED0" # Blau (Standard)
        if percent > 80: color = "#c42b1c" # Rot
        elif percent > 50: color = "#e3a008" # Gelb
        elif percent < 20: color = "#2cc985" # Grün

        self.value_label.configure(text=f"{percent:.1f}%")
        self.progress.set(percent / 100)
        self.progress.configure(progress_color=color)

        if temp_val is not None: 
            self.temp_label.configure(text=f"{temp_val:.0f}°C")
        elif sub_text: 
            self.temp_label.configure(text=sub_text)
            
        if vendor_update and vendor_update not in self.vendor_label.cget("text"):
            self.vendor_label.configure(text=f"🎮 {vendor_update}")

# --- 3. HAUPTFENSTER (Das Widget) ---
class DynamicWidget(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.monitor = HardwareMonitor()
        self.current_layout = None 
        self.settings_open = False

        # Fenster Setup
        self.title("Monitor")
        self.geometry("220x320") # Startgröße (Hochformat)
        self.min_size_val = 140
        
        self.overrideredirect(True)      # Rahmen entfernen
        self.attributes('-topmost', True) # Immer oben
        self.configure(fg_color="#111111")
        self.attributes('-alpha', 0.95)   # Start-Transparenz

        # Grid Konfiguration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Content Area wächst

        # --- HEADER (Drag Area & Settings) ---
        self.header = ctk.CTkFrame(self, fg_color="transparent", corner_radius=0, height=30)
        self.header.grid(row=0, column=0, sticky="ew")
        
        # Drag Logic Bindings
        self.header.bind("<Button-1>", self.start_move)
        self.header.bind("<B1-Motion>", self.do_move)

        self.title_lbl = ctk.CTkLabel(self.header, text=":: MONITOR ::", font=("Arial", 9, "bold"), text_color="#555555")
        self.title_lbl.pack(side="left", padx=10, expand=True)
        # Auch Text greifbar machen
        self.title_lbl.bind("<Button-1>", self.start_move)
        self.title_lbl.bind("<B1-Motion>", self.do_move)

        # Settings Button (Zahnrad)
        self.settings_btn = ctk.CTkButton(self.header, text="⚙", width=25, height=25, 
                                          fg_color="transparent", text_color="#666666", hover_color="#333333",
                                          command=self.toggle_settings)
        self.settings_btn.pack(side="right", padx=5)

        # --- SETTINGS BEREICH (Versteckt) ---
        self.settings_frame = ctk.CTkFrame(self, fg_color="#1a1a1a", corner_radius=0)
        
        self.opacity_label = ctk.CTkLabel(self.settings_frame, text="Transparenz:", font=("Arial", 10))
        self.opacity_label.pack(side="left", padx=10, pady=5)
        
        self.opacity_slider = ctk.CTkSlider(self.settings_frame, from_=0.3, to=1.0, number_of_steps=20, width=100, command=self.set_opacity)
        self.opacity_slider.set(0.95)
        self.opacity_slider.pack(side="right", padx=10, pady=5)

        # --- CONTENT BEREICH (Karten) ---
        self.content = ctk.CTkFrame(self, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Karten erstellen
        self.cpu_card = CompactCard(self.content, self.monitor.cpu_name, "💻")
        self.gpu_card = CompactCard(self.content, "GPU", "🎮")
        self.ram_card = CompactCard(self.content, "RAM", "💾")

        # Initial Layout setzen
        self.apply_vertical_layout()

        # --- RESIZE GRIP (Unten rechts) ---
        self.grip = ctk.CTkLabel(self, text="◢", font=("Arial", 14), text_color="#444444", cursor="sizing")
        self.grip.grid(row=3, column=0, sticky="se", padx=2, pady=0)
        self.grip.bind("<Button-1>", self.start_resize)
        self.grip.bind("<B1-Motion>", self.do_resize)

        # Rechtsklick Menü
        self.bind("<Button-3>", self.show_context_menu)
        
        # Event Listener für Layout-Wechsel
        self.bind("<Configure>", self.check_layout_change)

        # Start Update Loop
        self.update_metrics()

    # --- FUNKTIONEN ---
    def check_layout_change(self, event):
        if event.widget != self: return 

        w = self.winfo_width()
        h = self.winfo_height()

        # Automatische Umschaltung basierend auf Seitenverhältnis
        if w > h and self.current_layout != "horizontal":
            self.apply_horizontal_layout()
        elif h >= w and self.current_layout != "vertical":
            self.apply_vertical_layout()

    def apply_vertical_layout(self):
        self.current_layout = "vertical"
        for widget in self.content.winfo_children(): widget.grid_forget()
        
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_columnconfigure((1,2), weight=0)
        self.content.grid_rowconfigure((0,1,2), weight=1)

        self.cpu_card.grid(row=0, column=0, sticky="nsew", pady=2)
        self.gpu_card.grid(row=1, column=0, sticky="nsew", pady=2)
        self.ram_card.grid(row=2, column=0, sticky="nsew", pady=2)

    def apply_horizontal_layout(self):
        self.current_layout = "horizontal"
        for widget in self.content.winfo_children(): widget.grid_forget()

        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_rowconfigure((1,2), weight=0)
        self.content.grid_columnconfigure((0,1,2), weight=1)

        self.cpu_card.grid(row=0, column=0, sticky="nsew", padx=2)
        self.gpu_card.grid(row=0, column=1, sticky="nsew", padx=2)
        self.ram_card.grid(row=0, column=2, sticky="nsew", padx=2)

    def toggle_settings(self):
        if self.settings_open:
            self.settings_frame.grid_forget()
            self.settings_open = False
        else:
            self.settings_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
            self.settings_open = True

    def set_opacity(self, value):
        self.attributes('-alpha', value)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def do_move(self, event):
        x = self.winfo_x() + (event.x - self.x)
        y = self.winfo_y() + (event.y - self.y)
        self.geometry(f"+{x}+{y}")

    def start_resize(self, event):
        self.resize_start_x = event.x_root
        self.resize_start_y = event.y_root
        self.start_w = self.winfo_width()
        self.start_h = self.winfo_height()

    def do_resize(self, event):
        dx = event.x_root - self.resize_start_x
        dy = event.y_root - self.resize_start_y
        new_w = max(self.min_size_val, self.start_w + dx)
        new_h = max(self.min_size_val, self.start_h + dy)
        self.geometry(f"{new_w}x{new_h}")

    def show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0, bg="#2b2b2b", fg="white")
        menu.add_command(label="Beenden", command=self.destroy)
        menu.tk_popup(event.x_root, event.y_root)

    def update_metrics(self):
        try:
            # CPU Update
            cpu_usage, cpu_temp = self.monitor.get_cpu_data()
            self.cpu_card.update_view(cpu_usage, cpu_temp)

            # GPU Update
            gpu_temp, gpu_usage, gpu_vendor = self.monitor.get_gpu_data()
            if gpu_vendor:
                self.gpu_card.update_view(gpu_usage if gpu_usage else 0, gpu_temp, vendor_update=gpu_vendor)
            else:
                self.gpu_card.update_view(0, sub_text="N/A")

            # RAM Update
            mem_percent, used, total = self.monitor.get_ram_data()
            self.ram_card.update_view(mem_percent, sub_text=f"{used:.1f}GB")
        except:
            pass # Verhindert Absturz bei Lesefehlern

        self.after(1000, self.update_metrics)

if __name__ == "__main__":
    app = DynamicWidget()
    app.mainloop()
