from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_admin

router = APIRouter(prefix="/api-config", tags=["api-config"], dependencies=[Depends(get_current_admin)])


def _get_or_create(db: Session) -> models.ApiConfig:
    config = db.query(models.ApiConfig).first()
    if not config:
        config = models.ApiConfig()
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _to_out(config: models.ApiConfig) -> schemas.ApiConfigOut:
    return schemas.ApiConfigOut(
        id=config.id,
        endpoint_url=config.endpoint_url,
        resolution_width=config.resolution_width,
        resolution_height=config.resolution_height,
        jpeg_quality=config.jpeg_quality,
        check_interval_seconds=config.check_interval_seconds,
        change_threshold_percent=config.change_threshold_percent,
        max_interval_seconds=config.max_interval_seconds,
        request_timeout_seconds=config.request_timeout_seconds,
        updated_at=config.updated_at,
    )


@router.get("", response_model=schemas.ApiConfigOut)
def get_api_config(db: Session = Depends(get_db)):
    return _to_out(_get_or_create(db))


@router.put("", response_model=schemas.ApiConfigOut)
def update_api_config(payload: schemas.ApiConfigUpdate, db: Session = Depends(get_db)):
    config = _get_or_create(db)

    if payload.endpoint_url is not None:
        config.endpoint_url = payload.endpoint_url or None

    if payload.resolution_width is not None:
        config.resolution_width = payload.resolution_width or None
    if payload.resolution_height is not None:
        config.resolution_height = payload.resolution_height or None
    if payload.jpeg_quality is not None:
        config.jpeg_quality = payload.jpeg_quality

    if payload.check_interval_seconds is not None:
        config.check_interval_seconds = payload.check_interval_seconds
    if payload.change_threshold_percent is not None:
        config.change_threshold_percent = payload.change_threshold_percent
    if payload.max_interval_seconds is not None:
        config.max_interval_seconds = payload.max_interval_seconds
    if payload.request_timeout_seconds is not None:
        config.request_timeout_seconds = payload.request_timeout_seconds

    db.commit()
    db.refresh(config)
    return _to_out(config)
