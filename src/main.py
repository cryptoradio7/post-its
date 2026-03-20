#!/usr/bin/env python3
"""
Post-its Desktop — Point d'entrée.
Charge les notes, ouvre les fenêtres, gère le cycle de vie.
"""

import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk

# Ajouter src/ au path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from store import load_notes, save_notes, create_note
from note_window import NoteWindow
from control_window import ControlWindow


class PostItsApp:
    """Application principale."""

    def __init__(self):
        self.notes = []          # Liste de dicts
        self.windows = {}        # id → NoteWindow
        self.control = None

    def run(self):
        self._load_css()
        self.notes = load_notes()

        # Fenêtre de contrôle
        self.control = ControlWindow(self)

        # Ouvrir une fenêtre par note existante
        for note_data in self.notes:
            win = NoteWindow(self, note_data)
            self.windows[note_data["id"]] = win

        Gtk.main()

    def _load_css(self):
        css_path = Path(__file__).resolve().parent / "style.css"
        if css_path.exists():
            provider = Gtk.CssProvider()
            provider.load_from_path(str(css_path))
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )

    def save(self):
        """Sauvegarde toutes les notes."""
        save_notes(self.notes)

    def create_new_note(self):
        """Crée un nouveau post-it jaune, décalé si overlap."""
        # Position de base : centre écran
        screen = Gdk.Screen.get_default()
        cx = screen.get_width() // 2 - 125
        cy = screen.get_height() // 2 - 125

        # Décaler si un post-it existe déjà à cette position
        offset = 0
        existing_positions = {(n["x"], n["y"]) for n in self.notes}
        while (cx + offset, cy + offset) in existing_positions:
            offset += 30

        note_data = create_note(x=cx + offset, y=cy + offset)
        self.notes.append(note_data)
        self.save()

        win = NoteWindow(self, note_data)
        self.windows[note_data["id"]] = win
        win.present()
        win.focus_textview()

    def delete_note(self, note_id: str):
        """Supprime une note par son ID."""
        self.notes = [n for n in self.notes if n["id"] != note_id]
        self.windows.pop(note_id, None)
        self.save()

    def quit(self):
        """Sauvegarde finale et fermeture."""
        self.save()
        # Fermer toutes les fenêtres post-it
        for win in list(self.windows.values()):
            win.destroy()
        Gtk.main_quit()


if __name__ == "__main__":
    app = PostItsApp()
    app.run()
