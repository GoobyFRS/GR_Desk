#!/usr/bin/env python3
"""Secure password authentication handler.

Provides password hashing and verification using bcrypt with 12 rounds
of salting for strong cryptographic security. All passwords are hashed
with unique salts to prevent rainbow table attacks.
"""

__all__ = ["hash_password", "verify_password"]

import bcrypt


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password using bcrypt with 12 rounds.

    Args:
        plain_password: The plaintext password to hash.

    Returns:
        A bcrypt hash string (includes salt and rounds info).
    """
    salt = bcrypt.gensalt(rounds=12)
    hashed_user_password = bcrypt.hashpw(plain_password.encode(), salt)
    return hashed_user_password.decode()


def verify_password(plain_password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored bcrypt hash.

    Args:
        plain_password: The plaintext password to verify.
        stored_hash: The bcrypt hash string to verify against.

    Returns:
        True if the password matches the hash, False otherwise.
    """
    return bcrypt.checkpw(
        plain_password.encode(),
        stored_hash.encode()
    )
