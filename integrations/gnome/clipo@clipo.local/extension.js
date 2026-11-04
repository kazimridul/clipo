import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const SERVICE = 'com.clipo.Clipboard';
const PATH = '/com/clipo/Clipboard';
const IFACE = 'com.clipo.Clipboard1';

export default class ClipoBridge extends Extension {
    enable() {
        this._active = true;
        this._serial = 0;
        this._cancellable = new Gio.Cancellable();
        this._clipboard = St.Clipboard.get_default();
        this._selection = global.display.get_selection();
        this._handler = this._selection.connect('owner-changed', (_selection, type) => {
            if (type === Meta.SelectionType.SELECTION_CLIPBOARD)
                this._changed();
        });
        // Heartbeats report availability only. Never read the preexisting clipboard.
        this._heartbeat = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 10, () => {
            this._call('Status', new GLib.Variant('(s)', ['']), () => {});
            return GLib.SOURCE_CONTINUE;
        });
        this._call('Status', new GLib.Variant('(s)', ['']), () => {});
    }

    _call(method, parameters, callback) {
        if (!this._active)
            return;
        Gio.DBus.session.call(SERVICE, PATH, IFACE, method, parameters, null,
            Gio.DBusCallFlags.NO_AUTO_START, 2000, this._cancellable, (connection, result) => {
                if (!this._active)
                    return;
                try {
                    callback(connection.call_finish(result).deep_unpack()[0]);
                } catch (_error) {
                    // Clipo is closed, locked, or unavailable. No clipboard content is logged.
                }
            });
    }

    _changed() {
        const serial = ++this._serial;
        const source = global.display.focus_window?.get_wm_class() ?? '';
        this._call('Status', new GLib.Variant('(s)', [source]), response => {
            if (serial !== this._serial)
                return;
            const status = JSON.parse(response);
            if (!status.enabled)
                return;
            const types = this._clipboard.get_mimetypes(St.ClipboardType.CLIPBOARD) ?? [];
            if (types.some(type => ['application/x-keepassxc', 'x-kde-passwordManagerHint', 'application/x-qt-avoid-clipboard-history'].includes(type)))
                return;
            const send = payload => {
                if (this._active && serial === this._serial)
                    this._call('Ingest', new GLib.Variant('(s)', [JSON.stringify({...payload, source})]), () => {});
            };
            const content = (mime, limit, callback) => {
                this._clipboard.get_content(St.ClipboardType.CLIPBOARD, mime, (_clipboard, bytes) => {
                    if (!this._active || serial !== this._serial || !bytes)
                        return;
                    if (bytes.get_size() > limit) {
                        this._call('ReportError', new GLib.Variant('(s)', ['size-limit']), () => {});
                        return;
                    }
                    callback(bytes.get_data());
                });
            };
            if (types.includes('text/uri-list')) {
                content('text/uri-list', status.max_text_bytes, bytes => send({kind: 'files', text: new TextDecoder().decode(bytes)}));
            } else if (types.includes('image/png')) {
                content('image/png', status.max_image_bytes, bytes => send({kind: 'image', data: GLib.base64_encode(bytes)}));
            } else {
                this._clipboard.get_text(St.ClipboardType.CLIPBOARD, (_clipboard, text) => {
                    if (!this._active || serial !== this._serial || !text)
                        return;
                    if (new TextEncoder().encode(text).length > status.max_text_bytes) {
                        this._call('ReportError', new GLib.Variant('(s)', ['size-limit']), () => {});
                        return;
                    }
                    if (types.includes('text/html'))
                        content('text/html', status.max_text_bytes, bytes => send({kind: 'text', text, html: new TextDecoder().decode(bytes)}));
                    else
                        send({kind: 'text', text});
                });
            }
        });
    }

    disable() {
        this._active = false;
        this._serial++;
        this._cancellable?.cancel();
        if (this._handler)
            this._selection.disconnect(this._handler);
        if (this._heartbeat)
            GLib.source_remove(this._heartbeat);
        this._handler = 0;
        this._heartbeat = 0;
        this._selection = null;
        this._clipboard = null;
    }
}
