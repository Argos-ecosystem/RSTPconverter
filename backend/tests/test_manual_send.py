import unittest
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from app.capture.sender import send_frame
from app.capture.worker import CameraWorker

class ManualSendTests(unittest.TestCase):
    def test_duplicate_and_cancelled_requests(self):
        worker = CameraWorker(1)
        first = worker.request_send()
        with self.assertRaises(ValueError):
            worker.request_send()
        first.cancel()
        self.assertIsNot(first, worker.request_send())

    def test_api_response_recorded_and_key_redacted(self):
        config = SimpleNamespace(endpoint_url='https://example.test/ingest', request_timeout_seconds=2)
        camera = SimpleNamespace(external_camera_id='CAM1', api_key='secret-key', name='Test')
        for code in (200, 400):
            with self.subTest(code=code), patch('app.capture.sender.httpx.post', return_value=httpx.Response(code, text='received secret-key')) as post:
                result = send_frame(config, camera, b'jpeg', 'manual')
                self.assertEqual(result.success, code == 200)
                self.assertEqual(result.response_body, 'received [REDACTADO]')
                self.assertNotIn('secret-key', result.error_message or '')
                self.assertEqual(set(post.call_args.kwargs['json']), {'camera_id', 'image_base64', 'apikey'})

    def test_manual_uses_new_frame_before_next_scheduled_check(self):
        from concurrent.futures import Future
        from unittest.mock import MagicMock
        import numpy as np
        worker = CameraWorker(1)
        frame = np.zeros((8, 8, 3), dtype=np.uint8)
        db = MagicMock()
        db.query.return_value.get.return_value = SimpleNamespace(enabled=True, rtsp_url="rtsp://test")
        db.query.return_value.first.return_value = SimpleNamespace(
            check_interval_seconds=3600, max_interval_seconds=3600, change_threshold_percent=100)
        cap = MagicMock()
        cap.isOpened.return_value = True
        reads = []
        requests = []
        reasons = []
        def read():
            reads.append(1)
            if len(reads) == 2:
                requests.append(worker.request_send())
            if len(reads) == 3:
                worker._stop_event.set()
            return True, frame
        cap.read.side_effect = read
        def submit(fn, config, image, reason):
            reasons.append(reason)
            future = Future()
            future.set_result({"success": True})
            return future
        uploads = MagicMock()
        uploads.submit.side_effect = submit
        with patch("app.capture.worker.SessionLocal", return_value=db), patch("app.capture.worker.cv2.VideoCapture", return_value=cap), patch.object(worker, "_mark_frame_seen"), patch.object(worker, "_update_preview"):
            worker._capture_loop(uploads)
        self.assertEqual(reasons, ["heartbeat", "manual"])
        self.assertEqual(requests[0].result(), {"success": True})
