"""Secure credential storage using the OS keyring."""

from __future__ import annotations

import logging

import keyring

logger = logging.getLogger(__name__)

SERVICE_NAME = "product_gallery_normalizer"


def save_credentials(consumer_key: str, consumer_secret: str) -> None:
    """Persist consumer_key and consumer_secret in the OS keyring."""
    try:
        keyring.set_password(SERVICE_NAME, "consumer_key", consumer_key)
        keyring.set_password(SERVICE_NAME, "consumer_secret", consumer_secret)
    except Exception as exc:
        logger.error("save_credentials failed: %s", exc)


def load_credentials() -> tuple[str, str]:
    """Return (consumer_key, consumer_secret) from the OS keyring.

    Returns ("", "") if not found.
    """
    try:
        ck = keyring.get_password(SERVICE_NAME, "consumer_key") or ""
        cs = keyring.get_password(SERVICE_NAME, "consumer_secret") or ""
        return ck, cs
    except Exception as exc:
        logger.error("load_credentials failed: %s", exc)
        return "", ""


def clear_credentials() -> None:
    """Remove stored credentials from the OS keyring."""
    try:
        keyring.delete_password(SERVICE_NAME, "consumer_key")
    except Exception:
        pass
    try:
        keyring.delete_password(SERVICE_NAME, "consumer_secret")
    except Exception:
        pass
