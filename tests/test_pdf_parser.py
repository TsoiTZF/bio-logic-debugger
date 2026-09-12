import sys
from types import SimpleNamespace


def test_extract_text_stops_at_max_chars(monkeypatch):
    class Page:
        def get_text(self):
            return "abcd"

    class Doc:
        def __len__(self):
            return 50

        def load_page(self, _i):
            return Page()

        def close(self):
            return None

    monkeypatch.setitem(sys.modules, "fitz", SimpleNamespace(open=lambda *a, **k: Doc()))
    from bio_logic_debugger.knowledge.pdf_parser import extract_text
    text = extract_text(b"%PDF", max_chars=10)
    assert "abcd" in text
    assert text.count("abcd") <= 3
