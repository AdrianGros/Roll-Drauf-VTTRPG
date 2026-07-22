#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root." >&2
    exit 1
fi

GRD_USER="${GRD_USER:-}"
GRD_PASS="${GRD_PASS:-}"
RDP_PORT="${RDP_PORT:-3389}"
TLS_CERT="${TLS_CERT:-}"
TLS_KEY="${TLS_KEY:-}"
ASSUME_INGRESS_RESTRICTED="${ASSUME_INGRESS_RESTRICTED:-no}"

if [[ -z "${GRD_USER}" || -z "${GRD_PASS}" ]]; then
    echo "Set GRD_USER and GRD_PASS before running." >&2
    exit 1
fi

if [[ "${ASSUME_INGRESS_RESTRICTED}" != "yes" ]]; then
    cat >&2 <<'EOF'
Refusing to enable GNOME Remote Login.

Reason:
- This host currently has no active local firewall policy protecting port 3389.
- Starting GNOME Remote Desktop without restricted ingress would expose RDP broadly.

Set ASSUME_INGRESS_RESTRICTED=yes only after you have restricted access through:
- provider security group / external firewall
- VPN
- source-IP allowlist
- equivalent narrow ingress control
EOF
    exit 1
fi

if ! command -v grdctl >/dev/null 2>&1; then
    echo "grdctl is not installed." >&2
    exit 1
fi

echo "Enabling gdm.service ..."
systemctl enable --now gdm.service

echo "Configuring GNOME Remote Desktop system RDP ..."
grdctl --system rdp set-port "${RDP_PORT}"
grdctl --system rdp set-credentials "${GRD_USER}" "${GRD_PASS}"
grdctl --system rdp disable-view-only
grdctl --system rdp disable-port-negotiation

if [[ -n "${TLS_CERT}" || -n "${TLS_KEY}" ]]; then
    if [[ -z "${TLS_CERT}" || -z "${TLS_KEY}" ]]; then
        echo "Set both TLS_CERT and TLS_KEY, or neither." >&2
        exit 1
    fi
    if [[ ! -f "${TLS_CERT}" || ! -f "${TLS_KEY}" ]]; then
        echo "TLS_CERT or TLS_KEY path does not exist." >&2
        exit 1
    fi
    grdctl --system rdp set-tls-cert "${TLS_CERT}"
    grdctl --system rdp set-tls-key "${TLS_KEY}"
fi

grdctl --system rdp enable

echo "Enabling gnome-remote-desktop.service ..."
systemctl enable --now gnome-remote-desktop.service

echo
echo "Verification:"
systemctl --no-pager --full status gdm.service gnome-remote-desktop.service | sed -n '1,80p'
echo
grdctl --system status || true
echo
ss -tulpn | grep ":${RDP_PORT}\\b" || true

echo
echo "Next client step on Windows:"
echo "- Open Remote Desktop Connection (mstsc)"
echo "- Connect to <server-ip>:${RDP_PORT}"
echo "- Use the GRD_USER / GRD_PASS credentials you configured above"
