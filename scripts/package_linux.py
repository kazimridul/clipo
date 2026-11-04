#!/usr/bin/env python3
"""Build standalone binary, Debian package and optional AppImage without root."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from clipo import __version__

ROOT = Path(__file__).resolve().parents[1]


def run(arguments, **kwargs):
    subprocess.run([str(value) for value in arguments], check=True, **kwargs)


def minimum_glibc(bundle):
    versions = [(2, 34)]
    for path in bundle.rglob("*"):
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb") as stream:
            if stream.read(4) != b"\x7fELF":
                continue
        result = subprocess.run(["readelf", "--version-info", str(path)], capture_output=True, text=True, check=True)
        versions.extend((int(major), int(minor)) for major, minor in re.findall(r"GLIBC_(\d+)\.(\d+)", result.stdout))
    return ".".join(map(str, max(versions)))


def licenses(bundle):
    target = bundle / "licenses"
    target.mkdir(exist_ok=True)
    for package in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "Pillow", "qrcode", "python-xlib", "six", "Pygments", "pyinstaller"):
        distribution = importlib.metadata.distribution(package)
        for entry in distribution.files or []:
            if entry.name.lower().startswith(("license", "copying", "notice")):
                original = Path(distribution.locate_file(entry))
                if original.is_file():
                    directory = target / package
                    directory.mkdir(exist_ok=True)
                    shutil.copyfile(original, directory / entry.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-freeze", action="store_true")
    parser.add_argument("--bundle", type=Path, help="Package an existing frozen bundle, e.g. one built on Ubuntu 24.04")
    parser.add_argument("--appimagetool", type=Path)
    parser.add_argument("--runtime", type=Path)
    args = parser.parse_args()
    if not args.skip_freeze and not args.bundle:
        run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", ROOT / "packaging/clipo.spec"], cwd=ROOT)
    bundle = args.bundle.resolve() if args.bundle else ROOT / "dist/clipo"
    if not (bundle / "clipo").is_file():
        sys.exit("Build the standalone bundle first")
    licenses(bundle)
    build_info = bundle / "build-environment.json"
    if not args.bundle and not args.skip_freeze:
        build_info.write_text(json.dumps({"os": Path("/etc/os-release").read_text(), "python": sys.version}, indent=2))
    glibc = minimum_glibc(bundle)
    architecture = subprocess.check_output(["dpkg", "--print-architecture"], text=True).strip()
    stage = ROOT / "build/debian"
    if stage.exists():
        shutil.rmtree(stage)
    for directory in ("DEBIAN", "opt", "usr/bin", "usr/share/applications", "usr/share/icons/hicolor/scalable/apps", "usr/share/metainfo"):
        (stage / directory).mkdir(parents=True, exist_ok=True)
    shutil.copytree(bundle, stage / "opt/clipo", symlinks=True)
    launcher = stage / "usr/bin/clipo"
    launcher.write_text('#!/bin/sh\nexec /opt/clipo/clipo "$@"\n')
    launcher.chmod(0o755)
    shutil.copyfile(ROOT / "packaging/clipo.desktop", stage / "usr/share/applications/com.clipo.Clipo.desktop")
    shutil.copyfile(ROOT / "src/clipo/resources/clipo.svg", stage / "usr/share/icons/hicolor/scalable/apps/clipo.svg")
    shutil.copyfile(ROOT / "packaging/com.clipo.Clipo.metainfo.xml", stage / "usr/share/metainfo/com.clipo.Clipo.metainfo.xml")
    installed_kib = sum(file.stat().st_size for file in bundle.rglob("*") if file.is_file() and not file.is_symlink()) // 1024
    (stage / "DEBIAN/control").write_text(
        f"Package: clipo\nVersion: {__version__}\nArchitecture: {architecture}\nMaintainer: Clipo contributors <clipo@localhost>\n"
        f"Installed-Size: {installed_kib}\nSection: utils\nPriority: optional\n"
        f"Depends: libc6 (>= {glibc}), libegl1, libgl1, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-keysyms1, libxcb-shape0, libxcb-xinerama0, libdbus-1-3, libfontconfig1\n"
        "Recommends: tesseract-ocr, tesseract-ocr-eng\nDescription: Local Linux clipboard manager\n Search and organize text and image history, share offline QR codes, and extract text.\n"
    )
    deb = ROOT / f"dist/clipo_{__version__}_{architecture}.deb"
    run(["dpkg-deb", "--root-owner-group", "-Zxz", "--build", stage, deb])
    outputs = [deb]
    if args.appimagetool:
        if architecture != "amd64" or not args.runtime:
            sys.exit("The pinned AppImage toolchain requires amd64 and --runtime")
        pins = json.loads((ROOT / "packaging/appimage-tools.json").read_text())
        for label, file in (("appimagetool", args.appimagetool), ("runtime", args.runtime)):
            if hashlib.sha256(file.read_bytes()).hexdigest() != pins[label]["sha256"]:
                sys.exit(f"{label} checksum did not match the pinned official artifact")
        appdir = ROOT / "build/Clipo.AppDir"
        if appdir.exists():
            shutil.rmtree(appdir)
        (appdir / "usr/lib").mkdir(parents=True)
        shutil.copytree(bundle, appdir / "usr/lib/clipo", symlinks=True)
        shutil.copyfile(ROOT / "packaging/clipo.desktop", appdir / "com.clipo.Clipo.desktop")
        shutil.copyfile(ROOT / "src/clipo/resources/clipo.svg", appdir / "clipo.svg")
        shutil.copyfile(ROOT / "src/clipo/resources/clipo.png", appdir / "clipo.png")
        (appdir / ".DirIcon").symlink_to("clipo.png")
        (appdir / "usr/share/metainfo").mkdir(parents=True)
        shutil.copyfile(ROOT / "packaging/com.clipo.Clipo.metainfo.xml", appdir / "usr/share/metainfo/com.clipo.Clipo.appdata.xml")
        (appdir / "usr/share/applications").mkdir(parents=True)
        shutil.copyfile(ROOT / "packaging/clipo.desktop", appdir / "usr/share/applications/com.clipo.Clipo.desktop")
        entry = appdir / "AppRun"
        entry.write_text('#!/bin/sh\nCLIPO_APPDIR=$(dirname "$(readlink -f "$0")")\nexec "$CLIPO_APPDIR/usr/lib/clipo/clipo" "$@"\n')
        entry.chmod(0o755)
        output = ROOT / f"dist/Clipo-{__version__}-x86_64.AppImage"
        if shutil.which("appstreamcli"):
            run(["appstreamcli", "validate", "--no-net", "usr/share/metainfo/com.clipo.Clipo.appdata.xml"], cwd=appdir)
        run([args.appimagetool.resolve(), "--appimage-extract-and-run", "--no-appstream", "--runtime-file", args.runtime.resolve(), appdir, output], env={**os.environ, "ARCH": "x86_64", "SOURCE_DATE_EPOCH": "1793757600"})
        outputs.append(output)
    manifest = {"version": __version__, "build_environment": json.loads(build_info.read_text()) if build_info.exists() else {"os": "See original bundle build log"}, "minimum_glibc": glibc,
        "artifacts": {file.name: {"sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "bytes": file.stat().st_size} for file in outputs}}
    (ROOT / "dist/build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
