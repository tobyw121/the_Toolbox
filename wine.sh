#!/bin/bash

# Überprüfen, ob Wine bereits installiert ist
if dpkg -s winehq-stable >/dev/null 2>&1; then
  echo "Wine ist bereits installiert."

  # Backup des Wine-Ordners erstellen
  mkdir -p ~/wine-backup
  cp -r ~/.wine ~/wine-backup/wine-$(date +%Y%m%d%H%M%S)
  echo "Backup des Wine-Ordners erstellt."

  # Wine deinstallieren
  sudo apt remove --purge winehq-stable
  echo "Wine deinstalliert."
fi

# Wine installieren
sudo apt update
sudo dpkg --add-architecture i386 
sudo mkdir -pm755 /etc/apt/keyrings
sudo wget -O /etc/apt/keyrings/winehq-archive.key https://dl.winehq.org/wine-builds/winehq.key
sudo wget -NP /etc/apt/sources.list.d/ https://dl.winehq.org/wine-builds/ubuntu/dists/jammy/winehq-jammy.sources
sudo apt update
sudo apt-get install -f
sudo apt install --install-recommends winehq-stable
echo "WineHQ installiert."

# Wine einrichten (optional)
winecfg
echo "Wine eingerichtet."
exit

