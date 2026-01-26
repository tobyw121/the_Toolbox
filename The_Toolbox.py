import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject
import subprocess
import os
import sys
import urllib.request

# --- KONFIGURATION ---
# Einfach den Link kopieren, den du im Browser siehst, wenn du auf dein Repo gehst:
REPO_URL = "https://github.com/tobyw121/the_Toolbox"
BRANCH = "main" 

# Liste der Dateien, die exakt so im Repo liegen müssen:
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
        
        # Automatische URL-Korrektur (Github Web -> Raw)
        self.base_url = self.get_raw_base_url(REPO_URL, BRANCH)
        print(f"Update-Server: {self.base_url}")

        if self.script_name not in FILES_TO_SYNC:
            FILES_TO_SYNC.append(self.script_name)

        self.icon_path = os.path.join(self.script_dir, 'icon.png')

        # Icon Fallback
        if os.path.exists(self.icon_path):
            icon_arg = self.icon_path
        else:
            icon_arg = "system-run"

        self.indicator = AppIndicator3.Indicator.new(
            self.app, icon_arg,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

    def get_raw_base_url(self, url, branch):
        """Wandelt normale GitHub-URLs in Raw-URLs um."""
        url = url.strip()
        # Entferne .git Endung falls vorhanden
        if url.endswith(".git"):
            url = url[:-4]
        
        # Entferne abschließenden Slash
        if url.endswith("/"):
            url = url[:-1]

        # Wenn es schon eine raw-URL ist: Super.
        if "raw.githubusercontent.com" in url:
            return url + "/"
        
        # Wenn es eine normale github.com URL ist, umbauen
        if "github.com" in url:
            # Ersetzt github.com durch raw.githubusercontent.com
            # Struktur: https://github.com/USER/REPO -> https://raw.githubusercontent.com/USER/REPO/main/
            raw_url = url.replace("github.com", "raw.githubusercontent.com")
            return f"{raw_url}/{branch}/"
            
        return url + "/"

    def build_menu(self):
        menu = Gtk.Menu()

        item_app_update = Gtk.MenuItem(label='Toolbox synchronisieren')
        item_app_update.connect('activate', self.download_updates)
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

    def download_updates(self, source):
        updated_files = []
        errors = []
        needs_restart = False

        self.show_notification("Update gestartet", f"Prüfe {self.base_url}...")

        for filename in FILES_TO_SYNC:
            remote_url = self.base_url + filename
            local_path = os.path.join(self.script_dir, filename)

            try:
                # Timeout hinzugefügt, falls kein Internet da ist
                with urllib.request.urlopen(remote_url, timeout=10) as response:
                    remote_data = response.read()

                local_data = None
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        local_data = f.read()

                if local_data != remote_data:
                    with open(local_path, 'wb') as f:
                        f.write(remote_data)
                    updated_files.append(filename)
                    print(f"Aktualisiert: {filename}")
                    
                    if filename == self.script_name:
                        needs_restart = True
                    
                    if filename.endswith(".sh"):
                        os.chmod(local_path, 0o755)

            except urllib.error.HTTPError as e:
                # 404 bedeutet Datei nicht im Repo gefunden -> Ignorieren oder Fehler melden
                print(f"Datei nicht gefunden (404): {filename}")
                errors.append(filename)
            except Exception as e:
                print(f"Fehler bei {filename}: {e}")
                errors.append(filename)

        if updated_files:
            msg = f"Aktualisiert: {', '.join(updated_files)}"
            if needs_restart:
                self.show_notification("Neustart", "Hauptprogramm wurde aktualisiert.")
                import time
                time.sleep(1)
                python = sys.executable
                os.execl(python, python, *sys.argv)
            else:
                self.show_notification("Erfolg", msg)
        elif errors:
            self.show_notification("Warnung", "Einige Dateien konnten nicht geladen werden.")
        else:
            self.show_notification("Aktuell", "Keine Updates verfügbar.")

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
            print(f"Fehler: Skript '{full_path}' nicht gefunden.")

    def run_python_script(self, source, script_name):
        full_path = os.path.join(self.script_dir, script_name)
        try:
            subprocess.Popen(['python3', full_path])
        except FileNotFoundError:
            print(f"Fehler: Skript '{full_path}' nicht gefunden.")

if __name__ == "__main__":
    try:
        indicator = SystemTrayIcon()
        Gtk.main()
    except KeyboardInterrupt:
        pass
