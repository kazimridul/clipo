"""Exercise the real D-Bus wire protocol against a private fake portal."""
import asyncio
import shutil
import socket
import subprocess
import threading
import pytest
from clipo.system.portal import PortalShortcut

XML = '''<node><interface name="org.freedesktop.portal.GlobalShortcuts">
<method name="CreateSession"><arg type="a{sv}" direction="in"/><arg type="o" direction="out"/></method>
<method name="BindShortcuts"><arg type="o" direction="in"/><arg type="a(sa{sv})" direction="in"/><arg type="s" direction="in"/><arg type="a{sv}" direction="in"/><arg type="o" direction="out"/></method>
</interface></node>'''


@pytest.mark.parametrize("deny", [False, True])
def test_portal_registration_response_activation_denial_and_cleanup(qtbot, tmp_path, deny):
    if not shutil.which("dbus-daemon"):
        pytest.skip("D-Bus daemon is not installed")
    try:
        with socket.socket(socket.AF_UNIX) as probe:
            probe.bind(str(tmp_path / "probe.sock"))
    except PermissionError:
        pytest.skip("Sandbox blocks Unix sockets")
    daemon = subprocess.Popen(["dbus-daemon", "--session", "--nofork", "--print-address=1"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    address = daemon.stdout.readline().strip()
    started = threading.Event()
    state = {"calls": []}

    async def serve():
        from dbus_next.aio import MessageBus
        from dbus_next import Message, MessageType, Variant
        bus = await MessageBus(bus_address=address).connect()
        await bus.request_name("org.freedesktop.portal.Desktop")
        loop = asyncio.get_running_loop()
        stop = asyncio.Event()
        state.update(loop=loop, stop=stop)
        session = "/org/freedesktop/portal/desktop/session/test/one"
        def handler(message):
            if message.message_type != MessageType.METHOD_CALL:
                return
            state["calls"].append(message.member)
            if message.member == "Introspect":
                return Message.new_method_return(message, "s", [XML])
            if message.member in ("Register", "Close"):
                return Message.new_method_return(message)
            if message.member in ("CreateSession", "BindShortcuts"):
                token = message.body[-1]["handle_token"].value
                sender = message.sender[1:].replace(".", "_")
                path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
                values = {"session_handle": Variant("s", session)} if message.member == "CreateSession" else {"shortcuts": Variant("a(sa{sv})", [["quick", {"description": Variant("s", "Clipo")} ]])}
                denied = deny and message.member == "BindShortcuts"
                loop.call_later(.02, lambda: bus.send(Message.new_signal(path, "org.freedesktop.portal.Request", "Response", "ua{sv}", [2 if denied else 0, {} if denied else values])))
                if message.member == "BindShortcuts" and not denied:
                    loop.call_later(.05, lambda: bus.send(Message.new_signal("/org/freedesktop/portal/desktop", "org.freedesktop.portal.GlobalShortcuts", "Activated", "osta{sv}", [session, "quick", 0, {}])))
                return Message.new_method_return(message, "o", [path])
        bus.add_message_handler(handler)
        started.set()
        await stop.wait()
        bus.disconnect()

    thread = threading.Thread(target=lambda: asyncio.run(serve()), daemon=True)
    thread.start()
    assert started.wait(5)
    portal = PortalShortcut("Ctrl+Shift+V", bus_address=address)
    statuses, activations = [], []
    portal.status.connect(statuses.append)
    portal.activated.connect(lambda: activations.append(True))
    try:
        portal.start()
        qtbot.waitUntil(lambda: bool(statuses), timeout=5000)
        if deny:
            assert "denied" in statuses[-1]
        else:
            qtbot.waitUntil(lambda: bool(activations), timeout=5000)
            assert "connected" in statuses[-1]
        portal.close()
        assert not portal.isRunning()
        assert "Register" in state["calls"] and "BindShortcuts" in state["calls"]
        assert state["calls"].count("Close") >= 2
    finally:
        portal.close()
        state["loop"].call_soon_threadsafe(state["stop"].set)
        thread.join(3)
        daemon.terminate()
        daemon.communicate(timeout=3)
