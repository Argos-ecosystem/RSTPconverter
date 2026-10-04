import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from app.capture.worker import CameraWorker


class PreviewTests(unittest.TestCase):
    def test_capture_continues_during_blocked_upload(self):
        worker = CameraWorker(1)
        started = threading.Event()
        release = threading.Event()
        captured = []
        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        camera = SimpleNamespace(enabled=True, rtsp_url='rtsp://test')
        config = SimpleNamespace(check_interval_seconds=30, max_interval_seconds=60,
                                 change_threshold_percent=1)
        db = MagicMock()
        db.query.return_value.get.return_value = camera
        db.query.return_value.first.return_value = config
        cap = MagicMock()
        cap.isOpened.return_value = True

        def read():
            if captured:
                self.assertTrue(started.wait(2))
            captured.append(1)
            if len(captured) == 5:
                worker._stop_event.set()
            return True, frame

        def send(*args):
            started.set()
            release.wait(3)

        cap.read.side_effect = read
        with patch('app.capture.worker.SessionLocal', return_value=db), \
             patch('app.capture.worker.cv2.VideoCapture', return_value=cap), \
             patch.object(worker, '_mark_frame_seen'), \
             patch.object(worker, '_set_status'), \
             patch.object(worker, '_update_preview') as preview, \
             patch.object(worker, '_send', side_effect=send) as upload:
            with ThreadPoolExecutor(max_workers=1) as pool:
                try:
                    worker._capture_loop(pool)
                    self.assertEqual(len(captured), 5)
                    self.assertFalse(release.is_set())
                    preview.assert_called()
                    upload.assert_called_once()
                    cap.release.assert_called_once()
                finally:
                    release.set()


if __name__ == '__main__':
    unittest.main()
