"""Best-effort active-application identity on X11, never inferred on Wayland."""
import os


def active_application():
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return None
    try:
        from Xlib import X, display
        connection = display.Display()
        try:
            atom = connection.intern_atom("_NET_ACTIVE_WINDOW")
            value = connection.screen().root.get_full_property(atom, X.AnyPropertyType)
            if value and value.value[0]:
                window = connection.create_resource_object("window", value.value[0])
                return ".".join(window.get_wm_class() or ()) or None
        finally:
            connection.close()
    except Exception:
        pass
    return None
