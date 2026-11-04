# Packaging and installation checks

The portable executable is a PyInstaller directory bundle, with dynamically loaded
Qt libraries, application resources, and collected third-party license notices.
The Debian package installs it to `/opt/clipo`, adds `/usr/bin/clipo`, a desktop
entry, icon, and AppStream metadata. No installation script touches clipboard data.
User config/history persist across package removal and upgrades.

## Native build

```bash
sudo apt install libpython3.12 binutils dpkg-dev
.venv/bin/python -m pip install -e '.[test,build]'
.venv/bin/python scripts/package_linux.py
```

Use the `libpython` package matching the build interpreter. The script measures
versioned glibc dependencies in bundled ELF files and adds the minimum to Debian
metadata. Build on the oldest Ubuntu release you intend to support: copying a
newer system's libraries into an AppImage does not make them compatible with older
systems.

## Isolated Ubuntu 24.04 build

```bash
docker build -f packaging/Dockerfile.ubuntu24 -t clipo-build:ubuntu24 .
```

The Docker build runs the test suite, isolated native X11 probe, actual `.deb`
installation, frozen executable startup/shutdown, uninstall, and a data-preservation
check. It does not install Clipo on the host. Build artifacts are under `/work/dist`
in the resulting image and can be exported with `docker create` / `docker cp`,
then the export container can be removed.

The current release binaries were built using Ubuntu 24.04 / Python 3.12.3 and
require glibc 2.38 or newer. Ubuntu 24.04 supplies a suitable runtime. The desktop
and OCR dependencies in Debian metadata are resolved by `apt install ./file.deb`.

## AppImage

The project does not download build tools automatically. Obtain the official
[appimagetool](https://github.com/AppImage/appimagetool/releases) and
[type2 runtime](https://github.com/AppImage/type2-runtime/releases) artifacts.
Their exact approved SHA-256 values are recorded in `packaging/appimage-tools.json`.
The current upstream continuous URLs may change: a mismatched checksum stops the
build and must be reviewed before updating the pins.

```bash
.venv/bin/python scripts/package_linux.py \
  --bundle build/ubuntu24-clipo \
  --appimagetool /path/to/appimagetool.AppImage \
  --runtime /path/to/runtime-x86_64
```

`--bundle` packages an already frozen bundle from the older target OS. Without it,
the script freezes the current environment. No FUSE mount is needed during build;
the build tool is run with `--appimage-extract-and-run`. AppImage users can use the
same fallback if their desktop lacks FUSE.

`dist/build-manifest.json` records checksums, sizes, glibc minimum, and original
bundle build environment. Build outputs are ignored by Git. The CI workflow also
builds an Ubuntu 24.04 Debian artifact; it has not been pushed or run remotely here.

AppStream metadata is validated explicitly with `--no-net` when `appstreamcli`
is available; appimagetool's additional network-based validation is disabled.
This keeps packaging offline after the pinned tools have been obtained.
