from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Iterable

import pandas as pd


YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"


def fetch_adjusted_close(symbol: str, start: str, end: str | None = None) -> pd.Series:
    """Fetch one adjusted-close series from Yahoo's public chart endpoint."""
    start_ts = int(pd.Timestamp(start, tz="UTC").timestamp())
    if end is None:
        end_ts = int(pd.Timestamp.now("UTC").timestamp())
    else:
        end_ts = int((pd.Timestamp(end, tz="UTC") + pd.Timedelta(days=1)).timestamp())

    query = urllib.parse.urlencode(
        {
            "period1": start_ts,
            "period2": end_ts,
            "interval": "1d",
            "events": "div,splits",
        }
    )
    request = urllib.request.Request(
        YAHOO_CHART_URL.format(symbol=symbol) + "?" + query,
        headers={"User-Agent": "Mozilla/5.0 (compatible; equity-research-lab/0.1)"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.load(response)

    chart = payload.get("chart", {})
    if chart.get("error"):
        raise RuntimeError(f"Yahoo returned an error for {symbol}: {chart['error']}")

    result = chart["result"][0]
    timestamps = result.get("timestamp") or []
    indicators = result.get("indicators", {})
    adjusted = indicators.get("adjclose", [{}])[0].get("adjclose")
    if not timestamps or adjusted is None:
        raise RuntimeError(f"No adjusted-close data returned for {symbol}")

    index = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert("America/New_York")
    index = index.normalize().tz_localize(None)
    series = pd.Series(adjusted, index=index, name=symbol, dtype="float64")
    series = series[~series.index.duplicated(keep="last")].dropna().sort_index()
    return series


def download_universe(
    tickers: Iterable[str],
    start: str,
    end: str | None,
    cache_path: str | Path,
    refresh: bool = False,
) -> pd.DataFrame:
    """Download and cache a wide adjusted-close matrix."""
    cache_path = Path(cache_path)
    if cache_path.exists() and not refresh:
        return pd.read_csv(cache_path, index_col=0, parse_dates=True).sort_index()

    series = []
    for index, ticker in enumerate(tickers):
        series.append(fetch_adjusted_close(ticker, start=start, end=end))
        if index < len(list(tickers)) - 1:
            time.sleep(0.2)

    prices = pd.concat(series, axis=1).sort_index()
    prices = prices.ffill(limit=5)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    prices.to_csv(cache_path, index_label="date")
    return prices


from dataclasses import dataclass

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def drawdown(equity: pd.Series) -> pd.Series:
    running_max = equity.cummax()
    return equity / running_max - 1.0


def max_drawdown(equity: pd.Series) -> float:
    if equity.empty:
        return float("nan")
    return float(drawdown(equity).min())


def annualized_return(returns: pd.Series, periods: int = TRADING_DAYS) -> float:
    returns = returns.dropna()
    if returns.empty:
        return float("nan")
    growth = float((1.0 + returns).prod())
    years = len(returns) / periods
    if years <= 0 or growth <= 0:
        return float("nan")
    return growth ** (1.0 / years) - 1.0


def annualized_volatility(returns: pd.Series, periods: int = TRADING_DAYS) -> float:
    returns = returns.dropna()
    if len(returns) < 2:
        return float("nan")
    return float(returns.std(ddof=1) * np.sqrt(periods))


def sharpe_ratio(returns: pd.Series, risk_free: pd.Series | None = None) -> float:
    aligned = pd.concat([returns.rename("returns"), risk_free.rename("rf")], axis=1).dropna() if risk_free is not None else returns.dropna().to_frame("returns")
    if risk_free is None:
        aligned["rf"] = 0.0
    excess = aligned["returns"] - aligned["rf"]
    if len(excess) < 2 or excess.std(ddof=1) == 0:
        return float("nan")
    return float(excess.mean() / excess.std(ddof=1) * np.sqrt(TRADING_DAYS))


def sortino_ratio(returns: pd.Series, risk_free: pd.Series | None = None) -> float:
    aligned = pd.concat([returns.rename("returns"), risk_free.rename("rf")], axis=1).dropna() if risk_free is not None else returns.dropna().to_frame("returns")
    if risk_free is None:
        aligned["rf"] = 0.0
    excess = aligned["returns"] - aligned["rf"]
    downside = excess[excess < 0]
    if len(downside) < 2 or downside.std(ddof=1) == 0:
        return float("nan")
    return float(excess.mean() / downside.std(ddof=1) * np.sqrt(TRADING_DAYS))


def calmar_ratio(returns: pd.Series, equity: pd.Series) -> float:
    mdd = abs(max_drawdown(equity))
    if mdd == 0:
        return float("nan")
    return annualized_return(returns) / mdd


def monthly_returns(returns: pd.Series) -> pd.Series:
    if not isinstance(returns.index, pd.DatetimeIndex):
        return pd.Series(dtype="float64")
    return (1.0 + returns).resample("ME").prod() - 1.0


def yearly_returns(returns: pd.Series) -> pd.Series:
    if not isinstance(returns.index, pd.DatetimeIndex):
        return pd.Series(dtype="float64")
    return (1.0 + returns).resample("YE").prod() - 1.0


@dataclass(frozen=True)
class Performance:
    cagr: float
    volatility: float
    sharpe: float
    sortino: float
    max_drawdown: float
    calmar: float
    cumulative_return: float
    hit_rate: float
    best_month: float
    worst_month: float


def performance_stats(returns: pd.Series, equity: pd.Series, risk_free: pd.Series | None = None) -> Performance:
    months = monthly_returns(returns)
    return Performance(
        cagr=annualized_return(returns),
        volatility=annualized_volatility(returns),
        sharpe=sharpe_ratio(returns, risk_free),
        sortino=sortino_ratio(returns, risk_free),
        max_drawdown=max_drawdown(equity),
        calmar=calmar_ratio(returns, equity),
        cumulative_return=float(equity.iloc[-1] - 1.0) if not equity.empty else float("nan"),
        hit_rate=float((months > 0).mean()) if not months.empty else float("nan"),
        best_month=float(months.max()) if not months.empty else float("nan"),
        worst_month=float(months.min()) if not months.empty else float("nan"),
    )


from dataclasses import dataclass
from typing import Any

import pandas as pd



@dataclass
class BacktestResult:
    returns: pd.Series
    equity: pd.Series
    benchmark_equity: pd.Series
    weights: pd.DataFrame
    rebalances: pd.DataFrame
    yearly_returns: pd.DataFrame
    risk_free: pd.Series
    config: dict[str, Any]


def _empty_weights(columns: pd.Index) -> pd.Series:
    return pd.Series(0.0, index=columns, dtype="float64")


def run_dual_momentum(prices: pd.DataFrame, config: dict[str, Any]) -> BacktestResult:
    """Run a close-to-close, long-only dual-momentum rotation backtest.

    The signal is computed at a month-end close. The new target is applied at
    the next trading day's close, so the earliest return affected by a signal
    is the following day.
    """
    prices = prices.sort_index().ffill(limit=5)
    rankable = [ticker for ticker in config["rankable_tickers"] if ticker in prices.columns]
    safe_asset = config["safe_asset"]
    if safe_asset not in prices.columns:
        raise ValueError(f"safe asset {safe_asset!r} is missing from the price matrix")

    daily_returns = prices.pct_change(fill_method=None)
    momentum = prices.div(prices.shift(int(config["lookback_days"]))).sub(1.0)
    trend = prices.gt(prices.rolling(int(config["trend_days"]), min_periods=int(config["trend_days"])).mean())

    start = pd.Timestamp(config["backtest_start"])
    month_ends = prices.resample("ME").last().index
    month_ends = [date for date in month_ends if date < prices.index.max()]

    target_weights = pd.DataFrame(0.0, index=prices.index, columns=prices.columns)
    previous = _empty_weights(prices.columns)
    logs: list[dict[str, Any]] = []

    for signal_date in month_ends:
        signal_dates = prices.index[prices.index <= signal_date]
        if signal_dates.empty:
            continue
        signal_date = signal_dates[-1]

        mom_row = momentum.loc[signal_date, rankable].dropna()
        trend_row = trend.loc[signal_date, rankable].reindex(rankable).fillna(False)
        eligible = mom_row[(mom_row > 0.0) & trend_row.astype(bool)].sort_values(ascending=False)
        selected = eligible.head(int(config["top_n"])).index.tolist()

        weights = _empty_weights(prices.columns)
        if selected:
            weights.loc[selected] = 1.0 / len(selected)
        remainder = 1.0 - float(weights.sum())
        if remainder > 1e-12:
            weights.loc[safe_asset] = remainder

        future_dates = prices.index[prices.index > signal_date]
        if future_dates.empty:
            continue
        execution_date = future_dates[0]

        previous_execution_dates = target_weights.index[(target_weights.sum(axis=1) > 0)]
        if previous_execution_dates.empty or execution_date >= start:
            target_weights.loc[execution_date, :] = weights

        turnover = float((weights - previous).abs().sum() * 0.5)
        cost = turnover * float(config["transaction_cost_bps"]) / 10_000.0
        previous = weights

        logs.append(
            {
                "signal_date": signal_date.date().isoformat(),
                "execution_date": execution_date.date().isoformat(),
                "selected": "|".join(selected),
                "safe_asset_weight": float(weights.loc[safe_asset]),
                "turnover": turnover,
                "transaction_cost": cost,
                "momentum": "|".join(f"{ticker}:{mom_row[ticker]:.6f}" for ticker in selected),
                "weights": "|".join(f"{ticker}:{weight:.6f}" for ticker, weight in weights.items() if weight > 0),
            }
        )

    # Hold each target between rebalance dates. A target recorded at the
    # execution close affects returns beginning on the following trading day.
    execution_mask = target_weights.sum(axis=1) > 0.0
    target_weights = target_weights.where(execution_mask).ffill().fillna(0.0)
    weights_for_returns = target_weights.shift(1).fillna(0.0)
    gross_returns = (weights_for_returns * daily_returns.fillna(0.0)).sum(axis=1)

    costs = pd.Series(
        [row["transaction_cost"] for row in logs],
        index=pd.to_datetime([row["execution_date"] for row in logs]),
        dtype="float64",
    )
    net_returns = gross_returns - costs.reindex(prices.index).fillna(0.0)

    active_index = net_returns.index[net_returns.index >= start]
    net_returns = net_returns.loc[active_index]
    equity = (1.0 + net_returns).cumprod()
    spy_returns = daily_returns["SPY"].reindex(net_returns.index).fillna(0.0)
    benchmark_equity = (1.0 + spy_returns).cumprod()
    risk_free = daily_returns[safe_asset].reindex(net_returns.index).fillna(0.0)

    yearly = pd.concat(
        {
            "Strategy": yearly_returns(net_returns),
            "SPY": yearly_returns(spy_returns),
        },
        axis=1,
    )
    rebalances = pd.DataFrame(logs)
    return BacktestResult(
        returns=net_returns,
        equity=equity,
        benchmark_equity=benchmark_equity,
        weights=weights_for_returns.loc[active_index],
        rebalances=rebalances,
        yearly_returns=yearly,
        risk_free=risk_free,
        config=config,
    )


def summarize(result: BacktestResult) -> dict[str, dict[str, float]]:
    """Return full-period and out-of-sample performance summaries."""
    config = result.config
    oos_start = pd.Timestamp(config["oos_start"])
    periods = {
        "full": result.returns.index,
        "in_sample": result.returns.index[result.returns.index < oos_start],
        "out_of_sample": result.returns.index[result.returns.index >= oos_start],
    }
    summary: dict[str, dict[str, float]] = {}
    for label, index in periods.items():
        if len(index) == 0:
            continue
        returns = result.returns.loc[index]
        equity = result.equity.loc[index]
        benchmark_returns = result.benchmark_equity.pct_change(fill_method=None).loc[index].fillna(0.0)
        benchmark_equity = result.benchmark_equity.loc[index]
        strategy_stats = performance_stats(returns, equity, result.risk_free.loc[index])
        benchmark_stats = performance_stats(benchmark_returns, benchmark_equity, result.risk_free.loc[index])
        summary[label] = {
            "strategy_cagr": strategy_stats.cagr,
            "strategy_volatility": strategy_stats.volatility,
            "strategy_sharpe": strategy_stats.sharpe,
            "strategy_sortino": strategy_stats.sortino,
            "strategy_max_drawdown": strategy_stats.max_drawdown,
            "strategy_calmar": strategy_stats.calmar,
            "strategy_cumulative_return": strategy_stats.cumulative_return,
            "strategy_monthly_hit_rate": strategy_stats.hit_rate,
            "strategy_best_month": strategy_stats.best_month,
            "strategy_worst_month": strategy_stats.worst_month,
            "spy_cagr": benchmark_stats.cagr,
            "spy_volatility": benchmark_stats.volatility,
            "spy_sharpe": benchmark_stats.sharpe,
            "spy_sortino": benchmark_stats.sortino,
            "spy_max_drawdown": benchmark_stats.max_drawdown,
            "spy_calmar": benchmark_stats.calmar,
            "spy_cumulative_return": benchmark_stats.cumulative_return,
            "spy_monthly_hit_rate": benchmark_stats.hit_rate,
            "observations": int(len(returns)),
        }
        summary[label]["cagr_excess_vs_spy"] = summary[label]["strategy_cagr"] - summary[label]["spy_cagr"]
        summary[label]["drawdown_improvement_vs_spy"] = summary[label]["strategy_max_drawdown"] - summary[label]["spy_max_drawdown"]
    return summary



def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the US ETF dual-momentum backtest.")
    parser.add_argument("--refresh-data", action="store_true")
    args = parser.parse_args()

    config = {
        "tickers": ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC", "BIL"],
        "rankable_tickers": ["SPY", "QQQ", "IWM", "EFA", "EEM", "TLT", "IEF", "GLD", "VNQ", "DBC"],
        "safe_asset": "BIL",
        "data_start": "2007-06-01",
        "backtest_start": "2008-07-01",
        "oos_start": "2018-01-01",
        "lookback_days": 63,
        "trend_days": 200,
        "top_n": 3,
        "transaction_cost_bps": 10,
    }
    here = Path(__file__).resolve().parent
    prices = download_universe(
        tickers=config["tickers"],
        start=config["data_start"],
        end=None,
        cache_path=here / "adjusted_close.csv",
        refresh=args.refresh_data,
    )
    result = run_dual_momentum(prices, config)
    summary = summarize(result)
    payload = {
        key: {name: (None if pd.isna(value) else value) for name, value in values.items()}
        for key, values in summary.items()
    }
    (here / "summary.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    result.returns.rename("strategy_return").to_frame().join(
        result.benchmark_equity.pct_change(fill_method=None).rename("spy_return")
    ).to_csv(here / "daily_returns.csv", index_label="date")
    result.yearly_returns.to_csv(here / "yearly_returns.csv", index_label="year")
    result.rebalances.to_csv(here / "rebalances.csv", index=False)
    full = summary["full"]
    oos = summary["out_of_sample"]
    print(f"Period: {result.returns.index[0].date()} to {result.returns.index[-1].date()}")
    print(f"Strategy CAGR: {full['strategy_cagr']:.2%} | SPY CAGR: {full['spy_cagr']:.2%}")
    print(f"Strategy Sharpe: {full['strategy_sharpe']:.2f} | SPY Sharpe: {full['spy_sharpe']:.2f}")
    print(f"Strategy max drawdown: {full['strategy_max_drawdown']:.2%} | SPY max drawdown: {full['spy_max_drawdown']:.2%}")
    print(f"OOS CAGR: {oos['strategy_cagr']:.2%} | OOS Sharpe: {oos['strategy_sharpe']:.2f}")


if __name__ == "__main__":
    main()
