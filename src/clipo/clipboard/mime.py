"""Qt-owned MIME payloads that can safely outlive Python's interpreter."""
from PySide6.QtGui import QStandardItemModel


def native_mime_data():
    # A Python-constructed QMimeData uses a Shiboken virtual-method trampoline.
    # Qt's global clipboard may destroy it after Python has finalized, crashing
    # process exit (reproduced on PySide 6.12). A C++ model MIME factory returns a
    # native QMimeData without that trampoline. Clear its model format before use.
    model = QStandardItemModel(1, 1)
    mime = model.mimeData([model.index(0, 0)])
    if mime is None:
        raise RuntimeError("Qt could not create a clipboard payload")
    mime.clear()
    return mime
