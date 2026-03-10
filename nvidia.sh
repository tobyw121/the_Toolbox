#!/bin/bash

# Bash-Skript zur vollständigen Neuinstallation von NVIDIA-Treibern unter Linux Mint/Ubuntu

# --- Konfiguration ---
LOG_FILE="/var/log/nvidia_reinstall_$(date +%Y%m%d_%H%M%S).log"
# --- Ende Konfiguration ---

# --- Funktionen ---

log_message() {
    echo "$(date +%Y-%m-%d_%H:%M:%S) - $1" | tee -a "$LOG_FILE"
}

error_exit() {
    log_message "FEHLER: $1"
    log_message "Das Skript wird beendet. Bitte überprüfe die Log-Datei ($LOG_FILE) für Details."
    exit 1
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "Dieses Skript muss mit Root-Rechten ausgeführt werden. Bitte starte es mit 'sudo'."
    fi
}

check_internet() {
    log_message "Überprüfe Internetverbindung..."
    ping -c 1 google.com &>/dev/null
    if [ $? -ne 0 ]; then
        error_exit "Keine Internetverbindung erkannt. Bitte stelle sicher, dass du online bist."
    fi
    log_message "Internetverbindung ist aktiv."
}

remove_nvidia_drivers() {
    log_message "Beginne mit dem Entfernen aller bestehenden NVIDIA-Treiber..."

    # Versuche, alle NVIDIA-Pakete zu entfernen
    log_message "Entferne NVIDIA-Pakete mit apt purge..."
    sudo apt-get purge "nvidia-*" -y >> "$LOG_FILE" 2>&1 || log_message "Keine 'nvidia-*' Pakete gefunden oder Fehler beim Purgen."

    log_message "Führe apt autoremove und apt clean aus..."
    sudo apt-get autoremove -y >> "$LOG_FILE" 2>&1
    sudo apt-get clean >> "$LOG_FILE" 2>&1

    # Versuche, das NVIDIA-Deinstallationsprogramm auszuführen, falls eine manuelle Installation erfolgte
    if [ -f "/usr/bin/nvidia-uninstall" ]; then
        log_message "Führe /usr/bin/nvidia-uninstall aus (falls vorhanden)..."
        sudo /usr/bin/nvidia-uninstall >> "$LOG_FILE" 2>&1 || log_message "Fehler oder nicht gefunden: /usr/bin/nvidia-uninstall"
    elif [ -f "/usr/local/bin/nvidia-uninstall" ]; then
        log_message "Führe /usr/local/bin/nvidia-uninstall aus (falls vorhanden)..."
        sudo /usr/local/bin/nvidia-uninstall >> "$LOG_FILE" 2>&1 || log_message "Fehler oder nicht gefunden: /usr/local/bin/nvidia-uninstall"
    else
        log_message "Kein manuelles NVIDIA-Deinstallationsprogramm gefunden."
    fi

    # Blackliste den Nouveau-Treiber
    log_message "Blackliste den Nouveau-Treiber..."
    echo -e "blacklist nouveau\noptions nouveau modeset=0" | sudo tee /etc/modprobe.d/blacklist-nouveau.conf >> "$LOG_FILE" 2>&1
    sudo update-initramfs -u >> "$LOG_FILE" 2>&1 || error_exit "Fehler beim Aktualisieren der Initramfs nach Nouveau-Blacklisting."

    # Entferne alte Xorg-Konfigurationsdateien
    log_message "Entferne alte Xorg-Konfigurationsdateien..."
    sudo rm -f /etc/X11/xorg.conf.d/20-nvidia.conf >> "$LOG_FILE" 2>&1
    sudo rm -f /etc/X11/xorg.conf >> "$LOG_FILE" 2>&1

    log_message "NVIDIA-Treiber-Entfernung abgeschlossen. Ein Neustart ist möglicherweise erforderlich, um in einen stabilen Zustand zurückzukehren."
    log_message "Wenn der Bildschirm nach dem Neustart schwarz bleibt, boote mit der 'nomodeset'-Option im GRUB-Menü."
}

install_prerequisites() {
    log_message "Beginne mit der Installation der erforderlichen Pakete und Aktualisierungen..."

    log_message "Aktualisiere Paketlisten und System..."
    sudo apt update -y >> "$LOG_FILE" 2>&1 || error_exit "Fehler beim Aktualisieren der Paketlisten."
    sudo apt upgrade -y >> "$LOG_FILE" 2>&1 || error_exit "Fehler beim System-Upgrade."
    sudo apt dist-upgrade -y >> "$LOG_FILE" 2>&1 || error_exit "Fehler beim Distribution-Upgrade."

    log_message "Installiere build-essential, dkms und Kernel-Header..."
    # Überprüfe, ob die Kernel-Header für den aktuellen Kernel verfügbar sind
    KERNEL_VERSION=$(uname -r)
    sudo apt install build-essential dkms "linux-headers-${KERNEL_VERSION}" -y >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        error_exit "Konnte build-essential, dkms oder Kernel-Header für ${KERNEL_VERSION} nicht installieren. Überprüfe deine Paketquellen."
    fi
    log_message "Erforderliche Pakete wurden installiert."
}

install_nvidia_drivers() {
    log_message "Beginne mit der Installation der NVIDIA-Treiber..."

    # Füge das graphics-drivers PPA hinzu, um die neuesten stabilen Treiber zu erhalten
    log_message "Füge das 'graphics-drivers/ppa' Repository hinzu..."
    sudo add-apt-repository ppa:graphics-drivers/ppa -y >> "$LOG_FILE" 2>&1 || log_message "Konnte PPA nicht hinzufügen. Versuche Installation ohne PPA."
    sudo apt update -y >> "$LOG_FILE" 2>&1 || error_exit "Fehler beim Aktualisieren der Paketlisten nach PPA-Hinzufügung."

    log_message "Installiere den empfohlenen NVIDIA-Treiber mit 'ubuntu-drivers autoinstall'..."
    # ubuntu-drivers autoinstall wählt den besten verfügbaren Treiber für deine Hardware
    DEBIAN_FRONTEND=noninteractive sudo ubuntu-drivers autoinstall >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        error_exit "Fehler bei der automatischen Installation des NVIDIA-Treibers. Versuche eine manuelle Installation oder überprüfe die Log-Datei."
    fi

    log_message "NVIDIA-Treiber-Installation abgeschlossen."
    log_message "Führe 'nvidia-xconfig' aus, um die Xorg-Konfiguration zu erstellen (falls nicht automatisch geschehen)..."
    sudo nvidia-xconfig >> "$LOG_FILE" 2>&1 || log_message "nvidia-xconfig konnte nicht ausgeführt werden oder ist nicht notwendig."

    log_message "Die Installation des NVIDIA-Treibers ist abgeschlossen. Ein Neustart ist ZWINGEND erforderlich, damit die Änderungen wirksam werden."
}

verify_nvidia_installation() {
    log_message "Überprüfe die NVIDIA-Treiber-Installation..."
    log_message "Führe 'nvidia-smi' aus:"
    nvidia-smi >> "$LOG_FILE" 2>&1
    if [ $? -ne 0 ]; then
        log_message "WARNUNG: 'nvidia-smi' konnte nicht ausgeführt werden. Der Treiber ist möglicherweise nicht korrekt geladen oder installiert."
        log_message "Bitte starte das System neu und überprüfe es erneut."
        return 1
    fi

    log_message "Führe 'glxinfo | grep \"OpenGL renderer\"' aus:"
    glxinfo | grep "OpenGL renderer" | tee -a "$LOG_FILE"
    if glxinfo | grep "OpenGL renderer" | grep -q "NVIDIA"; then
        log_message "NVIDIA-Treiber scheint erfolgreich geladen zu sein."
    else
        log_message "WARNUNG: 'glxinfo' zeigt keinen NVIDIA-Renderer an. Der Treiber ist möglicherweise nicht korrekt aktiv."
        log_message "Bitte starte das System neu und überprüfe es erneut."
        return 1
    fi

    log_message "NVIDIA-Treiber-Überprüfung abgeschlossen."
    return 0
}

# --- Hauptskript-Logik ---

log_message "--- Starte NVIDIA-Treiber Neuinstallations-Skript ---"
log_message "Log-Datei: $LOG_FILE"

check_root
check_internet

# Schritt 1: Treiber entfernen
log_message "Schritt 1/3: Entferne alte NVIDIA-Treiber."
remove_nvidia_drivers

read -p "Die alten Treiber wurden entfernt. Es wird DRINGEND empfohlen, jetzt neu zu starten, um in einen stabilen Zustand zu gelangen. Möchtest du jetzt neu starten? (j/N): " REBOOT_NOW
if [[ "$REBOOT_NOW" =~ ^[Jj]$ ]]; then
    log_message "Neustart angefordert. Das Skript wird nach dem Neustart manuell fortgesetzt werden müssen."
    sudo reboot
    exit 0 # Skript beenden, da ein Neustart erfolgt
else
    log_message "Neustart übersprungen. Fortsetzung auf eigene Gefahr. Bei Problemen nach dem Neustart im Textmodus/mit 'nomodeset' booten."
fi

# Gib dem Benutzer Zeit, sich zu orientieren, falls er nicht neu gestartet hat
log_message "Warte 5 Sekunden, bevor die Installation der Voraussetzungen beginnt..."
sleep 5

# Schritt 2: Voraussetzungen installieren
log_message "Schritt 2/3: Installiere erforderliche Pakete und aktualisiere das System."
install_prerequisites

# Schritt 3: Neue NVIDIA-Treiber installieren
log_message "Schritt 3/3: Installiere den empfohlenen NVIDIA-Treiber."
install_nvidia_drivers

log_message "--- NVIDIA-Treiber Installation abgeschlossen ---"

# Überprüfung nach der Installation
log_message "Führe eine erste Überprüfung der Installation durch..."
if verify_nvidia_installation; then
    log_message "Die erste Überprüfung war erfolgreich. Ein Neustart ist jedoch weiterhin notwendig."
else
    log_message "Die erste Überprüfung zeigte Probleme. Bitte überprüfe die Log-Datei ($LOG_FILE)."
    log_message "Ein Neustart könnte das Problem beheben. Wenn nicht, musst du möglicherweise manuell eingreifen."
fi

read -p "Die Installation ist abgeschlossen. Ein Neustart ist erforderlich, um die neuen Treiber zu aktivieren. Möchtest du jetzt neu starten? (j/N): " FINAL_REBOOT
if [[ "$FINAL_REBOOT" =~ ^[Jj]$ ]]; then
    log_message "Finaler Neustart angefordert. Viel Erfolg!"
    sudo reboot
else
    log_message "Finaler Neustart übersprungen. Die neuen Treiber werden erst nach einem Neustart aktiv sein."
    log_message "Bitte starte dein System manuell neu, um die Installation abzuschließen."
fi

log_message "--- Skript beendet ---"
