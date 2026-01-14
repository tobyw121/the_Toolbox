import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
from gi.repository import Gtk, AppIndicator3, GObject
import subprocess
import os

class SystemTrayIcon:
    def __init__(self):
        self.app = 'System_Icon'
        # Pfad zu den Dateien und Skripten
        self.home_dir = os.path.expanduser("~")
        self.icon_path = os.path.join(self.home_dir, '/home/*/Dokumente/the_toolbox/icon.png')
        self.script_dir = os.path.join(self.home_dir, '/home/*/Dokumente/the_toolbox/')

        self.indicator = AppIndicator3.Indicator.new(
            self.app, self.icon_path,
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        self.indicator.set_menu(self.build_menu())

    def build_menu(self):
        menu = Gtk.Menu()

        # Systemupdate
        item_update = Gtk.MenuItem(label='Systemupdate')
        item_update.connect('activate', self.run_script_in_terminal, os.path.join(self.script_dir, 'update.sh'))
        menu.append(item_update)

        # Wireguard fix
        item_wireguard = Gtk.MenuItem(label='Wireguard fix')
        item_wireguard.connect('activate', self.run_script_in_terminal, os.path.join(self.script_dir, 'nmcli.sh'))
        menu.append(item_wireguard)

        # Wine installer
        item_wine = Gtk.MenuItem(label='Wine installer')
        item_wine.connect('activate', self.run_script_in_terminal, os.path.join(self.script_dir, 'wine.sh'))
        menu.append(item_wine)

        # CPU-GPU
        item_cpu_gpu = Gtk.MenuItem(label='CPU-GPU')
        item_cpu_gpu.connect('activate', self.run_python_script, os.path.join(self.script_dir, 'cpu-gpu.py'))
        menu.append(item_cpu_gpu)

        # PKILL
        item_pkill = Gtk.MenuItem(label='PKILL')
        item_pkill.connect('activate', self.run_script_in_terminal, os.path.join(self.script_dir, 'pkill.sh'))
        menu.append(item_pkill)

        # Beenden
        item_quit = Gtk.MenuItem(label='Beenden')
        item_quit.connect('activate', Gtk.main_quit)
        menu.append(item_quit)

        menu.show_all()
        return menu

    def run_script_in_terminal(self, source, script_path):
        try:
            # Terminal öffnen und Skript mit sudo ausführen
            desktop_env = os.environ.get('DESKTOP_SESSION')
            if desktop_env in ['xfce', 'mate']:
                terminal_command = 'xfce4-terminal' if desktop_env == 'xfce' else 'mate-terminal'
                subprocess.Popen([terminal_command, '-x', 'sudo', 'bash', script_path])
            else:
                # Fallback für andere Desktop-Umgebungen
                subprocess.Popen(['xterm', '-e', 'sudo', 'bash', script_path])
        except FileNotFoundError:
            print(f"Fehler: Skript '{script_path}' nicht gefunden.")

    def run_script_as_root(self, source, script_path):
        try:
            subprocess.Popen(['pkexec', 'bash', script_path])
        except FileNotFoundError:
            print(f"Fehler: Skript '{script_path}' nicht gefunden.")

    def run_python_script(self, source, script_path):
        try:
            subprocess.Popen(['python3', script_path])
        except FileNotFoundError:
            print(f"Fehler: Skript '{script_path}' nicht gefunden.")

if __name__ == "__main__":
    indicator = SystemTrayIcon()
    Gtk.main()
