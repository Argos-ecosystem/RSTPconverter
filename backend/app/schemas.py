import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- Auth ----------

class SetupStatus(BaseModel):
    setup_required: bool


class AdminCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    created_at: datetime.datetime


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


# ---------- Cameras ----------

class CameraCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    rtsp_url: str = Field(min_length=1, max_length=512)
    external_camera_id: Optional[str] = None
    api_key: Optional[str] = None
    enabled: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    rtsp_url: Optional[str] = None
    external_camera_id: Optional[str] = None
    # None = no change, "" = clear stored key
    api_key: Optional[str] = None
    clear_api_key: bool = False
    enabled: Optional[bool] = None


class CameraOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    rtsp_url: str
    external_camera_id: Optional[str]
    has_api_key: bool
    enabled: bool
    last_status: str
    last_error: Optional[str]
    last_frame_at: Optional[datetime.datetime]
    last_sent_at: Optional[datetime.datetime]
    created_at: datetime.datetime
    updated_at: datetime.datetime


# ---------- API config ----------

class ApiConfigUpdate(BaseModel):
    endpoint_url: Optional[str] = None

    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    jpeg_quality: Optional[int] = Field(default=None, ge=1, le=100)

    check_interval_seconds: Optional[float] = Field(default=None, gt=0)
    change_threshold_percent: Optional[float] = Field(default=None, ge=0, le=100)
    max_interval_seconds: Optional[float] = Field(default=None, gt=0)
    request_timeout_seconds: Optional[float] = Field(default=None, gt=0)


class ApiConfigOut(BaseModel):
    id: int
    endpoint_url: Optional[str]

    resolution_width: Optional[int]
    resolution_height: Optional[int]
    jpeg_quality: int

    check_interval_seconds: float
    change_threshold_percent: float
    max_interval_seconds: float
    request_timeout_seconds: float

    updated_at: Optional[datetime.datetime]


# ---------- Stats ----------

class SendLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    camera_id: int
    camera_name: str
    sent_at: datetime.datetime
    success: bool
    http_status: Optional[int]
    latency_ms: Optional[int]
    frame_bytes: Optional[int]
    trigger_reason: Optional[str]
    error_message: Optional[str]
    response_body: Optional[str] = None


class CameraStats(BaseModel):
    camera_id: int
    camera_name: str
    status: str
    frames_sent_total: int
    frames_sent_today: int
    frames_failed_total: int
    success_rate: float
    last_sent_at: Optional[datetime.datetime]
    avg_latency_ms: Optional[float]
    longest_uptime_seconds: float
    longest_gap_seconds: float


class StatsSummary(BaseModel):
    frames_sent_total: int
    frames_sent_today: int
    frames_failed_total: int
    success_rate: float
    active_cameras: int
    total_cameras: int
    avg_latency_ms: Optional[float]
    longest_uptime_seconds: float
    longest_gap_seconds: float
    cameras: list[CameraStats]
