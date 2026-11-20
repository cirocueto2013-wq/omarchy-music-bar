# Music Bar for Omarchy

A free, open source music panel for the Omarchy top bar. Search public YouTube music and play audio without a Google account, browser, extension or subscription.

Click the monochrome music icon beside the weather to open the native Omarchy panel. Search for an artist or song, click a result, and use previous, play/pause, next, stop and volume (0–100%). Volume is saved locally and does not change the system volume. The current search becomes the playback queue. Recent tracks stay on your computer.

This is an independent community plugin, not an official YouTube or Google product. It does not unlock paid, private, age restricted or otherwise unavailable content. YouTube may require verification for some content or connections; in that case the panel reports the failure and does not request credentials or bypass verification. Continued service availability is not guaranteed.

## Requirements

Omarchy with Quickshell plugins, Python 3, mpv and an up-to-date yt-dlp. Install the dependencies from your normal Arch repositories:

```sh
omarchy pkg add mpv yt-dlp
```

No pip packages or privileged service is required.

## Install from a downloaded archive

Extract the archive, open a terminal inside its directory and run:

```sh
python3 install.py
```

The installer backs up `~/.config/omarchy/shell.json`, preserves other widgets, and adds this plugin immediately after the weather. Code lives under `~/.config/omarchy/plugins/ciro.youtube-music/`. It replaces only the older version of this same plugin ID, and retires the earlier project's own Chrome native-messaging registration if present; it does not change browser policy or other extensions.

The public Git repository can also be installed using `omarchy plugin add https://github.com/cirocueto2013-wq/omarchy-music-bar --enable`. Dependencies must be installed first. The manifest's default placement is beside the clock; use the installer if you want the precise position after the weather.

## Remove

```sh
python3 ~/.config/omarchy/plugins/ciro.youtube-music/install.py --remove
```

Removal stops the local player and moves this plugin into `~/.local/state/omarchy/plugin-backups/`. Other modules are preserved. Search/playback history is retained at `~/.local/state/omarchy/music-public/`; you may remove that directory separately if you no longer want it.

## Network and local data

There are no background catalogue refreshes. A search contacts YouTube when you submit it; selecting a track resolves its public audio stream and plays it through mpv. Playback naturally continues using the network while listening. Thumbnails load from YouTube/Google image hosts. No cookies, login tokens, browser profiles, private playlists or account data are read. No telemetry or own remote server is used.

A single local Python process serves all monitors through a user-only Unix socket. mpv starts only when you select audio. The process remains available after closing the panel; closing the panel does not interrupt music. To stop playback press Stop; to stop the service use the removal command. State and up to 40 recent tracks are stored locally. Audio is streamed and not saved as a music download, apart from normal transient player buffering.

## Troubleshooting

If a song fails, try another public song and update yt-dlp with `omarchy pkg add yt-dlp`. Connection restrictions or a YouTube verification requirement are shown inside the panel. If a dependency is missing, the panel names it. The plugin never asks you to export cookies or sign in.

## Development

```sh
python3 checks/test_backend.py
omarchy plugin validate .
```

Backend tests cover untrusted metadata, stale search responses, visible failures, command validation, allowed stream origins and local recent history. See `VALIDATION.md` for the release's manual checks.

References: [yt-dlp](https://github.com/yt-dlp/yt-dlp), [mpv JSON IPC](https://mpv.io/manual/stable/#json-ipc), [Omarchy plugins](https://omarchy.org/manual/shell-plugins/).

Licensed under MIT. Dependencies retain their own licenses. The monochrome YouTube Music mark identifies the service; YouTube and YouTube Music are trademarks of their respective owner, and no affiliation is implied.
