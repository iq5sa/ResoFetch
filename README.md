# ResoFetch

ResoFetch reads the resolution, file size, format, codec, duration, and FPS of a
local video file or video stream URL. File size is reported as unknown for
network streams when the source does not expose a local file.

## Install on macOS

Install [pipx](https://pipx.pypa.io/stable/installation/) if it is not already
available, then run this from the project directory:

```sh
pipx install .
```

This installs the `ResoFetch` command in your user environment without changing
the system Python. If the command is not found, run `pipx ensurepath` and restart
your terminal.

## Use

```sh
ResoFetch /path/to/video.mp4
ResoFetch https://example.com/video.mp4
```

Capture exactly five images from evenly spaced time positions in a URL or local
video. The tool samples the midpoint of each fifth of the video's duration for
consistent coverage without random seeks. Each run creates a separate `task-*`
folder under `captures/` and prints the five saved image paths. Progress is
displayed as each frame is extracted and saved; images are written one by one,
so completed images are available before the run finishes.
Videos with fewer than five frames may produce repeated frame selections to
maintain the requested image count:

```sh
ResoFetchCapture https://example.com/video.mp4
ResoFetchCapture /path/to/video.mp4 --output-dir ~/Pictures/video-captures
```

Capture positions are derived from the video's duration, estimated from its
frame count and FPS metadata. Network URLs are read sequentially until each
selected time rather than seeking to remote offsets; local files seek directly
to each selected time. Sources without usable duration metadata return an
error.

Format is inferred from the source filename or URL extension. Duration and FPS
are derived from the video metadata exposed by OpenCV. Some containers or live
streams may not provide these values; unavailable values are shown as `Unknown`.

To update after changing or pulling the project:

```sh
pipx install --force .
```

To uninstall:

```sh
pipx uninstall resofetch
```
