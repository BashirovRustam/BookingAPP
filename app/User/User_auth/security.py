"""Модуль для работы с безопасностью: хеширование и проверка паролей."""

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    """
    Хеширует пароль с использованием passlib (Argon2).

    Argon2 не имеет ограничения в 72 байта, поэтому можно использовать
    пароли любой длины.

    :param password: Пароль в открытом виде (plain text).
    :return: Хеш пароля в виде строки (Argon2 hash).
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Проверяет, соответствует ли пароль хешу.

    :param plain_password: Пароль в открытом виде для проверки.
    :param hashed_password: Хеш пароля из базы данных.
    :return: True, если пароль соответствует хешу, иначе False.
    """
    return pwd_context.verify(plain_password, hashed_password)
