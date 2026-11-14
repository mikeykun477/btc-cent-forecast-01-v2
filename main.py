#!/usr/bin/env python3
"""BTC 4-hour-ahead price forecast for make.fun's btc-cent-forecast-01.

Contract: for every <id>.in found in $MAKEFUN_INPUT_DIR (default /input),
write <id>.out to $MAKEFUN_OUTPUT_DIR (default /output) holding
{"forecasts": [{"case": "<id>", "price": <number>}]}. One market per case,
one number per case. Deterministic, standard library only, no network,
milliseconds per case (limit 8 s).

The number is a conditional median, the MAE-optimal point forecast under
the cent-based absolute-error score. Four-hour BTC returns are close to a
martingale, so the forecast stays near the last close: persistence alone
scores 40,007 cents on 45 days of Binance BTCUSDT 1-minute closes (1,005
pseudo-cases, 72 h of history, +240 min target), while drift, mean
reversion, AR(1) and longer-window momentum all do worse. The single
robust exception is a small short-horizon continuation effect, so the
guess carries forward 22% of the last 5-minute log-move:

    guess = last * exp(0.22 * ln(last / close 5 minutes ago))

That scores 39,943 cents on the same 1,005 pseudo-cases (-0.16% against
persistence, better in both halves), 46,217 vs 47,055 on the five practice
cases with recoverable answers (p00-p04; house six-case baseline 44,522),
and 53,623 vs 54,020 on 16 hourly pseudo-cases from the practice tape.
The tilt is deliberately small: bigger coefficients, longer windows,
drift or reversion all lose on the 45-day sample. When the last five
minutes are flat - about 30% of minutes in this pool - the guess is
exactly the last close.
"""

import json
import math
import os
from pathlib import Path

# Tunables. 0.22 is the argmin of a fine 0.10-0.28 grid at a 5-minute
# window on the 45-day Binance sample (39,943 cents; 39,944 at 0.20;
# 40,007 persistence). It also wins both cross-checks over 0.20
# (practice 46,217 vs 46,293; hourly pseudo-cases 53,623 vs 53,659).
# The curve is flat across 0.18-0.28, so the scale stays conservative;
# the 5-minute window beat 10/15/20/30-minute windows at every scale,
# and a 6-minute window is worse (39,969 at 0.20).
MOMENTUM_WINDOW = 5
MOMENTUM_SCALE = 0.22

INPUT_DIR = os.environ.get("MAKEFUN_INPUT_DIR", "/input")
OUTPUT_DIR = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")

MIN_PRICE = 0.00001
MAX_PRICE = 9_999_999.99999


def clamp_price(value):
    """Round value onto the 5-decimal price grid, clamped to (0, 10M)."""
    return round(min(MAX_PRICE, max(MIN_PRICE, value)) * 1e5) / 1e5


def is_valid_price(value):
    """True when value is a positive finite number usable as a price."""
    return (
        isinstance(value, (int, float))
        and math.isfinite(value)
        and value > 0
    )


def tilted_price(last, base):
    """Last close tilted by a damped share of its recent log-move.

    A base that fails is_valid_price means "no usable history", so the
    tilt is skipped and the last close is returned unchanged.
    """
    if not is_valid_price(base):
        return last
    move = math.log(last / base)
    return last * math.exp(MOMENTUM_SCALE * move)


def extract_prices(case, case_name):
    """Pull the single market's price list out of a parsed case file.

    Raises ValueError naming the case when the shape is wrong, so a bad
    input fails loudly here instead of crashing deeper in the forecast.
    """
    if not isinstance(case, dict):
        raise ValueError("%s is not a JSON object" % case_name)
    markets = case.get("markets")
    if not isinstance(markets, list) or len(markets) != 1:
        raise ValueError("%s does not hold exactly one market" % case_name)
    market = markets[0]
    if (
        not isinstance(market, dict)
        or "prices" not in market
        or not isinstance(market["prices"], list)
    ):
        raise ValueError("%s market has no prices list" % case_name)
    return market["prices"]


def forecast(prices):
    """Median forecast of the price 240 minutes after the last close."""
    if not prices:
        raise ValueError("market has no prices")
    last = prices[-1]
    if not is_valid_price(last):
        raise ValueError("last price is not a positive finite number")
    if len(prices) > MOMENTUM_WINDOW:
        return clamp_price(tilted_price(last, prices[-1 - MOMENTUM_WINDOW]))
    return clamp_price(last)


def run_case(path):
    """Score one case file and write its <id>.out among the outputs."""
    case_id = path.name[: -len(".in")]
    with path.open("r", encoding="utf-8") as handle:
        case = json.load(handle)
    prices = extract_prices(case, case_id)
    guess = forecast(prices)
    out_path = Path(OUTPUT_DIR) / (case_id + ".out")
    with out_path.open("w", encoding="utf-8") as handle:
        handle.write(
            json.dumps({"forecasts": [{"case": case_id, "price": guess}]}) + "\n"
        )


def main():
    """Forecast every case in the input dir, writing one output per case."""
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(Path(INPUT_DIR).glob("*.in")):
        run_case(path)


if __name__ == "__main__":
    main()
