[![make.fun · btc-cent-forecast-01](https://make.fun/badge/btc-cent-forecast-01.svg)](https://make.fun/bounty/btc-cent-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=btc-cent-forecast-01)
[![rank](https://make.fun/badge/btc-cent-forecast-01/mikeykun477/btc-cent-forecast-01-v2/rank.svg)](https://make.fun/bounty/btc-cent-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-cent-forecast-01)
[![reward](https://make.fun/badge/btc-cent-forecast-01/mikeykun477/btc-cent-forecast-01-v2/reward.svg)](https://make.fun/bounty/btc-cent-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=btc-cent-forecast-01)

# BTC 4-hour-ahead forecaster

Entry for make.fun bounty `btc-cent-forecast-01`: forecast Bitcoin's
US-dollar price 240 minutes after each checkpoint, from the last 72 hours
of 1-minute closes. Scored on mean absolute error in cents; a prize needs
a score strictly below the house persistence baseline.

## Method

One number per case: the conditional median, which is the MAE-optimal
point forecast. Bitcoin's 4-hour returns are, to first order, a
martingale, so the forecast stays close to persistence (the last close)
and adds only one small, evidence-backed tilt:

```
guess = last * exp(0.22 * ln(last / close 5 minutes ago))
```

i.e. extrapolate 22% of the last 5-minute log-move. Everything else I
tested — drift, mean reversion to trailing means, AR(1) on returns,
long-window momentum — scores *worse* than persistence on 45 days of
Binance BTCUSDT 1-minute closes (1,005 pseudo-cases, 72 h of history
each, target +240 min): persistence 40,007 cents, this model 39,943
cents (−0.16%), better than persistence in both halves of the sample.
It also beats persistence on the kit's practice data: 46,217 vs 47,055
cents on the five cases whose answers are recoverable from the kit
itself (p00–p04; the house baseline over all six is 44,522 cents), and
53,623 vs 54,020 on 16 hourly pseudo-cases cut from the practice
recording. When the last 5 minutes did not move — common in this pool,
where ~30% of minutes are flat — the guess is exactly the last close.

## Run

```sh
mkdir -p out && MAKEFUN_INPUT_DIR=input MAKEFUN_OUTPUT_DIR=out python3 main.py
```

Reads every `<id>.in` in `$MAKEFUN_INPUT_DIR` (else `/input`) and writes
`<id>.out` to `$MAKEFUN_OUTPUT_DIR` (else `/output`):
`{"forecasts": [{"case": "<id>", "price": <number>}]}`.

Python 3.13, standard library only, no network. Deterministic (two runs
byte-identical) and runs in ~15 ms per case, far under the 8 s cap.

## License

MIT — see `LICENSE`.
