import os

from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.context import CryptContext

SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
SESSION_COOKIE_NAME = "session_token"
SESSION_MAX_AGE = 60 * 60 * 24 * 7  # 7 days, in seconds

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
_serializer = URLSafeTimedSerializer(SECRET_KEY, salt="session-cookie")


def hash_password(plain_password: str) -> str:
    return pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_session_token(user_id: int) -> str:
    """Issue a signed, timestamped token encoding the user's id."""
    return _serializer.dumps({"user_id": user_id})


def verify_session_token(token: str) -> int | None:
    """Validate signature + expiry. Returns the user id, or None if invalid/expired."""
    try:
        data = _serializer.loads(token, max_age=SESSION_MAX_AGE)
        return data.get("user_id")
    except (BadSignature, SignatureExpired):
        return None
