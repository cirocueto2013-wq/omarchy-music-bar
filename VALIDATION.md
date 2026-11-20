# Validation · 2.0.1

Checked on Omarchy 4.5.0 / Qt 6.12, 20 November 2026:

- Omarchy manifest validation passed.
- QML syntax check passed; the real panel loaded with the native kit and no QML errors in its test log.
- Seven backend regression tests passed: plain text/thumbnail validation, stale search protection, visible errors, safe commands, recent history and stream origin checks.
- Public yt-dlp search, with --ignore-config and no credentials, returned results.
- Search through the installed backend returned 20 results without an error.
- Public audio extraction returned an audio-only format without cookies or account access.
- mpv successfully decoded three seconds of that public audio with null audio output, so this check made no sound.
- The installed panel was visually reviewed with real public results, native colors and controls.

These checks do not guarantee that every song or network will be accepted by YouTube. Age restricted, private, paid or verification-gated content is unavailable. The plugin reports extraction and playback failures instead of collecting credentials.

The volume command was also checked against the live paused mpv player at 37%, then restored to its prior level; playback remained paused.

The marketplace uses left/center/right for defaultSection; the manifest now uses center. The installer still positions the widget immediately after the weather.

Marketplace approval and other users' computers are separate from these local checks.
