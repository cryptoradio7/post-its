"""
Fenêtre de contrôle — petite fenêtre avec bouton "+" pour créer des post-its.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk


class ControlWindow(Gtk.Window):
    """Fenêtre de contrôle minimaliste."""

    def __init__(self, app):
        super().__init__(title="Post-its")
        self.app = app

        self.set_default_size(180, 60)
        self.set_resizable(False)
        self.set_keep_above(True)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.get_style_context().add_class("control-window")

        self.connect("delete-event", self._on_close)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hbox.set_margin_start(10)
        hbox.set_margin_end(10)
        hbox.set_margin_top(8)
        hbox.set_margin_bottom(8)

        label = Gtk.Label(label="Post-its")
        label.get_style_context().add_class("control-title")
        hbox.pack_start(label, True, True, 0)

        add_btn = Gtk.Button(label="+")
        add_btn.set_tooltip_text("Nouveau post-it")
        add_btn.get_style_context().add_class("note-add-btn")
        add_btn.connect("clicked", self._on_add)
        hbox.pack_end(add_btn, False, False, 0)

        self.add(hbox)

        # Sous Wayland, move() est ignoré. On utilise set_gravity + set_position
        # pour demander au WM de placer la fenêtre au mieux.
        self.set_gravity(Gdk.Gravity.NORTH_EAST)
        self.set_position(Gtk.WindowPosition.NONE)
        self.show_all()

        # Tenter move() — fonctionne sous X11, ignoré sous Wayland
        screen = Gdk.Screen.get_default()
        screen_w = screen.get_width()
        self.move(screen_w - 200, 20)

    def _on_add(self, btn):
        self.app.create_new_note()

    def _on_close(self, widget, event):
        self.app.quit()
        return True
