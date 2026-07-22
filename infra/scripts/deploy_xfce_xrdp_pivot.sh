#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root." >&2
    exit 1
fi

XRDP_TAG="${XRDP_TAG:-v0.10.3}"
XORGXRDP_TAG="${XORGXRDP_TAG:-v0.10.4}"
BUILD_ROOT="${BUILD_ROOT:-/usr/local/src/dadm-xrdp-build}"
SYSTEMD_UNIT_DIR="$(pkg-config --variable=systemdsystemunitdir systemd)"

echo "Installing required packages ..."
pacman -Syu --needed --noconfirm \
    base-devel git autoconf automake libtool pkgconf nasm \
    openssl pam libx11 libxfixes libxrandr systemd \
    xorg-server xorg-xinit xfce4 xterm

mkdir -p "${BUILD_ROOT}"
rm -rf "${BUILD_ROOT}/xrdp" "${BUILD_ROOT}/xorgxrdp"

echo "Cloning xrdp ${XRDP_TAG} ..."
git clone --recursive --depth 1 --branch "${XRDP_TAG}" \
    https://github.com/neutrinolabs/xrdp.git "${BUILD_ROOT}/xrdp"

echo "Building xrdp ${XRDP_TAG} ..."
pushd "${BUILD_ROOT}/xrdp" >/dev/null
./bootstrap
./configure \
    --prefix=/usr \
    --sysconfdir=/etc \
    --localstatedir=/var \
    --with-systemdsystemunitdir="${SYSTEMD_UNIT_DIR}"
make -j"$(nproc)"
make install
popd >/dev/null

echo "Cloning xorgxrdp ${XORGXRDP_TAG} ..."
git clone --depth 1 --branch "${XORGXRDP_TAG}" \
    https://github.com/neutrinolabs/xorgxrdp.git "${BUILD_ROOT}/xorgxrdp"

echo "Building xorgxrdp ${XORGXRDP_TAG} ..."
pushd "${BUILD_ROOT}/xorgxrdp" >/dev/null
./bootstrap
./configure --prefix=/usr
make -j"$(nproc)"
make install
popd >/dev/null

echo "Installing Arch PAM profile for xrdp-sesman ..."
install -Dm644 \
    "${BUILD_ROOT}/xrdp/instfiles/pam.d/xrdp-sesman.arch" \
    /etc/pam.d/xrdp-sesman

echo "Generating xrdp RSA keys if needed ..."
if [[ ! -f /etc/xrdp/rsakeys.ini ]]; then
    /usr/bin/xrdp-keygen xrdp auto
fi

echo "Configuring Xfce as the xrdp session ..."
if [[ -f /etc/xrdp/startwm.sh && ! -f /etc/xrdp/startwm.sh.dadm-20260330.bak ]]; then
    cp /etc/xrdp/startwm.sh /etc/xrdp/startwm.sh.dadm-20260330.bak
fi
cat > /etc/xrdp/startwm.sh <<'EOF'
#!/usr/bin/env bash
export DESKTOP_SESSION=xfce
export XDG_SESSION_DESKTOP=xfce
export XDG_CURRENT_DESKTOP=XFCE
exec startxfce4
EOF
chmod 755 /etc/xrdp/startwm.sh

echo "Adding Xorg wrapper compatibility for headless xrdp ..."
mkdir -p /etc/X11
cat > /etc/X11/Xwrapper.config <<'EOF'
allowed_users=anybody
needs_root_rights=yes
EOF
chmod 644 /etc/X11/Xwrapper.config

echo "Handing port 3389 from GNOME RDP to xrdp ..."
systemctl disable --now gnome-remote-desktop.service || true
systemctl disable --now gdm.service || true

echo "Starting xrdp services ..."
systemctl daemon-reload
systemctl enable --now xrdp-sesman.service xrdp.service

echo
echo "Verification:"
systemctl --no-pager --full status xrdp.service xrdp-sesman.service | sed -n '1,120p'
echo
ss -tulpn | grep ':3389\b' || true
echo
journalctl -u xrdp.service -u xrdp-sesman.service -n 80 --no-pager || true
