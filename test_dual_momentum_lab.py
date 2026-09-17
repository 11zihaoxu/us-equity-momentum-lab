from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dual_momentum_lab import max_drawdown, performance_stats, run_dual_momentum  # noqa: E402


class BacktestTimingTests(unittest.TestCase):
    def setUp(self):
        index = pd.bdate_range("2019-01-01", periods=800)
        base = np.linspace(100.0, 180.0, len(index))
        self.prices = pd.DataFrame(
            {
                "SPY": base,
                "QQQ": base * 1.2,
                "IWM": base * 0.9,
                "BIL": np.linspace(100.0, 110.0, len(index)),
            },
            index=index,
        )
        self.config = {
            "rankable_tickers": ["SPY", "QQQ", "IWM"],
            "safe_asset": "BIL",
            "backtest_start": "2019-01-01",
            "oos_start": "2021-01-01",
            "lookback_days": 20,
            "trend_days": 50,
            "top_n": 2,
            "transaction_cost_bps": 10,
        }

    def test_execution_weights_lag_the_signal(self):
        result = run_dual_momentum(self.prices, self.config)
        execution_dates = pd.to_datetime(result.rebalances["execution_date"])
        active_rebalances = result.rebalances.loc[execution_dates >= pd.Timestamp(self.config["backtest_start"])]
        first_execution = pd.Timestamp(active_rebalances.iloc[0]["execution_date"])
        self.assertTrue(np.allclose(result.weights.loc[first_execution].values, 0.0))
        later = result.weights.loc[result.weights.index > first_execution]
        self.assertTrue(np.allclose(later.sum(axis=1).values, 1.0))

    def test_returns_do_not_use_execution_day_information(self):
        changed = self.prices.copy()
        changed.loc[changed.index > "2020-06-01", "QQQ"] *= 1.5
        first = run_dual_momentum(self.prices, self.config)
        second = run_dual_momentum(changed, self.config)
        left = first.weights.loc[:"2020-06-01"]
        right = second.weights.loc[:"2020-06-01"]
        pd.testing.assert_frame_equal(left, right, check_exact=False, atol=1e-12)


class MetricTests(unittest.TestCase):
    def test_max_drawdown(self):
        equity = pd.Series([1.0, 1.2, 0.9, 1.1])
        self.assertAlmostEqual(max_drawdown(equity), -0.25)

    def test_performance_stats_are_finite(self):
        returns = pd.Series([0.01, -0.005, 0.002, 0.003])
        equity = (1.0 + returns).cumprod()
        stats = performance_stats(returns, equity)
        self.assertTrue(np.isfinite(stats.cagr))
        self.assertTrue(np.isfinite(stats.sharpe))
        self.assertTrue(np.isfinite(stats.max_drawdown))


if __name__ == "__main__":
    unittest.main()

