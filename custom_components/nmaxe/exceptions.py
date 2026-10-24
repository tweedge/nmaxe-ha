"""Exceptions for the NMAxe integration."""

from __future__ import annotations


class NMAxeError(Exception):
    """Base exception for NMAxe API failures."""


class NMAxeConnectionError(NMAxeError):
    """Raised when the miner cannot be reached."""


class NMAxeResponseError(NMAxeError):
    """Raised when the miner returns an unusable response."""


class NMAxeDataError(NMAxeResponseError):
    """Raised when the miner response does not match the expected schema."""
