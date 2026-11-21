"""Request body checks. Anything malformed becomes a 400 with a message, never a 500."""

import math

from flask import request


class ApiError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


_MISSING = object()


def json_body() -> dict:
    """The JSON object sent with the request; an empty body counts as {}."""
    if not request.get_data(cache=True):
        return {}
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError("The request body must be a JSON object.")
    return data


def _get(data: dict, name: str, required: bool):
    value = data.get(name, _MISSING)
    if value is _MISSING or value is None:
        if required:
            raise ApiError(f"{name} is required.")
        return _MISSING
    return value


def string(data: dict, name: str, required: bool = True, max_length: int = 4096) -> str | None:
    value = _get(data, name, required)
    if value is _MISSING:
        return None
    if not isinstance(value, str) or not value or len(value) > max_length:
        raise ApiError(f"{name} must be a non-empty string.")
    return value


def number(data: dict, name: str, minimum: float, maximum: float, required: bool = True) -> float | None:
    value = _get(data, name, required)
    if value is _MISSING:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ApiError(f"{name} must be a number.")
    if not minimum <= value <= maximum:
        raise ApiError(f"{name} must be between {minimum:g} and {maximum:g}.")
    return float(value)


def integer(data: dict, name: str, minimum: int = 0, required: bool = True, default: int | None = None) -> int | None:
    value = _get(data, name, required)
    if value is _MISSING:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ApiError(f"{name} must be a whole number of at least {minimum}.")
    return value


def boolean(data: dict, name: str, default: bool | None = None) -> bool | None:
    value = _get(data, name, required=False)
    if value is _MISSING:
        return default
    if not isinstance(value, bool):
        raise ApiError(f"{name} must be true or false.")
    return value


def string_list(data: dict, name: str, max_items: int = 100_000) -> list[str]:
    value = _get(data, name, required=True)
    if not isinstance(value, list) or len(value) > max_items or not all(isinstance(v, str) and v for v in value):
        raise ApiError(f"{name} must be a list of track ids.")
    return value


def choice(data: dict, name: str, options: tuple[str, ...]) -> str | None:
    value = _get(data, name, required=False)
    if value is _MISSING:
        return None
    if value not in options:
        raise ApiError(f"{name} must be one of: {', '.join(options)}.")
    return value
