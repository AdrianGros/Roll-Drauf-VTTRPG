#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root." >&2
    exit 1
fi

backup_file() {
    local src="$1"
    local bak="${src}.dadm-20260330.bak"
    if [[ -f "${src}" && ! -f "${bak}" ]]; then
        cp "${src}" "${bak}"
    fi
}

echo "Creating xrdp runtime group and user if needed ..."
if ! getent group xrdp >/dev/null; then
    groupadd --system xrdp
fi
if ! getent passwd xrdp >/dev/null; then
    useradd --system --home-dir / --no-create-home --shell /usr/bin/nologin --gid xrdp xrdp
fi

backup_file /etc/xrdp/xrdp.ini
backup_file /etc/xrdp/sesman.ini

echo "Activating runtime_user/runtime_group in xrdp.ini ..."
sed -i \
    -e 's/^#runtime_user=xrdp$/runtime_user=xrdp/' \
    -e 's/^#runtime_group=xrdp$/runtime_group=xrdp/' \
    /etc/xrdp/xrdp.ini

echo "Activating SessionSockdirGroup and disabling root login in sesman.ini ..."
sed -i \
    -e 's/^AllowRootLogin=true$/AllowRootLogin=false/' \
    -e 's/^#SessionSockdirGroup=xrdp$/SessionSockdirGroup=xrdp/' \
    /etc/xrdp/sesman.ini

echo "Repairing permissions for xrdp runtime files ..."
chown root:xrdp /etc/xrdp/rsakeys.ini /etc/xrdp/cert.pem /etc/xrdp/key.pem
chmod 640 /etc/xrdp/rsakeys.ini /etc/xrdp/cert.pem /etc/xrdp/key.pem

mkdir -p /etc/tmpfiles.d
cat > /etc/tmpfiles.d/xrdp.conf <<'EOF'
d /run/xrdp 0755 root xrdp -
EOF
systemd-tmpfiles --create /etc/tmpfiles.d/xrdp.conf
chown root:xrdp /run/xrdp
chmod 755 /run/xrdp

echo "Restarting xrdp services ..."
systemctl restart xrdp-sesman.service xrdp.service

echo
echo "Running xrdp privilege checker ..."
/usr/share/xrdp/xrdp-chkpriv || true

echo
echo "Verification:"
systemctl --no-pager --full status xrdp.service xrdp-sesman.service | sed -n '1,120p'
echo
ss -tulpn | grep ':3389\b' || true
echo
journalctl -u xrdp.service -u xrdp-sesman.service -n 80 --no-pager || true
