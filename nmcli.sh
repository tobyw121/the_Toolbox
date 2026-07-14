#!/bin/bash

# Dieses Skript startet verschiedene Netzwerkdienste unter Linux neu 
# und startet das NetworkManager-Symbol in der Taskleiste neu.

# NetworkManager neu starten
sudo systemctl restart NetworkManager
echo "NetworkManager wurde neu gestartet1."

# networking neu starten
sudo systemctl restart networking.service
echo "networking.service wurde neu gestartet."

# wpa_supplicant neu starten (falls installiert)
if command -v wpa_supplicant &> /dev/null; then
  sudo systemctl restart wpa_supplicant.service
  echo "wpa_supplicant.service wurde neu gestartet."
fi

# NetworkManager-Applet neu starten
killall nm-applet
nm-applet &
echo "NetworkManager-Applet wurde neu gestartet."


echo "VPN getrennt ."
nmcli connection down wg0
