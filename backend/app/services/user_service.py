import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    def __init__(self, db: Session):
        self.user_repo = UserRepository(db)

    def get_user(self, user_id: uuid.UUID) -> User:
        user = self.user_repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def list_users(self, skip: int = 0, limit: int = 100) -> list[User]:
        return self.user_repo.list_all(skip=skip, limit=limit)

    def deactivate_user(self, user_id: uuid.UUID) -> User:
        user = self.get_user(user_id)
        user.is_active = False
        return self.user_repo.update(user)

    def activate_user(self, user_id: uuid.UUID) -> User:
        user = self.get_user(user_id)
        user.is_active = True
        return self.user_repo.update(user)
