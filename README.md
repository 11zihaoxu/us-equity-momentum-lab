# US Equity Momentum Lab

A reproducible, long-only US ETF research project built around a dual-momentum rotation strategy. The repository contains the data downloader, signal logic, backtest engine, timing tests, transaction-cost assumptions and report generation code.

This is a research project, not investment advice and not a promise of live performance.

![Strategy report](results/01_report.png)

## Strategy

The primary configuration is a monthly long-only rotation across liquid US and global ETFs:

- **Ranking signal:** 63-trading-day total return
- **Trend filter:** price above its 200-trading-day moving average
- **Absolute filter:** momentum must be positive
- **Selection:** top three eligible ETFs, equal weight
- **Safe asset:** unallocated capital is held in BIL
- **Execution:** month-end close signal, next trading-day close execution
- **Costs:** 10 basis points on one-way traded notional

Universe:

`SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, VNQ, DBC` with `BIL` as the defensive asset.

## Results

The backtest runs from **2008-07-01 to 2026-09-16**, with data downloaded from Yahoo Finance adjusted-close history.

| Metric | Strategy | SPY buy & hold |
|---|---:|---:|
| CAGR | 10.0% | 12.2% |
| Annualized volatility | 14.8% | 19.7% |
| Sharpe ratio | 0.63 | 0.62 |
| Sortino ratio | 0.82 | 0.75 |
| Maximum drawdown | -30.8% | -47.2% |
| Calmar ratio | 0.33 | 0.26 |
| Monthly hit rate | 62.1% | 67.6% |

The primary objective is not to beat SPY on raw return. The strategy is designed to improve risk-adjusted behaviour and reduce drawdown. It gives up some upside while holding fewer assets and rotating into defensive exposure during unfavorable regimes.

### Out-of-sample split

The strategy was frozen before interpreting the out-of-sample period.

| Out-of-sample metric | Strategy | SPY |
|---|---:|---:|
| Period | 2018-01-01 to 2026-09-16 | 2018-01-01 to 2026-09-16 |
| CAGR | 12.1% | 14.4% |
| Sharpe ratio | 0.67 | 0.67 |
| Maximum drawdown | -20.9% | -33.7% |
| Monthly hit rate | 66.7% | 66.7% |

![Strategy logic](results/02_strategy.png)

![Robustness diagnostics](results/03_robustness.png)

## Research Controls

- Signals use only prices available at the month-end close.
- New target weights are applied at the next trading-day close.
- Returns begin on the following day, preventing execution-day information from leaking backward.
- Adjusted close captures distributions and corporate actions.
- A fixed 10 bps cost is charged against one-way turnover.
- No shorting, leverage, market making or intraday assumptions are used.
- A small pre-specified sensitivity set across momentum horizons and portfolio widths is saved to `results/parameter_sweep.csv`.
- Tests verify that future price changes cannot alter historical allocations.

## Project Structure

```text
configs/                  Strategy configuration
data/                     Local data cache (not committed)
docs/                     Methodology notes
results/                  Generated statistics, logs and report images
scripts/                  Data, backtest and robustness runners
src/equity_lab/           Core research package
tests/                    Timing and metric tests
```

## Reproduce

The project requires Python 3.10+, pandas, numpy and Pillow.

```bash
python -m pip install -r requirements.txt
python scripts/run_backtest.py --refresh-data
python scripts/run_parameter_sweep.py
python -m unittest discover -s tests -v
```

The raw price cache is written to `data/adjusted_close.csv` and is ignored by Git. Re-running the downloader refreshes the dataset from Yahoo Finance.

## Limitations

- ETF prices do not model taxes, borrow costs, bid/ask spread, fund closures or capacity constraints.
- The strategy assumes monthly rebalancing can be executed at the next close without material market impact.
- In-sample model selection can still create selection bias even when the out-of-sample period is held back.
- Historical performance is not a forecast.
- This project is for research and demonstration purposes.

## License

MIT
