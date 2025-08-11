import hashlib
import os

def hash_password(password, salt=None):
    """Hash password with SHA256 + salt."""
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt
