#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root." >&2
    exit 1
fi

XS_DIR="/usr/share/xsessions"
mkdir -p "${XS_DIR}"

cat > "${XS_DIR}/gnome.desktop" <<'EOF'
[Desktop Entry]
Name=GNOME
Comment=This session logs you into GNOME
Exec=/usr/bin/gnome-session
TryExec=/usr/bin/gnome-session
Type=Application
DesktopNames=GNOME
X-GDM-SessionRegisters=true
X-GDM-CanRunHeadless=true
EOF

cat > "${XS_DIR}/gnome-xorg.desktop" <<'EOF'
[Desktop Entry]
Name=GNOME on Xorg
Comment=This session logs you into GNOME using Xorg
Exec=/usr/bin/gnome-session
TryExec=/usr/bin/gnome-session
Type=Application
DesktopNames=GNOME
X-GDM-SessionRegisters=true
X-GDM-CanRunHeadless=true
EOF

chmod 644 "${XS_DIR}/gnome.desktop" "${XS_DIR}/gnome-xorg.desktop"

echo "Restarting gdm.service ..."
systemctl restart gdm.service

echo "Restarting gnome-remote-desktop.service ..."
systemctl restart gnome-remote-desktop.service

echo
echo "Verification:"
ls -la "${XS_DIR}"
echo
systemctl --no-pager --full status gdm.service gnome-remote-desktop.service | sed -n '1,100p'
echo
ss -tulpn | grep ':3389\b' || true
echo
journalctl -u gdm.service -n 40 --no-pager || true
