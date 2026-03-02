"""
TC420 Device Manager — wraps USB HID communication.
Uses the correct TC420 binary protocol (reverse-engineered, GPL-3.0).

Protocol packet format (64 bytes):
  [0-1]  Magic: 0x55 0xAA
  [2]    Command byte
  [3-4]  Data length (big-endian unsigned short)
  [5..]  Payload data
  [-3]   Checksum (sum of all bytes before it, mod 256)
  [-2]   0x0D
  [-1]   0x0A

NOTE: The TC420 is WRITE-ONLY. There is no protocol command to READ
programs back from the device. The device stores programs in its own
memory and runs them autonomously.
"""
import time
import threading
from struct import pack, unpack
from typing import Optional, Callable, List, Tuple
from datetime import datetime
from src.models import ModeProgram, ChannelProgram, TimePoint, NUM_CHANNELS


# ---------------------------------------------------------------------------
# Packet helpers
# ---------------------------------------------------------------------------

class _Packet:
    """Build a 64-byte TC420 protocol packet."""

    MAGIC = b'\x55\xaa'

    def __init__(self, command: int) -> None:
        self._buf = bytearray(64)
        self._buf[0:2] = self.MAGIC
        self._buf[2] = command
        self._pos = 5  # first payload byte

    def _add(self, data: bytes, pos: int = None) -> None:
        p = self._pos if pos is None else (64 + pos if pos < 0 else pos)
        assert p + len(data) <= 62
        self._buf[p:p + len(data)] = data
        if pos is None:
            self._pos += len(data)

    def add_uchar(self, v: int, pos: int = None) -> None:
        self._add(pack('!B', v & 0xff), pos)

    def add_ushort(self, v: int, pos: int = None) -> None:
        self._add(pack('!H', v & 0xffff), pos)

    def add_bytes(self, b: bytes, pos: int = None) -> None:
        self._add(b, pos)

    def build(self) -> bytes:
        # Write data length
        data_len = self._pos - 5
        self._buf[3:5] = pack('!H', data_len)
        # Checksum
        checksum = sum(self._buf[:-3]) & 0xff
        self._buf[-3] = checksum
        self._buf[-2] = 0x0d
        self._buf[-1] = 0x0a
        return bytes(self._buf)


def _pkt_time_sync(dt: datetime = None) -> bytes:
    """Command 0x11 — set device clock."""
    dt = dt or datetime.now()
    p = _Packet(0x11)
    p.add_ushort(dt.year)
    p.add_uchar(dt.month)
    p.add_uchar(dt.day)
    p.add_uchar(dt.hour)
    p.add_uchar(dt.minute)
    p.add_uchar(dt.second)
    return p.build()


def _pkt_mode_init(bank: int, step_count: int, name: str) -> bytes:
    """Command 0x12 — start a mode definition (bank=mode index 0-based)."""
    name_bytes = name.encode('ascii', errors='replace')[:8]
    p = _Packet(0x12)
    p.add_uchar(bank)
    p.add_uchar(step_count)
    p.add_bytes(name_bytes)
    return p.build()


def _pkt_mode_step(hour: int, minute: int, ch: Tuple[int, int, int, int, int]) -> bytes:
    """Command 0x13 — one timeline step (all 5 channels at a given time)."""
    p = _Packet(0x13)
    p.add_uchar(hour)
    p.add_uchar(minute)
    for v in ch:
        p.add_uchar(max(0, min(100, v)))
    p.add_uchar(0)  # jump flags (0 = fade)
    return p.build()


def _pkt_steps_stop() -> bytes:
    """Command 0x01 — end of step list (no response expected)."""
    return _Packet(0x01).build()


def _pkt_mode_stop() -> bytes:
    """Command 0x02 — commit all modes to device."""
    return _Packet(0x02).build()


def _pkt_clear_all() -> bytes:
    """Command 0x03 — erase all modes on device."""
    return _Packet(0x03).build()


def _pkt_play_channels(ch: Tuple[int, int, int, int, int]) -> bytes:
    """Command 0x16 — set live channel brightness values."""
    p = _Packet(0x16)
    p.add_uchar(0xf5)
    for v in ch:
        p.add_uchar(max(0, min(100, v)))
    p.add_uchar(0)
    return p.build()


# ---------------------------------------------------------------------------
# Device Manager
# ---------------------------------------------------------------------------

class TC420DeviceManager:
    """Manages USB HID communication with the TC420 LED controller."""

    VENDOR_ID = 0x0888
    PRODUCT_ID = 0x4000
    USB_TIMEOUT = 5000  # ms

    def __init__(self):
        self._connected = False
        self._device = None
        self._in_ep = None
        self._out_ep = None
        self._mock_mode = False
        self._lock = threading.Lock()
        self._on_connection_change: Optional[Callable] = None
        self._mock_channel_values = [0] * NUM_CHANNELS

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_mock(self) -> bool:
        return self._mock_mode

    def set_connection_callback(self, callback: Callable):
        self._on_connection_change = callback

    def check_connection(self) -> bool:
        """
        Probe the USB bus to verify the TC420 is still attached.
        If the device has been unplugged, clean up state and fire the
        connection-change callback so the UI can update immediately.
        Returns True if still connected, False if just detected as gone.
        """
        if not self._connected or self._mock_mode:
            return self._connected  # Nothing to probe

        try:
            import usb.core
            dev = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)
            if dev is None:
                # Device unplugged — clean up
                self._connected = False
                self._device = None
                self._in_ep = None
                self._out_ep = None
                self._mock_mode = False
                if self._on_connection_change:
                    self._on_connection_change(False)
                return False
            return True
        except Exception:
            # Any USB error → assume disconnected
            self._connected = False
            self._device = None
            self._in_ep = None
            self._out_ep = None
            if self._on_connection_change:
                self._on_connection_change(False)
            return False

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self) -> tuple[bool, str]:
        """Try to connect to a real TC420 device; fall back to mock mode."""
        with self._lock:
            try:
                import usb.core
                import usb.util
                import sys

                dev = usb.core.find(idVendor=self.VENDOR_ID, idProduct=self.PRODUCT_ID)

                if dev is not None:
                    try:
                        if dev.is_kernel_driver_active(0):
                            dev.detach_kernel_driver(0)
                    except Exception:
                        pass

                    dev.set_configuration()

                    # Get the correct endpoints from the interface
                    cfg = dev[0]
                    intf = cfg[(0, 0)]
                    self._in_ep = intf[0]   # Input endpoint (device → host)
                    self._out_ep = intf[1]  # Output endpoint (host → device)

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
        self._in_ep = None
        self._out_ep = None

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
            self._in_ep = None
            self._out_ep = None
            self._mock_mode = False

            if self._on_connection_change:
                self._on_connection_change(False)

            return True, "Déconnecté"

    # ------------------------------------------------------------------
    # Low-level USB send/receive
    # ------------------------------------------------------------------

    def _send(self, packet: bytes, expect_response: bool = True) -> Optional[bytes]:
        """Send a 64-byte packet and optionally read the 64-byte response."""
        if not self._out_ep:
            return None
        try:
            self._out_ep.write(packet, timeout=self.USB_TIMEOUT)
        except Exception as e:
            raise RuntimeError(f"USB write error: {e}") from e
        if expect_response:
            try:
                return bytes(self._in_ep.read(64, timeout=self.USB_TIMEOUT))
            except Exception:
                return None
        return None

    def _drain_input(self) -> None:
        """Discard any pending bytes from the device input buffer."""
        if not self._in_ep:
            return
        try:
            self._in_ep.read(64, timeout=50)  # 50ms — silent discard
        except Exception:
            pass  # Timeout = no stale data, that is fine

    def _send_ok(self, packet: bytes, expect_response: bool = True) -> bool:
        """Send packet and return True if device replied OK (data=0x00)."""
        resp = self._send(packet, expect_response)
        if not expect_response:
            return True
        if resp is None:
            return False
        # Response: the data length is at [3:5] big-endian, data starts at [5]
        data_len = unpack('!H', resp[3:5])[0]
        return data_len == 1 and resp[5:6] == b'\x00'

    # ------------------------------------------------------------------
    # Time sync
    # ------------------------------------------------------------------

    def sync_time(self) -> tuple[bool, str]:
        """Sync device time with system clock."""
        if not self._connected:
            return False, "Non connecté"

        now = datetime.now()
        if self._mock_mode:
            return True, f"Heure synchronisée (simulation): {now.strftime('%H:%M:%S')}"

        try:
            ok = self._send_ok(_pkt_time_sync(now))
            if ok:
                return True, f"Heure synchronisée: {now.strftime('%H:%M:%S')}"
            else:
                return False, "Erreur sync horloge"
        except Exception as e:
            return False, f"Erreur sync: {e}"

    # ------------------------------------------------------------------
    # Channel control (live / manual)
    # ------------------------------------------------------------------

    def set_channel(self, channel: int, brightness: int) -> tuple[bool, str]:
        """Set a single channel brightness (0-100) in live/manual mode."""
        if not self._connected:
            return False, "Non connecté"
        if not 0 <= channel < NUM_CHANNELS:
            return False, "Canal invalide"

        brightness = max(0, min(100, brightness))

        if self._mock_mode:
            self._mock_channel_values[channel] = brightness
            return True, f"CH{channel+1}: {brightness}%"

        try:
            self._mock_channel_values[channel] = brightness
            ch = tuple(self._mock_channel_values)
            self._send(_pkt_play_channels(ch))
            return True, f"CH{channel+1}: {brightness}%"
        except Exception as e:
            return False, f"Erreur: {e}"

    def set_all_channels(self, values: list) -> tuple[bool, str]:
        """Set all 5 channels at once."""
        if not self._connected:
            return False, "Non connecté"

        clamped = [max(0, min(100, v)) for v in values[:NUM_CHANNELS]]
        for i, v in enumerate(clamped):
            self._mock_channel_values[i] = v

        if self._mock_mode:
            return True, "Tous les canaux mis à jour"

        try:
            self._send(_pkt_play_channels(tuple(clamped)))
            return True, "Tous les canaux mis à jour"
        except Exception as e:
            return False, f"Erreur: {e}"

    # ------------------------------------------------------------------
    # Program upload
    # ------------------------------------------------------------------

    def upload_program(self,
                       modes: List[ModeProgram],
                       progress_cb: Callable[[int, int, str], None] = None) -> tuple[bool, str]:
        """
        Upload one or more ModeProgram objects to the device.

        The TC420 works in "banks" — each mode occupies one bank (0-based).
        Steps are interleaved across all channels per time point.

        Args:
            modes: list of ModeProgram to send (index = bank number)
            progress_cb: called with (current_step, total_steps, label)

        NOTE: This clears ALL existing modes on the device first.
        """
        if not self._connected:
            return False, "Non connecté"

        if self._mock_mode:
            names = ", ".join(f"'{m.name}'" for m in modes)
            return True, f"Programmes {names} envoyés (simulation)"

        try:
            # --- 1. Clear device ---
            if progress_cb:
                progress_cb(0, 1, "Effacement des modes existants…")
            ok = self._send_ok(_pkt_clear_all())
            if not ok:
                return False, "Erreur lors de l'effacement des modes"

            # --- 2. Build merged timeline per mode ---
            # The TC420 expects ALL 5 channels' values at each time point.
            # We collect all unique time points per mode and send them together.
            total_steps = sum(
                max(len(ch.points) for ch in m.channels) or 1
                for m in modes
            ) + len(modes)
            done = 0

            for bank, mode in enumerate(modes):
                # Collect all unique time points across 5 channels
                all_times = set()
                for ch in mode.channels:
                    for pt in ch.points:
                        all_times.add(pt.time_minutes)

                if not all_times:
                    # Empty mode — skip (device needs at least 2 steps)
                    continue

                sorted_times = sorted(all_times)

                # Ensure at least 2 steps
                if len(sorted_times) < 2:
                    sorted_times = [0, sorted_times[0]]
                    sorted_times = sorted(set(sorted_times))
                    if len(sorted_times) < 2:
                        sorted_times = [0, 1439]

                step_count = len(sorted_times)

                # Build the 8-char name shown on the TC420 LCD.
                # Mode names from XML look like "Mode 1 (01/03)".
                # We extract the original XML date and prefix "J" → "J01/03".
                import re as _re
                _m = _re.search(r'\(([^)]+)\)$', mode.name.strip())
                if _m:
                    xml_date = _m.group(1)          # e.g. "01/03"
                    name = f"J{xml_date}"[:8]        # "J01/03" = 6 chars
                else:
                    name = (mode.name[:8] if mode.name else f"Mode{bank+1}")

                if progress_cb:
                    progress_cb(done, total_steps, f"Init mode '{name}'…")

                ok = self._send_ok(_pkt_mode_init(bank, step_count, name))
                if not ok:
                    return False, f"Erreur init mode '{name}'"
                done += 1

                # Send each step
                for t in sorted_times:
                    h, m = divmod(t, 60)
                    ch_values = tuple(
                        mode.channels[i].get_brightness_at(t) if i < len(mode.channels) else 0
                        for i in range(5)
                    )
                    ok = self._send_ok(_pkt_mode_step(h, m, ch_values))
                    if not ok:
                        return False, f"Erreur envoi step {h:02d}:{m:02d}"
                    done += 1
                    if progress_cb:
                        progress_cb(done, total_steps, f"Mode '{name}' — {h:02d}:{m:02d}")

                # End of steps — no response expected, but device may
                # still emit one; drain it so it doesn't pollute the next
                # ModeInit response.
                self._send(_pkt_steps_stop(), expect_response=False)
                self._drain_input()

                # Small delay so the TC420 can finalise this mode
                # before we start the next ModeInit command.
                time.sleep(0.15)

            # --- 3. Commit ---
            if progress_cb:
                progress_cb(done, total_steps, "Finalisation…")
            ok = self._send_ok(_pkt_mode_stop())
            if not ok:
                return False, "Erreur lors de la finalisation"

            names = ", ".join(f"'{m.name}'" for m in modes)
            return True, f"✅ Programmes envoyés: {names}"

        except Exception as e:
            return False, f"Erreur upload: {e}"

    def set_active_mode(self, mode_index: int) -> tuple[bool, str]:
        """
        The TC420 doesn't have a 'set active mode via USB' command.
        The active mode is selected on the device itself via its buttons.
        This is a no-op kept for API compatibility.
        """
        return True, f"Mode {mode_index + 1} (sélection manuelle sur l'appareil)"

    def get_status_text(self) -> str:
        """Get a human-readable status string."""
        if not self._connected:
            return "⚫ Déconnecté"
        if self._mock_mode:
            return "🟡 Mode simulation"
        return "🟢 TC420 connecté"
