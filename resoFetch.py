import argparse
import math
import os
from dataclasses import dataclass
from typing import Tuple, Union
from urllib.parse import urlsplit

import cv2


@dataclass(frozen=True)
class VideoDetails:
    width: int
    height: int
    file_size_bytes: Union[int, None]
    format: str
    codec: str
    duration_seconds: Union[float, None]
    fps: Union[float, None]


def _validate_video_source(video_source: str) -> None:
    if not isinstance(video_source, str) or not video_source.strip():
        raise ValueError("Video source must be a non-empty string.")

    source = video_source.strip()
    if os.path.isfile(source):
        return

    if source.startswith(("http://", "https://", "rtsp://", "rtmp://")):
        return

    raise ValueError(
        "Video source must be a valid file path or a supported URL "
        "(http, https, rtsp, rtmp)."
    )


def _format_name(video_source: str) -> str:
    path = urlsplit(video_source).path if "://" in video_source else video_source
    extension = os.path.splitext(path)[1].lstrip(".").upper()
    return extension or "Unknown"


def _codec_name(fourcc_value: float) -> str:
    fourcc = int(fourcc_value)
    if not fourcc:
        return "Unknown"

    code = bytes((fourcc >> (8 * index)) & 0xFF for index in range(4))
    codec = code.decode("ascii", errors="replace").strip("\x00 ")
    normalized = codec.lower()
    known_codecs = {
        "avc1": "H.264 / AVC",
        "avc3": "H.264 / AVC",
        "h264": "H.264 / AVC",
        "x264": "H.264 / AVC",
        "hev1": "H.265 / HEVC",
        "hvc1": "H.265 / HEVC",
        "hevc": "H.265 / HEVC",
        "av01": "AV1",
        "vp90": "VP9",
        "vp80": "VP8",
        "mp4v": "MPEG-4",
        "xvid": "Xvid",
        "mjpg": "Motion JPEG",
    }
    return known_codecs.get(normalized, codec or "Unknown")


def _read_video_details(video_source: str) -> Union[VideoDetails, str]:
    try:
        _validate_video_source(video_source)
    except ValueError as exc:
        return str(exc)

    source = video_source.strip()
    cap = cv2.VideoCapture(source)
    try:
        if not cap.isOpened():
            return "Error: Could not open video stream."

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if width == 0 or height == 0:
            return "Error: Could not read video dimensions."

        fps_value = cap.get(cv2.CAP_PROP_FPS)
        frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT)
        fps = fps_value if math.isfinite(fps_value) and fps_value > 0 else None
        duration = (
            frame_count / fps
            if fps is not None
            and math.isfinite(frame_count)
            and frame_count > 0
            else None
        )
        file_size = os.path.getsize(source) if os.path.isfile(source) else None

        return VideoDetails(
            width=width,
            height=height,
            file_size_bytes=file_size,
            format=_format_name(source),
            codec=_codec_name(cap.get(cv2.CAP_PROP_FOURCC)),
            duration_seconds=duration,
            fps=fps,
        )
    finally:
        cap.release()


def get_video_details(video_source: str) -> Union[VideoDetails, str]:
    """Return resolution and available container, codec, duration, and FPS metadata."""
    return _read_video_details(video_source)


def get_video_resolution(video_source: str) -> Union[str, Tuple[int, int]]:
    """Return the width and height of a video as a tuple, or an error string."""
    details = _read_video_details(video_source)
    if isinstance(details, str):
        return details
    return details.width, details.height


def _format_file_size(size_bytes: Union[int, None]) -> str:
    if size_bytes is None:
        return "Unknown (network source)"

    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1000 or unit == "TB":
            return f"{size:.2f} {unit}" if unit != "B" else f"{size_bytes} B"
        size /= 1000
    return f"{size_bytes} B"


def _format_duration(seconds: Union[float, None]) -> str:
    if seconds is None:
        return "Unknown"

    total_milliseconds = round(seconds * 1000)
    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{whole_seconds:02}.{milliseconds:03}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Get metadata for a local video file or network video stream."
    )
    parser.add_argument("source", help="Path to a video file or URL of a video stream")
    args = parser.parse_args()

    details = get_video_details(args.source)
    if isinstance(details, str):
        print(details)
        return

    print(f"Resolution: {details.width}×{details.height}")
    print(f"File size: {_format_file_size(details.file_size_bytes)}")
    print(f"Format: {details.format} (from source extension)")
    print(f"Codec: {details.codec}")
    print(f"Duration: {_format_duration(details.duration_seconds)}")
    fps = f"{details.fps:.2f} FPS" if details.fps is not None else "Unknown"
    print(f"FPS: {fps}")


if __name__ == "__main__":
    main()
