"""
File I/O for TC420 program files.
Save/load program configurations as JSON (.tc420 files).
"""
import json
import os
from typing import Optional
from src.models import AppState


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
