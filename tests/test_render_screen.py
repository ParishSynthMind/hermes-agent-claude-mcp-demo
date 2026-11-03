import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import render_screen as rs  # noqa: E402


def test_colour_markers():
    rows = rs.parse("$ run it\n! refused\n+ ok\nplain")
    assert rows[0] == ("$ run it", rs.COLOURS["$ "])
    assert rows[1] == ("refused", rs.COLOURS["! "])
    assert rows[3][1] == rs.PLAIN


def test_renders_png(tmp_path):
    out = tmp_path / "s.png"
    rs.render(rs.parse((ROOT / "media" / "screens" / "refusal.txt").read_text()), "t").save(out)
    assert out.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"
