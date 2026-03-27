import pandas as pd
import numpy as np
import riskfolio as rp
import quantstats as qs

class QuantEngine:
    @staticmethod
    def get_optimization_results(returns, risk_measure='MV'):
        port = rp.Portfolio(returns=returns)
        port.assets_stats(method_mu='hist', method_cov='hist')
        w_opt = port.optimization(model='Classic', rm=risk_measure, obj='Sharpe', rf=0, l=0)
        frontier = port.efficient_frontier(model='Classic', rm=risk_measure, points=20, rf=0)
        
        # Risk Contribution calculation
        weights = w_opt.values.flatten()
        cov = port.cov
        p_vol = np.sqrt(weights.T @ cov @ weights)
        marginal_contrib = (cov @ weights) / p_vol
        risk_contrib = weights * marginal_contrib
        rc_series = pd.Series(risk_contrib, index=w_opt.index)

        return {
            "weights": w_opt,
            "frontier": frontier,
            "risk_contrib": rc_series,
            "mu": port.mu,
            "cov": port.cov
        }

    @staticmethod
    def get_backtest_results(returns, weights):
        w_array = weights.values.flatten()
        port_rets = (returns * w_array).sum(axis=1)
        equity_curve = (1 + port_rets).cumprod() * 10000
        drawdown = qs.stats.to_drawdown_series(port_rets)
        
        metrics = {
            "Sharpe Ratio": round(qs.stats.sharpe(port_rets), 2),
            "Sortino Ratio": round(qs.stats.sortino(port_rets), 2),
            "Max Drawdown": f"{round(qs.stats.max_drawdown(port_rets) * 100, 2)}%",
            "Annual Volatility": f"{round(qs.stats.volatility(port_rets) * 100, 2)}%"
        }
        return equity_curve, drawdown, metrics