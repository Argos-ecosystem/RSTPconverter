import datetime
import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor

import cv2

from .. import models
from ..config import (
    RTSP_OPEN_TIMEOUT_MS,
    RTSP_READ_TIMEOUT_MS,
    RTSP_RECONNECT_SECONDS,
    RTSP_TRANSPORT,
)
from ..database import SessionLocal
from . import change_detection, frame_cache
from .sender import send_frame

PREVIEW_MAX_WIDTH = 480
PREVIEW_JPEG_QUALITY = 70

logger = logging.getLogger("rstpconverter.worker")

RECONNECT_BACKOFF_SECONDS = RTSP_RECONNECT_SECONDS

# Forces the FFmpeg backend to use TCP (more reliable than UDP over wifi/VPNs)
# and bounds how long it waits to open/read the stream, same knobs Iris uses.
os.environ.setdefault(
    "OPENCV_FFMPEG_CAPTURE_OPTIONS",
    f"rtsp_transport;{RTSP_TRANSPORT}|stimeout;{RTSP_OPEN_TIMEOUT_MS * 1000}|max_delay;{RTSP_READ_TIMEOUT_MS * 1000}",
)


class CameraWorker:
    def __init__(self, camera_id: int):
        self.camera_id = camera_id
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._manual_lock = threading.Lock()
        self._manual_request = None

    def request_send(self):
        with self._manual_lock:
            if self._stop_event.is_set():
                raise ValueError("La camara se esta deteniendo")
            if self._manual_request and not self._manual_request.done():
                raise ValueError("Ya hay un envio manual pendiente")
            self._manual_request = Future()
            return self._manual_request

    @staticmethod
    def _complete_manual(upload, request):
        try:
            request.set_result(upload.result())
        except Exception as exc:
            request.set_exception(exc)

    def start(self):
        self._thread = threading.Thread(target=self._run, name=f"camera-{self.camera_id}", daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        with self._manual_lock:
            if self._manual_request:
                self._manual_request.cancel()
        if self._thread:
            self._thread.join(timeout=10)
        self._set_status("stopped")

    def _set_status(self, status: str, error: str | None = None):
        db = SessionLocal()
        try:
            camera = db.query(models.Camera).get(self.camera_id)
            if camera:
                camera.last_status = status
                camera.last_error = error
                db.commit()
        finally:
            db.close()

    def _run(self):
        # Uploads must never block RTSP decoding or the local preview.
        with ThreadPoolExecutor(max_workers=1, thread_name_prefix=f"upload-{self.camera_id}") as uploads:
            self._capture_loop(uploads)

    def _capture_loop(self, uploads):
        cap: cv2.VideoCapture | None = None
        last_sent_frame = None
        last_sent_at: datetime.datetime | None = None
        pending_upload = None
        next_check = 0.0
        next_preview = 0.0

        while not self._stop_event.is_set():
            db = SessionLocal()
            try:
                camera = db.query(models.Camera).get(self.camera_id)
                if not camera or not camera.enabled:
                    break
                rtsp_url = camera.rtsp_url
            finally:
                db.close()

            if cap is None or not cap.isOpened():
                self._set_status("connecting")
                cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG, [
                    cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, RTSP_OPEN_TIMEOUT_MS,
                    cv2.CAP_PROP_READ_TIMEOUT_MSEC, RTSP_READ_TIMEOUT_MS,
                ])
                if not cap.isOpened():
                    self._set_status("error", "No se pudo conectar al stream RTSP")
                    if self._stop_event.wait(RECONNECT_BACKOFF_SECONDS):
                        break
                    continue

            ok, frame = cap.read()
            if not ok or frame is None:
                self._set_status("error", "Se perdio la senal del stream")
                cap.release()
                cap = None
                if self._stop_event.wait(RECONNECT_BACKOFF_SECONDS):
                    break
                continue

            monotonic_now = time.monotonic()
            if monotonic_now >= next_preview:
                self._mark_frame_seen()
                self._update_preview(frame)
                next_preview = monotonic_now + 0.5

            # Keep draining the stream between change checks; sleeping here
            # builds up old RTSP frames and makes the preview appear frozen.
            with self._manual_lock:
                manual = self._manual_request
                manual_pending = manual is not None and not manual.done() and not manual.running()
            if monotonic_now < next_check and not manual_pending:
                continue

            db = SessionLocal()
            try:
                config = db.query(models.ApiConfig).first()
            finally:
                db.close()

            if config is None:
                next_check = monotonic_now + 2.0
                continue

            next_check = monotonic_now + max(0.1, config.check_interval_seconds)
            if pending_upload is not None:
                if not pending_upload.done():
                    continue
                try:
                    pending_upload.result()
                except Exception:
                    logger.exception("Fallo de envio de la camara %s", self.camera_id)
                pending_upload = None

            now = datetime.datetime.utcnow()
            pct = change_detection.change_percent(last_sent_frame, frame)

            should_send = False
            trigger_reason = None
            if manual_pending:
                should_send = True
                trigger_reason = "manual"
            elif last_sent_at is None:
                should_send = True
                trigger_reason = "heartbeat"
            elif (now - last_sent_at).total_seconds() >= config.max_interval_seconds:
                should_send = True
                trigger_reason = "heartbeat"
            elif pct >= config.change_threshold_percent:
                should_send = True
                trigger_reason = "change"

            if should_send:
                if trigger_reason == "manual" and not manual.set_running_or_notify_cancel():
                    continue
                pending_upload = uploads.submit(self._send, config, frame.copy(), trigger_reason)
                if trigger_reason == "manual":
                    pending_upload.add_done_callback(lambda upload, request=manual: self._complete_manual(upload, request))
                last_sent_frame = frame
                last_sent_at = now

        if cap is not None:
            cap.release()
        frame_cache.clear_frame(self.camera_id)
        self._set_status("stopped")

    def _update_preview(self, frame):
        preview = frame
        height, width = frame.shape[:2]
        if width > PREVIEW_MAX_WIDTH:
            scale = PREVIEW_MAX_WIDTH / width
            preview = cv2.resize(frame, (PREVIEW_MAX_WIDTH, int(height * scale)), interpolation=cv2.INTER_AREA)

        ok, buffer = cv2.imencode(".jpg", preview, [int(cv2.IMWRITE_JPEG_QUALITY), PREVIEW_JPEG_QUALITY])
        if ok:
            frame_cache.set_frame(self.camera_id, buffer.tobytes())

    def _mark_frame_seen(self):
        db = SessionLocal()
        try:
            camera = db.query(models.Camera).get(self.camera_id)
            if camera:
                camera.last_status = "connected"
                camera.last_error = None
                camera.last_frame_at = datetime.datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _send(self, config: models.ApiConfig, frame, trigger_reason: str):
        db = SessionLocal()
        try:
            camera = db.query(models.Camera).get(self.camera_id)
            if not camera:
                return

            transformed = frame
            width = config.resolution_width or 0
            height = config.resolution_height or 0
            if width > 0 and height > 0:
                transformed = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

            quality = max(1, min(100, config.jpeg_quality or 85))
            ok, buffer = cv2.imencode(".jpg", transformed, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
            if not ok:
                raise ValueError("No se pudo codificar la imagen")

            jpeg_bytes = buffer.tobytes()
            result = send_frame(config, camera, jpeg_bytes, trigger_reason)

            log = models.SendLog(
                camera_id=camera.id,
                success=result.success,
                http_status=result.http_status,
                latency_ms=result.latency_ms,
                frame_bytes=len(jpeg_bytes),
                trigger_reason=trigger_reason,
                error_message=result.error_message,
                response_body=result.response_body,
            )
            db.add(log)

            if result.success:
                camera.last_sent_at = datetime.datetime.utcnow()
            db.commit()
            db.refresh(log)
            return {
                **{field: getattr(log, field) for field in (
                    "id", "camera_id", "sent_at", "success", "http_status", "latency_ms",
                    "frame_bytes", "trigger_reason", "error_message", "response_body")},
                "camera_name": camera.name,
            }
        finally:
            db.close()
