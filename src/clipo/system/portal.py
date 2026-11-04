"""XDG global shortcut registration on a dedicated asyncio/D-Bus thread."""
import asyncio
import uuid
from PySide6.QtCore import QThread, Signal


class PortalShortcut(QThread):
    activated = Signal()
    status = Signal(str)

    def __init__(self, shortcut, parent=None, bus_address=None):
        super().__init__(parent)
        self.shortcut = shortcut
        self.loop = self.task = None
        self.closing = False
        self.bus_address = bus_address

    def run(self):
        asyncio.run(self.main())

    async def main(self):
        from dbus_next.aio import MessageBus
        from dbus_next import Variant, Message, MessageType
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        bus, session = None, None
        requests = {}
        try:
            if self.closing:
                return
            bus = await MessageBus(bus_address=self.bus_address).connect()
            if self.closing:
                return
            await bus.call(Message(destination='org.freedesktop.portal.Desktop', path='/org/freedesktop/portal/desktop', interface='org.freedesktop.host.portal.Registry', member='Register', signature='sa{sv}', body=['com.clipo.Clipo', {}]))
            intro = await bus.introspect('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop')
            proxy = bus.get_proxy_object('org.freedesktop.portal.Desktop', '/org/freedesktop/portal/desktop', intro)
            interface = proxy.get_interface('org.freedesktop.portal.GlobalShortcuts')

            def handler(message):
                if message.message_type == MessageType.SIGNAL and message.interface == 'org.freedesktop.portal.Request' and message.member == 'Response':
                    future = requests.get(message.path)
                    if future and not future.done():
                        future.set_result(message.body)
                if message.message_type == MessageType.SIGNAL and message.interface == 'org.freedesktop.portal.GlobalShortcuts' and message.member == 'Activated' and session and message.body[:2] == [session, 'quick']:
                    self.activated.emit()
            bus.add_message_handler(handler)
            for name in ('org.freedesktop.portal.Request', 'org.freedesktop.portal.GlobalShortcuts'):
                await bus.call(Message(destination='org.freedesktop.DBus', path='/org/freedesktop/DBus', interface='org.freedesktop.DBus', member='AddMatch', signature='s', body=[f"type='signal',interface='{name}'"]))

            async def request(method, arguments):
                token = 'clipo' + uuid.uuid4().hex
                sender = bus.unique_name[1:].replace('.', '_')
                path = f'/org/freedesktop/portal/desktop/request/{sender}/{token}'
                future = self.loop.create_future()
                requests[path] = future
                options = {'handle_token': Variant('s', token)}
                if not arguments:
                    options['session_handle_token'] = Variant('s', 'clipo' + uuid.uuid4().hex)
                try:
                    actual = await method(*arguments, options)
                    requests[actual] = future
                    response, values = await asyncio.wait_for(future, 120)
                    if response:
                        raise ValueError('Desktop shortcut permission was cancelled or denied. Enable it again in Settings to retry.')
                    return values
                finally:
                    try:
                        await asyncio.wait_for(bus.call(Message(destination='org.freedesktop.portal.Desktop', path=path, interface='org.freedesktop.portal.Request', member='Close')), 1)
                    except Exception:
                        pass
                    for key in list(requests):
                        if requests[key] is future:
                            requests.pop(key)

            result = await request(interface.call_create_session, [])
            session = result['session_handle'].value
            preferred = self.shortcut.replace('Ctrl', 'CTRL').replace('Shift', 'SHIFT').replace('Alt', 'ALT').replace('Meta', 'LOGO')
            result = await request(interface.call_bind_shortcuts, [session, [['quick', {'description': Variant('s', 'Open Clipo quick clipboard'), 'preferred_trigger': Variant('s', preferred)}]], ''])
            shortcuts = result.get('shortcuts')
            if not shortcuts or not shortcuts.value:
                raise ValueError('The desktop did not bind a shortcut. Configure clipo --quick manually.')
            self.status.emit('Wayland desktop shortcut portal connected')
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass
        except Exception as error:
            self.status.emit(str(error) if isinstance(error, ValueError) else 'Desktop shortcut portal unavailable. Configure clipo --quick in desktop settings.')
        finally:
            if bus:
                if session:
                    try:
                        await asyncio.wait_for(bus.call(Message(destination='org.freedesktop.portal.Desktop', path=session, interface='org.freedesktop.portal.Session', member='Close')), 2)
                    except Exception:
                        pass
                bus.disconnect()
            self.task = self.loop = None

    def close(self):
        self.closing = True
        if self.loop and self.task:
            try:
                self.loop.call_soon_threadsafe(self.task.cancel)
            except RuntimeError:
                pass
        self.wait(5000)
