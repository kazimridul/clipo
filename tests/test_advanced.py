from io import BytesIO
import xml.etree.ElementTree as ET
import pytest
from PIL import Image
from clipo.services.qr import generate_qr, QROptions, split_payload
from clipo.services.recognition import recognize, format_json
from clipo.services.ocr import extract_text
from clipo.system.shortcuts import parse_shortcut


def test_qr_png_svg_and_unicode_payload_parts():
    text = "Hello বাংলা 👋\n  exact text  "
    png, svg = generate_qr(text)
    image = Image.open(BytesIO(png))
    assert image.width == image.height and image.width <= 512
    root = ET.fromstring(svg)
    assert root.tag.endswith("svg")
    assert root.find("{http://www.w3.org/2000/svg}path") is not None
    chunks = split_payload(text * 100, 50)
    assert "".join(chunks) == text * 100
    assert all(len(chunk.encode()) <= 50 for chunk in chunks)


@pytest.mark.parametrize("text", ["https://ubuntu.com", "  বাংলা 👋\nexact text  ", "WIFI:T:WPA;S:Test Network;P:example-only;;", "def hello():\n    return 42"])
def test_qr_decode_preserves_exact_payload(text):
    import zxingcpp
    png, _ = generate_qr(text)
    decoded = zxingcpp.read_barcode(Image.open(BytesIO(png)))
    assert decoded is not None
    assert decoded.bytes == text.encode("utf-8")


@pytest.mark.parametrize("text,options", [("", QROptions()), ("x" * 4000, QROptions()), ("text", QROptions(foreground="#ffffff")), ("text", QROptions(background="red")), ("a" * 1000, QROptions(size=128))])
def test_qr_rejects_unscannable_or_oversize_inputs(text, options):
    with pytest.raises(ValueError):
        generate_qr(text, options)


def test_recognition_and_json_never_execute_content():
    assert recognize("https://ubuntu.com")[0] == "url"
    assert recognize("me@example.com")[0] == "email"
    assert recognize('{"hello":1}') == ("snippet", "JSON")
    assert recognize("def hello():\n    return 1") == ("snippet", "Python")
    assert format_json('{ "a": 1 }', True) == '{"a":1}'
    with pytest.raises(ValueError):
        format_json("__import__('os').system('false')")


def test_ocr_missing_engine_has_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setattr("clipo.services.ocr.shutil.which", lambda _: None)
    with pytest.raises(ValueError, match="Tesseract"):
        extract_text(tmp_path / "image.png")


def test_real_ocr_when_engine_available(tmp_path):
    import shutil
    if not shutil.which("tesseract"):
        pytest.skip("Optional Tesseract engine is not installed")
    from PIL import ImageDraw, ImageFont
    image = Image.new("RGB", (1100, 180), "white")
    draw = ImageDraw.Draw(image)
    draw.text((40, 45), "Clipo reads clipboard images", fill="black", font=ImageFont.load_default(size=48))
    path = tmp_path / "ocr.png"
    image.save(path)
    assert extract_text(path) == "Clipo reads clipboard images"


def test_ocr_invocation_is_argument_list_and_handles_failures(monkeypatch, tmp_path):
    from types import SimpleNamespace
    path = tmp_path / "image; touch ignored.png"
    path.write_bytes(b"test")
    monkeypatch.setattr("clipo.services.ocr.shutil.which", lambda _: "/usr/bin/tesseract")
    calls = []
    def run(arguments, **kwargs):
        calls.append(arguments)
        return SimpleNamespace(returncode=0, stdout="  Extracted text\n")
    monkeypatch.setattr("clipo.services.ocr.subprocess.run", run)
    assert extract_text(path, "eng+ben") == "Extracted text"
    assert calls[0] == ["tesseract", str(path), "stdout", "-l", "eng+ben"]
    with pytest.raises(ValueError):
        extract_text(path, "--help")


def test_shortcut_parser():
    assert parse_shortcut("Ctrl+Shift+V") == ("V", 5)
    with pytest.raises(ValueError):
        parse_shortcut("SuperMagic+X")


def test_quick_popup_search_and_copy(qtbot):
    from clipo.ui.quick_popup import QuickPopup
    from clipo.models.item import ClipboardItem, HistoryPage, HistoryQuery
    popup = QuickPopup()
    qtbot.addWidget(popup)
    popup.generation = 1
    popup.show_page(HistoryPage(HistoryQuery(), (ClipboardItem(3, "copy me", "hash", "2026-11-04"),), 1), 1)
    with qtbot.waitSignal(popup.restore_requested) as signal:
        popup.copy()
    assert signal.args == [3]


def test_background_job_dispatches_result_on_gui_thread(qtbot):
    from PySide6.QtCore import QThread
    from clipo.services.jobs import JobRunner
    runner = JobRunner()
    results = []
    gui = QThread.currentThread()
    runner.submit(lambda: 42, lambda value: results.append((value, QThread.currentThread() == gui)), lambda error: results.append(error))
    qtbot.waitUntil(lambda: bool(results))
    assert results == [(42, True)]
    runner.close()
