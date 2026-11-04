import os

# Deterministic UI tests never read or modify the user's desktop clipboard.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
