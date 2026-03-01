#!/bin/bash
# ============================================================
# TC420 Controller — Build Ubuntu .deb installer
# ============================================================
# Usage: bash build_deb.sh
# Output: dist/tc420-controller_1.0_amd64.deb
# ============================================================

set -e

APP_NAME="tc420-controller"
APP_VERSION="1.0"
ARCH="amd64"
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
DIST_DIR="$PROJECT_DIR/dist"
DEB_ROOT="$BUILD_DIR/deb_package"
DEB_FILE="$DIST_DIR/${APP_NAME}_${APP_VERSION}_${ARCH}.deb"

echo "🔨 Building TC420 Controller v${APP_VERSION} for Ubuntu..."

# ---- Step 1: Clean previous builds ----
echo "📦 Cleaning previous builds..."
rm -rf "$BUILD_DIR" "$DIST_DIR"
mkdir -p "$BUILD_DIR" "$DIST_DIR"

# ---- Step 2: Build standalone executable with PyInstaller ----
echo "⚙️  Building standalone executable with PyInstaller..."

# Install PyInstaller if needed
pip install pyinstaller 2>/dev/null || pip3 install pyinstaller 2>/dev/null || python3 -m pip install pyinstaller

cd "$PROJECT_DIR"
python3 -m PyInstaller \
    --noconfirm \
    --onedir \
    --name "$APP_NAME" \
    --windowed \
    --add-data "$PROJECT_DIR/assets:assets" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtGui" \
    --hidden-import "usb" \
    --hidden-import "usb.core" \
    --hidden-import "usb.backend" \
    --hidden-import "usb.backend.libusb1" \
    --distpath "$DIST_DIR/pyinstaller" \
    --workpath "$BUILD_DIR/pyinstaller" \
    --specpath "$BUILD_DIR" \
    main.py

echo "✅ Executable built successfully"

# ---- Step 3: Create .deb package structure ----
echo "📁 Creating .deb package structure..."

mkdir -p "$DEB_ROOT/DEBIAN"
mkdir -p "$DEB_ROOT/opt/$APP_NAME"
mkdir -p "$DEB_ROOT/usr/share/applications"
mkdir -p "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$DEB_ROOT/usr/bin"
mkdir -p "$DEB_ROOT/etc/udev/rules.d"

# ---- Step 4: Copy files ----
echo "📋 Copying files..."

# Copy the PyInstaller output
cp -r "$DIST_DIR/pyinstaller/$APP_NAME/"* "$DEB_ROOT/opt/$APP_NAME/"

# Create launcher symlink script
cat > "$DEB_ROOT/usr/bin/$APP_NAME" << 'LAUNCHER'
#!/bin/bash
exec /opt/tc420-controller/tc420-controller "$@"
LAUNCHER
chmod +x "$DEB_ROOT/usr/bin/$APP_NAME"

# Copy desktop file
cp "$PROJECT_DIR/tc420-controller.desktop" "$DEB_ROOT/usr/share/applications/"

# Copy icon
cp "$PROJECT_DIR/assets/icons/tc420-controller.svg" "$DEB_ROOT/usr/share/icons/hicolor/scalable/apps/"

# Copy udev rules
cat > "$DEB_ROOT/etc/udev/rules.d/99-tc420.rules" << 'UDEV'
# TC420 LED Controller - allow access for plugdev group
SUBSYSTEM=="usb", ATTR{idVendor}=="0888", ATTR{idProduct}=="4000", MODE="0666", GROUP="plugdev"
UDEV

# ---- Step 5: Create DEBIAN control file ----
echo "📝 Creating package metadata..."

cat > "$DEB_ROOT/DEBIAN/control" << EOF
Package: $APP_NAME
Version: $APP_VERSION
Section: utils
Priority: optional
Architecture: $ARCH
Depends: libusb-1.0-0
Installed-Size: $(du -sk "$DEB_ROOT/opt" | cut -f1)
Maintainer: TC420 Controller <tc420@localhost>
Description: TC420 LED Controller GUI Application
 A modern GUI application to program and control TC420 USB LED
 controllers on Ubuntu. Features a visual 24-hour timeline editor
 with 5 independent channels, 4 programmable modes, manual channel
 control, and save/load program files.
 .
 Designed for aquarium lighting, plant growth, and any multi-channel
 LED automation project.
Homepage: https://github.com/tc420-controller
EOF

# ---- Step 6: Create post-install script ----
cat > "$DEB_ROOT/DEBIAN/postinst" << 'POSTINST'
#!/bin/bash
set -e

# Reload udev rules
udevadm control --reload-rules 2>/dev/null || true
udevadm trigger 2>/dev/null || true

# Update icon cache
gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true

# Update desktop database
update-desktop-database /usr/share/applications 2>/dev/null || true

echo ""
echo "✅ TC420 Controller installed successfully!"
echo "   Launch from Applications menu or run: tc420-controller"
echo ""
echo "⚠️  If using a TC420 device, you may need to:"
echo "   1. Add your user to the plugdev group: sudo adduser \$USER plugdev"
echo "   2. Unplug and replug your TC420 device"
echo "   3. Log out and back in for group changes to take effect"
echo ""
POSTINST
chmod 755 "$DEB_ROOT/DEBIAN/postinst"

# ---- Step 7: Create post-remove script ----
cat > "$DEB_ROOT/DEBIAN/postrm" << 'POSTRM'
#!/bin/bash
set -e
# Clean up on removal
if [ "$1" = "purge" ]; then
    rm -rf /opt/tc420-controller
fi
update-desktop-database /usr/share/applications 2>/dev/null || true
gtk-update-icon-cache /usr/share/icons/hicolor 2>/dev/null || true
POSTRM
chmod 755 "$DEB_ROOT/DEBIAN/postrm"

# ---- Step 8: Set correct permissions ----
echo "🔒 Setting permissions..."
find "$DEB_ROOT" -type d -exec chmod 755 {} \;
find "$DEB_ROOT/opt" -type f -exec chmod 644 {} \;
chmod 755 "$DEB_ROOT/opt/$APP_NAME/$APP_NAME"
chmod 755 "$DEB_ROOT/usr/bin/$APP_NAME"

# ---- Step 9: Build .deb ----
echo "📦 Building .deb package..."
dpkg-deb --build --root-owner-group "$DEB_ROOT" "$DEB_FILE"

# ---- Done ----
DEB_SIZE=$(du -h "$DEB_FILE" | cut -f1)
echo ""
echo "============================================================"
echo "✅ Package built successfully!"
echo "   📦 $DEB_FILE"
echo "   📏 Size: $DEB_SIZE"
echo ""
echo "   To install:"
echo "     sudo dpkg -i $DEB_FILE"
echo ""
echo "   To uninstall:"
echo "     sudo apt remove $APP_NAME"
echo "============================================================"
