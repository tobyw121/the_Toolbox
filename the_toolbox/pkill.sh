#!/bin/bash

# Funktion zum Beenden aller Prozesse mit einem ähnlichen Namen
kill_processes() {
  local name="$1"
  local pids=$(pgrep -f "$name")
  if [ -n "$pids" ]; then
    sudo kill -9 $pids
    echo "Prozesse mit dem Namen '$name' beendet."
  else
    echo "Keine Prozesse mit dem Namen '$name' gefunden."
  fi
}

# Steam beenden
kill_processes "steam"

# Wine beenden
kill_processes "wine"

# Firefox beenden
kill_processes "firefox"

kill_processes "rustdesk"

exit
