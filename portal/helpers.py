# portal/helpers.py
import hashlib
import os

def hash_password(password, salt=None):
    """SHA256 + salt hashing helper (you might already have this in security.py)."""
    if not salt:
        salt = os.urandom(16).hex()
    hashed = hashlib.sha256((password + salt).encode()).hexdigest()
    return hashed, salt

def calculate_new_marks(existing_marks: int, new_marks: int) -> int:
    total = existing_marks + new_marks
    if total > 100:
        raise ValueError("Total marks cannot exceed 100")
    return total

    """
    Business rule to combine marks when same student+subject is added.
    This example simply adds them (as asked) — adjust if you want another rule.
    """
    return existing_marks + new_marks
