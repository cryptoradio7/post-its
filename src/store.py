"""
Store JSON — persistance des notes dans data/notes.json
Sauvegarde atomique (.tmp puis rename), résilience JSON invalide.
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_FILE = DATA_DIR / "notes.json"

COLORS = {
    "jaune": "#FDFD96",
    "vert": "#77DD77",
    "bleu": "#AEC6CF",
    "rose": "#FFB7CE",
}

DEFAULT_COLOR = COLORS["jaune"]


def _ensure_data_dir():
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_notes() -> list[dict]:
    """Charge les notes depuis le JSON. Retourne [] si fichier absent ou invalide."""
    _ensure_data_dir()
    if not DATA_FILE.exists():
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("notes", [])
    except (json.JSONDecodeError, ValueError, KeyError):
        return []


def save_notes(notes: list[dict]):
    """Sauvegarde atomique : écriture .tmp, fsync, rename, permissions 0600."""
    _ensure_data_dir()
    tmp_file = DATA_FILE.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump({"notes": notes}, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(str(tmp_file), str(DATA_FILE))
    os.chmod(str(DATA_FILE), 0o600)


def create_note(x=200, y=200, width=250, height=250, color=None, content="") -> dict:
    """Crée une note avec des valeurs par défaut."""
    now = datetime.now().isoformat(timespec="seconds")
    return {
        "id": str(uuid.uuid4()),
        "content": content,
        "color": color or DEFAULT_COLOR,
        "x": x,
        "y": y,
        "width": width,
        "height": height,
        "created": now,
        "modified": now,
    }


def update_note(notes: list[dict], note_id: str, **kwargs):
    """Met à jour les champs d'une note existante."""
    for note in notes:
        if note["id"] == note_id:
            note.update(kwargs)
            note["modified"] = datetime.now().isoformat(timespec="seconds")
            return
