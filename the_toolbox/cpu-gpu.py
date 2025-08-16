#!/usr/bin/env python3

import psutil
import tkinter as tk
from tkinter import ttk, font
import subprocess
import json
import os

def get_cpu_temp():
    """Liest die CPU-Temperatur aus."""
    try:
        temps = psutil.sensors_temperatures()
        for key, entries in temps.items():
            for entry in entries:
                if "core" in entry.label.lower():
                    return f"{entry.current:.1f}°C"
    except Exception as e:
        print(f"Fehler beim Auslesen der CPU-Temperatur: {e}")
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            temp = int(f.read()) / 1000.0
            return f"{temp:.1f}°C"
    except FileNotFoundError:
        print("Fehler: /sys/class/thermal/thermal_zone0/temp nicht gefunden.")
    return "N/A"

def install_gpu_dependencies():
    """Versucht, die benötigten Pakete für die GPU-Temperaturmessung zu installieren."""
    package_managers = {
        "apt-get": ["nvidia-utils", "radeontop", "lm-sensors"],
        "dnf": ["nvidia-settings", "radeontop", "lm-sensors"],
        "pacman": ["nvidia", "radeontop", "lm-sensors"],
        "zypper": ["nvidia-gl", "radeontop", "lm-sensors"],
    }

    for pm, packages in package_managers.items():
        try:
            subprocess.check_call(["which", pm])
            for package in packages:
                try:
                    subprocess.check_call([pm, "install", "-y", package])
                except subprocess.CalledProcessError:
                    pass  # Paket eventuell schon installiert
            return  # Erfolgreiche Installation
        except subprocess.CalledProcessError:
            pass  # Paketmanager nicht gefunden

    print("Warnung: Konnte keine passenden Pakete für die GPU-Temperaturmessung finden.")

def get_gpu_temp():
    """Versucht, die GPU-Temperatur für verschiedene Hersteller auszulesen."""
    install_gpu_dependencies()  # Abhängigkeiten installieren (falls nötig)

    try:
        # NVIDIA
        output = subprocess.check_output(["nvidia-smi", "--query-gpu=temperature.gpu", "--format=csv,noheader"])
        temp = output.decode('utf-8').strip()
        return f"{temp}°C (NVIDIA)"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        # AMD (mit radeontop)
        output = subprocess.check_output(["radeontop", "-d", "1", "-l", "1"])
        lines = output.decode('utf-8').splitlines()
        for line in lines:
            if "GPU Temp" in line:
                temp = line.split(":")[1].strip()
                return f"{temp} (AMD)"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    try:
        # Intel (mit sensors)
        output = subprocess.check_output(["sensors"])
        lines = output.decode('utf-8').splitlines()
        for line in lines:
            if "Package id 0" in line:
                temp = line.split(":")[1].strip().split()[0]
                return f"{temp} (Intel)"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    if "N/A" not in get_gpu_temp():  # Grafikkarte erkannt
        tk.messagebox.showwarning(
            "Fehlende Abhängigkeit",
            "Grafikkarte erkannt, aber die benötigte Abhängigkeit für die Temperaturmessung fehlt.\n"
            "Bitte installieren Sie die entsprechenden Pakete manuell."
        )

    return "N/A"  # Kein unterstützter Hersteller gefunden

def get_gpu_temp_and_usage():
    """Liest GPU-Temperatur und -Auslastung für verschiedene Treiber aus."""
    temp, usage = "N/A", "N/A"

    # Proprietäre Treiber (NVIDIA, AMD, Intel)
    for func in [get_nvidia_info, get_amd_info, get_intel_info]:
        try:
            temp, usage = func()
            if temp != "N/A" and usage != "N/A":
                return temp, usage
        except Exception as e:
            print(f"Fehler beim Auslesen der GPU-Daten ({func.__name__}): {e}")

    # Nouveau-Treiber
    try:
        temp = get_nouveau_temp()
        if temp != "N/A":
            return temp, "N/A"  # Auslastung nicht verfügbar für Nouveau
    except Exception as e:
        print(f"Fehler beim Auslesen der Nouveau-Temperatur: {e}")

    # Wenn keine GPU-Daten gefunden werden
    if temp == "N/A" and usage == "N/A":
        install_gpu_dependencies()  # Erneut versuchen, Abhängigkeiten zu installieren

        temp, usage = get_gpu_temp_and_usage()  # Erneut versuchen, Daten auszulesen

        if temp == "N/A" and usage == "N/A":
            tk.messagebox.showwarning(
                "GPU nicht gefunden",
                "Es wurde keine kompatible GPU gefunden oder die erforderlichen Abhängigkeiten fehlen.\n"
                "Bitte installieren Sie die entsprechenden Pakete manuell."
            )

    return temp, usage

def get_cpu_usage():
    """Liest die CPU-Auslastung aus."""
    return f"{psutil.cpu_percent(interval=1):.1f}%"

def get_ram_info():
    """Liest den RAM-Verbrauch und die RAM-Auslastung aus."""
    ram = psutil.virtual_memory()
    total = ram.total / 1024**3  # in GB
    used = ram.used / 1024**3
    percent = ram.percent
    return f"{used:.1f} GB / {total:.1f} GB ({percent:.1f}%)"

def update_temps():
    """Aktualisiert die Anzeigen."""
    try:
        cpu_temp_label.config(text=f"CPU: {get_cpu_temp()}, {get_cpu_usage()}")
    except Exception as e:
        print(f"Fehler bei der Aktualisierung der CPU-Temperatur: {e}")

    try:
        gpu_temp, gpu_usage = get_gpu_temp_and_usage()
        gpu_temp_label.config(text=f"GPU: {gpu_temp}, {gpu_usage}")  # Anzeige von Temperatur und Auslastung
    except Exception as e:
        print(f"Fehler bei der Aktualisierung der GPU-Daten: {e}")

    ram_label.config(text=f"RAM: {get_ram_info()}")
    root.after(1000, update_temps)  # Alle 1000ms aktualisieren

def on_right_click(event):
    """Zeigt das Kontextmenü bei Rechtsklick an."""
    try:
        popup_menu.tk_popup(event.x_root, event.y_root)
    finally:
        popup_menu.grab_release()

def quit_app():
    """Beendet die Anwendung."""
    root.destroy()
# Neue Funktionen für GPU-Informationen

def get_nvidia_info():
    """Liest Temperatur und Auslastung für NVIDIA GPUs aus."""
    output = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=temperature.gpu,utilization.gpu", "--format=csv,noheader"]
    )
    temp, usage = output.decode("utf-8").strip().split(",")
    return f"{temp}°C", f"{usage} (NVIDIA)"

def get_amd_info():
    """Liest Temperatur und Auslastung für AMD GPUs aus."""
    output = subprocess.check_output(["radeontop", "-d", "1", "-l", "1"])
    lines = output.decode('utf-8').splitlines()
    temp, usage = "N/A", "N/A"
    for line in lines:
        if "GPU Temp" in line:
            temp = line.split(":")[1].strip()
        if "GPU Load" in line:
            usage = line.split(":")[1].strip()
    return f"{temp}°C", f"{usage} (AMD)"

def get_intel_info():
    """Liest Temperatur und Auslastung für Intel GPUs aus."""
    # ... (Ihr vorhandener Code für Intel-GPUs)

def get_nouveau_temp():
    """Liest die Temperatur für Nouveau-Treiber aus."""
    try:
        output = subprocess.check_output(["nvidia-settings", "-q", "GPUCoreTemp", "-t"])
        temp = output.decode("utf-8").strip().split(":")[1].strip()
        return f"{temp}°C (Nouveau)"
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass  # nvidia-settings nicht gefunden oder Fehler
    return "N/A"

# GUI erstellen
root = tk.Tk()
root.title("Systemüberwachung")

# Styling (optional)
style = ttk.Style()
style.theme_use('clam')  # Oder ein anderes Theme

# System-Schriftart ermitteln
default_font = font.nametofont("TkDefaultFont")

# Labels für CPU, GPU und RAM (mit System-Schriftart)
cpu_temp_label = ttk.Label(root, text="CPU: ...", font=(default_font.cget("family"), 9))  
cpu_temp_label.pack(pady=5)

gpu_temp_label = ttk.Label(root, text="GPU: ...", font=(default_font.cget("family"), 9))
gpu_temp_label.pack(pady=5)

ram_label = ttk.Label(root, text="RAM: ...", font=(default_font.cget("family"), 9))
ram_label.pack(pady=5)
# Kontextmenü erstellen
popup_menu = tk.Menu(root, tearoff=0)
popup_menu.add_command(label="Beenden", command=quit_app)

# Rechtsklick-Ereignis binden
root.bind("<Button-3>", on_right_click)

# Erste Aktualisierung und Start der Schleife
update_temps()
root.mainloop()

