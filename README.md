# US Equity Momentum Lab

A reproducible, long-only US ETF dual-momentum research project. The repository contains the data downloader, signal logic, backtest engine, timing tests, transaction-cost assumptions and report generation code.

This is a research project, not investment advice.

## Strategy

- Ranking signal: 63-trading-day total return
- Trend filter: price above its 200-trading-day moving average
- Absolute filter: momentum must be positive
- Selection: top three eligible ETFs, equal weight
- Safe asset: unallocated capital is held in BIL
- Execution: month-end close signal, next trading-day close execution
- Costs: 10 basis points on one-way traded notional

The universe is SPY, QQQ, IWM, EFA, EEM, TLT, IEF, GLD, VNQ and DBC. BIL is used as the defensive asset.

## Results

Period: 2008-07-01 to 2026-09-16.

| Metric | Strategy | SPY buy & hold |
|---|---:|---:|
| CAGR | 10.0% | 12.2% |
| Annualized volatility | 14.8% | 19.7% |
| Sharpe ratio | 0.63 | 0.62 |
| Sortino ratio | 0.82 | 0.75 |
| Maximum drawdown | -30.8% | -47.2% |
| Calmar ratio | 0.33 | 0.26 |
| Monthly hit rate | 62.1% | 67.6% |

Out of sample from 2018-01-01 to 2026-09-16:

| Metric | Strategy | SPY |
|---|---:|---:|
| CAGR | 12.1% | 14.4% |
| Sharpe ratio | 0.67 | 0.67 |
| Maximum drawdown | -20.9% | -33.7% |

The objective is risk-adjusted improvement rather than beating SPY on raw return. The strategy gives up some upside while reducing drawdown and volatility.

## Research Controls

- Signals use only prices available at the month-end close.
- New target weights are applied at the next trading-day close.
- Returns begin on the following day, preventing execution-day information from leaking backward.
- Adjusted close captures distributions and corporate actions.
- A fixed 10 bps cost is charged against one-way turnover.
- No shorting, leverage, market making or intraday assumptions are used.
- A fixed sensitivity set is saved to results/parameter_sweep.csv.
- Automated tests verify that future price changes cannot alter historical allocations.

## Reproduce

Install requirements with: python -m pip install -r requirements.txt

Run the backtest with: python scripts/run_backtest.py --refresh-data

Run parameter checks with: python scripts/run_parameter_sweep.py

Run tests with: python -m unittest discover -s tests -v

Raw price data is excluded from version control. Re-running the downloader refreshes the dataset from Yahoo Finance.

## Limitations

- ETF prices do not model taxes, borrow costs, bid/ask spread, fund closures or capacity constraints.
- The strategy assumes monthly rebalancing can be executed at the next close without material market impact.
- In-sample model selection can still create selection bias even when the out-of-sample period is held back.
- Historical performance is not a forecast.

## License

MIT
