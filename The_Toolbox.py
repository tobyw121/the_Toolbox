import gi
import os
import sys
import subprocess
import urllib.request
import time
import random
import shutil  ## WICHTIG: Zum Löschen von Ordnern

gi.require_version('Gtk', '3.0')

try:
    gi.require_version('AppIndicator3', '0.1')
    from gi.repository import AppIndicator3
except ValueError:
    try:
        gi.require_version('AyatanaAppIndicator3', '0.1')
        from gi.repository import AyatanaAppIndicator3 as AppIndicator3
    except ValueError:
        print("FEHLER: AppIndicator Bibliothek fehlt.")
        sys.exit(1)

from gi.repository import Gtk, GLib

# --- KONFIGURATION ---
REPO_URL = "https://github.com/tobyw121/the_Toolbox"
BRANCH = "main"
UPDATE_INTERVAL_SECONDS = 20

FILES_TO_SYNC = [
    "update.sh",
    "nmcli.sh",
    "wine.sh",
    "cpu-gpu.py",
    "pkill.sh",
    "icon.png"
]
# ---------------------

class SystemTrayIcon:
    def __init__(self):
        self.app = 'System_Icon'
        self.script_dir = os.path.dirname(os.path.realpath(__file__))
        self.script_name = os.path.basename(__file__)
        
        self.base_url = self.get_raw_base_url(REPO_URL, BRANCH)
        print(f"Update-Server: {self.base_url}")

        if self.script_name not in FILES_TO_SYNC:
            FILES_TO_SYNC.append(self.script_name)

        self.icon_path = os.path.join(self.script_dir, 'icon.png')
        if os.path.exists(self.icon_path):
            icon_arg = self.icon_path
        else:
            icon_arg = "preferences-system"

        self.indicator = AppIndicator3.Indicator.new(
            self.app, icon_arg,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

        # --- AUTOMATISCHER UPDATER ---
        print(f"Starte Auto-Update (Cache-Cleanup aktiv) alle {UPDATE_INTERVAL_SECONDS} Sekunden...")
        GLib.timeout_add(UPDATE_INTERVAL_SECONDS * 1000, self.auto_update_task)

    def get_raw_base_url(self, url, branch):
        url = url.strip()
        if url.endswith(".git"): url = url[:-4]
        if url.endswith("/"): url = url[:-1]
        
        if "raw.githubusercontent.com" in url:
            return url + "/"
        
        if "github.com" in url:
            raw_url = url.replace("github.com", "raw.githubusercontent.com")
            return f"{raw_url}/{branch}/"
        return url + "/"

    def build_menu(self):
        menu = Gtk.Menu()

        item_app_update = Gtk.MenuItem(label='Jetzt manuell prüfen')
        item_app_update.connect('activate', lambda x: self.perform_update(silent=False))
        menu.append(item_app_update)

        menu.append(Gtk.SeparatorMenuItem())

        item_update = Gtk.MenuItem(label='Systemupdate')
        item_update.connect('activate', self.run_script_in_terminal, 'update.sh')
        menu.append(item_update)

        item_wireguard = Gtk.MenuItem(label='Wireguard fix')
        item_wireguard.connect('activate', self.run_script_in_terminal, 'nmcli.sh')
        menu.append(item_wireguard)

        item_wine = Gtk.MenuItem(label='Wine installer')
        item_wine.connect('activate', self.run_script_in_terminal, 'wine.sh')
        menu.append(item_wine)

        item_cpu_gpu = Gtk.MenuItem(label='CPU-GPU')
        item_cpu_gpu.connect('activate', self.run_python_script, 'cpu-gpu.py')
        menu.append(item_cpu_gpu)

        item_pkill = Gtk.MenuItem(label='PKILL')
        item_pkill.connect('activate', self.run_script_in_terminal, 'pkill.sh')
        menu.append(item_pkill)

        menu.append(Gtk.SeparatorMenuItem())

        item_quit = Gtk.MenuItem(label='Beenden')
        item_quit.connect('activate', Gtk.main_quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def auto_update_task(self):
        self.perform_update(silent=True)
        return True 

    def perform_update(self, silent=True):
        updated_files = []
        errors = []
        restart_needed = False
        
        # 1. Netzwerk-Cache bereinigen
        urllib.request.urlcleanup()

        if not silent:
            self.show_notification("Update", "Prüfe auf Änderungen...")

        for filename in FILES_TO_SYNC:
            # Cache-Busting per URL (Timestamp)
            timestamp = int(time.time())
            remote_url = f"{self.base_url}{filename}?t={timestamp}"
            local_path = os.path.join(self.script_dir, filename)

            try:
                # DOWNLOAD
                with urllib.request.urlopen(remote_url, timeout=5) as response:
                    remote_data = response.read()

                if len(remote_data) == 0: continue
                
                # HTML Schutz
                if b"<!doctype html>" in remote_data[:50].lower() or b"<html" in remote_data[:50].lower():
                    print(f"Warnung: HTML empfangen bei {filename}")
                    continue

                # VERGLEICH
                local_data = b""
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        local_data = f.read()

                if local_data != remote_data:
                    print(f"!!! UPDATE GEFUNDEN: {filename} !!!")
                    with open(local_path, 'wb') as f:
                        f.write(remote_data)
                    
                    if filename.endswith(".sh"):
                        os.chmod(local_path, 0o755)

                    updated_files.append(filename)
                    
                    if filename == self.script_name:
                        restart_needed = True

            except Exception as e:
                print(f"Fehler bei {filename}: {e}")
                if not silent: errors.append(filename)

        # BERICHT & NEUSTART
        if updated_files:
            msg = f"Aktualisiert: {', '.join(updated_files)}"
            
            if restart_needed:
                self.show_notification("Update", "Neustart zur Installation...")
                
                # --- CACHE CLEANUP VOR DEM NEUSTART ---
                self.clean_local_cache()
                # --------------------------------------
                
                time.sleep(1)
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                self.show_notification("Update erfolgreich", msg)
        
        elif not silent and errors:
            self.show_notification("Fehler", "Probleme beim Laden.")
        
        elif not silent:
            self.show_notification("Alles aktuell", "Keine neuen Versionen.")

    def clean_local_cache(self):
        """Löscht __pycache__ und temporäre Dateien, um sauberen Neustart zu garantieren."""
        print("Bereinige System-Cache...")
        
        # 1. __pycache__ Ordner löschen
        pycache_path = os.path.join(self.script_dir, "__pycache__")
        if os.path.exists(pycache_path):
            try:
                shutil.rmtree(pycache_path)
                print(f"Gelöscht: {pycache_path}")
            except Exception as e:
                print(f"Fehler beim Löschen von pycache: {e}")

        # 2. Falls Python Bytecode-Dateien (.pyc) direkt im Ordner liegen
        for file in os.listdir(self.script_dir):
            if file.endswith(".pyc"):
                try:
                    os.remove(os.path.join(self.script_dir, file))
                except:
                    pass

    def show_notification(self, title, message):
        try:
            subprocess.Popen(['notify-send', title, message])
        except FileNotFoundError:
            print(f"[{title}] {message}")

    def run_script_in_terminal(self, source, script_name):
        full_path = os.path.join(self.script_dir, script_name)
        try:
            desktop_env = os.environ.get('DESKTOP_SESSION')
            if desktop_env in ['xfce', 'mate']:
                terminal_command = 'xfce4-terminal' if desktop_env == 'xfce' else 'mate-terminal'
                subprocess.Popen([terminal_command, '-x', 'sudo', 'bash', full_path])
            else:
                subprocess.Popen(['xterm', '-e', 'sudo', 'bash', full_path])
        except FileNotFoundError:
            print(f"Datei fehlt: {full_path}")

    def run_python_script(self, source, script_name):
        full_path = os.path.join(self.script_dir, script_name)
        subprocess.Popen(['python3', full_path])

if __name__ == "__main__":
    try:
        indicator = SystemTrayIcon()
        Gtk.main()
    except KeyboardInterrupt:
        pass
