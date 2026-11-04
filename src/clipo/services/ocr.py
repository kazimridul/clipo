"""Local Tesseract integration, always called from a background job."""
from pathlib import Path
import re
import shutil
import subprocess


def languages():
    if not shutil.which("tesseract"):
        raise ValueError("Install tesseract-ocr and the desired language packs to enable OCR.")
    result = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError("Tesseract could not list its language packs")
    return [line.strip() for line in result.stdout.splitlines()[1:] if re.fullmatch(r"[\w-]+", line.strip())]


def extract_text(path, language="eng"):
    if not shutil.which("tesseract"):
        raise ValueError("OCR needs Tesseract. On Ubuntu install: sudo apt install tesseract-ocr")
    if not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", language):
        raise ValueError("Invalid OCR language; use installed language codes such as eng or eng+ben")
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError("The image file is missing")
    try:
        result = subprocess.run(["tesseract", str(path), "stdout", "-l", language], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise ValueError("OCR timed out after 60 seconds. Try a smaller image.") from None
    if result.returncode:
        raise ValueError("OCR failed. Check the selected language pack and image.")
    if len(result.stdout.encode()) > 8 * 1024 * 1024:
        raise ValueError("OCR output exceeded 8 MiB")
    return result.stdout.strip()


def extract_bytes(data, language="eng"):
    if not shutil.which("tesseract"):
        raise ValueError("OCR needs Tesseract and installed language packs")
    if not re.fullmatch(r"[A-Za-z0-9_]+(?:\+[A-Za-z0-9_]+)*", language):
        raise ValueError("Invalid OCR language")
    try:
        result = subprocess.run(["tesseract", "stdin", "stdout", "-l", language], input=data, capture_output=True, timeout=60)
    except subprocess.TimeoutExpired:
        raise ValueError("OCR timed out after 60 seconds") from None
    if result.returncode or len(result.stdout) > 8 * 1024 * 1024:
        raise ValueError("OCR failed. Check language packs and image size.")
    return result.stdout.decode("utf-8").strip()
