from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MediaPart:
    """A media input (image or video) to include in the prompt.

    For inline data (``data`` or ``file_path``), small files are sent directly
    in the request body.  Files larger than ~20 MB are automatically uploaded
    via the Gemini File API (supports up to 2 GB).

    Usage::

        # Image from bytes
        MediaPart(data=image_bytes, mime_type="image/png")

        # Image from local file
        MediaPart(file_path="photo.jpg", mime_type="image/jpeg")

        # Video from local file
        MediaPart(file_path="/tmp/clip.mp4", mime_type="video/mp4")

        # Large video (>20 MB) — automatically uploaded via File API
        MediaPart(file_path="/tmp/long_video.mp4", mime_type="video/mp4")
    """

    data: bytes | None = None
    mime_type: str = "image/jpeg"
    file_path: str | None = None
