from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import get_db
from app.dependencies import require_admin
from app.models.user import User
from app.schemas import RoleOut, UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

ROLES: list[RoleOut] = [
    RoleOut(code="admin", label="管理员"),
    RoleOut(code="dealer", label="经销商"),
]


@router.get("/roles", response_model=list[RoleOut])
def list_roles(_: User = Depends(require_admin)):
    return ROLES


@router.get("", response_model=list[UserOut])
def list_users(_: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut)
def create_user(data: UserCreate, _: User = Depends(require_admin), db: Session = Depends(get_db)):
    _assert_email_available(db, data.email)
    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    updates = data.model_dump(exclude_unset=True)
    if "email" in updates and updates["email"] != user.email:
        _assert_email_available(db, updates["email"])
    if updates.get("role") == "dealer" and user.role == "admin":
        _assert_admin_remains(db, user.id)
    if current_user.id == user.id and updates.get("role") == "dealer":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="不能把当前登录管理员改为经销商")
    if "name" in updates:
        user.name = updates["name"]
    if "email" in updates:
        user.email = updates["email"]
    if "role" in updates:
        user.role = updates["role"]
    if updates.get("password"):
        user.password_hash = hash_password(updates["password"])
    db.commit()
    db.refresh(user)
    return user


def _assert_email_available(db: Session, email: str) -> None:
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="邮箱已被使用")


def _assert_admin_remains(db: Session, user_id: int) -> None:
    other_admin = db.query(User).filter(User.role == "admin", User.id != user_id).first()
    if other_admin is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="系统至少需要保留一个管理员")
