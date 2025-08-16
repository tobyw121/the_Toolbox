#!/bin/bash

# Update-Repository aktualisieren
sudo apt update > /dev/null

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

# Nach verfügbaren Updates suchen
updates=$(apt list --upgradable 2>/dev/null | grep -c '\-')

# Prüfen, ob Nvidia-Updates vorhanden sind
nvidia_updates=$(echo "$updates" | grep -i 'nvidia' | grep -c '\-')

if [ "$updates" -gt 0 ]; then
    echo "Es gibt folgende verfügbare Updates:"
    apt list --upgradable

    if [ "$nvidia_updates" -gt 0 ]; then
        echo "WARNUNG: Nvidia-Updates sind verfügbar."
        read -p "Möchten Sie die Nvidia-Updates installieren? (J/n): " nvidia_choice
        case "$nvidia_choice" in
            j|J|y|Y)
                sudo apt upgrade "*nvidia*"
                ;;
            n|N)
                echo "Nvidia-Updates werden übersprungen."
                sudo apt-mark hold *nvidia
                sudo apt-mark hold nvidia
                ;;
            *)
                echo "Ungültige Eingabe. Nvidia-Updates werden übersprungen."
                ;;
        esac
    fi

    read -r -p "Möchten Sie die anderen Updates installieren? (J/n): " -i "J" update_choice
    case "$update_choice" in
    j|J|y|Y|"")
        # Alle anderen Updates installieren
        echo "Updates werden installiert..." 
        sudo apt upgrade -y 

        echo "Log wird auf dem Desktop gespeichert (Pfad: ~/Schreibtisch/update_log/)!"
        current_date=$(date +"%Y-%m-%d")
        mkdir -p ~/Schreibtisch/update_log/
        sudo cp /var/log/dpkg.log ~/Schreibtisch/update_log/update_dpkg_$current_date.log
        sudo cp /var/log/apt/history.log ~/Schreibtisch/update_log/update_history_$current_date.log
        echo "Fertig."
                
            # Benutzer fragen, ob der Computer neu gestartet werden soll
            read -p "Möchten Sie den Computer jetzt neu starten? (J/n): " restart_choice
            case "$restart_choice" in
                j|J|y|Y|"")
                    sudo reboot
                    ;;
                n|N)
                    echo "Der Computer wird nicht neu gestartet."
                    ;;
                *)
                    echo "Ungültige Eingabe. Der Computer wird nicht neu gestartet."
                    ;;
            esac
            ;;
        n|N)
            echo "Andere Updates werden nicht installiert."
            ;;
        *)
            echo "Ungültige Eingabe. Andere Updates werden nicht installiert."
            ;;
    esac
else
    echo "Keine Updates verfügbar."
    # Fenster schließt nach 5 Sekunden 
    sleep 5
    exit
fi

