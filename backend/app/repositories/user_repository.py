import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import Role, RoleName, User


class UserRepository:
    """Encapsulates all persistence operations for User/Role entities.

    Keeping raw SQLAlchemy queries here means services never talk to the ORM
    directly, satisfying the Repository pattern and easing future swaps
    (e.g. to a different ORM or read-replica routing).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, username: str) -> User | None:
        stmt = select(User).where(User.username == username)
        return self.db.execute(stmt).scalar_one_or_none()

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.db.execute(stmt).scalar_one_or_none()

    def list_all(self, skip: int = 0, limit: int = 100) -> list[User]:
        stmt = select(User).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_role_by_name(self, name: RoleName) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        return self.db.execute(stmt).scalar_one_or_none()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def update(self, user: User) -> User:
        self.db.commit()
        self.db.refresh(user)
        return user

    def username_exists(self, username: str) -> bool:
        return self.get_by_username(username) is not None
