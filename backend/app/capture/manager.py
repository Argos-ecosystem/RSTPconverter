import threading

from .. import models
from ..database import SessionLocal
from .worker import CameraWorker


class CaptureManager:
    """Owns one CameraWorker thread per enabled camera and keeps them in sync with the DB."""

    def __init__(self):
        self._lock = threading.Lock()
        self._workers: dict[int, CameraWorker] = {}

    def start_all(self):
        db = SessionLocal()
        try:
            cameras = db.query(models.Camera).filter(models.Camera.enabled.is_(True)).all()
            for camera in cameras:
                self._start_worker(camera.id)
        finally:
            db.close()

    def stop_all(self):
        with self._lock:
            workers = list(self._workers.values())
            self._workers.clear()
        for worker in workers:
            worker.stop()

    def sync_camera(self, camera_id: int):
        """Call after a camera is created/updated/deleted so its worker reflects the change."""
        db = SessionLocal()
        try:
            camera = db.query(models.Camera).get(camera_id)
            should_run = bool(camera and camera.enabled)
        finally:
            db.close()

        with self._lock:
            existing = self._workers.pop(camera_id, None)
        if existing:
            existing.stop()

        if should_run:
            self._start_worker(camera_id)

    def request_send(self, camera_id: int):
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker is None:
                raise ValueError("La camara no esta activa")
            return worker.request_send()

    def _start_worker(self, camera_id: int):
        worker = CameraWorker(camera_id)
        with self._lock:
            self._workers[camera_id] = worker
        worker.start()


capture_manager = CaptureManager()
