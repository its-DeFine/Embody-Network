"""
Real portfolio optimization engine using modern portfolio theory
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from typing import Dict, List, Tuple, Optional
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PortfolioOptimizer:
    """Real portfolio optimization using Mean-Variance Optimization and other methods"""
    
    def __init__(self):
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
    async def optimize_portfolio(self, 
                               assets: List[Dict[str, any]], 
                               prices_history: Dict[str, List[float]],
                               method: str = "mean_variance",
                               constraints: Dict[str, any] = None) -> Dict[str, any]:
        """
        Optimize portfolio allocation using real calculations
        
        Args:
            assets: List of assets with current positions
            prices_history: Historical prices for each asset
            method: Optimization method (mean_variance, risk_parity, max_sharpe)
            constraints: Portfolio constraints
        """
        try:
            # Convert price history to returns
            returns_df = self._calculate_returns(prices_history)
            
            if returns_df.empty or len(returns_df.columns) < 2:
                raise ValueError("Insufficient data for optimization")
            
            # Calculate expected returns and covariance
            expected_returns = returns_df.mean() * 252  # Annualized
            cov_matrix = returns_df.cov() * 252  # Annualized
            
            # Get current weights
            total_value = sum(asset['usd_value'] for asset in assets)
            current_weights = np.array([asset['usd_value'] / total_value for asset in assets])
            symbols = [asset['symbol'] for asset in assets]
            
            # Optimize based on method
            if method == "mean_variance":
                optimal_weights = self._mean_variance_optimization(
                    expected_returns.values, 
                    cov_matrix.values, 
                    constraints
                )
            elif method == "risk_parity":
                optimal_weights = self._risk_parity_optimization(
                    cov_matrix.values,
                    constraints
                )
            elif method == "max_sharpe":
                optimal_weights = self._max_sharpe_optimization(
                    expected_returns.values,
                    cov_matrix.values,
                    constraints
                )
            else:
                raise ValueError(f"Unknown optimization method: {method}")
            
            # Calculate portfolio metrics
            portfolio_return = np.sum(optimal_weights * expected_returns.values)
            portfolio_volatility = np.sqrt(np.dot(optimal_weights.T, np.dot(cov_matrix.values, optimal_weights)))
            sharpe_ratio = (portfolio_return - self.risk_free_rate) / portfolio_volatility
            
            # Generate efficient frontier
            efficient_frontier = self._calculate_efficient_frontier(
                expected_returns.values,
                cov_matrix.values
            )
            
            # Calculate rebalancing trades
            trades = []
            for i, symbol in enumerate(symbols):
                current_weight = current_weights[i]
                optimal_weight = optimal_weights[i]
                weight_diff = optimal_weight - current_weight
                
                if abs(weight_diff) > 0.01:  # 1% threshold
                    trade_value = weight_diff * total_value
                    trades.append({
                        "symbol": symbol,
                        "action": "buy" if weight_diff > 0 else "sell",
                        "amount": abs(trade_value),
                        "weight_change": weight_diff
                    })
            
            return {
                "optimal_weights": {
                    symbols[i]: float(optimal_weights[i]) 
                    for i in range(len(symbols))
                },
                "current_weights": {
                    symbols[i]: float(current_weights[i]) 
                    for i in range(len(symbols))
                },
                "expected_return": float(portfolio_return),
                "expected_volatility": float(portfolio_volatility),
                "sharpe_ratio": float(sharpe_ratio),
                "efficient_frontier": efficient_frontier,
                "rebalancing_trades": trades,
                "optimization_method": method,
                "constraints_applied": constraints or {}
            }
            
        except Exception as e:
            logger.error(f"Portfolio optimization error: {e}")
            raise
    
    def _calculate_returns(self, prices_history: Dict[str, List[float]]) -> pd.DataFrame:
        """Calculate returns from price history"""
        df = pd.DataFrame(prices_history)
        returns = df.pct_change().dropna()
        return returns
    
    def _mean_variance_optimization(self, 
                                  expected_returns: np.ndarray,
                                  cov_matrix: np.ndarray,
                                  constraints: Dict = None) -> np.ndarray:
        """Mean-Variance Optimization (Markowitz)"""
        n_assets = len(expected_returns)
        
        # Default constraints
        if constraints is None:
            constraints = {}
        
        min_weight = constraints.get('min_weight', 0.0)
        max_weight = constraints.get('max_weight', 1.0)
        target_return = constraints.get('target_return', None)
        
        # Optimization constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]  # Sum to 1
        
        if target_return:
            cons.append({
                'type': 'eq',
                'fun': lambda x: np.sum(x * expected_returns) - target_return
            })
        
        # Bounds for each asset
        bounds = tuple((min_weight, max_weight) for _ in range(n_assets))
        
        # Initial guess (equal weights)
        x0 = np.array([1.0 / n_assets] * n_assets)
        
        # Objective: minimize portfolio variance
        def portfolio_variance(weights):
            return np.dot(weights.T, np.dot(cov_matrix, weights))
        
        # Optimize
        result = minimize(
            portfolio_variance,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'disp': False}
        )
        
        return result.x
    
    def _risk_parity_optimization(self,
                                cov_matrix: np.ndarray,
                                constraints: Dict = None) -> np.ndarray:
        """Risk Parity Optimization - Equal risk contribution"""
        n_assets = len(cov_matrix)
        
        # Risk parity objective
        def risk_parity_objective(weights):
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            marginal_contrib = np.dot(cov_matrix, weights) / portfolio_vol
            contrib = weights * marginal_contrib
            return np.sum((contrib - np.mean(contrib))**2)
        
        # Constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))
        x0 = np.array([1.0 / n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            risk_parity_objective,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'disp': False}
        )
        
        return result.x
    
    def _max_sharpe_optimization(self,
                               expected_returns: np.ndarray,
                               cov_matrix: np.ndarray,
                               constraints: Dict = None) -> np.ndarray:
        """Maximize Sharpe Ratio"""
        n_assets = len(expected_returns)
        
        # Negative Sharpe ratio (for minimization)
        def neg_sharpe_ratio(weights):
            portfolio_return = np.sum(weights * expected_returns)
            portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
            return -(portfolio_return - self.risk_free_rate) / portfolio_vol
        
        # Constraints
        cons = [{'type': 'eq', 'fun': lambda x: np.sum(x) - 1}]
        bounds = tuple((0.0, 1.0) for _ in range(n_assets))
        x0 = np.array([1.0 / n_assets] * n_assets)
        
        # Optimize
        result = minimize(
            neg_sharpe_ratio,
            x0,
            method='SLSQP',
            bounds=bounds,
            constraints=cons,
            options={'disp': False}
        )
        
        return result.x
    
    def _calculate_efficient_frontier(self,
                                    expected_returns: np.ndarray,
                                    cov_matrix: np.ndarray,
                                    n_points: int = 50) -> List[Dict[str, float]]:
        """Calculate efficient frontier points"""
        frontier = []
        
        # Get min and max possible returns
        min_return = expected_returns.min()
        max_return = expected_returns.max()
        
        # Generate target returns
        target_returns = np.linspace(min_return, max_return, n_points)
        
        for target_return in target_returns:
            try:
                # Optimize for each target return
                weights = self._mean_variance_optimization(
                    expected_returns,
                    cov_matrix,
                    {'target_return': target_return}
                )
                
                # Calculate metrics
                portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
                sharpe = (target_return - self.risk_free_rate) / portfolio_vol
                
                frontier.append({
                    'return': float(target_return),
                    'volatility': float(portfolio_vol),
                    'sharpe_ratio': float(sharpe)
                })
            except:
                continue
        
        return frontier
    
    async def analyze_portfolio_risk(self,
                                   positions: List[Dict[str, any]],
                                   market_data: Dict[str, any]) -> Dict[str, any]:
        """Analyze portfolio risk metrics"""
        try:
            # Calculate portfolio metrics
            total_value = sum(pos['usd_value'] for pos in positions)
            weights = np.array([pos['usd_value'] / total_value for pos in positions])
            
            # Get returns data
            returns_data = {}
            for pos in positions:
                symbol = pos['symbol']
                if symbol in market_data:
                    prices = market_data[symbol]['prices']
                    returns = np.diff(prices) / prices[:-1]
                    returns_data[symbol] = returns
            
            returns_df = pd.DataFrame(returns_data)
            
            # Calculate risk metrics
            portfolio_returns = returns_df.dot(weights)
            
            # Value at Risk (95% confidence)
            var_95 = np.percentile(portfolio_returns, 5)
            
            # Conditional VaR (Expected Shortfall)
            cvar_95 = portfolio_returns[portfolio_returns <= var_95].mean()
            
            # Maximum Drawdown
            cumulative_returns = (1 + portfolio_returns).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdowns = (cumulative_returns - running_max) / running_max
            max_drawdown = drawdowns.min()
            
            # Beta calculation (vs market proxy - assume first asset is market)
            if len(returns_df.columns) > 0:
                market_returns = returns_df.iloc[:, 0]
                covariance = np.cov(portfolio_returns, market_returns)[0, 1]
                market_variance = np.var(market_returns)
                beta = covariance / market_variance if market_variance > 0 else 1.0
            else:
                beta = 1.0
            
            # Sortino Ratio (downside deviation)
            downside_returns = portfolio_returns[portfolio_returns < 0]
            downside_deviation = np.std(downside_returns) * np.sqrt(252)
            expected_return = portfolio_returns.mean() * 252
            sortino_ratio = (expected_return - self.risk_free_rate) / downside_deviation
            
            return {
                "total_portfolio_value": float(total_value),
                "var_95": float(var_95),
                "cvar_95": float(cvar_95),
                "max_drawdown": float(max_drawdown),
                "beta": float(beta),
                "sortino_ratio": float(sortino_ratio),
                "portfolio_volatility": float(portfolio_returns.std() * np.sqrt(252)),
                "expected_annual_return": float(expected_return),
                "risk_adjusted_return": float(expected_return / (portfolio_returns.std() * np.sqrt(252)))
            }
            
        except Exception as e:
            logger.error(f"Risk analysis error: {e}")
            raise
    
    def calculate_correlation_matrix(self, returns_data: Dict[str, List[float]]) -> pd.DataFrame:
        """Calculate correlation matrix for assets"""
        df = pd.DataFrame(returns_data)
        return df.corr()
    
    def suggest_diversification(self, 
                              current_positions: List[Dict[str, any]],
                              available_assets: List[str],
                              correlation_threshold: float = 0.7) -> List[Dict[str, any]]:
        """Suggest assets for better diversification"""
        suggestions = []
        
        # This would analyze correlations and suggest uncorrelated assets
        # For now, return top uncorrelated assets
        
        return suggestions