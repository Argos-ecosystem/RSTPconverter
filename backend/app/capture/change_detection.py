import cv2
import numpy as np

# frames are compared at this small size purely to keep the diff cheap
_DIFF_SIZE = (160, 90)


def _prep(frame: np.ndarray) -> np.ndarray:
    small = cv2.resize(frame, _DIFF_SIZE, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    return cv2.GaussianBlur(gray, (5, 5), 0)


def change_percent(previous: np.ndarray | None, current: np.ndarray) -> float:
    """Percentage (0-100) of the frame area that changed vs the previous frame."""
    if previous is None:
        return 100.0

    prev_gray = _prep(previous)
    curr_gray = _prep(current)

    diff = cv2.absdiff(prev_gray, curr_gray)
    # same per-pixel delta threshold Iris uses (PIXEL_CHANGE_THRESHOLD)
    _, thresh = cv2.threshold(diff, 24, 255, cv2.THRESH_BINARY)
    changed_pixels = int(np.count_nonzero(thresh))
    total_pixels = thresh.size
    return (changed_pixels / total_pixels) * 100.0
