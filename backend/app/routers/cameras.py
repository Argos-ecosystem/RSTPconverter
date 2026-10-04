from concurrent.futures import TimeoutError, CancelledError

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..capture import frame_cache
from ..capture.manager import capture_manager
from ..database import get_db
from ..deps import get_current_admin

router = APIRouter(prefix="/cameras", tags=["cameras"], dependencies=[Depends(get_current_admin)])


def _to_out(camera: models.Camera) -> schemas.CameraOut:
    return schemas.CameraOut(
        id=camera.id,
        name=camera.name,
        rtsp_url=camera.rtsp_url,
        external_camera_id=camera.external_camera_id,
        has_api_key=bool(camera.api_key),
        enabled=camera.enabled,
        last_status=camera.last_status,
        last_error=camera.last_error,
        last_frame_at=camera.last_frame_at,
        last_sent_at=camera.last_sent_at,
        created_at=camera.created_at,
        updated_at=camera.updated_at,
    )


@router.get("", response_model=list[schemas.CameraOut])
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(models.Camera).order_by(models.Camera.id).all()
    return [_to_out(c) for c in cameras]


@router.post("/{camera_id}/send-now", response_model=schemas.SendLogOut)
def send_now(camera_id: int, db: Session = Depends(get_db)):
    camera = db.get(models.Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camara no encontrada")
    if not camera.enabled:
        raise HTTPException(409, "Habilita la camara antes de enviar")
    config = db.query(models.ApiConfig).first()
    if config is None:
        raise HTTPException(409, "Configura la API destino antes de enviar")
    timeout = 30 + 2 * (config.request_timeout_seconds or 10)
    db.rollback()  # Do not hold a read transaction while the worker writes its log.
    try:
        request = capture_manager.request_send(camera_id)
    except ValueError as exc:
        raise HTTPException(409, str(exc)) from exc
    try:
        return request.result(timeout=timeout)
    except TimeoutError as exc:
        cancelled = request.cancel()
        detail = ("No se obtuvo una imagen a tiempo; envio cancelado" if cancelled else
                  "El envio sigue en curso. Consulta el historial para ver el resultado")
        raise HTTPException(504, detail) from exc
    except (ValueError, CancelledError) as exc:
        raise HTTPException(409, str(exc) or "Envio cancelado") from exc


@router.get("/{camera_id}/snapshot")
def get_snapshot(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).get(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camara no encontrada")

    frame = frame_cache.get_frame(camera_id)
    if not frame:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Todavia no hay imagen de esta camara")

    return Response(content=frame, media_type="image/jpeg")


@router.post("", response_model=schemas.CameraOut, status_code=status.HTTP_201_CREATED)
def create_camera(payload: schemas.CameraCreate, db: Session = Depends(get_db)):
    camera = models.Camera(
        name=payload.name,
        rtsp_url=payload.rtsp_url,
        external_camera_id=payload.external_camera_id or None,
        api_key=payload.api_key or None,
        enabled=payload.enabled,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)

    capture_manager.sync_camera(camera.id)
    return _to_out(camera)


@router.put("/{camera_id}", response_model=schemas.CameraOut)
def update_camera(camera_id: int, payload: schemas.CameraUpdate, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).get(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camara no encontrada")

    if payload.name is not None:
        camera.name = payload.name
    if payload.rtsp_url is not None:
        camera.rtsp_url = payload.rtsp_url
    if payload.external_camera_id is not None:
        camera.external_camera_id = payload.external_camera_id or None
    if payload.clear_api_key:
        camera.api_key = None
    elif payload.api_key is not None:
        camera.api_key = payload.api_key
    if payload.enabled is not None:
        camera.enabled = payload.enabled

    db.commit()
    db.refresh(camera)

    capture_manager.sync_camera(camera.id)
    return _to_out(camera)


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera(camera_id: int, db: Session = Depends(get_db)):
    camera = db.query(models.Camera).get(camera_id)
    if not camera:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Camara no encontrada")

    db.delete(camera)
    db.commit()

    capture_manager.sync_camera(camera_id)
    frame_cache.clear_frame(camera_id)
