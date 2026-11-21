"""Audio output behind a small interface, so the engine runs (and is tested) without a sound card."""

from .base import AudioBackend, AudioUnavailableError, BackendError

__all__ = ["AudioBackend", "AudioUnavailableError", "BackendError"]
