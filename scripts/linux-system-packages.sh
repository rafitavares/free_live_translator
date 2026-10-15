#!/usr/bin/env bash
# Shared Linux package detection for setup-linux.sh.
# Keep distro-specific package names here so the main installer stays simple.

linux_package_manager() {
  local manager
  for manager in dnf apt-get zypper pacman apk yum; do
    if command -v "$manager" >/dev/null 2>&1; then
      printf '%s\n' "$manager"
      return 0
    fi
  done
  return 1
}

linux_distro_label() {
  if [[ -r /etc/os-release ]]; then
    (
      . /etc/os-release
      printf '%s\n' "${PRETTY_NAME:-${NAME:-Linux}}"
    )
    return
  fi
  printf 'Linux\n'
}

run_as_root() {
  if [[ "$(id -u)" -eq 0 ]]; then
    "$@"
  elif command -v sudo >/dev/null 2>&1; then
    sudo "$@"
  else
    echo "Root access is required for this system change. Install sudo or run setup as root." >&2
    return 1
  fi
}

python_is_supported() {
  "$1" -c 'import sys; raise SystemExit(0 if (3, 10) <= sys.version_info[:2] < (3, 14) else 1)' >/dev/null 2>&1
}

find_supported_linux_python() {
  local candidate
  for candidate in python3.12 python3.13 python3.11 python3.10 python3; do
    if command -v "$candidate" >/dev/null 2>&1 && python_is_supported "$candidate"; then
      command -v "$candidate"
      return 0
    fi
  done
  return 1
}

linux_available_kibibytes() {
  df -Pk "$1" 2>/dev/null | tail -n 1 | awk '{print $4}'
}

linux_storage_diagnostics() {
  local path="$1"
  echo "Filesystem space for $path:"
  df -h "$path" 2>/dev/null || true
  if command -v quota >/dev/null 2>&1; then
    echo "Current user quota:"
    quota -s 2>/dev/null || true
  else
    echo "The quota command is unavailable; a hosting, school, or managed account may still impose a separate user quota."
  fi
}

require_linux_install_space() {
  local path="$1"
  local minimum_kib="$2"
  local available_kib=""
  available_kib="$(linux_available_kibibytes "$path" || true)"
  if [[ "$available_kib" =~ ^[0-9]+$ ]] && (( available_kib < minimum_kib )); then
    echo "Church Cap needs at least 8 GiB free while creating its Python environment." >&2
    linux_storage_diagnostics "$path" >&2
    return 1
  fi
}

linux_active_firewall_manager() {
  local ufw_enabled=""

  if command -v firewall-cmd >/dev/null 2>&1 && [[ "$(firewall-cmd --state 2>/dev/null || true)" == "running" ]]; then
    printf 'firewalld\n'
    return 0
  fi

  if [[ -r /etc/ufw/ufw.conf ]]; then
    ufw_enabled="$(sed -n 's/^ENABLED=//p' /etc/ufw/ufw.conf | tail -n 1)"
  fi
  if command -v ufw >/dev/null 2>&1 && {
    [[ "$ufw_enabled" == "yes" ]] || { command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet ufw; }
  }; then
    printf 'ufw\n'
    return 0
  fi

  return 1
}

linux_firewalld_zone() {
  local interface=""
  local zone=""

  if command -v ip >/dev/null 2>&1; then
    interface="$(ip -o route show to default 2>/dev/null | awk '{print $5; exit}' || true)"
  fi
  if [[ -n "$interface" ]]; then
    zone="$(firewall-cmd --get-zone-of-interface="$interface" 2>/dev/null || true)"
  fi
  if [[ -z "$zone" || "$zone" == "no zone" ]]; then
    zone="$(firewall-cmd --get-default-zone 2>/dev/null || true)"
  fi
  if [[ "$zone" =~ ^[A-Za-z0-9_-]+$ ]]; then
    printf '%s\n' "$zone"
    return 0
  fi
  return 1
}

linux_firewalld_port_is_allowed() {
  local port="$1"
  local zone="$2"
  firewall-cmd --zone="$zone" --query-port="${port}/tcp" >/dev/null 2>&1 &&
    firewall-cmd --permanent --zone="$zone" --query-port="${port}/tcp" >/dev/null 2>&1
}

allow_linux_audience_port() {
  local manager="$1"
  local port="$2"
  local zone="${3:-}"

  case "$manager" in
    firewalld)
      run_as_root firewall-cmd --permanent --zone="$zone" --add-port="${port}/tcp" &&
        run_as_root firewall-cmd --zone="$zone" --add-port="${port}/tcp"
      ;;
    ufw)
      run_as_root ufw allow "${port}/tcp" comment "Church Cap audience captions"
      ;;
    *)
      echo "Unsupported firewall manager: $manager" >&2
      return 1
      ;;
  esac
}

dnf_python_package() {
  local package
  for package in python3.12 python3.13 python3.11 python3; do
    if dnf -q list --available "$package" >/dev/null 2>&1 || rpm -q "$package" >/dev/null 2>&1; then
      printf '%s\n' "$package"
      return 0
    fi
  done
  printf 'python3\n'
}

install_linux_system_packages() {
  local manager="$1"
  local python_package

  case "$manager" in
    apt-get)
      run_as_root apt-get update
      run_as_root apt-get install -y \
        python3 python3-venv python3-pip python3-dev \
        build-essential portaudio19-dev libsndfile1 \
        curl tar unzip ca-certificates
      ;;
    dnf)
      python_package="$(dnf_python_package)"
      if ! run_as_root dnf install -y \
        "$python_package" "${python_package}-pip" "${python_package}-devel" \
        gcc gcc-c++ make portaudio portaudio-devel libsndfile \
        curl tar unzip ca-certificates; then
        echo "dnf could not install all required packages." >&2
        echo "On AlmaLinux/Rocky/RHEL, make sure the standard AppStream and CRB repositories are enabled, then rerun setup." >&2
        return 1
      fi
      ;;
    yum)
      run_as_root yum install -y \
        python3 python3-pip python3-devel \
        gcc gcc-c++ make portaudio portaudio-devel libsndfile \
        curl tar unzip ca-certificates
      ;;
    zypper)
      run_as_root zypper --non-interactive refresh
      run_as_root zypper --non-interactive install \
        python3 python3-pip python3-devel \
        gcc gcc-c++ make portaudio-devel libsndfile1 \
        curl tar unzip ca-certificates
      ;;
    pacman)
      run_as_root pacman -S --needed --noconfirm \
        python python-pip base-devel portaudio libsndfile \
        curl tar unzip ca-certificates
      ;;
    apk)
      run_as_root apk add \
        python3 py3-pip py3-virtualenv python3-dev \
        build-base linux-headers portaudio-dev libsndfile-dev \
        curl tar unzip ca-certificates
      ;;
    *)
      echo "Unsupported package manager: $manager" >&2
      return 1
      ;;
  esac
}
