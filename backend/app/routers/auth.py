from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..deps import get_current_admin
from ..security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.get("/status", response_model=schemas.SetupStatus)
def setup_status(db: Session = Depends(get_db)):
    exists = db.query(models.AdminUser).first() is not None
    return schemas.SetupStatus(setup_required=not exists)


@router.post("/setup", response_model=schemas.TokenResponse)
def setup_admin(payload: schemas.AdminCreate, db: Session = Depends(get_db)):
    if db.query(models.AdminUser).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="El admin ya fue configurado")

    user = models.AdminUser(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()

    token = create_access_token(subject=user.username)
    return schemas.TokenResponse(access_token=token)


@router.post("/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.AdminUser).filter(models.AdminUser.username == payload.username).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario o contrasena incorrectos")

    token = create_access_token(subject=user.username)
    return schemas.TokenResponse(access_token=token)


@router.get("/me", response_model=schemas.AdminOut)
def me(current_admin: models.AdminUser = Depends(get_current_admin)):
    return current_admin


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_admin: models.AdminUser = Depends(get_current_admin),
):
    if not verify_password(payload.current_password, current_admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Contrasena actual incorrecta")

    current_admin.password_hash = hash_password(payload.new_password)
    db.commit()
    return {"ok": True}
