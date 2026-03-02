"""
File I/O for TC420 program files.
Save/load program configurations as JSON (.tc420) and XML (PLED) files.
"""
import json
import os
import xml.etree.ElementTree as ET
from typing import Optional, List, Tuple
from src.models import AppState, ModeProgram, ChannelProgram, TimePoint, NUM_CHANNELS, CHANNEL_NAMES, NUM_MODES


def save_program(state: AppState, filepath: str) -> bool:
    """Save the current program to a .tc420 JSON file."""
    try:
        data = state.to_dict()
        data["version"] = "1.0"
        data["app"] = "TC420 Controller"

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error saving program: {e}")
        return False


def load_program(filepath: str) -> Optional[AppState]:
    """Load a program from a .tc420 JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return AppState.from_dict(data)
    except Exception as e:
        print(f"Error loading program: {e}")
        return None


def load_xml_mode_names(filepath: str) -> List[str]:
    """Read an XML file and return the list of mode names available."""
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        return [mode.get("name", f"Mode {i+1}") for i, mode in enumerate(root.findall("mode"))]
    except Exception as e:
        print(f"Error reading XML mode names: {e}")
        return []


def _parse_xml_mode(mode_elem) -> ModeProgram:
    """Parse a single <mode> XML element into a ModeProgram."""
    mode_name = mode_elem.get("name", "Mode")
    channels = []
    for ch_idx, channel_elem in enumerate(mode_elem.findall("channel")):
        points = []
        for step in channel_elem.findall("step"):
            hour = int(step.get("hour", "0"))
            minute = int(step.get("minute", "0"))
            value = int(step.get("value", "0"))
            time_minutes = hour * 60 + minute
            # Clamp to valid range
            time_minutes = max(0, min(1439, time_minutes))
            value = max(0, min(100, value))
            points.append(TimePoint(time_minutes=time_minutes, brightness=value))
        ch_name = CHANNEL_NAMES[ch_idx] if ch_idx < NUM_CHANNELS else f"Channel {ch_idx+1}"
        ch = ChannelProgram(points=points, name=ch_name)
        ch.sort()
        channels.append(ch)
    mode = ModeProgram(name=mode_name)
    mode.channels = channels
    # Pad to NUM_CHANNELS if needed
    while len(mode.channels) < NUM_CHANNELS:
        mode.channels.append(ChannelProgram(name=CHANNEL_NAMES[len(mode.channels)]))
    return mode


def load_xml_program(filepath: str, selected_indices: List[int]) -> Optional[AppState]:
    """Load selected modes from a PLED XML file into an AppState.

    Args:
        filepath: Path to the XML file.
        selected_indices: Indices of modes to load. They are mapped
                          to Mode 1-N in the app.
    """
    try:
        tree = ET.parse(filepath)
        root = tree.getroot()
        all_modes = root.findall("mode")

        state = AppState()
        # Limit to NUM_MODES
        max_to_load = min(len(selected_indices), NUM_MODES)
        for app_idx, xml_idx in enumerate(selected_indices[:max_to_load]):
            if 0 <= xml_idx < len(all_modes):
                mode = _parse_xml_mode(all_modes[xml_idx])
                mode.name = f"Mode {app_idx + 1} ({mode.name})"
                state.modes[app_idx] = mode

        return state
    except Exception as e:
        print(f"Error loading XML program: {e}")
        return None
