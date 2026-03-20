"""
Fenêtre post-it — chaque note = une Gtk.Window indépendante.
Drag par barre de titre, resize par bords/coins, menu couleur clic droit.
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

COLOR_NAMES = {
    "#FDFD96": "jaune",
    "#77DD77": "vert",
    "#AEC6CF": "bleu",
    "#FFB7CE": "rose",
}

COLORS_LIST = ["#FDFD96", "#77DD77", "#AEC6CF", "#FFB7CE"]
COLOR_LABELS = {"#FDFD96": "Jaune", "#77DD77": "Vert", "#AEC6CF": "Bleu", "#FFB7CE": "Rose"}

RESIZE_MARGIN = 8  # pixels de zone sensible sur les bords


class NoteWindow(Gtk.Window):
    """Fenêtre post-it unique."""

    def __init__(self, app, note_data: dict):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.app = app
        self.note_data = note_data
        self._drag_offset = None
        self._drag_win_origin = None
        self._resize_edge = None
        self._resize_origin = None
        self._resize_win_geom = None
        self._save_pos_timer = None
        self._save_size_timer = None
        self._save_text_timer = None

        self._setup_window()
        self._build_ui()
        self._apply_color()
        self._load_content()

    def _setup_window(self):
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_decorated(False)
        self.set_resizable(True)
        self.set_default_size(
            max(self.note_data.get("width", 250), 100),
            max(self.note_data.get("height", 250), 100),
        )
        self.set_size_request(100, 100)

        x = self.note_data.get("x", 200)
        y = self.note_data.get("y", 200)
        self.move(x, y)

        self.connect("configure-event", self._on_configure)
        self.connect("delete-event", self._on_delete)

        # Events pour le resize sur les bords
        self.add_events(
            Gdk.EventMask.POINTER_MOTION_MASK
            | Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
        )
        self.connect("motion-notify-event", self._on_window_motion)
        self.connect("button-press-event", self._on_window_press)
        self.connect("button-release-event", self._on_window_release)

        self.get_style_context().add_class("note-window")

    def _build_ui(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_margin_start(RESIZE_MARGIN)
        vbox.set_margin_end(RESIZE_MARGIN)
        vbox.set_margin_bottom(RESIZE_MARGIN)
        self.add(vbox)

        # Barre de titre custom
        titlebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        titlebar.get_style_context().add_class("note-titlebar")
        self._titlebar = titlebar

        # Ronds de couleur
        for hex_color in COLORS_LIST:
            color_btn = Gtk.Button()
            color_btn.set_size_request(16, 16)
            color_btn.get_style_context().add_class("color-dot")
            color_btn.get_style_context().add_class(f"dot-{COLOR_NAMES[hex_color]}")
            color_btn.set_tooltip_text(COLOR_LABELS[hex_color])
            color_btn.connect("clicked", self._on_color_dot_clicked, hex_color)
            titlebar.pack_start(color_btn, False, False, 2)

        # Zone draggable (EventBox) — espace entre les ronds et les boutons
        drag_area = Gtk.EventBox()
        drag_area.set_hexpand(True)
        drag_area.connect("button-press-event", self._on_title_press)
        drag_area.connect("motion-notify-event", self._on_title_motion)
        drag_area.connect("button-release-event", self._on_title_release)
        drag_area.set_events(
            Gdk.EventMask.BUTTON_PRESS_MASK
            | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK
        )

        # Bouton +
        add_btn = Gtk.Button(label="+")
        add_btn.get_style_context().add_class("note-add-btn")
        add_btn.connect("clicked", self._on_add_clicked)

        # Bouton fermer
        close_btn = Gtk.Button(label="✕")
        close_btn.get_style_context().add_class("note-close-btn")
        close_btn.connect("clicked", self._on_close_clicked)

        titlebar.pack_start(drag_area, True, True, 0)
        titlebar.pack_end(close_btn, False, False, 2)
        titlebar.pack_end(add_btn, False, False, 2)

        vbox.pack_start(titlebar, False, False, 0)

        # Zone texte
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)

        self.textview = Gtk.TextView()
        self.textview.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.textview.get_style_context().add_class("note-textview")
        self.textview.get_buffer().connect("changed", self._on_text_changed)

        scrolled.add(self.textview)
        vbox.pack_start(scrolled, True, True, 0)

        self.show_all()

    def _apply_color(self):
        color = self.note_data.get("color", "#FDFD96")
        name = COLOR_NAMES.get(color, "jaune")

        sc = self.get_style_context()
        for cn in COLOR_NAMES.values():
            sc.remove_class(f"color-{cn}")
        sc.add_class(f"color-{name}")

        tb_sc = self._titlebar.get_style_context()
        for cn in COLOR_NAMES.values():
            tb_sc.remove_class(f"titlebar-{cn}")
        tb_sc.add_class(f"titlebar-{name}")

        css = f".color-{name} {{ background-color: {color}; }}"
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode())
        sc.add_provider(provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 1)

    def _load_content(self):
        content = self.note_data.get("content", "")
        self.textview.get_buffer().set_text(content)

    # --- Détection bord/coin sous le curseur ---
    def _get_edge(self, x, y):
        """Retourne le bord/coin sous (x,y) ou None si dans la zone intérieure."""
        w, h = self.get_size()
        m = RESIZE_MARGIN

        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m

        if top and left:
            return Gdk.WindowEdge.NORTH_WEST
        if top and right:
            return Gdk.WindowEdge.NORTH_EAST
        if bottom and left:
            return Gdk.WindowEdge.SOUTH_WEST
        if bottom and right:
            return Gdk.WindowEdge.SOUTH_EAST
        if left:
            return Gdk.WindowEdge.WEST
        if right:
            return Gdk.WindowEdge.EAST
        if top:
            return Gdk.WindowEdge.NORTH
        if bottom:
            return Gdk.WindowEdge.SOUTH
        return None

    def _cursor_for_edge(self, edge):
        """Retourne le type de curseur pour un bord."""
        mapping = {
            Gdk.WindowEdge.NORTH: Gdk.CursorType.TOP_SIDE,
            Gdk.WindowEdge.SOUTH: Gdk.CursorType.BOTTOM_SIDE,
            Gdk.WindowEdge.WEST: Gdk.CursorType.LEFT_SIDE,
            Gdk.WindowEdge.EAST: Gdk.CursorType.RIGHT_SIDE,
            Gdk.WindowEdge.NORTH_WEST: Gdk.CursorType.TOP_LEFT_CORNER,
            Gdk.WindowEdge.NORTH_EAST: Gdk.CursorType.TOP_RIGHT_CORNER,
            Gdk.WindowEdge.SOUTH_WEST: Gdk.CursorType.BOTTOM_LEFT_CORNER,
            Gdk.WindowEdge.SOUTH_EAST: Gdk.CursorType.BOTTOM_RIGHT_CORNER,
        }
        return mapping.get(edge)

    # --- Resize via bords/coins ---
    def _on_window_motion(self, widget, event):
        if self._resize_edge is not None:
            self._do_resize(event.x_root, event.y_root)
            return True

        edge = self._get_edge(event.x, event.y)
        gdk_win = self.get_window()
        if gdk_win is None:
            return False

        if edge is not None:
            cursor_type = self._cursor_for_edge(edge)
            cursor = Gdk.Cursor.new_for_display(self.get_display(), cursor_type)
            gdk_win.set_cursor(cursor)
        else:
            gdk_win.set_cursor(None)
        return False

    def _on_window_press(self, widget, event):
        if event.button != 1:
            return False
        edge = self._get_edge(event.x, event.y)
        if edge is not None:
            self._resize_edge = edge
            self._resize_origin = (event.x_root, event.y_root)
            pos = self.get_position()
            size = self.get_size()
            self._resize_win_geom = (pos[0], pos[1], size[0], size[1])
            return True
        return False

    def _on_window_release(self, widget, event):
        if self._resize_edge is not None:
            self._resize_edge = None
            return True
        return False

    def _do_resize(self, x_root, y_root):
        """Calcule la nouvelle géométrie pendant un resize."""
        ox, oy = self._resize_origin
        wx, wy, ww, wh = self._resize_win_geom
        dx = x_root - ox
        dy = y_root - oy
        edge = self._resize_edge

        new_x, new_y, new_w, new_h = wx, wy, ww, wh

        if edge in (Gdk.WindowEdge.EAST, Gdk.WindowEdge.NORTH_EAST, Gdk.WindowEdge.SOUTH_EAST):
            new_w = max(100, ww + int(dx))
        if edge in (Gdk.WindowEdge.WEST, Gdk.WindowEdge.NORTH_WEST, Gdk.WindowEdge.SOUTH_WEST):
            new_w = max(100, ww - int(dx))
            new_x = wx + ww - new_w
        if edge in (Gdk.WindowEdge.SOUTH, Gdk.WindowEdge.SOUTH_EAST, Gdk.WindowEdge.SOUTH_WEST):
            new_h = max(100, wh + int(dy))
        if edge in (Gdk.WindowEdge.NORTH, Gdk.WindowEdge.NORTH_EAST, Gdk.WindowEdge.NORTH_WEST):
            new_h = max(100, wh - int(dy))
            new_y = wy + wh - new_h

        self.move(new_x, new_y)
        self.resize(new_w, new_h)

    # --- Drag par barre de titre ---
    def _on_title_press(self, widget, event):
        if event.button == 1:
            self._drag_offset = (event.x_root, event.y_root)
            win_pos = self.get_position()
            self._drag_win_origin = (win_pos[0], win_pos[1])

    def _on_title_motion(self, widget, event):
        if self._drag_offset:
            dx = event.x_root - self._drag_offset[0]
            dy = event.y_root - self._drag_offset[1]
            new_x = int(self._drag_win_origin[0] + dx)
            new_y = int(self._drag_win_origin[1] + dy)
            self.move(new_x, new_y)

    def _on_title_release(self, widget, event):
        self._drag_offset = None

    # --- Configure (position/taille) ---
    def _on_configure(self, widget, event):
        if self._save_pos_timer:
            GLib.source_remove(self._save_pos_timer)
        self._save_pos_timer = GLib.timeout_add(500, self._save_position)

        if self._save_size_timer:
            GLib.source_remove(self._save_size_timer)
        self._save_size_timer = GLib.timeout_add(500, self._save_size)
        return False

    def _save_position(self):
        pos = self.get_position()
        self.note_data["x"] = pos[0]
        self.note_data["y"] = pos[1]
        self.app.save()
        self._save_pos_timer = None
        return False

    def _save_size(self):
        size = self.get_size()
        self.note_data["width"] = max(size[0], 100)
        self.note_data["height"] = max(size[1], 100)
        self.app.save()
        self._save_size_timer = None
        return False

    # --- Texte ---
    def _on_text_changed(self, buffer):
        if self._save_text_timer:
            GLib.source_remove(self._save_text_timer)
        self._save_text_timer = GLib.timeout_add(500, self._save_text)

    def _save_text(self):
        buf = self.textview.get_buffer()
        start, end = buf.get_bounds()
        text = buf.get_text(start, end, True)
        self.note_data["content"] = text
        from datetime import datetime
        self.note_data["modified"] = datetime.now().isoformat(timespec="seconds")
        self.app.save()
        self._save_text_timer = None
        return False

    # --- Boutons ---
    def _on_close_clicked(self, btn):
        """Suppression explicite du post-it (bouton ✕)."""
        self.app.delete_note(self.note_data["id"])
        self.destroy()

    def _on_add_clicked(self, btn):
        self.app.create_new_note()

    def _on_delete(self, widget, event):
        # Fermeture via WM (Alt+F4, etc.) → cacher la fenêtre, pas supprimer la note
        self.hide()
        return True

    # --- Changement de couleur via ronds ---
    def _on_color_dot_clicked(self, btn, hex_color):
        self.note_data["color"] = hex_color
        self._apply_color()
        self.app.save()

    def focus_textview(self):
        """Donne le focus au TextView."""
        self.textview.grab_focus()
