import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_admin

router = APIRouter(prefix="/stats", tags=["stats"], dependencies=[Depends(get_current_admin)])


def _streak_metrics(sent_at_list: list[datetime.datetime], healthy_gap_seconds: float) -> tuple[float, float]:
    """Returns (longest_uptime_seconds, longest_gap_seconds) from an ascending list of successful send timestamps."""
    if len(sent_at_list) < 2:
        return 0.0, 0.0

    longest_uptime = 0.0
    longest_gap = 0.0
    streak_start = sent_at_list[0]
    prev = sent_at_list[0]

    for ts in sent_at_list[1:]:
        gap = (ts - prev).total_seconds()
        longest_gap = max(longest_gap, gap)
        if gap > healthy_gap_seconds:
            longest_uptime = max(longest_uptime, (prev - streak_start).total_seconds())
            streak_start = ts
        prev = ts

    longest_uptime = max(longest_uptime, (prev - streak_start).total_seconds())
    return longest_uptime, longest_gap


@router.get("/summary", response_model=schemas.StatsSummary)
def get_summary(db: Session = Depends(get_db)):
    config = db.query(models.ApiConfig).first()
    healthy_gap = (config.max_interval_seconds * 2) if config else 120.0

    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    cameras = db.query(models.Camera).order_by(models.Camera.id).all()

    camera_stats: list[schemas.CameraStats] = []
    global_uptime = 0.0
    global_gap = 0.0

    for camera in cameras:
        logs = (
            db.query(models.SendLog)
            .filter(models.SendLog.camera_id == camera.id)
            .order_by(models.SendLog.sent_at.asc())
            .all()
        )
        success_logs = [l for l in logs if l.success]
        total = len(logs)
        total_success = len(success_logs)
        total_today = sum(1 for l in logs if l.sent_at >= today_start)
        failed_total = total - total_success
        success_rate = (total_success / total * 100.0) if total else 0.0
        latencies = [l.latency_ms for l in success_logs if l.latency_ms is not None]
        avg_latency = (sum(latencies) / len(latencies)) if latencies else None

        uptime, gap = _streak_metrics([l.sent_at for l in success_logs], healthy_gap)
        global_uptime = max(global_uptime, uptime)
        global_gap = max(global_gap, gap)

        camera_stats.append(
            schemas.CameraStats(
                camera_id=camera.id,
                camera_name=camera.name,
                status=camera.last_status,
                frames_sent_total=total_success,
                frames_sent_today=total_today,
                frames_failed_total=failed_total,
                success_rate=round(success_rate, 2),
                last_sent_at=camera.last_sent_at,
                avg_latency_ms=round(avg_latency, 1) if avg_latency is not None else None,
                longest_uptime_seconds=uptime,
                longest_gap_seconds=gap,
            )
        )

    frames_sent_total = sum(c.frames_sent_total for c in camera_stats)
    frames_failed_total = sum(c.frames_failed_total for c in camera_stats)
    frames_sent_today = sum(c.frames_sent_today for c in camera_stats)
    total_attempts = frames_sent_total + frames_failed_total
    overall_success_rate = (frames_sent_total / total_attempts * 100.0) if total_attempts else 0.0

    all_latencies_query = (
        db.query(func.avg(models.SendLog.latency_ms)).filter(models.SendLog.success.is_(True)).scalar()
    )

    return schemas.StatsSummary(
        frames_sent_total=frames_sent_total,
        frames_sent_today=frames_sent_today,
        frames_failed_total=frames_failed_total,
        success_rate=round(overall_success_rate, 2),
        active_cameras=sum(1 for c in cameras if c.last_status == "connected"),
        total_cameras=len(cameras),
        avg_latency_ms=round(all_latencies_query, 1) if all_latencies_query is not None else None,
        longest_uptime_seconds=global_uptime,
        longest_gap_seconds=global_gap,
        cameras=camera_stats,
    )


@router.get("/logs", response_model=list[schemas.SendLogOut])
def get_logs(
    camera_id: int | None = None,
    limit: int = Query(default=50, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(models.SendLog).order_by(models.SendLog.sent_at.desc())
    if camera_id is not None:
        query = query.filter(models.SendLog.camera_id == camera_id)
    logs = query.offset(offset).limit(limit).all()

    camera_names = {c.id: c.name for c in db.query(models.Camera).all()}
    return [
        schemas.SendLogOut(
            id=log.id,
            camera_id=log.camera_id,
            camera_name=camera_names.get(log.camera_id, "?"),
            sent_at=log.sent_at,
            success=log.success,
            http_status=log.http_status,
            latency_ms=log.latency_ms,
            frame_bytes=log.frame_bytes,
            trigger_reason=log.trigger_reason,
            error_message=log.error_message,
            response_body=log.response_body,
        )
        for log in logs
    ]
