#!/usr/bin/env bash
# Prepara uma EC2 Amazon Linux (ou Ubuntu) para a coleta: Docker e o plugin Compose.
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  if command -v dnf >/dev/null 2>&1; then
    sudo dnf install -y docker
  else
    sudo apt-get update
    sudo apt-get install -y docker.io
  fi
  sudo systemctl enable --now docker
fi

if ! sudo docker compose version >/dev/null 2>&1; then
  case "$(uname -m)" in
    aarch64 | arm64) arch=aarch64 ;;
    *) arch=x86_64 ;;
  esac
  sudo mkdir -p /usr/local/lib/docker/cli-plugins
  sudo curl -fsSL \
    "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-${arch}" \
    -o /usr/local/lib/docker/cli-plugins/docker-compose
  sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
fi

if ! swapon --show | grep -q '/swapfile'; then
  if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
  fi
  sudo swapon /swapfile
  grep -q '/swapfile' /etc/fstab || echo '/swapfile swap swap defaults 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

sudo docker compose version
