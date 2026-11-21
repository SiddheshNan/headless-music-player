from mutagen.id3 import APIC, TALB, TIT2, TPE1
from mutagen.wave import WAVE

from headless_music_player.library import Library
from headless_music_player.library import library as library_module

from .conftest import make_wav

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def tag(path, title=None, artist=None, album=None, cover=None):
    audio = WAVE(path)
    audio.add_tags()
    if title:
        audio.tags.add(TIT2(encoding=3, text=title))
    if artist:
        audio.tags.add(TPE1(encoding=3, text=artist))
    if album:
        audio.tags.add(TALB(encoding=3, text=album))
    if cover:
        audio.tags.add(APIC(encoding=3, mime="image/png", type=3, desc="", data=cover))
    audio.save()


def test_scans_subfolders_and_skips_others(tmp_path):
    music = tmp_path / "music"
    make_wav(music / "top.wav")
    make_wav(music / "Album" / "Disc 1" / "deep.wav")
    make_wav(music / ".hidden" / "skip.wav")
    make_wav(music / "._junk.wav")
    (music / "notes.txt").write_text("not music")
    lib = Library(music, tmp_path / "cache")
    result = lib.scan()
    assert result.total == 2
    assert sorted(t.id for t in lib.tracks()) == ["Album/Disc 1/deep.wav", "top.wav"]
    assert lib.path_for("Album/Disc 1/deep.wav").is_file()


def test_reads_tags_and_stores_shared_covers_once(tmp_path):
    music = tmp_path / "music"
    tag(make_wav(music / "x.wav"), "Song X", "Band", "Record", PNG)
    tag(make_wav(music / "y.wav"), "Song Y", "Band", "Record", PNG)
    lib = Library(music, tmp_path / "cache")
    lib.scan()
    x = lib.get("x.wav")
    assert (x.title, x.artist, x.album, x.duration_ms) == ("Song X", "Band", "Record", 60_000)
    assert x.cover and x.cover == lib.get("y.wav").cover and x.cover.endswith(".png")
    assert len(list(lib.covers_dir.iterdir())) == 1
    assert lib.cover_path(x.cover).read_bytes() == PNG


def test_untagged_files_use_artist_dash_title(library):
    track = library.get("A - One.wav")
    assert (track.title, track.artist) == ("One", "A")


def test_index_cache_avoids_rereading_unchanged_files(tmp_path, music_dir, monkeypatch):
    Library(music_dir, tmp_path / "cache").scan()
    reads = []
    original = library_module.read_metadata
    monkeypatch.setattr(library_module, "read_metadata", lambda p: reads.append(p) or original(p))

    lib = Library(music_dir, tmp_path / "cache")
    lib.load_cache()
    assert len(lib) == 4
    lib.scan()
    assert reads == []

    make_wav(music_dir / "A - One.wav", 30_000)
    lib.scan()
    assert [p.name for p in reads] == ["A - One.wav"]
    assert lib.get("A - One.wav").duration_ms == 30_000


def test_removed_files_drop_out_and_covers_are_pruned(tmp_path):
    music = tmp_path / "music"
    tag(make_wav(music / "x.wav"), "X", cover=PNG)
    lib = Library(music, tmp_path / "cache")
    lib.scan()
    version = lib.version
    (music / "x.wav").unlink()
    result = lib.scan()
    assert result.removed == 1 and len(lib) == 0 and lib.version > version
    assert list(lib.covers_dir.iterdir()) == []


def test_cover_path_rejects_anything_but_cover_names(library):
    assert library.cover_path("../state.json") is None
    assert library.cover_path("library.json") is None
