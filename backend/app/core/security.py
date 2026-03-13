"""
Security utility module for the Oasis NHI Ticket System.
Provides functions for password hashing and verification using bcrypt.
"""

import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifies a plain text password against a hashed password using bcrypt directly.

    Args:
        plain_password (str): The plain text password provided by the user.
        hashed_password (str): The bcrypt-hashed password stored in the database.

    Returns:
        bool: True if the passwords match, False otherwise.
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

    Args:
        password (str): The plain text password to hash.

    Returns:
        str: The generated bcrypt hash as a string.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')
