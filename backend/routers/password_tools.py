from bcrypt import gensalt, hashpw, checkpw


def hash_password(password: str) -> bytes:
    password_bytes = password.encode()
    salt = gensalt()
    return hashpw(password_bytes, salt)


def check_password(user_password: str, hashed_password: bytes) -> bool:
    user_password_bytes = user_password.encode()
    return checkpw(user_password_bytes, hashed_password)

