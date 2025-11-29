# crypto_utils.py
import os
import base64
import secrets
from typing import Optional, Tuple

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    import keyring
except Exception:
    keyring = None


# ---------------------------
#  KEY GENERATION / STORAGE
# ---------------------------

def generate_key() -> bytes:
    """Return a new 32-byte AES key."""
    return secrets.token_bytes(32)


def encode_key_b64(key: bytes) -> str:
    return base64.b64encode(key).decode("utf-8")


def decode_key_b64(s: str) -> bytes:
    return base64.b64decode(s.encode("utf-8"))


# --------- KEYRING ---------

def store_key_in_keyring(service: str, username: str, key: bytes) -> bool:
    """
    Store base64(key) in OS keyring (Windows Credential Manager, macOS Keychain,
    Linux Secret Service).
    """
    if keyring is None:
        return False
    try:
        key_b64 = encode_key_b64(key)
        keyring.set_password(service, username, key_b64)
        return True
    except Exception:
        return False


def get_key_from_keyring(service: str, username: str) -> Optional[bytes]:
    """Retrieve master AES key from OS keyring."""
    if keyring is None:
        return None
    try:
        k = keyring.get_password(service, username)
        if k is None:
            return None
        return decode_key_b64(k)
    except Exception:
        return None


# --------- PASSPHRASE-FALLBACK ---------

def derive_key_from_passphrase(passphrase: str, salt: bytes, iterations: int = 200_000) -> bytes:
    """PBKDF2-HMAC-SHA256 to derive a secure AES key."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))


# ---------------------------
#  AES-GCM ENCRYPT / DECRYPT
# ---------------------------

def encrypt_bytes_aes_gcm(key: bytes, plaintext: bytes) -> Tuple[bytes, bytes]:
    """
    AES-GCM encryption.
    Returns (nonce, ciphertext).
    Nonce is 12 bytes (recommended size for AES-GCM).
    """
    nonce = secrets.token_bytes(12)
    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)
    return nonce, ciphertext


def decrypt_bytes_aes_gcm(key: bytes, nonce: bytes, ciphertext: bytes) -> bytes:
    """
    AES-GCM decryption (raises exception if authentication fails).
    """
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, associated_data=None)
