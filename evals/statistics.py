"""评测统计量与确定性 Bootstrap 置信区间。"""

from __future__ import annotations

import random
import statistics
from typing import Any


def bootstrap_mean_ci(
    values: list[float],
    *,
    samples: int = 5000,
    confidence_level: float = 0.95,
    seed: int = 20260813,
) -> dict[str, Any]:
    if not values:
        return {"mean": None, "lower": None, "upper": None, "sample_size": 0}
    if samples <= 0:
        raise ValueError("bootstrap samples 必须大于 0")
    if not 0 < confidence_level < 1:
        raise ValueError("confidence_level 必须在 0 和 1 之间")
    rng = random.Random(seed)
    size = len(values)
    means = sorted(
        statistics.fmean(values[rng.randrange(size)] for _ in range(size))
        for _ in range(samples)
    )
    tail = (1.0 - confidence_level) / 2.0

    def quantile(q: float) -> float:
        position = (len(means) - 1) * q
        lower = int(position)
        upper = min(lower + 1, len(means) - 1)
        fraction = position - lower
        return means[lower] * (1 - fraction) + means[upper] * fraction

    return {
        "mean": round(statistics.fmean(values), 4),
        "lower": round(quantile(tail), 4),
        "upper": round(quantile(1.0 - tail), 4),
        "confidence_level": confidence_level,
        "bootstrap_samples": samples,
        "sample_size": size,
        "seed": seed,
    }

