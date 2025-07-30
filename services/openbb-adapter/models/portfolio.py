"""
Portfolio management models for OpenBB Adapter
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class Position(BaseModel):
    """Model for a portfolio position"""
    symbol: str = Field(..., description="Asset symbol")
    quantity: float = Field(..., description="Number of shares/units")
    cost_basis: float = Field(..., description="Average purchase price")
    current_price: Optional[float] = Field(None, description="Current market price")
    
    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "AAPL",
                "quantity": 100,
                "cost_basis": 145.50,
                "current_price": 150.25
            }
        }


class PortfolioRequest(BaseModel):
    """Request model for portfolio analysis"""
    positions: List[Position] = Field(..., description="List of portfolio positions")
    benchmark: Optional[str] = Field(default="SPY", description="Benchmark symbol")
    risk_free_rate: Optional[float] = Field(default=0.05, description="Risk-free rate")
    
    class Config:
        json_schema_extra = {
            "example": {
                "positions": [
                    {"symbol": "AAPL", "quantity": 100, "cost_basis": 145.50},
                    {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800.00},
                    {"symbol": "MSFT", "quantity": 75, "cost_basis": 380.00}
                ],
                "benchmark": "SPY",
                "risk_free_rate": 0.05
            }
        }


class PortfolioResponse(BaseModel):
    """Response model for portfolio analysis"""
    total_value: float
    total_cost: float
    total_return: float
    total_return_pct: float
    positions: List[Dict[str, Any]]
    metrics: Dict[str, float]
    risk_analysis: Dict[str, Any]
    diversification: Dict[str, Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_value": 50000.0,
                "total_cost": 45000.0,
                "total_return": 5000.0,
                "total_return_pct": 0.111,
                "positions": [
                    {
                        "symbol": "AAPL",
                        "quantity": 100,
                        "value": 15025.0,
                        "weight": 0.30,
                        "return": 475.0,
                        "return_pct": 0.0327
                    }
                ],
                "metrics": {
                    "sharpe_ratio": 1.25,
                    "sortino_ratio": 1.45,
                    "beta": 1.1,
                    "alpha": 0.02
                },
                "risk_analysis": {
                    "var_95": -2500.0,
                    "cvar_95": -3000.0,
                    "max_drawdown": -0.15,
                    "volatility": 0.18
                },
                "diversification": {
                    "sector_weights": {
                        "Technology": 0.60,
                        "Healthcare": 0.25,
                        "Finance": 0.15
                    },
                    "concentration_risk": "moderate"
                }
            }
        }


class OptimizationRequest(BaseModel):
    """Request model for portfolio optimization"""
    positions: List[Position] = Field(..., description="Current positions")
    objective: str = Field(default="sharpe", description="Optimization objective")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="Optimization constraints")
    
    class Config:
        json_schema_extra = {
            "example": {
                "positions": [
                    {"symbol": "AAPL", "quantity": 100, "cost_basis": 145.50},
                    {"symbol": "GOOGL", "quantity": 50, "cost_basis": 2800.00}
                ],
                "objective": "sharpe",
                "constraints": {
                    "min_weight": 0.05,
                    "max_weight": 0.40,
                    "target_return": 0.10
                }
            }
        }


class OptimizationResponse(BaseModel):
    """Response model for portfolio optimization"""
    optimal_weights: Dict[str, float]
    expected_return: float
    expected_risk: float
    sharpe_ratio: float
    recommendations: List[Dict[str, Any]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "optimal_weights": {
                    "AAPL": 0.25,
                    "GOOGL": 0.20,
                    "MSFT": 0.20,
                    "BRK.B": 0.15,
                    "JNJ": 0.10,
                    "JPM": 0.10
                },
                "expected_return": 0.12,
                "expected_risk": 0.15,
                "sharpe_ratio": 1.40,
                "recommendations": [
                    {
                        "action": "reduce",
                        "symbol": "AAPL",
                        "current_weight": 0.40,
                        "target_weight": 0.25,
                        "reason": "Over-concentrated position"
                    }
                ]
            }
        }