"""
TC420 Device Manager — wraps USB HID communication.
Provides a mock mode when no device is connected.
"""
import time
import threading
from typing import Optional, Callable, List
from datetime import datetime
from src.models import ModeProgram, ChannelProgram, TimePoint, NUM_CHANNELS


class TC420DeviceManager:
    """Manages USB HID communication with the TC420 LED controller."""

    # TC420 USB identifiers
    VENDOR_ID = 0x0888
    PRODUCT_ID = 0x4000

    def __init__(self):
        self._connected = False
        self._device = None
        self._mock_mode = False
        self._lock = threading.Lock()
        self._on_connection_change: Optional[Callable] = None
        self._mock_channel_values = [0] * NUM_CHANNELS
        self._mock_modes: List[ModeProgram] = [
            ModeProgram(name=f"Mode {i+1}") for i in range(4)
        ]
        self._mock_active_mode = 0

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    def set_connection_callback(self, callback: Callable):
        self._on_connection_change = callback

    def connect(self) -> tuple[bool, str]:
        """
        Try to connect to a real TC420 device.
        If not found, fall back to mock mode.
        """
        with self._lock:
            try:
                import usb.core
                import usb.util

                dev = usb.core.find(
                    idVendor=self.VENDOR_ID,
                    idProduct=self.PRODUCT_ID
                )

                if dev is not None:
                    try:
                        if dev.is_kernel_driver_active(0):
                            dev.detach_kernel_driver(0)
                    except Exception:
                        pass

                    dev.set_configuration()
                    self._device = dev
                    self._connected = True
                    self._mock_mode = False

                    if self._on_connection_change:
                        self._on_connection_change(True)

                    return True, "TC420 connecté avec succès!"
                else:
                    return self._connect_mock()

            except ImportError:
                return self._connect_mock()
            except Exception as e:
                return self._connect_mock()

    def _connect_mock(self) -> tuple[bool, str]:
        """Connect in mock/simulation mode."""
        self._connected = True
        self._mock_mode = True
        self._device = None

        if self._on_connection_change:
            self._on_connection_change(True)

        return True, "Mode simulation activé (aucun TC420 détecté)"

    def disconnect(self) -> tuple[bool, str]:
        """Disconnect from device."""
        with self._lock:
            if self._device:
                try:
                    import usb.util
                    usb.util.dispose_resources(self._device)
                except Exception:
                    pass

            self._connected = False
            self._device = None
            self._mock_mode = False

            if self._on_connection_change:
                self._on_connection_change(False)

            return True, "Déconnecté"

    def sync_time(self) -> tuple[bool, str]:
        """Sync device time with system clock."""
        if not self._connected:
            return False, "Non connecté"

        if self._mock_mode:
            now = datetime.now()
            return True, f"Heure synchronisée (simulation): {now.strftime('%H:%M:%S')}"

        try:
            now = datetime.now()
            # TC420 time sync protocol
            # Command: 0x04 (set time)
            data = bytearray(64)
            data[0] = 0x04  # Set time command
            data[1] = now.year - 2000
            data[2] = now.month
            data[3] = now.day
            data[4] = now.hour
            data[5] = now.minute
            data[6] = now.second
            data[7] = now.weekday()

            self._send_command(data)
            return True, f"Heure synchronisée: {now.strftime('%H:%M:%S')}"
        except Exception as e:
            return False, f"Erreur sync: {e}"

    def get_device_time(self) -> Optional[str]:
        """Get current time from device."""
        if not self._connected:
            return None
        if self._mock_mode:
            return datetime.now().strftime("%H:%M:%S")

        try:
            data = bytearray(64)
            data[0] = 0x05  # Get time command
            response = self._send_command(data, expect_response=True)
            if response:
                h = response[4]
                m = response[5]
                s = response[6]
                return f"{h:02d}:{m:02d}:{s:02d}"
        except Exception:
            pass
        return None

    def set_channel(self, channel: int, brightness: int) -> tuple[bool, str]:
        """Set a single channel brightness (0-100). Direct/manual control."""
        if not self._connected:
            return False, "Non connecté"
        if not 0 <= channel < NUM_CHANNELS:
            return False, "Canal invalide"

        brightness = max(0, min(100, brightness))

        if self._mock_mode:
            self._mock_channel_values[channel] = brightness
            return True, f"CH{channel+1}: {brightness}%"

        try:
            # TC420 direct control protocol
            data = bytearray(64)
            data[0] = 0x07  # Set channel command
            data[1] = channel
            data[2] = brightness
            self._send_command(data)
            return True, f"CH{channel+1}: {brightness}%"
        except Exception as e:
            return False, f"Erreur: {e}"

    def set_all_channels(self, values: list) -> tuple[bool, str]:
        """Set all 5 channels at once."""
        if not self._connected:
            return False, "Non connecté"

        if self._mock_mode:
            for i, v in enumerate(values[:NUM_CHANNELS]):
                self._mock_channel_values[i] = max(0, min(100, v))
            return True, "Tous les canaux mis à jour"

        try:
            data = bytearray(64)
            data[0] = 0x07
            for i, v in enumerate(values[:NUM_CHANNELS]):
                data[1 + i] = max(0, min(100, v))
            self._send_command(data)
            return True, "Tous les canaux mis à jour"
        except Exception as e:
            return False, f"Erreur: {e}"

    def upload_program(self, mode_index: int, program: ModeProgram) -> tuple[bool, str]:
        """Upload a mode program to the device."""
        if not self._connected:
            return False, "Non connecté"
        if not 0 <= mode_index < 4:
            return False, "Mode invalide"

        if self._mock_mode:
            self._mock_modes[mode_index] = program
            return True, f"Programme '{program.name}' envoyé (simulation)"

        try:
            # Send each channel's time points
            for ch_idx, channel in enumerate(program.channels):
                num_points = len(channel.points)

                # First send the header for this channel
                data = bytearray(64)
                data[0] = 0x02  # Program mode command
                data[1] = mode_index
                data[2] = ch_idx
                data[3] = num_points
                self._send_command(data)

                # Then send the time points in batches
                for i, point in enumerate(channel.points):
                    data = bytearray(64)
                    data[0] = 0x03  # Time point data
                    data[1] = mode_index
                    data[2] = ch_idx
                    data[3] = i
                    data[4] = point.hours
                    data[5] = point.minutes
                    data[6] = point.brightness
                    self._send_command(data)

                time.sleep(0.05)  # Small delay between channels

            return True, f"Programme '{program.name}' envoyé!"
        except Exception as e:
            return False, f"Erreur upload: {e}"

    def set_active_mode(self, mode_index: int) -> tuple[bool, str]:
        """Set the active mode on the device."""
        if not self._connected:
            return False, "Non connecté"

        if self._mock_mode:
            self._mock_active_mode = mode_index
            return True, f"Mode {mode_index + 1} activé (simulation)"

        try:
            data = bytearray(64)
            data[0] = 0x06  # Set active mode
            data[1] = mode_index
            self._send_command(data)
            return True, f"Mode {mode_index + 1} activé"
        except Exception as e:
            return False, f"Erreur: {e}"

    def _send_command(self, data: bytearray, expect_response: bool = False):
        """Send raw command to TC420 via USB HID."""
        if not self._device:
            return None

        try:
            # TC420 uses endpoint 0x02 for output, 0x81 for input
            self._device.write(0x02, data)

            if expect_response:
                response = self._device.read(0x81, 64, timeout=1000)
                return response
        except Exception as e:
            raise e

        return None

    def get_status_text(self) -> str:
        """Get a human-readable status string."""
        if not self._connected:
            return "⚫ Déconnecté"
        if self._mock_mode:
            return "🟡 Mode simulation"
        return "🟢 TC420 connecté"
