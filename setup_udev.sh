#!/bin/bash
# TC420 LED Controller - udev rules setup
# Run this script with sudo to enable USB access without root

RULES_FILE="/etc/udev/rules.d/99-tc420.rules"

echo "Installing TC420 udev rules..."

cat > "$RULES_FILE" << 'EOF'
# TC420 LED Controller
# Allow access for users in plugdev group
SUBSYSTEM=="usb", ATTR{idVendor}=="0888", ATTR{idProduct}=="4000", MODE="0666", GROUP="plugdev"
EOF

# Reload udev rules
udevadm control --reload-rules
udevadm trigger

# Add current user to plugdev group if not already a member
if ! groups "$SUDO_USER" | grep -q plugdev; then
    adduser "$SUDO_USER" plugdev
    echo "Added $SUDO_USER to plugdev group. Please log out and back in for changes to take effect."
fi

echo "TC420 udev rules installed successfully!"
echo "Please unplug and replug your TC420 device."
