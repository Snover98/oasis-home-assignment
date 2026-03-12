import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password using bcrypt directly.
    :param plain_password: The plain text password.
    :param hashed_password: The hashed password.
    :return: True if match, False otherwise.
    """
    password_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    try:
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False

def get_password_hash(password: str) -> str:
    """
    Generates a bcrypt hash for a plain text password.
    :param password: The plain text password.
    :return: The hashed password.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
