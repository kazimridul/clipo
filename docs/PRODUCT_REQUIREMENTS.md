# Project: Advanced Linux Clipboard Manager
## Complete Product Requirements & Development Specification

**Project name:** ClipFlow (working name — make it configurable)

**Platform:** Linux (Ubuntu first, with support for other major Linux distributions)

**Application type:** Native desktop application with background clipboard monitoring, system tray integration and a modern graphical interface.

**Primary technologies:**
- Python 3.11+
- PySide6 / Qt 6
- SQLite
- Pillow
- OpenCV (optional, for advanced image processing)
- Tesseract OCR
- QR code generation library
- Linux clipboard integrations (Wayland and X11)
- FFmpeg (optional, for future media support)

---

# 1. Project Objective

Develop a powerful, modern and feature-rich clipboard manager for Linux operating systems.

The application should provide all the essential and advanced features available in CopyQ, while introducing additional productivity features that make clipboard management easier, faster and more intelligent.

The application must:

1. Monitor clipboard activity in the background.
2. Automatically store copied text, images, URLs, files and supported clipboard formats.
3. Maintain searchable clipboard history.
4. Allow users to organize, edit, pin, categorize and restore clipboard items.
5. Generate QR codes from copied text and URLs for easy phone sharing.
6. Support OCR to extract text from copied images.
7. Provide a modern desktop interface.
8. Support keyboard shortcuts and quick-access popup windows.
9. Protect sensitive clipboard information.
10. Work reliably on Ubuntu and other Linux distributions.

The application should feel like a polished commercial desktop product, not a basic Python utility.

# 2. Technology and Architecture

Use a modular architecture with clear separation between UI, clipboard monitoring, storage, business logic and operating-system integration.

### Recommended stack

| Component | Technology |
|---|---|
| Programming language | Python 3.11+ |
| Desktop framework | PySide6 |
| UI rendering | Qt Widgets / Qt Quick where appropriate |
| Database | SQLite |
| Database access | SQLAlchemy or a lightweight repository layer |
| Image processing | Pillow |
| OCR | Tesseract |
| QR generation | qrcode |
| Clipboard monitoring | QClipboard + platform-specific adapters |
| Keyboard shortcuts | QHotkey or suitable Linux integration |
| Configuration | JSON / QSettings |
| Logging | Python logging |
| Packaging | Debian package (.deb), AppImage |
| Testing | pytest + pytest-qt |

### Architecture

Organize the project into these modules:

- `application/` — application lifecycle and initialization.
- `core/` — application services and business logic.
- `clipboard/` — clipboard monitoring and platform adapters.
- `storage/` — SQLite database and repositories.
- `models/` — clipboard item, category, tag and settings models.
- `services/` — QR, OCR, search, export and synchronization.
- `ui/` — desktop interface and reusable components.
- `system/` — system tray, global shortcuts and startup integration.
- `security/` — sensitive content detection and privacy controls.
- `config/` — configuration management.
- `tests/` — unit, integration and UI tests.
- `resources/` — icons, themes, fonts and other assets.

Use dependency injection where practical. Avoid putting database, clipboard or business logic directly inside UI components.

# 3. Clipboard Monitoring Engine

This is the most important part of the application.

Build a reliable background clipboard monitoring engine.

### Supported content types

- Plain text
- Rich text / HTML
- Images
- URLs
- File paths
- Copied files
- Supported MIME types
- Other supported clipboard formats

### Requirements

1. Detect clipboard changes automatically.
2. Capture clipboard content without requiring users to open the application.
3. Avoid saving duplicate consecutive clipboard items.
4. Store timestamps for each clipboard item.
5. Maintain clipboard source information when available.
6. Support configurable history limits.
7. Allow users to pause and resume clipboard monitoring.
8. Allow users to exclude specific applications.
9. Support large clipboard content efficiently.
10. Handle clipboard access errors gracefully.

### Linux compatibility

Support both:

- X11
- Wayland

Implement separate platform adapters where necessary.

Important: Do not assume that QClipboard alone provides reliable background clipboard monitoring on every Wayland desktop. Evaluate the available compositor and desktop integration mechanisms, including clipboard history protocols, portals and supported desktop-specific APIs.

Clearly communicate when the current desktop environment restricts background clipboard access.

The application must never silently pretend that clipboard monitoring is working when the operating system blocks it.

# 4. Clipboard History Management

Build a powerful history management system.

### Features

- Store unlimited history when configured.
- Configure maximum history items.
- Configure automatic cleanup.
- Sort by newest, oldest and frequently used.
- Search clipboard history.
- Filter by content type.
- Display copied time.
- Preview clipboard content.
- Restore previously copied items.
- Edit stored text.
- Delete individual items.
- Delete multiple selected items.
- Clear entire history.
- Undo accidental deletion where practical.
- Detect duplicate clipboard entries.
- Pin important items.
- Mark items as favorites.

### Clipboard item actions

Every item should support:

- Copy
- Paste / restore
- Edit
- Pin / unpin
- Favorite / unfavorite
- Generate QR code
- Share
- Export
- Delete
- View details

# 5. Modern UI/UX Design

The UI/UX is a major priority.

Do not create an outdated-looking desktop application.

Build a clean, modern, minimal and professional interface inspired by modern productivity applications.

### Main application window

Use a three-part layout.

**Left sidebar**

- All Items
- Recent
- Favorites
- Pinned
- Text
- Images
- Links
- Files
- Code Snippets
- QR History
- Custom Collections
- Settings

**Center panel**

Display clipboard history in a clean list or grid.

Each item should show:

- Content preview
- Content type icon
- Timestamp
- Favorite indicator
- Pinned indicator
- Context menu

**Right preview panel**

When an item is selected, display:

- Full clipboard content
- Image preview where applicable
- Original creation time
- Content type
- Character count or file size
- Available actions

### UI requirements

- Modern light theme.
- Modern dark theme.
- System theme detection.
- Smooth animations.
- Rounded cards and panels.
- Consistent spacing.
- Modern typography.
- Professional iconography.
- Subtle hover effects.
- Keyboard navigation.
- Resizable panels.
- Responsive window layouts.
- Native-feeling Linux integration.

Avoid excessive gradients, unnecessary animations and oversized components.

### Quick Clipboard Popup

Create a separate compact popup window.

This should be accessible using a configurable global keyboard shortcut.

Default suggested shortcut:

`Ctrl + Shift + V`

The popup should:

1. Appear near the mouse cursor or screen center.
2. Display recent clipboard items.
3. Provide instant search.
4. Allow keyboard navigation.
5. Restore a selected clipboard item.
6. Close automatically after selection.
7. Support image and text previews.

The popup should be extremely fast and lightweight.

# 6. Advanced QR Code Generator and Sharing

This is a key feature that should distinguish the application from CopyQ.

Users should be able to generate a QR code from any supported text-based clipboard item.

### QR code functionality

- Generate QR from plain text.
- Generate QR from URLs.
- Generate QR from email addresses.
- Generate QR from Wi-Fi configuration text.
- Generate QR from code snippets.
- Generate QR from selected text.
- Generate QR from manually entered text.

### QR preview window

When the user clicks Generate QR:

Open a modern modal window containing:

- QR code preview.
- Original text.
- QR error correction level.
- QR image size.
- Foreground color.
- Background color.
- Custom QR styling where supported.

### Actions

- Copy QR image to clipboard.
- Save QR as PNG.
- Save QR as SVG.
- Print QR.
- Regenerate QR.
- Copy original text.
- Share using another supported application.

### Phone sharing

The user should be able to scan the QR code using a phone camera and retrieve the original text.

Important requirements:

- Handle QR payload size limitations.
- Warn users when the text is too large for practical QR scanning.
- Provide options to shorten or split large content.
- Never silently truncate text.
- Allow users to generate a QR from a URL pointing to an explicitly configured sharing service for large content.

Do not assume QR generation automatically provides internet-based sharing. Local QR sharing should work without an internet connection.

# 7. OCR – Extract Text from Images

Implement an OCR feature using Tesseract.

When a user copies an image, provide an option:

**Extract Text from Image**

Features:

- OCR copied images.
- Extract text from screenshots.
- Support multiple languages where installed.
- Display extracted text.
- Copy extracted text to clipboard.
- Generate QR code from extracted text.
- Save extracted text as a separate clipboard item.
- Search images using OCR-extracted text.

Allow OCR to run manually by default, with an optional automatic OCR setting.

# 8. Smart Clipboard and Content Recognition

Implement an intelligent content recognition system.

Automatically identify clipboard content types.

Examples:

- URL
- Email address
- Phone number
- IP address
- JSON
- XML
- HTML
- SQL query
- Python code
- JavaScript code
- Shell commands
- Markdown
- UUID
- Credit card-like numbers

Display an appropriate content type and relevant actions.

### Smart actions

For URLs:
- Open URL.
- Generate QR.
- Copy URL.

For email addresses:
- Copy.
- Create email.
- Generate QR.

For code:
- Syntax-highlighted preview.
- Copy code.
- Format code where a supported formatter is available.
- Save as a snippet.

For JSON:
- Pretty-print.
- Minify.
- Validate JSON.
- Copy formatted JSON.

For SQL:
- Syntax-highlighted preview.
- Copy query.
- Format query using an available formatter.

Do not automatically execute copied commands, SQL or scripts.

# 9. Code Snippet Manager

Create a dedicated section for developers.

Features:

- Save code snippets.
- Assign programming language.
- Add titles.
- Add descriptions.
- Add tags.
- Search snippets.
- Pin frequently used snippets.
- Syntax highlighting.
- Edit snippets.
- Copy snippets.
- Export snippets.

Support common languages:

- Python
- Java
- JavaScript
- TypeScript
- C
- C++
- SQL
- Bash
- HTML
- CSS
- JSON
- YAML
- PHP
- Go
- Rust

# 10. Collections, Categories and Tags

Allow users to organize clipboard items.

Features:

- Create custom collections.
- Rename collections.
- Delete collections.
- Assign multiple tags.
- Move items between collections.
- Assign colors to categories.
- Filter items by category.
- Search by tags.
- Pin collections.

Example collections:

- Work
- Programming
- SQL Queries
- Personal
- URLs
- Emails
- Frequently Used

An item may belong to multiple collections or have multiple tags.

# 11. Advanced Search

Build a powerful search engine for clipboard history.

Support:

- Full-text search.
- Search by content type.
- Search by date.
- Search by category.
- Search by tags.
- Search favorites.
- Search pinned items.
- Search OCR text.
- Search code snippets.

Add filters:

- Today
- Yesterday
- Last 7 days
- Last 30 days
- Custom date range

Search should be fast even with thousands of clipboard records.

Consider SQLite FTS5 for full-text indexing.

# 12. Image Clipboard Management

Build a complete image clipboard experience.

Features:

- Image thumbnails.
- Full-size preview.
- Zoom in/out.
- Copy image.
- Save image.
- Export image.
- Delete image.
- Generate QR when applicable to extracted text.
- OCR.
- Image metadata.
- Image dimensions.
- File size.
- Duplicate image detection.

Store image files separately from SQLite and maintain references in the database.

Use content hashes to detect duplicate images.

# 13. Privacy and Security

Clipboard content can contain highly sensitive information.

Privacy must be a first-class feature.

### Sensitive content detection

Provide configurable detection for:

- Password-like content.
- API keys.
- Access tokens.
- Private keys.
- Authentication headers.
- Sensitive credential patterns.

Allow users to:

- Exclude applications.
- Exclude specific patterns.
- Pause monitoring.
- Enable private mode.
- Delete sensitive clipboard entries automatically.
- Set automatic history expiration.
- Disable clipboard persistence.
- Clear history securely where technically possible.

### Private mode

When enabled:

- Stop recording new clipboard items.
- Do not save temporary copied information.
- Resume monitoring only when explicitly disabled.

Provide a visible status indicator when private mode is active.

### Storage security

- Keep database files in the user's application data directory.
- Set appropriate file permissions.
- Avoid storing secrets in logs.
- Offer optional database encryption.
- Never upload clipboard contents without explicit user permission.

# 14. Import and Export

Support exporting and importing clipboard history.

Supported export formats:

- JSON
- TXT
- CSV
- HTML

For images, support exporting the original image files.

Features:

- Export selected items.
- Export complete history.
- Export individual collections.
- Import previously exported backups.
- Restore history from backup.
- Schedule automatic backups.

Ensure imports validate data and do not execute imported content.

# 15. System Tray and Desktop Integration

The application should run in the background.

### System tray menu

Include:

- Open Clipboard Manager
- Quick Clipboard
- Pause Monitoring
- Resume Monitoring
- Private Mode
- Generate QR
- Settings
- Exit

### Startup

- Start on system login.
- Minimize to tray.
- Continue clipboard monitoring when the main window closes.
- Option to fully exit the application.

Support appropriate Linux desktop integration.

# 16. Keyboard Shortcuts

Provide configurable keyboard shortcuts.

Suggested defaults:

| Action | Shortcut |
|---|---|
| Open Quick Clipboard | Ctrl + Shift + V |
| Open Main Window | Configurable |
| Search History | Ctrl + F |
| Generate QR | Configurable |
| Copy Selected Item | Enter |
| Pin Item | Ctrl + P |
| Delete Item | Delete |
| Toggle Private Mode | Configurable |
| Pause Monitoring | Configurable |
| Close Popup | Escape |

Make shortcuts configurable from Settings.

Detect shortcut conflicts and handle unsupported global shortcut mechanisms gracefully.

# 17. Cross-Device Sharing – Future Module

Design the application so cross-device sharing can be added later.

Potential features:

- Share clipboard text between Linux and Android.
- Generate temporary sharing links.
- Generate QR codes for remote sharing.
- Optional local network sharing.
- Optional encrypted synchronization.
- Device management.
- Expiring shared content.

This module must be optional and disabled by default.

Never transmit clipboard content without explicit user consent.

# 18. Performance Requirements

The application must remain lightweight.

Requirements:

- Clipboard monitoring should use minimal CPU.
- Database operations should not block the UI.
- Image processing and OCR must run in background workers.
- Use asynchronous/background task execution where appropriate.
- Load image previews lazily.
- Avoid loading the entire clipboard history into memory.
- Use pagination or virtualized lists.
- Index searchable database columns.
- Avoid duplicate file storage.
- Handle large clipboard items gracefully.

The application should remain responsive with at least 50,000 clipboard records in a realistic test environment.

# 19. Database Design

Use SQLite.

Create tables for:

### clipboard_items

- id
- content_type
- content_text
- content_html
- image_path
- file_metadata
- content_hash
- created_at
- updated_at
- source_application
- is_favorite
- is_pinned
- is_sensitive
- ocr_text

### categories

- id
- name
- color
- created_at

### tags

- id
- name

### item_categories

- item_id
- category_id

### item_tags

- item_id
- tag_id

### settings

- key
- value

### qr_history

- id
- clipboard_item_id
- qr_image_path
- created_at

Add appropriate indexes, foreign keys and migration support.

Do not store image binary data directly in the main clipboard history table unless there is a compelling technical reason.

# 20. Settings Panel

Create a comprehensive settings interface.

Organize it into:

1. General
2. Appearance
3. Clipboard Monitoring
4. History Management
5. Keyboard Shortcuts
6. QR Code
7. OCR
8. Privacy and Security
9. Backup and Restore
10. System Integration
11. Advanced

Users should be able to configure all important application behaviors without editing configuration files manually.

# 21. Packaging and Installation

The application must be distributable as a Linux desktop application.

Primary target:

Ubuntu `.deb` package.

Additional targets:

- AppImage
- Other Debian-based distributions
- Fedora-compatible packaging in a future release

Requirements:

- Desktop launcher.
- Application icon.
- Application metadata.
- Startup integration.
- System tray integration.
- Uninstallation support.
- Configuration and data preservation options during upgrades.
- Clean installation and removal.

The application must not require users to launch it manually through Python commands.

# 22. Testing Requirements

Write tests throughout development.

Test the following:

- Clipboard monitoring.
- Text capture.
- Image capture.
- Duplicate detection.
- Clipboard restoration.
- Database persistence.
- QR generation.
- QR decoding and text integrity.
- OCR extraction.
- Search.
- Category management.
- Privacy mode.
- Application exclusions.
- Keyboard shortcuts.
- Background execution.
- X11 compatibility.
- Wayland compatibility.
- Packaging and installation.

Provide a manual testing checklist for Ubuntu.

# 23. Development Roadmap

Develop the project incrementally.

**Phase 1 – Foundation**
- Project architecture.
- PySide6 application.
- SQLite database.
- Clipboard monitoring.
- Basic text history.
- Copy and restore.

**Phase 2 – Core Clipboard Features**
- Image support.
- History management.
- Search.
- Favorites.
- Pinning.
- Categories and tags.

**Phase 3 – Modern UI/UX**
- Main application interface.
- Quick clipboard popup.
- System tray.
- Dark and light themes.
- Keyboard shortcuts.

**Phase 4 – Advanced Features**
- QR generator.
- QR history.
- OCR.
- Smart content detection.
- Code snippet manager.
- JSON formatting.

**Phase 5 – Privacy and Performance**
- Sensitive content detection.
- Private mode.
- Application exclusions.
- Background workers.
- Database optimization.

**Phase 6 – Distribution**
- Ubuntu `.deb`.
- AppImage.
- Installation testing.
- Upgrade and uninstall testing.
- Documentation.

**Phase 7 – Future Enhancements**
- Cross-device synchronization.
- Local network sharing.
- Android integration.
- Advanced automation.

# 24. Important Development Instructions

Follow these instructions throughout development:

1. Build a production-quality application, not a prototype.
2. Use modular and maintainable code.
3. Keep UI and backend logic separate.
4. Do not hardcode configuration values.
5. Do not put all functionality into a single Python file.
6. Use proper error handling and structured logging.
7. Use type hints and meaningful documentation.
8. Implement unit tests for core services.
9. Never block the UI thread with heavy operations.
10. Use reusable UI components.
11. Ensure accessibility and keyboard navigation.
12. Keep the application compatible with Linux desktop environments.
13. Test actual clipboard behavior on X11 and Wayland.
14. Document platform-specific limitations.
15. Avoid implementing fake or non-functional buttons.
16. Every visible feature must have working functionality.
17. Do not mark a development phase complete until its acceptance criteria pass.
18. Update README documentation as features are implemented.

## Final Expected Product

Deliver a fully functional Linux clipboard manager with:

- CopyQ-level clipboard management capabilities.
- A modern and polished desktop interface.
- Background clipboard monitoring.
- Text and image history.
- Advanced search and organization.
- QR-code generation and phone sharing.
- OCR.
- Developer-friendly snippet management.
- Privacy and security controls.
- System tray integration.
- Global keyboard shortcuts.
- Ubuntu `.deb` installation package.

The final application should feel like a modern productivity tool that users can rely on every day.

Start by analyzing the architecture, creating the project structure and implementing Phase 1. Do not attempt to implement every feature in a single step. Build, test and document each phase before moving to the next one.