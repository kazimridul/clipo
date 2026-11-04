#!/usr/bin/env python3
"""Run only in a private headless GNOME session with the test fixture enabled."""
import base64
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QTimer
from PySide6.QtDBus import QDBusInterface
from PySide6.QtGui import QIcon, QImage, QColor
from PySide6.QtWidgets import QApplication
from clipo.application.controller import Controller
from clipo.config.settings import Settings
from clipo.models.item import HistoryQuery
from clipo.storage.repository import HistoryRepository


def main():
    if os.environ.get('CLIPO_ISOLATED_DISPLAY') != '1':
        raise SystemExit('Only run in an isolated GNOME session; this modifies its test clipboard.')
    app = QApplication([])
    with tempfile.TemporaryDirectory(prefix='clipo-wayland-history-') as folder:
        root = Path(folder)
        controller = Controller(app, Settings(), root/'settings.json', root/'data', QIcon(str(Path(__file__).parents[1]/'src/clipo/resources/clipo.svg')))
        producer = QDBusInterface('com.clipo.TestProducer','/com/clipo/TestProducer','com.clipo.TestProducer')
        assert producer.isValid(), producer.lastError().message()
        image = QImage(70,50,QImage.Format.Format_RGBA8888)
        image.fill(QColor('#6754d9'))
        from PySide6.QtCore import QBuffer, QIODevice
        buffer = QBuffer(); buffer.open(QIODevice.OpenModeFlag.WriteOnly); image.save(buffer,'PNG')
        png = base64.b64encode(bytes(buffer.data())).decode()
        def text(value):
            reply = producer.call('SetText',value)
            assert not reply.errorMessage(), reply.errorMessage()
        def content(mime,data):
            reply = producer.call('SetContent',mime,data)
            assert not reply.errorMessage(), reply.errorMessage()
        exact = '  Wayland background বাংলা 👋\n\tExact text  '
        QTimer.singleShot(1500, lambda: text(exact))
        QTimer.singleShot(2300, lambda: text(exact))
        QTimer.singleShot(3100, lambda: text('https://ubuntu.com'))
        QTimer.singleShot(3900, lambda: content('image/png',png))
        QTimer.singleShot(4700, lambda: content('text/uri-list',base64.b64encode(b'file:///tmp/clipo-test.txt\r\n').decode()))
        QTimer.singleShot(5500, lambda: content('text/uri-list',base64.b64encode(b'https://ubuntu.com/desktop\r\n').decode()))
        QTimer.singleShot(6300, lambda: controller.monitor.set_private(True))
        QTimer.singleShot(6600, lambda: text('private text must not persist'))
        QTimer.singleShot(7400, lambda: controller.monitor.set_private(False))
        QTimer.singleShot(8300, app.quit)
        app.exec()
        repo=HistoryRepository(root/'data/history.sqlite3')
        page=repo.page(HistoryQuery())
        print([(item.id,item.content_type) for item in page.items],flush=True)
        assert page.total==5, f'Expected 5 events, got {page.total}'
        assert repo.get(1).content_text==exact
        assert repo.get(2).content_type=='url'
        assert repo.get(3).content_type=='image'
        assert repo.get(4).content_type=='files'
        assert repo.get(5).content_type=='url' and repo.get(5).content_text=='https://ubuntu.com/desktop'
        assert controller.monitor.external_active
        assert repo.page(HistoryQuery(text='private text')).total==0
        repo.close()
        print('PASS: real headless GNOME Wayland background bridge, exact Unicode, deduplication, URL, image, file URLs, private mode, resume without retroactive capture',flush=True)


if __name__=='__main__': main()
