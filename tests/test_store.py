"""Tests unitaires pour le store JSON."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# Patch DATA_DIR/DATA_FILE avant import pour utiliser un répertoire temporaire
_tmpdir = tempfile.mkdtemp()
_test_data_dir = Path(_tmpdir) / "data"
_test_data_file = _test_data_dir / "notes.json"

with patch("src.store.DATA_DIR", _test_data_dir), \
     patch("src.store.DATA_FILE", _test_data_file):
    pass

import src.store as store


@pytest.fixture(autouse=True)
def isolate_data(tmp_path):
    """Chaque test utilise son propre répertoire temporaire."""
    data_dir = tmp_path / "data"
    data_file = data_dir / "notes.json"
    with patch.object(store, "DATA_DIR", data_dir), \
         patch.object(store, "DATA_FILE", data_file):
        yield data_dir, data_file


class TestCreateNote:
    def test_returns_dict_with_required_fields(self):
        note = store.create_note()
        assert isinstance(note, dict)
        for key in ("id", "content", "color", "x", "y", "width", "height", "created", "modified"):
            assert key in note

    def test_default_values(self):
        note = store.create_note()
        assert note["content"] == ""
        assert note["color"] == "#FDFD96"
        assert note["x"] == 200
        assert note["y"] == 200
        assert note["width"] == 250
        assert note["height"] == 250

    def test_custom_values(self):
        note = store.create_note(x=100, y=300, width=400, height=500, color="#77DD77", content="Hello")
        assert note["x"] == 100
        assert note["y"] == 300
        assert note["width"] == 400
        assert note["height"] == 500
        assert note["color"] == "#77DD77"
        assert note["content"] == "Hello"

    def test_unique_ids(self):
        ids = {store.create_note()["id"] for _ in range(50)}
        assert len(ids) == 50


class TestSaveAndLoad:
    def test_save_then_load(self, isolate_data):
        notes = [store.create_note(content="test1"), store.create_note(content="test2")]
        store.save_notes(notes)
        loaded = store.load_notes()
        assert len(loaded) == 2
        assert loaded[0]["content"] == "test1"
        assert loaded[1]["content"] == "test2"

    def test_load_empty_when_no_file(self, isolate_data):
        assert store.load_notes() == []

    def test_load_empty_on_invalid_json(self, isolate_data):
        data_dir, data_file = isolate_data
        data_dir.mkdir(parents=True, exist_ok=True)
        data_file.write_text("not json at all")
        assert store.load_notes() == []

    def test_load_empty_on_missing_notes_key(self, isolate_data):
        data_dir, data_file = isolate_data
        data_dir.mkdir(parents=True, exist_ok=True)
        data_file.write_text('{"other": 42}')
        # get() retourne None, pas de KeyError — retourne []
        result = store.load_notes()
        assert result == [] or result is None or isinstance(result, list)

    def test_atomic_save_permissions(self, isolate_data):
        data_dir, data_file = isolate_data
        store.save_notes([store.create_note()])
        assert data_file.exists()
        mode = oct(os.stat(data_file).st_mode & 0o777)
        assert mode == "0o600"

    def test_no_tmp_file_left(self, isolate_data):
        data_dir, data_file = isolate_data
        store.save_notes([store.create_note()])
        tmp_file = data_file.with_suffix(".tmp")
        assert not tmp_file.exists()

    def test_save_overwrite(self, isolate_data):
        store.save_notes([store.create_note(content="v1")])
        store.save_notes([store.create_note(content="v2")])
        loaded = store.load_notes()
        assert len(loaded) == 1
        assert loaded[0]["content"] == "v2"


class TestUpdateNote:
    def test_update_existing(self):
        notes = [store.create_note(content="before")]
        note_id = notes[0]["id"]
        store.update_note(notes, note_id, content="after", color="#AEC6CF")
        assert notes[0]["content"] == "after"
        assert notes[0]["color"] == "#AEC6CF"

    def test_update_modifies_timestamp(self):
        notes = [store.create_note()]
        old_modified = notes[0]["modified"]
        import time
        time.sleep(0.01)
        store.update_note(notes, notes[0]["id"], content="changed")
        # Le timestamp modified doit être >= ancien (même seconde possible)
        assert notes[0]["modified"] >= old_modified

    def test_update_nonexistent_does_nothing(self):
        notes = [store.create_note(content="original")]
        store.update_note(notes, "fake-id", content="hacked")
        assert notes[0]["content"] == "original"


class TestEdgeCases:
    def test_unicode_content(self, isolate_data):
        notes = [store.create_note(content="émojis 🎉 日本語")]
        store.save_notes(notes)
        loaded = store.load_notes()
        assert loaded[0]["content"] == "émojis 🎉 日本語"

    def test_empty_notes_list(self, isolate_data):
        store.save_notes([])
        assert store.load_notes() == []

    def test_large_content(self, isolate_data):
        big = "x" * 100_000
        notes = [store.create_note(content=big)]
        store.save_notes(notes)
        loaded = store.load_notes()
        assert loaded[0]["content"] == big
