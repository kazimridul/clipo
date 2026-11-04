#!/usr/bin/env python3
"""Run inside a disposable Ubuntu container: install old/new packages and verify data."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from clipo.storage.repository import HistoryRepository
from clipo.models.item import HistoryQuery


def run(command):
    subprocess.run(command, check=True)


def startup(data):
    process = subprocess.Popen(['/usr/bin/clipo','--data-dir',str(data)],env={**os.environ,'QT_QPA_PLATFORM':'offscreen'},stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        time.sleep(.8)
        if process.poll() is not None:
            raise RuntimeError('Application exited during upgrade probe startup')
    finally:
        process.terminate()
        output, errors = process.communicate(timeout=10)
    assert process.returncode == 0, errors.decode(errors='replace')


def main():
    if os.environ.get('CLIPO_DISPOSABLE_INSTALL_TEST') != '1':
        raise SystemExit('Only run in a disposable container with CLIPO_DISPOSABLE_INSTALL_TEST=1')
    previous, current = map(str, map(Path, sys.argv[1:3]))
    with tempfile.TemporaryDirectory(prefix='clipo-upgrade-test-') as folder:
        root = Path(folder)
        repo = HistoryRepository(root/'history.sqlite3')
        repo.add('Preserve Unicode বাংলা and pinned data',100)
        item=repo.page(HistoryQuery()).items[0]
        repo.flag(item.id,'is_pinned')
        repo.organize(item.id,'upgrade-check','Work')
        repo.close()
        run(['apt-get','install','-y',previous])
        startup(root)
        run(['apt-get','install','-y',current])
        run(['/usr/bin/clipo','--self-test'])
        startup(root)
        repo=HistoryRepository(root/'history.sqlite3')
        item=repo.get(item.id)
        assert item.content_text=='Preserve Unicode বাংলা and pinned data'
        assert item.is_pinned and item.tags=='upgrade-check' and item.collections=='Work'
        repo.close()
        run(['apt-get','remove','-y','clipo'])
        assert (root/'history.sqlite3').exists()
        print('PASS: real 0.2 → 0.3 package upgrade, preserved Unicode/pins/tags/collections, startup and uninstall',flush=True)


if __name__=='__main__': main()
