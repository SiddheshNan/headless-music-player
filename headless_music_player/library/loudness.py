"""Integrated loudness (LUFS) of a song, following ITU-R BS.1770 / EBU R128.

The file is decoded in chunks to mono (what the speaker plays), K-weighted, and measured
in 400 ms blocks with the standard absolute (-70 LUFS) and relative (-10 LU) gates.
The K-weighting is applied per 100 ms chunk in the frequency domain, which needs only
numpy and gives the same mean-square energy as filtering in time to within a fraction of
a dB.
"""

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

SAMPLE_RATE = 44_100
CHUNK = SAMPLE_RATE // 10  # 100 ms
BLOCK_CHUNKS = 4  # a 400 ms block = 4 chunks, overlapping by 75%
ABSOLUTE_GATE = -70.0
RELATIVE_GATE = -10.0

# K-weighting filter (BS.1770-4, specified at 48 kHz): a high shelf, then a high pass.
_SHELF = ([1.53512485958697, -2.69169618940638, 1.19839281085285], [1.0, -1.69065929318241, 0.73248077421585])
_HIGHPASS = ([1.0, -2.0, 1.0], [1.0, -1.99004745483398, 0.99007225036621])


class LoudnessError(Exception):
    pass


@lru_cache(maxsize=4)
def _k_weight(n: int, sample_rate: int) -> np.ndarray:
    """|H(f)|^2 of the K-weighting filter at the rfft bins of an n-sample chunk."""
    freqs = np.fft.rfftfreq(n, 1 / sample_rate)
    z = np.exp(-2j * np.pi * freqs / 48_000)  # evaluate the 48 kHz design at these frequencies
    response = np.ones_like(freqs)
    for b, a in (_SHELF, _HIGHPASS):
        num = b[0] + b[1] * z + b[2] * z**2
        den = a[0] + a[1] * z + a[2] * z**2
        response = response * np.abs(num / den) ** 2
    return response


def chunk_power(samples: np.ndarray, sample_rate: int = SAMPLE_RATE) -> float:
    """K-weighted mean square of one chunk (Parseval's theorem over the rfft)."""
    n = len(samples)
    spectrum = np.abs(np.fft.rfft(samples)) ** 2
    weights = _k_weight(n, sample_rate)
    # Every bin except DC (and Nyquist for even n) stands for two in the full spectrum.
    scale = np.full(len(spectrum), 2.0)
    scale[0] = 1.0
    if n % 2 == 0:
        scale[-1] = 1.0
    return float(np.sum(spectrum * weights * scale) / (n * n))


def integrated_loudness(chunk_powers: list[float]) -> float | None:
    """Gated loudness from 100 ms chunk powers. None for silence or anything under 400 ms."""
    if len(chunk_powers) < BLOCK_CHUNKS:
        return None
    powers = np.asarray(chunk_powers)
    blocks = np.convolve(powers, np.ones(BLOCK_CHUNKS) / BLOCK_CHUNKS, mode="valid")
    with np.errstate(divide="ignore"):
        loudness = -0.691 + 10 * np.log10(blocks)

    gated = blocks[loudness > ABSOLUTE_GATE]
    if not len(gated):
        return None
    relative = -0.691 + 10 * math.log10(float(np.mean(gated))) + RELATIVE_GATE
    gated = blocks[(loudness > ABSOLUTE_GATE) & (loudness > relative)]
    if not len(gated):
        return None
    return round(-0.691 + 10 * math.log10(float(np.mean(gated))), 2)


def measure(path: Path, should_stop=lambda: False) -> float | None:
    """Loudness of a file in LUFS; None when it's silent. Raises LoudnessError if unreadable."""
    import miniaudio

    try:
        stream = miniaudio.stream_file(
            str(path),
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=1,
            sample_rate=SAMPLE_RATE,
            frames_to_read=CHUNK,
        )
        powers: list[float] = []
        pending = np.empty(0, dtype=np.float32)
        for frames in stream:
            if should_stop():
                raise LoudnessError("stopped")
            pending = np.concatenate([pending, np.frombuffer(frames, dtype=np.float32)])
            while len(pending) >= CHUNK:
                powers.append(chunk_power(pending[:CHUNK].astype(np.float64)))
                pending = pending[CHUNK:]
    except miniaudio.DecodeError as e:
        raise LoudnessError(str(e)) from e
    return integrated_loudness(powers)
