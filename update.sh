#!/bin/bash

# Konfiguration
BACKUP_BASE_DIR="/home/*/Schreibtisch/update_log"  # Basisverzeichnis für Backups
UPDATE_LOGS_DIR="$BACKUP_BASE_DIR/update_logs"  # Verzeichnis für Update-Logs
SOURCES_BACKUP_DIR="$BACKUP_BASE_DIR/apt_sources_backup"  # Verzeichnis für sources.list Backups
LOG_FILE="$UPDATE_LOGS_DIR/system_update_$(date +"%Y-%m-%d_%H-%M").log"  # Verbessertes Zeitstempelformat

# Herunterladen der neuesten Version von Discord
wget -q -O discord.deb https://discord.com/api/download?platform=linux

# Aktuell installierte Version von Discord abrufen
installed_version=$(dpkg-query --showformat='${Version}' --show discord 2>/dev/null)

# Wenn Discord nicht installiert ist, wird die Variable auf einen leeren Wert gesetzt
if [ -z "$installed_version" ]; then
    installed_version="0.0.0"
fi

# Versionsinformationen aus der heruntergeladenen discord.deb-Datei extrahieren
downloaded_version=$(dpkg-deb --showformat='${Version}' -W discord.deb)

# Versionsvergleich
if dpkg --compare-versions "$downloaded_version" gt "$installed_version"; then
    echo "Eine neuere Version von Discord ist verfügbar. Installiere..."
    # Installation der neuen Version
    sudo dpkg -i discord.deb
    echo "Discord wurde erfolgreich aktualisiert."
else
    echo "Keine neue Version von Discord verfügbar oder die installierte Version ist neuer."
fi

# Bereinigung
sudo rm discord.deb

# Farbdefinitionen mit Check für Terminalunterstützung
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    CYAN='\033[0;36m'
    NC='\033[0m' # No Color
else
    RED=''; GREEN=''; YELLOW=''; BLUE=''; CYAN=''; NC=''
fi

### Hilfsfunktionen ###

# Verbesserte Log-Funktion mit automatischem Zeilenumbruch
log_message() {
    local message="$1"
    local timestamp=$(date +"%Y-%m-%d %H:%M:%S")
    # Formatierung für bessere Lesbarkeit
    echo -e "[$timestamp] $message" | fold -s -w 100 | tee -a "$LOG_FILE"
}

# Verbesserte Root-Check-Funktion
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_message "${RED}Fehler: Dieser Vorgang benötigt Root-Rechte (sudo).${NC}"
        log_message "${YELLOW}Tipp: Skript mit 'sudo' ausführen oder 'sudo -i' für Root-Shell.${NC}"
        return 1
    fi
    return 0
}

# Robustere Paketprüfung
is_package_installed() {
    dpkg-query -W -f='${Status}' "$1" 2>/dev/null | grep -q "install ok installed"
}

### Hauptfunktionen ###

# Verbesserte Update-Anzeige mit Spaltenausrichtung
show_updates() {
    echo -e "\n${YELLOW}Verfügbare Aktualisierungen:${NC}"
    echo -e "${BLUE}Paketname                        → Aktuelle Version       → Verfügbare Version${NC}"

    tmp_file=$(mktemp)
    local updates_available=0

    apt list --upgradable 2>/dev/null | grep -v 'Listing...' | grep '/' | while read -r line; do
        pkg=$(echo "$line" | cut -d'/' -f1)
        current_version=$(dpkg-query --showformat='${Version}' --show "$pkg" 2>/dev/null || echo "nicht installiert")
        available_version=$(echo "$line" | awk '{print $2}')
        
        if [ "$current_version" = "nicht installiert" ]; then
            printf "%-30s → ${RED}%-25s${NC} → ${GREEN}%s${NC}\n" "$pkg" "$current_version" "$available_version" >> "$tmp_file"
        else
            printf "%-30s → ${YELLOW}%-25s${NC} → ${GREEN}%s${NC}\n" "$pkg" "$current_version" "$available_version" >> "$tmp_file"
        fi
        ((updates_available++))
    done

    if [ -s "$tmp_file" ]; then
        sort "$tmp_file" | uniq
        log_message "${YELLOW}Gesamt: $updates_available Aktualisierungen verfügbar${NC}"
    else
        log_message "${GREEN}Keine Aktualisierungen verfügbar.${NC}"
    fi
    rm -f "$tmp_file"
}

# Überarbeitete Paketverwaltung mit mehr Funktionen
manage_held_packages() {
    local held_packages=$(apt-mark showhold)
    local available_updates=$(apt list --upgradable 2>/dev/null | grep '/' | cut -d'/' -f1)

    log_message "${YELLOW}=== Paketverwaltung (Zurückhalten/Freigeben) ===${NC}"

    if [ -n "$held_packages" ]; then
        log_message "\nAktuell zurückgehaltene Pakete:"
        echo "$held_packages" | while IFS= read -r pkg; do
            echo -e "  ${RED}- $pkg${NC}" | tee -a "$LOG_FILE"
        done
    else
        log_message "\n${GREEN}Derzeit werden keine Pakete zurückgehalten.${NC}"
    fi

    while true; do
        echo -e "\n${CYAN}Optionen:${NC}"
        echo -e "1) Paket freigeben (unhold)"
        echo -e "2) Paket zurückhalten (hold)"
        echo -e "3) Einzelnes Update installieren"
        echo -e "4) Alle Pakete freigeben"
        echo -e "5) Alle Updates außer Wine/Nvidia installieren"
        echo -e "6) Zurück zum Hauptmenü"

        read -rp "Ihre Auswahl (1-6): " choice

        case $choice in
            1) # Paket freigeben
                if [ -z "$held_packages" ]; then
                    log_message "${YELLOW}Keine Pakete zum Freigeben vorhanden.${NC}"
                    continue
                fi
                read -rp "Welches Paket soll freigegeben werden? " pkg
                if echo "$held_packages" | grep -qw "^$pkg$"; then
                    if check_root; then
                        sudo apt-mark unhold "$pkg" && {
                            log_message "${GREEN}Paket '$pkg' wurde freigegeben.${NC}"
                            held_packages=$(apt-mark showhold)
                        } || log_message "${RED}Fehler beim Freigeben von '$pkg'.${NC}"
                    fi
                else
                    log_message "${YELLOW}Paket '$pkg' wird nicht zurückgehalten oder existiert nicht.${NC}"
                fi
                ;;
            2) # Paket zurückhalten
                read -rp "Welches Paket soll zurückgehalten werden? " pkg_to_hold
                if [ -z "$pkg_to_hold" ]; then
                    log_message "${YELLOW}Kein Paketname angegeben.${NC}"
                    continue
                fi
                if check_root; then
                    if is_package_installed "$pkg_to_hold"; then
                        sudo apt-mark hold "$pkg_to_hold" && {
                            log_message "${GREEN}Paket '$pkg_to_hold' wird nun zurückgehalten.${NC}"
                            held_packages=$(apt-mark showhold)
                        } || log_message "${RED}Fehler beim Zurückhalten von '$pkg_to_hold'.${NC}"
                    else
                        log_message "${YELLOW}Paket '$pkg_to_hold' ist nicht installiert.${NC}"
                    fi
                fi
                ;;
            3) # Einzelnes Update installieren
                show_updates
                read -rp "Welches Paket soll aktualisiert werden? " pkg
                if echo "$available_updates" | grep -qw "^$pkg$"; then
                    if check_root; then
                        log_message "Versuche '$pkg' zu aktualisieren..."
                        sudo apt-mark unhold "$pkg" 2>/dev/null
                        sudo apt-get install --only-upgrade "$pkg" -y | tee -a "$LOG_FILE" && \
                            log_message "${GREEN}Update für '$pkg' erfolgreich installiert.${NC}" || \
                            log_message "${RED}Fehler bei der Installation des Updates für '$pkg'.${NC}"
                    fi
                else
                    log_message "${RED}Aktualisierung für '$pkg' nicht verfügbar oder Paketname ungültig.${NC}"
                fi
                ;;
            4) # Alle Pakete freigeben
                if [ -n "$held_packages" ]; then
                    if check_root; then
                        sudo apt-mark unhold $held_packages && {
                            log_message "${GREEN}Alle zurückgehaltenen Pakete wurden freigegeben.${NC}"
                            held_packages=""
                        } || log_message "${RED}Fehler beim Freigeben der Pakete.${NC}"
                    fi
                else
                    log_message "${YELLOW}Keine Pakete zum Freigeben vorhanden.${NC}"
                fi
                ;;
            5) # Alle Updates außer Wine/Nvidia installieren
                if check_root; then
                    local to_install=($(apt list --upgradable 2>/dev/null | grep '/' | awk -F/ '{print $1}' | grep -vi -e 'wine' -e 'nvidia'))

                    if [ ${#to_install[@]} -gt 0 ]; then
                        log_message "${YELLOW}Installiere folgende Pakete (ohne Wine/Nvidia):${NC}"
                        printf '%s\n' "${to_install[@]}" | while read pkg; do echo -e "${BLUE}- $pkg${NC}"; done | tee -a "$LOG_FILE"

                        sudo apt-mark unhold "${to_install[@]}" 2>/dev/null
                        sudo apt-get install --only-upgrade -y "${to_install[@]}" | tee -a "$LOG_FILE" && \
                            log_message "${GREEN}Ausgewählte Pakete erfolgreich aktualisiert.${NC}" || \
                            log_message "${RED}Fehler bei der Installation einiger Pakete.${NC}"
                    else
                        log_message "${YELLOW}Keine passenden Aktualisierungen (ohne Wine/Nvidia) gefunden.${NC}"
                    fi
                    held_packages=$(apt-mark showhold)
                fi
                ;;
            6) # Zurück zum Hauptmenü
                break
                ;;
            *)
                log_message "${RED}Ungültige Eingabe! Bitte 1-6 wählen.${NC}"
                ;;
        esac
    done
}

# Verbesserte Quellen-Reparatur mit mehr Distributionen
repair_sources() {
    check_root || return 1

    log_message "${YELLOW}=== Paketquellen reparieren/zurücksetzen ===${NC}"
# Schritt 1: Standard-Reparaturversuche
    log_message "Starte Standard-Reparaturversuche (clean & fix-broken)..."
    sudo apt-get clean
    sudo apt-get update
    sudo apt-get update --fix-missing | tee -a "$LOG_FILE"
    sudo apt-get upgrade -y | tee -a "$LOG_FILE"
    sudo apt --fix-broken install -y | tee -a "$LOG_FILE"
    sudo apt-get install -f -y | tee -a "$LOG_FILE"
    sudo dpkg --configure -a | tee -a "$LOG_FILE"
    #sudo apt-get dist-upgrade -y | tee -a "$LOG_FILE"
    #sudo apt-get autoremove  | tee -a "$LOG_FILE"
    #sudo apt-get autoclean  | tee -a "$LOG_FILE"
    
    log_message "${GREEN}Bereinigung und Reparaturversuch abgeschlossen.${NC}"
# Schritt 2: Backup
    CURRENT_DATE=$(date +"%Y%m%d_%H%M%S")
    BACKUP_DIR="$SOURCES_BACKUP_DIR/$CURRENT_DATE"
    mkdir -p "$BACKUP_DIR"
# Schritt 3: Quellen zurücksetzen
    log_message "Erstelle Backup der aktuellen APT-Konfiguration..."
    sudo cp -a /etc/apt/sources.list "$BACKUP_DIR/" 2>/dev/null
    sudo cp -a /etc/apt/sources.list.d/. "$BACKUP_DIR/sources.list.d/" 2>/dev/null
    log_message "Backup erstellt in: ${GREEN}$BACKUP_DIR${NC}"

    if ! command -v lsb_release &>/dev/null; then
        log_message "${RED}Fehler: lsb_release nicht gefunden. Installieren Sie lsb-release.${NC}"
        return 1
    fi

    local DISTRO=$(lsb_release -is | tr '[:upper:]' '[:lower:]')
    local CODENAME=$(lsb_release -cs)
    local RELEASE=$(lsb_release -rs)
    local ARCH=$(dpkg --print-architecture)
    local REPO_FILE="/etc/apt/sources.list.d/official-package-repositories.list"

    if [ ! -f "$REPO_FILE" ]; then
        log_message "${YELLOW}Hinweis: Standard-Datei '$REPO_FILE' nicht gefunden. Verwende '/etc/apt/sources.list'.${NC}"
        REPO_FILE="/etc/apt/sources.list"
    else
        if [ -f /etc/apt/sources.list ] && [ -s /etc/apt/sources.list ] && grep -q '^[[:space:]]*deb' /etc/apt/sources.list; then
            log_message "${YELLOW}Warnung: '/etc/apt/sources.list' enthält aktive 'deb'-Einträge.${NC}"
            read -rp "Soll /etc/apt/sources.list geleert werden (empfohlen)? [J/n]: " empty_sources_list
            if [[ "$empty_sources_list" =~ ^[nN]$ ]]; then
                log_message "${YELLOW}Behalte vorhandene Einträge in sources.list.${NC}"
            else
                sudo sh -c "> /etc/apt/sources.list"
                log_message "'/etc/apt/sources.list' wurde geleert."
            fi
        elif [ ! -f /etc/apt/sources.list ]; then
            sudo touch /etc/apt/sources.list
        fi
    fi

    log_message "Erstelle Standard-Paketquellen für ${YELLOW}${DISTRO^} ${RELEASE} (${CODENAME})${NC} in '$REPO_FILE'..."

    case $DISTRO in
        linuxmint)
            case $RELEASE in
                20*) UBUNTU_CODENAME="focal" ;;
                21*) UBUNTU_CODENAME="jammy" ;;
                22*) UBUNTU_CODENAME="noble" ;;
                *)
                    log_message "${RED}Unbekannte Linux Mint Version '$RELEASE'. Abbruch.${NC}"
                    return 1 ;;
            esac

            sudo sh -c "cat > '$REPO_FILE' <<EOF
# Official Linux Mint repositories
deb http://packages.linuxmint.com $CODENAME main upstream import backport

# Official Ubuntu base repositories
deb http://archive.ubuntu.com/ubuntu $UBUNTU_CODENAME main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $UBUNTU_CODENAME-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $UBUNTU_CODENAME-backports main restricted universe multiverse

# Official Ubuntu security updates
deb http://security.ubuntu.com/ubuntu/ $UBUNTU_CODENAME-security main restricted universe multiverse
EOF"
            ;;
        ubuntu|pop)
            sudo sh -c "cat > '$REPO_FILE' <<EOF
# Standard Ubuntu repositories
deb http://archive.ubuntu.com/ubuntu $CODENAME main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $CODENAME-updates main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu $CODENAME-backports main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu $CODENAME-security main restricted universe multiverse
EOF"
            ;;
        debian)
            sudo sh -c "cat > '$REPO_FILE' <<EOF
# Debian main repositories
deb http://deb.debian.org/debian $CODENAME main contrib non-free
deb http://deb.debian.org/debian $CODENAME-updates main contrib non-free
deb http://deb.debian.org/debian-security $CODENAME-security main contrib non-free
EOF"
            ;;
        *)
            log_message "${RED}Nicht unterstützte Distribution: ${DISTRO^}.${NC}"
            log_message "Backup wurde in '$BACKUP_DIR' erstellt."
            return 1 ;;
    esac

    # Partner-Repositories für Ubuntu-basierte Systeme
    if [[ "$DISTRO" =~ (ubuntu|linuxmint|pop) ]]; then
        read -rp "Optionales Partner-Repository hinzufügen? [j/N]: " partner_choice
        if [[ "$partner_choice" =~ ^[jJ]$ ]]; then
            log_message "Füge Partner-Repository hinzu..."
            sudo sh -c "echo '' >> '$REPO_FILE'; echo '# Partner repository' >> '$REPO_FILE'; echo '#deb http://archive.canonical.com/ubuntu $UBUNTU_CODENAME partner' >> '$REPO_FILE'"
        fi
    fi

    log_message "Aktualisiere Paketlisten..."
    sudo apt-get update | tee -a "$LOG_FILE" && \
        log_message "\n${GREEN}Paketquellen erfolgreich aktualisiert!${NC}\nKonfigurationsdatei: ${YELLOW}$REPO_FILE${NC}" || \
        log_message "\n${RED}Fehler beim Aktualisieren der Paketlisten.${NC}\nBackup der alten Konfiguration: ${YELLOW}$BACKUP_DIR${NC}"
}

# Verbesserte Discord-Update-Funktion
update_discord() {
    log_message "${YELLOW}=== Discord Update Prüfung ===${NC}"

    # Abhängigkeiten prüfen
    local missing_deps=()
    for dep in wget dpkg-deb; do
        if ! command -v $dep &>/dev/null; then
            missing_deps+=("$dep")
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        log_message "${RED}Fehlende Abhängigkeiten: ${missing_deps[*]}${NC}"
        read -rp "Möchten Sie die fehlenden Pakete installieren? [J/n]: " install_deps
        if [[ "$install_deps" =~ ^[nN]$ ]]; then
            return 1
        fi
        if check_root; then
            sudo apt-get install -y "${missing_deps[@]}" | tee -a "$LOG_FILE" || {
                log_message "${RED}Installation der Abhängigkeiten fehlgeschlagen.${NC}"
                return 1
            }
        else
            return 1
        fi
    fi

    local discord_deb_path="$UPDATE_LOGS_DIR/discord_latest.deb"

    log_message "Lade aktuelle Discord .deb-Datei herunter..."
    wget --show-progress -q -O "$discord_deb_path" "https://discord.com/api/download?platform=linux&format=deb" || {
        log_message "${RED}Fehler beim Herunterladen von Discord.${NC}"
        rm -f "$discord_deb_path"
        return 1
    }

    log_message "Download abgeschlossen: $discord_deb_path"

    local installed_version="nicht installiert"
    if is_package_installed "discord"; then
        installed_version=$(dpkg-query --showformat='${Version}' --show discord 2>/dev/null)
    fi
    log_message "Installierte Version: $installed_version"

    local downloaded_version=$(dpkg-deb --showformat='${Version}' -W "$discord_deb_path" 2>/dev/null) || {
        log_message "${RED}Fehler beim Lesen der heruntergeladenen Version.${NC}"
        rm -f "$discord_deb_path"
        return 1
    }
    log_message "Heruntergeladene Version: $downloaded_version"

    if [ "$installed_version" = "nicht installiert" ] || dpkg --compare-versions "$downloaded_version" gt "$installed_version"; then
        local action_text="installieren"
        if [ "$installed_version" != "nicht installiert" ]; then
            log_message "Neue Discord-Version verfügbar: ${YELLOW}$installed_version${NC} → ${GREEN}$downloaded_version${NC}"
            action_text="aktualisieren"
        fi

        read -rp "Discord jetzt ${action_text}? [J/n]: " install_update_discord
        if [[ "$install_update_discord" =~ ^[nN]$ ]]; then
            log_message "${YELLOW}${action_text^} übersprungen.${NC}"
            return 0
        fi

        log_message "${action_text^}e Discord..."
        if check_root; then
            sudo apt install "$discord_deb_path" -y | tee -a "$LOG_FILE" && {
                log_message "${GREEN}Discord erfolgreich ${action_text}t auf Version $downloaded_version.${NC}"
                rm -f "$discord_deb_path"
            } || {
                log_message "${RED}Fehler bei der Installation/Aktualisierung von Discord.${NC}"
                log_message "${YELLOW}Versuche Abhängigkeiten zu beheben...${NC}"
                sudo apt --fix-broken install -y | tee -a "$LOG_FILE"
            }
        fi
    else
        log_message "${GREEN}Discord ist bereits aktuell (Version $installed_version).${NC}"
        rm -f "$discord_deb_path"
    fi
}

# Verbesserte Log-Speicherung
save_update_logs() {
    mkdir -p "$UPDATE_LOGS_DIR"
    local current_timestamp=$(date +"%Y-%m-%d_%H%M")

    log_message "\n${GREEN}Speichere System-Logdateien...${NC}"
    
    # Liste der zu sichernden Logdateien
    local log_files=(
        "/var/log/dpkg.log"
        "/var/log/apt/history.log"
        "/var/log/apt/term.log"
        "/var/log/syslog"
    )
    
    for log_file in "${log_files[@]}"; do
        if [ -r "$log_file" ]; then
            local log_name=$(basename "$log_file")
            sudo cp "$log_file" "$UPDATE_LOGS_DIR/${log_name%.log}_${current_timestamp}.log" 2>/dev/null && \
                log_message "Gespeichert: ${YELLOW}$log_name${NC}" || \
                log_message "${RED}Fehler beim Speichern von $log_name${NC}"
        fi
    done

    # Fehleranalyse
    local failed_ops=$(grep -Ei 'fehler|error|E:|failed|warning|warn' "$LOG_FILE" | \
        grep -v -e 'Fehler: Dieser Vorgang benötigt Root-Rechte' | \
        sort | uniq)

    if [ -n "$failed_ops" ]; then
        log_message "\n${RED}Mögliche Probleme während des Laufs:${NC}"
        echo "$failed_ops" | while read -r line; do
            log_message " - ${line}"
        done
    fi

    log_message "\n${GREEN}Logdateien gespeichert in:${NC}"
    ls -1t "$UPDATE_LOGS_DIR"/*.log 2>/dev/null | head -n 5 | while read -r file; do
        log_message "${YELLOW}$file${NC}"
    done
}

# Überarbeitete Systemaktualisierung mit besserer Fehlerbehandlung
system_updates() {
    log_message "${YELLOW}=== Systemaktualisierung ===${NC}"

    if ! check_root; then return 1; fi

    log_message "Aktualisiere Paketlisten (apt update)..."
    sudo apt-get update | tee -a "$LOG_FILE" || {
        log_message "${RED}Fehler bei 'apt update'. Paketquellen prüfen (Option 3).${NC}"
        return 1
    }

    local updates_count=$(apt list --upgradable 2>/dev/null | grep -c '/')

    if [ "$updates_count" -eq 0 ]; then
        log_message "${GREEN}System ist auf dem neuesten Stand.${NC}"
        return 0
    fi

    log_message "${YELLOW}$updates_count Aktualisierungen verfügbar.${NC}"
    show_updates

    local held_packages_sys=$(apt-mark showhold)
    if [ -n "$held_packages_sys" ]; then
        log_message "\n${RED}Zurückgehaltene Pakete:${NC}"
        echo "$held_packages_sys" | while IFS= read -r pkg; do
            echo -e "  ${RED}- $pkg${NC}" | tee -a "$LOG_FILE"
        done
        log_message "${YELLOW}(Diese Pakete werden bei normalen Upgrades übersprungen)${NC}"
    fi

    local nvidia_updates=$(apt list --upgradable 2>/dev/null | grep -i 'nvidia' | grep '/')
    local skip_nvidia=0

    if [ -n "$nvidia_updates" ]; then
        log_message "\n${YELLOW}Nvidia-Aktualisierungen gefunden:${NC}"
        echo "$nvidia_updates" | tee -a "$LOG_FILE"
        
        read -rp "Nvidia Updates überspringen? [J/n]: " skip_nvidia_choice
        [[ "$skip_nvidia_choice" =~ ^[nN]$ ]] || skip_nvidia=1
    fi

    read -rp "Alle Aktualisierungen jetzt installieren? [J/n]: " choice
    case "$choice" in
        [nN])
            log_message "${YELLOW}Aktualisierung übersprungen.${NC}"
            ;;
        *)
            log_message "\n${YELLOW}Führe Systemaktualisierung durch...${NC}"
            
            if [ "$skip_nvidia" -eq 1 ]; then
                log_message "${YELLOW}Überspringe Nvidia-Updates...${NC}"
                local packages_to_upgrade=$(apt list --upgradable 2>/dev/null | grep '/' | awk -F/ '{print $1}' | grep -vi 'nvidia')
                
                if [ -n "$packages_to_upgrade" ]; then
                    echo "$packages_to_upgrade" | xargs sudo apt-mark unhold 2>/dev/null
                    sudo apt-get install --only-upgrade -y $packages_to_upgrade | tee -a "$LOG_FILE"
                else
                    log_message "${YELLOW}Keine Pakete (ohne Nvidia) zum Aktualisieren.${NC}"
                fi
            else
                sudo apt-get upgrade -y | tee -a "$LOG_FILE"
            fi

            if [ $? -eq 0 ]; then
                log_message "${GREEN}Systemaktualisierung erfolgreich.${NC}"
                
                read -rp "Nicht mehr benötigte Pakete entfernen (autoremove)? [J/n]: " clean_choice
                if [[ ! "$clean_choice" =~ ^[nN]$ ]]; then
                    log_message "Führe autoremove und clean aus..."
                    sudo apt-get autoremove -y | tee -a "$LOG_FILE"
                    sudo apt-get clean | tee -a "$LOG_FILE"
                fi
                
                save_update_logs
                
                if [ -f /var/run/reboot-required ]; then
                    log_message "${RED}Ein Neustart wird dringend empfohlen!${NC}"
                    read -rp "Jetzt neu starten? [j/N]: " reboot_choice
                    [[ "$reboot_choice" =~ ^[jJ]$ ]] && sudo reboot
                fi
            else
                log_message "${RED}Systemaktualisierung mit Fehlern beendet.${NC}"
            fi
            ;;
    esac
}

### Initialisierung ###

mkdir -p "$BACKUP_BASE_DIR" "$UPDATE_LOGS_DIR" "$SOURCES_BACKUP_DIR"
touch "$LOG_FILE"

log_message "============================================="
log_message "System Update Manager gestartet am $(date)"
log_message "Basisverzeichnis: $BACKUP_BASE_DIR"
log_message "Logdatei: $LOG_FILE"
log_message "System: $(lsb_release -ds 2>/dev/null || uname -a)"
log_message "============================================="

### Hauptprogramm ###

while true; do
    echo -e "\n${YELLOW}=== System Update Manager ===${NC}"
    echo -e "${CYAN}1) System aktualisieren${NC}"
    echo -e "${CYAN}2) Pakete verwalten (hold/unhold)${NC}"
    echo -e "${CYAN}3) Paketquellen reparieren${NC}"
    echo -e "${CYAN}4) Letzte Log-Einträge anzeigen${NC}"
    echo -e "${CYAN}5) Discord Update prüfen${NC}"
    echo -e "${CYAN}6) Beenden${NC}"

    read -rp "Ihre Auswahl (1-6): " main_choice

    case $main_choice in
        1) system_updates ;;
        2) manage_held_packages ;;
        3) repair_sources ;;
        4)
            echo -e "\n${YELLOW}=== Letzte Log-Einträge ===${NC}"
            if [ -f "$LOG_FILE" ]; then
                tail -n 25 "$LOG_FILE" | sed 's/^/  /'
            else
                echo -e "  ${RED}Keine Logdatei vorhanden.${NC}"
            fi
            ;;
        5) update_discord ;;
        6)
            log_message "Skript wird beendet."
            exit 0
            ;;
        *)
            log_message "${RED}Ungültige Eingabe! Bitte 1-6 wählen.${NC}"
            ;;
    esac

    if [ "$main_choice" != "6" ]; then
        echo ""
        read -rp "Enter drücken, um fortzufahren..."
    fi
done
