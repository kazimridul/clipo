# Vault and sharing security

## Encrypted history

The optional vault uses SQLCipher's encrypted/authenticated SQLite storage and
its password KDF. The driver must expose `cipher_version`; no silent fallback to
ordinary SQLite is allowed. SQLite temporary data stays in memory, and SQLCipher
memory security is enabled. Database, WAL and ordinary private-file permissions
remain restricted to the current user.

Images, thumbnails, and generated QR files are independently encrypted with
AES-256-GCM. A 256-bit key is derived with scrypt (N=32768, r=8, p=1) and a random
16-byte vault salt. Each write uses a new 12-byte nonce; relative file paths are
authenticated. Missing salt metadata and tampered files fail explicitly. Do not
copy only the encrypted database: use portable backups or preserve the whole vault.

Migration copies base tables and managed blobs into a staging vault, verifies
counts, closes it, then atomically publishes the directory. Only after settings
are saved can the user's selected removal of original unencrypted history run.
Failed migration leaves the source in place. Existing external exports/backups
remain outside this operation. Removing files is not forensic secure erasure.

Lock disables capture, closes the database, removes cached UI previews/thumbnails,
releases key/passphrase references, clears the app-owned clipboard, and rejects
open content dialogs. Late OCR/format/page callbacks are ignored. Python memory
cannot promise forensic zeroization or protection against a compromised account.
Passphrases are not logged or saved in settings and cannot be recovered.

Automatic backups of an encrypted vault use authenticated `.clipo` containers:
independent salt/nonce, scrypt, AES-256-GCM, and authenticated headers. They are
assembled in memory, so no new plaintext backup file is written. Manual exports
may explicitly be plaintext. Portable backups include decrypted content inside
that encrypted container and can restore into a different store using the password.

Session-only history is independent, with temporary image files removed when its
repository closes. Locking a session-only repository discards that temporary session;
persistent encrypted data is not removed. Do not downgrade to an older Clipo version
that does not understand encrypted settings.

## One-time phone sharing

No network server starts at launch or while monitoring. The user selects an item,
opens Share, chooses a private IPv4 interface and lifetime, and presses Create link.
That creates a temporary TLS 1.2+ server bound to that specific interface, a random
256-bit bearer token, and a one-use transfer. Expiration, revoke, dialog close,
private mode, lock, and app exit terminate the transfer and release payload data.
Public, multicast, and wildcard binding addresses are rejected.

The recipient first sees a confirmation page; GET/link previews do not reveal or
consume content. An authenticated POST retrieves it once. Content is not cached,
HTML text is escaped, and server access logs are disabled. No content is written
to disk, uploaded to a cloud, or automatically synchronized.

The local certificate is self-signed and changes for each transfer. The phone
browser will show a certificate prompt. **Compare its SHA-256 fingerprint with
Clipo before accepting.** Anyone who obtains the bearer link may receive that
transfer; revoke it if exposed. Self-signed local sharing is not a public Internet
sharing service and does not establish persistent device trust or an Android app.

Tests pin the generated certificate on a loopback client and verify confirmation,
TLS, escaping, one-time behavior, binding restrictions, and cleanup. Physical phone
certificate UX and firewall/router behavior still need a manual test on your LAN.
