"""In-memory cache of the latest JPEG frame per camera, for the live preview
in the panel. Deliberately not persisted: it's just whatever the capture
thread last decoded, not meant to survive a restart."""
import threading

_lock = threading.Lock()
_frames: dict[int, bytes] = {}


def set_frame(camera_id: int, jpeg_bytes: bytes) -> None:
    with _lock:
        _frames[camera_id] = jpeg_bytes


def get_frame(camera_id: int) -> bytes | None:
    with _lock:
        return _frames.get(camera_id)


def clear_frame(camera_id: int) -> None:
    with _lock:
        _frames.pop(camera_id, None)
