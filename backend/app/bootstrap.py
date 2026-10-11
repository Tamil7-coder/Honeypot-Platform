"""
One-off bootstrap run at container startup (see docker-entrypoint.sh):
1. Applies Alembic migrations.
2. Seeds a default admin user if one does not already exist.

Kept idempotent so it is safe to run on every container start.
"""
import os

from app.core.logging_config import configure_logging, get_logger
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import Role, RoleName, User

configure_logging()
logger = get_logger(__name__)


def seed_admin_user() -> None:
    admin_username = os.getenv("DEFAULT_ADMIN_USERNAME", "admin")
    admin_email = os.getenv("DEFAULT_ADMIN_EMAIL", "admin@honeypot-platform.com")
    admin_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "ChangeMe123!")

    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == admin_username).one_or_none()
        if existing:
            logger.info("Default admin user already exists, skipping seed.")
            return

        admin_role = db.query(Role).filter(Role.name == RoleName.ADMIN).one_or_none()
        if admin_role is None:
            logger.error("Admin role not found - has the initial migration run?")
            return

        user = User(
            username=admin_username,
            full_name=os.getenv("DEFAULT_ADMIN_FULL_NAME", "Platform Administrator"),
            email=admin_email,
            hashed_password=hash_password(admin_password),
            role_id=admin_role.id,
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        logger.info("Seeded default admin user '%s'.", admin_username)
    finally:
        db.close()


if __name__ == "__main__":
    seed_admin_user()
