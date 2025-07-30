"""
Technical analysis models for OpenBB Adapter
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class AnalysisRequest(BaseModel):
    """Request model for technical analysis"""
    symbol: str = Field(..., description="Stock/crypto symbol")
    indicators: List[str] = Field(..., description="List of technical indicators")
    period: Optional[int] = Field(default=14, description="Period for indicators")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "indicators": ["rsi", "macd", "sma", "ema", "bollinger"],
                "period": 14
            }
        }


class AnalysisResponse(BaseModel):
    """Response model for technical analysis"""
    symbol: str
    indicators: Dict[str, Any]
    timestamp: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "indicators": {
                    "rsi": {"value": 55.5, "signal": "neutral"},
                    "macd": {
                        "macd_line": 1.25,
                        "signal_line": 1.10,
                        "histogram": 0.15,
                        "signal": "bullish"
                    },
                    "sma": {"sma_20": 150.25, "sma_50": 148.75},
                    "ema": {"ema_20": 151.00, "ema_50": 149.50}
                },
                "timestamp": "2024-01-15T10:00:00Z"
            }
        }


class BacktestRequest(BaseModel):
    """Request model for backtesting"""
    symbol: str = Field(..., description="Stock/crypto symbol")
    strategy: str = Field(..., description="Strategy name")
    start_date: str = Field(..., description="Backtest start date")
    end_date: str = Field(..., description="Backtest end date")
    initial_capital: float = Field(default=10000.0, description="Initial capital")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "strategy": "ma_crossover",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31",
                "initial_capital": 10000.0,
                "parameters": {
                    "fast_ma": 20,
                    "slow_ma": 50
                }
            }
        }


class BacktestResponse(BaseModel):
    """Response model for backtesting results"""
    symbol: str
    strategy: str
    performance: Dict[str, float]
    trades: List[Dict[str, Any]]
    metrics: Dict[str, float]
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "strategy": "ma_crossover",
                "performance": {
                    "total_return": 0.15,
                    "annual_return": 0.15,
                    "sharpe_ratio": 1.25,
                    "max_drawdown": -0.08
                },
                "trades": [
                    {
                        "date": "2023-02-15",
                        "action": "buy",
                        "price": 145.50,
                        "shares": 68
                    }
                ],
                "metrics": {
                    "win_rate": 0.65,
                    "profit_factor": 1.8,
                    "avg_win": 250.0,
                    "avg_loss": -150.0
                }
            }
        }