import argparse
import math
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Union

import cv2


def capture_random_frames(
    video_source: str,
    output_root: Union[str, Path] = "captures",
    progress_callback: Union[Callable[[str], None], None] = None,
) -> list[Path]:
    """Capture five evenly spaced frames, saving each immediately to its task folder."""
    if not isinstance(video_source, str) or not video_source.strip():
        raise ValueError("Video source must be a non-empty URL or file path.")

    source = video_source.strip()
    is_local_file = os.path.isfile(source)
    if not is_local_file and not source.startswith(
        ("http://", "https://", "rtsp://", "rtmp://")
    ):
        raise ValueError(
            "Video source must be a valid file path or a supported URL "
            "(http, https, rtsp, rtmp)."
        )

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        capture.release()
        raise RuntimeError("Could not open video source.")

    image_paths = []
    try:
        root = Path(output_root).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        task_folder = Path(tempfile.mkdtemp(prefix="task-", dir=str(root)))
        if progress_callback is not None:
            progress_callback(f"Saving images to {task_folder.resolve()}")

        fps = capture.get(cv2.CAP_PROP_FPS)
        frame_count = capture.get(cv2.CAP_PROP_FRAME_COUNT)
        if (
            not math.isfinite(fps)
            or fps <= 0
            or not math.isfinite(frame_count)
            or frame_count <= 0
        ):
            raise RuntimeError(
                "Could not determine video duration, so evenly spaced capture "
                "positions are unavailable for this source."
            )

        duration = frame_count / fps
        latest_time = max(0.0, duration - (1.0 / fps))
        segment_duration = duration / 5
        target_times = [
            min((image_number + 0.5) * segment_duration, latest_time)
            for image_number in range(5)
        ]

        if is_local_file:
            for image_number, target_time in enumerate(target_times, start=1):
                if progress_callback is not None:
                    progress_callback(
                        f"Extracting image {image_number}/5 "
                        f"(video time {target_time:.2f}s)..."
                    )
                if not capture.set(cv2.CAP_PROP_POS_MSEC, target_time * 1000):
                    raise RuntimeError(
                        f"Could not seek to video time {target_time:.2f}s."
                    )
                success, frame = capture.read()
                if not success or frame is None:
                    raise RuntimeError(
                        f"Could not read video at {target_time:.2f}s."
                    )
                _save_frame(
                    frame,
                    image_number,
                    task_folder,
                    image_paths,
                    progress_callback,
                    target_time,
                )
        else:
            next_image = 0
            frame_index = 0
            last_time = -1.0
            while next_image < len(target_times):
                success, frame = capture.read()
                if not success or frame is None:
                    raise RuntimeError(
                        f"Video ended before reaching the requested time "
                        f"{target_times[next_image]:.2f}s."
                    )
                reported_time = capture.get(cv2.CAP_PROP_POS_MSEC) / 1000
                fallback_time = frame_index / fps
                if (
                    math.isfinite(reported_time)
                    and reported_time >= 0
                    and reported_time > last_time
                ):
                    current_time = reported_time
                else:
                    current_time = fallback_time
                frame_index += 1
                last_time = current_time
                while (
                    next_image < len(target_times)
                    and current_time >= target_times[next_image]
                ):
                    image_number = next_image + 1
                    target_time = target_times[next_image]
                    if progress_callback is not None:
                        progress_callback(
                            f"Extracting image {image_number}/5 "
                            f"(video time {target_time:.2f}s)..."
                        )
                    _save_frame(
                        frame,
                        image_number,
                        task_folder,
                        image_paths,
                        progress_callback,
                        target_time,
                    )
                    next_image += 1
    finally:
        capture.release()

    return image_paths


def _save_frame(
    frame: Any,
    image_number: int,
    task_folder: Path,
    image_paths: list[Path],
    progress_callback: Union[Callable[[str], None], None],
    target_time: float,
) -> None:
    image_path = task_folder / f"capture_{image_number:02}.jpg"
    if not cv2.imwrite(str(image_path), frame):
        raise RuntimeError(f"Could not save captured image to {image_path}.")
    image_paths.append(image_path)
    if progress_callback is not None:
        progress_callback(
            f"Progress: {image_number}/5 images saved "
            f"({image_number * 20}%) at {target_time:.2f}s."
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture five evenly spaced images from a video."
    )
    parser.add_argument("source", help="Video URL or path to a local video file")
    parser.add_argument(
        "--output-dir",
        default="captures",
        help="Parent folder for unique per-run capture folders (default: captures)",
    )
    args = parser.parse_args()

    try:
        image_paths = capture_random_frames(
            args.source,
            output_root=args.output_dir,
            progress_callback=lambda message: print(
                message, file=sys.stderr, flush=True
            ),
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Capture cancelled. Any images already saved are still available "
            "in the task folder shown above.",
            file=sys.stderr,
            flush=True,
        )
        return 130

    for image_path in image_paths:
        print(image_path.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
