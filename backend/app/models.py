import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from .database import Base


def utcnow():
    return datetime.datetime.utcnow()


class AdminUser(Base):
    __tablename__ = "admin_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=utcnow)


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    # full RTSP URL, credentials included inline (rtsp://user:pass@host:port/path)
    rtsp_url = Column(String(512), nullable=False)
    enabled = Column(Boolean, default=True)

    # camera_id expected by the destination ingest API (e.g. Iris's "CAM1").
    # Must match whatever camera_id the cloud API has configured for this source.
    external_camera_id = Column(String(64), nullable=True)
    # Each camera authenticates with its own API key against the ingest API
    # (a shared key would let one leaked key send frames as any camera).
    api_key = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    # last known runtime status, updated by the capture worker
    last_status = Column(String(32), default="stopped")  # stopped|connecting|connected|error
    last_error = Column(Text, nullable=True)
    last_frame_at = Column(DateTime, nullable=True)
    last_sent_at = Column(DateTime, nullable=True)

    logs = relationship("SendLog", back_populates="camera", cascade="all, delete-orphan")


class ApiConfig(Base):
    """Singleton row holding the cloud API destination and transform settings."""

    __tablename__ = "api_config"

    id = Column(Integer, primary_key=True, index=True)

    # cloud API destination; each camera authenticates with its own
    # X-API-Key (see Camera.api_key) against this same endpoint.
    endpoint_url = Column(String(512), nullable=True)

    # image transform (defaults match Iris's tuned FRAME_WIDTH/HEIGHT/JPEG_QUALITY)
    resolution_width = Column(Integer, nullable=True, default=640)  # null/0 = keep original
    resolution_height = Column(Integer, nullable=True, default=480)
    jpeg_quality = Column(Integer, default=80)

    # send trigger (change_threshold_percent matches Iris's CHANGE_THRESHOLD_PERCENT)
    check_interval_seconds = Column(Float, default=2.0)
    change_threshold_percent = Column(Float, default=1.0)
    max_interval_seconds = Column(Float, default=60.0)

    request_timeout_seconds = Column(Float, default=10.0)

    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)


class SendLog(Base):
    __tablename__ = "send_logs"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False, index=True)
    sent_at = Column(DateTime, default=utcnow, index=True)
    success = Column(Boolean, default=False)
    http_status = Column(Integer, nullable=True)
    latency_ms = Column(Integer, nullable=True)
    frame_bytes = Column(Integer, nullable=True)
    trigger_reason = Column(String(32), nullable=True)  # change|heartbeat
    error_message = Column(Text, nullable=True)
    response_body = Column(Text, nullable=True)

    camera = relationship("Camera", back_populates="logs")
