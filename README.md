# RSTP Converter

Versión actual: **1.0.0**.

Servicio local que lee las mismas fuentes RTSP que Iris, extrae frames y los
envia a una API en la nube, con un panel web para configurar el destino, la
transformacion de imagen, y ver estadisticas de envio. Pensado para correr en
la misma red local que las camaras (un equipo, un Raspberry Pi, un NAS, etc.).

## Componentes

- `backend/`: servicio Python (FastAPI + OpenCV) que se conecta a cada camara
  RTSP, decide cuando enviar un frame, lo transforma y lo sube a la API
  configurada. Expone tambien la API REST que usa el panel web y guarda todo
  en SQLite (`backend/data/rstp_converter.db`).
- `frontend/`: panel web (React) para el usuario admin: alta de camaras,
  configuracion de la API destino/credenciales/transformacion, y dashboard de
  estadisticas.

## Como se decide cuando enviar un frame

Por cada camara, cada "intervalo de chequeo" se compara el frame actual contra
el ultimo que se envio:

- Si el cambio detectado supera el **umbral de cambio (%)** configurado, se
  envia ese frame (motivo `change`).
- Si paso el **intervalo maximo (heartbeat)** sin que se cumpliera lo
  anterior, igual se envia un frame de referencia (motivo `heartbeat`), para
  que la nube siempre tenga una imagen reciente aunque no haya movimiento.

Todo esto se configura desde la pestana "API y transformacion" del panel.

## Requisitos

- Python 3.10+
- Node.js 18+
- Acceso de red a las camaras RTSP (las mismas URLs que usa Iris)

## Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Queda escuchando en `http://localhost:8000`. La base de datos SQLite y la
clave de firma de sesiones se crean solas en `backend/data/` la primera vez
que arranca.

Variables de entorno opcionales (`backend/.env` o exportadas antes de correr):

| Variable | Default | Que hace |
|---|---|---|
| `SECRET_KEY` | generada y guardada en `data/.secret_key` | firma los tokens de sesion |
| `DATABASE_URL` | `sqlite:///./data/rstp_converter.db` | conexion a la base |
| `CORS_ORIGINS` | `http://localhost:5173` | origenes permitidos para el panel |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` | duracion de la sesion admin |

## Frontend

```bash
cd frontend
npm install
cp .env.example .env.local   # ajustar VITE_API_BASE_URL si el backend no esta en localhost:8000
npm run dev
```

Abrir `http://localhost:5173`.

## Alineado con Iris

`backend/data/rstp_converter.db` ya viene sembrada con las 3 camaras RTSP
reales de `iris/.env` (Vivero Interior, Entrada Vivero -deshabilitada, igual
que en Iris-, Sala tio) y con los valores que Iris ya tiene afinados:
resolucion 640x480, calidad JPEG 80, umbral de cambio 1% y transporte RTSP
por TCP con los mismos timeouts/reconexion (`RTSP_TRANSPORT`,
`RTSP_OPEN_TIMEOUT_MS`, `RTSP_READ_TIMEOUT_MS`, `RTSP_RECONNECT_SECONDS` en
`backend/.env.example`). Lo que no se copio (claves de DashScope, Telegram,
Mongo, prompts de IA) porque no aplica a este servicio: aca solo se reenvian
frames a la API de la nube, no se analizan.

## Primer uso

1. Al entrar por primera vez, el panel pide crear el **usuario admin** (no
   hay usuario por defecto ni contrasena precargada).
2. En **Camaras** ya deberian aparecer las 3 camaras de Iris; se pueden
   editar/agregar mas fuentes RTSP igual que alli.
3. En **API y transformacion**, cargar el endpoint de la API en la nube, el
   tipo de autenticacion y sus credenciales, la resolucion de salida (vacio =
   se mantiene la resolucion original), la calidad JPEG, y los parametros de
   cuando enviar (umbral de cambio / intervalo heartbeat). Cada campo de
   credencial muestra si esta **configurado** o no, para evitar confundir un
   campo vacio con uno ya guardado; dejar un campo de contrasena/token en
   blanco al editar significa "no cambiar", hay un boton aparte para
   borrarlo.
4. En **Resumen** se ven las estadisticas: frames enviados (total/hoy), tasa
   de exito, latencia promedio, camaras activas, mayor tiempo de actividad
   seguido sin caidas y la mayor caida detectada, tanto global como por
   camara.

## Produccion / correr como servicio local

Para dejarlo corriendo permanentemente conviene usar un gestor de procesos
(systemd, pm2, launchd, supervisor, etc.) que levante `backend/run.py` y, si
se sirve el frontend por separado, `npm run build` + servir `frontend/dist`
con cualquier servidor estatico (nginx, Caddy) apuntando su `VITE_API_BASE_URL`
al backend.
