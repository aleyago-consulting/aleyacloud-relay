from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


class TokenEncryptionError(Exception):
    """Token material could not be encrypted or decrypted safely."""


def _cipher() -> Fernet:
    try:
        return Fernet(settings.TOKEN_ENCRYPTION_KEY.encode("utf-8"))
    except (AttributeError, ValueError) as error:
        raise TokenEncryptionError("Token encryption is not configured.") from error


def encrypt_token(token: str) -> str:
    try:
        return _cipher().encrypt(token.encode("utf-8")).decode("utf-8")
    except (AttributeError, UnicodeError) as error:
        raise TokenEncryptionError("Token material is invalid.") from error


def decrypt_token(ciphertext: str) -> str:
    try:
        return _cipher().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except (AttributeError, InvalidToken, UnicodeError) as error:
        raise TokenEncryptionError("Stored token material cannot be decrypted.") from error

