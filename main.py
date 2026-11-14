#!/usr/bin/env python3
"""Forecast Bitcoin's US-dollar price 240 minutes (4 hours) ahead.

Entry for make.fun bounty btc-cent-forecast-01.

Method (one number per case: the conditional median, which is the
MAE-optimal point forecast)
---------------------------------------------------------------
The score is the mean absolute error in cents, so the best guess is the
median of the price 240 minutes after the checkpoint. Bitcoin's 4-hour
returns are, to first order, a martingale: on 45 days of Binance BTCUSDT
1-minute closes (1,005 pseudo-cases, 72 h of history each, target +240 min)
persistence (guess = last close) scores 40,007 cents, and every drift,
mean-reversion, AR(1) or long-window momentum variant I tried scores
*worse* than persistence. The one exception is a tiny, robust short-horizon
momentum effect: the last few minutes' move keeps going a little.

    guess = last * exp(0.20 * ln(last / close 5 minutes ago))

i.e. extrapolate 20% of the last 5-minute log-move. On the same 1,005
Binance pseudo-cases this scores 39,944 cents (-0.16% vs persistence),
better than persistence in *both* halves of the sample, and it also beats
persistence on the kit's own practice data: 46,293 cents vs 47,055 on the
five practice cases whose answers are recoverable from the kit itself
(p00-p04; the house baseline over all six is 44,522 cents), and 53,659 vs
54,020 on 16 hourly pseudo-cases cut from the practice recording.

The effect is small and the model stays close to persistence on purpose:
any larger tilt (longer windows, bigger coefficients, drift, reversion)
loses on the 45-day sample. When the last 5 minutes did not move at all
- common in this pool, where ~30% of minutes are flat - the guess is
exactly the last close.

Deterministic, standard library only, no network, runs in milliseconds
per case (limit is 8 s).

Reads every <id>.in in $MAKEFUN_INPUT_DIR (else /input) and writes
<id>.out to $MAKEFUN_OUTPUT_DIR (else /output):
{"forecasts": [{"case": "<id>", "price": <number>}]}.
"""

import json
import math
import os
from pathlib import Path

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999

# Last-5-minute log-move, extrapolated with this damping. Tuned on 45 days
# of Binance BTCUSDT 1-minute closes (1,005 pseudo-cases): 0.20 was the
# best of the 0.10/0.15/0.20 grid at a 5-minute window, and the 5-minute
# window beat 10/15/20/30-minute windows at every scale tried.
MOMENTUM_WINDOW = 5      # minutes of recent move to extrapolate
MOMENTUM_SCALE = 0.20    # fraction of that move carried forward


def price5(x):
    """Clamp x to (0, 10,000,000) and round to the grid's 5 decimals."""
    return round(min(MAX_PRICE, max(MIN_PRICE, x)) * 1e5) / 1e5


def forecast(prices):
    """Median forecast of the price 240 minutes after the last close."""
    if not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not isinstance(last, (int, float)) or not math.isfinite(last) or last <= 0:
        raise ValueError("last price is not a positive finite number")
    if len(prices) > MOMENTUM_WINDOW:
        base = prices[-1 - MOMENTUM_WINDOW]
        if isinstance(base, (int, float)) and math.isfinite(base) and base > 0:
            move = math.log(last / base)
            return price5(last * math.exp(MOMENTUM_SCALE * move))
    return price5(last)


def main():
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    inputs = sorted(Path(INPUT_DIR).glob("*.in"))
    for path in inputs:
        case_id = path.name[: -len(".in")]
        with path.open("r", encoding="utf-8") as f:
            case = json.load(f)
        markets = case.get("markets")
        if not isinstance(markets, list) or len(markets) != 1:
            raise ValueError("%s does not hold exactly one market" % path.name)
        guess = forecast(markets[0]["prices"])
        out_path = out_dir / (case_id + ".out")
        with out_path.open("w", encoding="utf-8") as f:
            f.write(json.dumps({"forecasts": [{"case": case_id, "price": guess}]}) + "\n")


if __name__ == "__main__":
    main()
