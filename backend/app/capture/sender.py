import base64
import time

import httpx

from .. import models

API_KEY_HEADER = "X-API-Key"


class SendResult:
    def __init__(self, success: bool, http_status: int | None, latency_ms: int, error_message: str | None, response_body: str | None = None):
        self.success = success
        self.http_status = http_status
        self.latency_ms = latency_ms
        self.error_message = error_message
        self.response_body = response_body


def send_frame(config: models.ApiConfig, camera: models.Camera, jpeg_bytes: bytes, trigger_reason: str) -> SendResult:
    if not config.endpoint_url:
        return SendResult(False, None, 0, "No hay endpoint de API configurado")

    camera_id = camera.external_camera_id or None
    if not camera_id:
        return SendResult(
            False, None, 0, f"La camara '{camera.name}' no tiene configurado el Camera ID de la API destino"
        )
    if not camera.api_key:
        return SendResult(False, None, 0, f"La camara '{camera.name}' no tiene configurada su API Key")

    # the live API rejects the request outright if any extra field is present
    # (e.g. captured_at) and validates apikey as a body field, not just the header
    payload = {
        "camera_id": camera_id,
        "image_base64": base64.b64encode(jpeg_bytes).decode("ascii"),
        "apikey": camera.api_key,
    }

    start = time.monotonic()
    try:
        response = httpx.post(
            config.endpoint_url,
            json=payload,
            headers={API_KEY_HEADER: camera.api_key},
            timeout=config.request_timeout_seconds or 10.0,
        )
        latency_ms = int((time.monotonic() - start) * 1000)
        success = 200 <= response.status_code < 300
        body = response.text.replace(camera.api_key, "[REDACTADO]")
        body = body[:8000] + ("\n[Respuesta truncada]" if len(body) > 8000 else "")
        error_message = None if success else f"HTTP {response.status_code}: {body[:300]}"
        return SendResult(success, response.status_code, latency_ms, error_message, body)
    except httpx.HTTPError as exc:
        latency_ms = int((time.monotonic() - start) * 1000)
        return SendResult(False, None, latency_ms, str(exc).replace(camera.api_key, "[REDACTADO]"))
