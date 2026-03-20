"""
Security utility module for the Oasis NHI Ticket System.
Provides functions for password hashing and verification using bcrypt.
"""

import bcrypt

def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """
    Verifies a plain text secret against a bcrypt hash.

    Args:
        plain_secret (str): The plain text secret provided by the caller.
        hashed_secret (str): The bcrypt-hashed secret stored by the application.

    Returns:
        bool: True if the secret matches, False otherwise.
    """
    secret_bytes = plain_secret.encode('utf-8')
    hashed_bytes = hashed_secret.encode('utf-8')
    try:
        return bcrypt.checkpw(secret_bytes, hashed_bytes)
    except Exception:
        return False

def get_secret_hash(secret: str) -> str:
    """
    Generates a bcrypt hash for a plain text secret.

    Args:
        secret (str): The plain text secret to hash.

    Returns:
        str: The generated bcrypt hash as a string.
    """
    secret_bytes = secret.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(secret_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password using bcrypt directly.

    Args:
        plain_password (str): The plain text password provided by the user.
        hashed_password (str): The bcrypt-hashed password stored in the database.

    Returns:
        bool: True if the passwords match, False otherwise.
    """
    return verify_secret(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Generates a bcrypt hash for a plain text password.

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The generated bcrypt hash as a string.
    """
    return get_secret_hash(password)
