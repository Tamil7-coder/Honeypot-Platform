"""
Encrypts secrets before persisting them to the database (Phase 12: the SMTP
password becomes admin-configurable via the Settings UI, which means it now
lives in a DB row rather than only in .env -- it must not be stored in
plaintext).

The Fernet key is derived from SECRET_KEY via SHA-256 rather than requiring
a second manually-generated secret in .env. This is real encryption (not
obfuscation) but shares a key with JWT signing, so rotating SECRET_KEY
invalidates both active sessions and previously-encrypted settings -- an
acceptable tradeoff for this deployment's scale; a production system at
larger scale would use a dedicated KMS-managed key.
"""
import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _get_fernet() -> Fernet:
    digest = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_secret(plaintext: str) -> str:
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str | None:
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError):
        return None
