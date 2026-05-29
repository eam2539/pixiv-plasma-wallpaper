# Pixiv Wallpaper for KDE Plasma 6

Pixiv Wallpaper is a KDE Plasma 6 wallpaper plugin that downloads Pixiv illustrations and rotates them on your desktop.

## Usage

You can get the package in the [KDE Store](https://store.kde.org/p/2360473/)

1. Select `Pixiv Wallpaper` in the Plasma wallpaper settings.
2. Click `Login` and complete Pixiv OAuth in the browser.
3. Choose a source: daily recommendations, theme search, daily ranking, or following.
4. Configure fetch/rotate intervals (hour/minute/second), filters, and image positioning.
5. Optionally add local image files or folders, one path per line.
6. Choose the sort order: modified time (newest first), modified time (oldest first), or random non-repeating cycle.
7. Enable local images if you want local paths to be mixed into rotation.

## Right-Click Actions

- `Rotate Now`: switch to another available wallpaper.
- `Fetch Images Now`: fetch new Pixiv images immediately.
- `Choose Local Image`: opens the local Pixiv cache directory by default and lets you pick an image.
- `Open Current Image`: opens the currently displayed image in the default image viewer.
- `Open Pixiv Page`: opens the currently displayed image on the Pixiv website

## Tips

To rotate the wallpaper with a keyboard shortcut, open KDE System Settings → `Keyboard` → `Shortcut Key`, add a custom shell shortcut and paste:

```bash
/usr/bin/python3 ~/.local/share/plasma/wallpapers/org.pixiv.wallpaper/contents/code/pixiv_wallpaper.py rotate-now
```

## Requirements

- KDE Plasma 6.
- Python 3.10 or newer.
- PixivPy3.
- A browser for Pixiv OAuth login.

## Install

From the project directory:

```bash
kpackagetool6 --type Plasma/Wallpaper --install org.pixiv.wallpaper
```

If the plugin is already installed:

```bash
kpackagetool6 --type Plasma/Wallpaper --upgrade org.pixiv.wallpaper
```

Restart Plasma Shell after installation:

```bash
systemctl --user restart plasma-plasmashell.service
```

Then open Desktop and Wallpaper settings and select `Pixiv Wallpaper`.

## Uninstall

Remove the wallpaper package:

```bash
kpackagetool6 --type Plasma/Wallpaper --remove org.pixiv.wallpaper
```

The package cannot run code after `kpackagetool6` deletes the plugin directory, so cleanup is handled by the external timer runner. After removal, the next timer execution detects that the plugin no longer exists and removes the desktop URL handlers, systemd user units, MIME defaults, and runner file.

To clean up immediately instead of waiting for the next timer run, run this before removing the package:

```bash
/usr/bin/python3 ~/.local/share/plasma/wallpapers/org.pixiv.wallpaper/contents/code/pixiv_wallpaper.py cleanup
```

## Privacy

- Pixiv OAuth tokens are stored locally in Plasma configuration and helper cache files.
- Downloaded images are cached locally under `~/.cache/pixiv-plasma-wallpaper`.

## Troubleshooting

Check recent Plasma Shell logs:

```bash
journalctl --user -u plasma-plasmashell --since "10 minutes ago" --no-pager
```

If right-click actions or translations do not update after upgrading, restart Plasma Shell:

```bash
systemctl --user restart plasma-plasmashell.service
```

## License

GPL-3.0-or-later.

## Disclaimer

This project is not affiliated with Pixiv Inc. Use it with your own Pixiv account and follow Pixiv's terms of service.
