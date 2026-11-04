import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
const XML = '<node><interface name="com.clipo.TestProducer"><method name="SetText"><arg type="s" direction="in"/></method><method name="SetContent"><arg type="s" direction="in"/><arg type="s" direction="in"/></method></interface></node>';
export default class Producer extends Extension {
    enable() {
        this._object = Gio.DBusExportedObject.wrapJSObject(XML, {
            SetText: text => St.Clipboard.get_default().set_text(St.ClipboardType.CLIPBOARD, text),
            SetContent: (mime, encoded) => St.Clipboard.get_default().set_content(St.ClipboardType.CLIPBOARD, mime, new GLib.Bytes(GLib.base64_decode(encoded))),
        });
        this._object.export(Gio.DBus.session, '/com/clipo/TestProducer');
        this._name = Gio.bus_own_name_on_connection(Gio.DBus.session, 'com.clipo.TestProducer', Gio.BusNameOwnerFlags.NONE, null, null);
    }
    disable() {
        this._object.unexport();
        Gio.bus_unown_name(this._name);
    }
}
