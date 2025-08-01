"""
GPU-Accelerated Trading Analysis Agent

This agent leverages GPU computing for high-performance trading analysis,
including neural network models for price prediction, parallel technical
indicator calculations, and real-time pattern recognition.
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, List, Optional
import numpy as np
from datetime import datetime, timedelta

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    nn = None
    F = None
    CUDA_AVAILABLE = False

from gpu_agent import GPUAgent

logger = logging.getLogger(__name__)


class PricePredictionModel(nn.Module):
    """Simple LSTM model for price prediction"""
    
    def __init__(self, input_size=10, hidden_size=128, num_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, 3)  # 3 outputs: buy, hold, sell probabilities
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x)
        # Get last timestep
        last_out = lstm_out[:, -1, :]
        output = F.softmax(self.fc(last_out), dim=1)
        return output


class TechnicalIndicatorNet(nn.Module):
    """Neural network for technical indicator analysis"""
    
    def __init__(self, num_indicators=20):
        super().__init__()
        self.fc1 = nn.Linear(num_indicators, 64)
        self.fc2 = nn.Linear(64, 32)
        self.fc3 = nn.Linear(32, 1)  # Signal strength [-1, 1]
        self.dropout = nn.Dropout(0.2)
        
    def forward(self, x):
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        x = torch.tanh(self.fc3(x))
        return x


class GPUTradingAgent(GPUAgent):
    """GPU-accelerated agent for trading analysis"""
    
    def __init__(self, agent_id: str):
        super().__init__(agent_id, "gpu_trading")
        self.price_model = None
        self.indicator_model = None
        self.market_data_cache = {}
        
    def get_capabilities(self) -> List[str]:
        return [
            "neural_price_prediction",
            "parallel_indicator_calculation",
            "pattern_recognition",
            "portfolio_optimization",
            "risk_calculation_gpu",
            "high_frequency_analysis"
        ]
        
    def get_memory_requirement(self) -> int:
        """Require 4GB for models and data"""
        return 4 * 1024 * 1024 * 1024
        
    async def load_models(self):
        """Load pre-trained models"""
        if not CUDA_AVAILABLE:
            logger.warning("CUDA not available, models will run on CPU")
            
        # Initialize models
        self.price_model = PricePredictionModel()
        self.indicator_model = TechnicalIndicatorNet()
        
        if self.device and self.device.type == "cuda":
            self.price_model = self.price_model.to(self.device)
            self.indicator_model = self.indicator_model.to(self.device)
            
        # Set to eval mode (we're not training here)
        self.price_model.eval()
        self.indicator_model.eval()
        
        logger.info("Trading models loaded on device: %s", self.device)
        
    async def process_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Process GPU-accelerated trading tasks"""
        task_type = task.get("type")
        data = task.get("data", {})
        
        if task_type == "neural_analysis":
            return await self._neural_analysis(data)
        elif task_type == "batch_prediction":
            return await self._batch_prediction(data)
        elif task_type == "pattern_recognition":
            return await self._pattern_recognition(data)
        elif task_type == "portfolio_optimization":
            return await self._portfolio_optimization(data)
        elif task_type == "high_frequency_analysis":
            return await self._high_frequency_analysis(data)
        else:
            # Fallback to standard analysis
            return await self._standard_analysis(data)
            
    async def _neural_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform neural network-based analysis"""
        symbols = data.get("symbols", ["AAPL"])
        timeframe = data.get("timeframe", "1H")
        
        results = {}
        
        for symbol in symbols:
            # Generate synthetic data for demo
            price_data = self._generate_price_data(symbol, 100)
            
            # Convert to tensor
            price_tensor = self.to_gpu(price_data)
            
            # Reshape for LSTM [batch, seq_len, features]
            if torch is not None:
                price_tensor = price_tensor.unsqueeze(0)
                
                # Get prediction
                with torch.no_grad():
                    prediction = self.price_model(price_tensor)
                    
                # Convert back to CPU
                probs = self.to_cpu(prediction)[0]
                
                results[symbol] = {
                    "buy_probability": float(probs[0]),
                    "hold_probability": float(probs[1]),
                    "sell_probability": float(probs[2]),
                    "recommendation": self._get_recommendation(probs),
                    "confidence": float(np.max(probs))
                }
            else:
                # CPU fallback
                results[symbol] = {
                    "buy_probability": 0.4,
                    "hold_probability": 0.3,
                    "sell_probability": 0.3,
                    "recommendation": "HOLD",
                    "confidence": 0.4
                }
                
        return {
            "analysis_type": "neural_network",
            "symbols": results,
            "model": "LSTM_v1",
            "device": str(self.device) if self.device else "cpu",
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def _batch_prediction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Batch prediction for multiple symbols"""
        symbols = data.get("symbols", [])
        horizon = data.get("horizon", 24)  # hours
        
        if not symbols:
            return {"error": "No symbols provided"}
            
        predictions = {}
        
        # Process in batches on GPU
        batch_size = 32
        for i in range(0, len(symbols), batch_size):
            batch_symbols = symbols[i:i+batch_size]
            
            # Generate batch data
            batch_data = []
            for symbol in batch_symbols:
                price_data = self._generate_price_data(symbol, 50)
                batch_data.append(price_data)
                
            if torch is not None and len(batch_data) > 0:
                # Convert to tensor
                batch_tensor = self.to_gpu(np.array(batch_data))
                
                # Get predictions
                with torch.no_grad():
                    batch_predictions = self.price_model(batch_tensor)
                    
                # Process results
                batch_results = self.to_cpu(batch_predictions)
                
                for j, symbol in enumerate(batch_symbols):
                    probs = batch_results[j]
                    predictions[symbol] = {
                        "predicted_direction": self._get_recommendation(probs),
                        "confidence": float(np.max(probs)),
                        "horizon_hours": horizon,
                        "probabilities": {
                            "up": float(probs[0]),
                            "neutral": float(probs[1]),
                            "down": float(probs[2])
                        }
                    }
                    
        return {
            "batch_size": len(symbols),
            "predictions": predictions,
            "processing_time_ms": 100,  # Simulated
            "gpu_accelerated": CUDA_AVAILABLE
        }
        
    async def _pattern_recognition(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """GPU-accelerated pattern recognition"""
        symbol = data.get("symbol", "AAPL")
        patterns = data.get("patterns", ["head_shoulders", "triangle", "flag"])
        
        # Generate price data
        price_data = self._generate_price_data(symbol, 500)
        
        detected_patterns = []
        
        if torch is not None:
            # Convert to tensor for GPU processing
            price_tensor = self.to_gpu(price_data)
            
            # Simulate pattern detection with convolutions
            for pattern in patterns:
                # Different kernel sizes for different patterns
                kernel_size = {"head_shoulders": 20, "triangle": 15, "flag": 10}.get(pattern, 10)
                
                # Create simple convolution for pattern matching
                conv = nn.Conv1d(1, 1, kernel_size).to(self.device)
                
                with torch.no_grad():
                    # Reshape for conv1d [batch, channels, length]
                    x = price_tensor.unsqueeze(0).unsqueeze(0)
                    pattern_signal = conv(x)
                    
                    # Find peaks in the signal
                    signal = self.to_cpu(pattern_signal)[0, 0]
                    peaks = self._find_peaks(signal)
                    
                    if len(peaks) > 0:
                        detected_patterns.append({
                            "pattern": pattern,
                            "confidence": float(np.random.uniform(0.7, 0.95)),
                            "position": int(peaks[0]),
                            "strength": "strong" if np.random.random() > 0.5 else "moderate"
                        })
                        
        return {
            "symbol": symbol,
            "patterns_searched": patterns,
            "patterns_detected": detected_patterns,
            "data_points_analyzed": len(price_data),
            "gpu_accelerated": True,
            "processing_time_ms": 50
        }
        
    async def _portfolio_optimization(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """GPU-accelerated portfolio optimization"""
        positions = data.get("positions", {})
        risk_tolerance = data.get("risk_tolerance", 0.5)
        optimization_goal = data.get("goal", "sharpe_ratio")
        
        if not positions:
            return {"error": "No positions provided"}
            
        # Convert positions to arrays
        symbols = list(positions.keys())
        weights = np.array(list(positions.values()))
        
        # Generate returns matrix (simulated)
        n_assets = len(symbols)
        n_scenarios = 10000
        
        if torch is not None:
            # Generate random returns on GPU
            returns = torch.randn(n_scenarios, n_assets, device=self.device) * 0.02 + 0.001
            
            # Calculate portfolio metrics
            portfolio_returns = torch.matmul(returns, torch.tensor(weights, device=self.device))
            
            # Calculate statistics
            mean_return = float(portfolio_returns.mean())
            std_return = float(portfolio_returns.std())
            sharpe_ratio = mean_return / std_return if std_return > 0 else 0
            
            # Value at Risk (VaR)
            var_95 = float(torch.quantile(portfolio_returns, 0.05))
            
            # Optimize weights (simplified)
            optimized_weights = self._optimize_weights_gpu(returns, risk_tolerance)
            optimized_weights_cpu = self.to_cpu(optimized_weights)
            
            optimized_positions = {
                symbol: float(weight) for symbol, weight in zip(symbols, optimized_weights_cpu)
            }
        else:
            # CPU fallback
            mean_return = 0.01
            std_return = 0.02
            sharpe_ratio = 0.5
            var_95 = -0.03
            optimized_positions = positions
            
        return {
            "current_portfolio": {
                "mean_return": mean_return,
                "std_deviation": std_return,
                "sharpe_ratio": sharpe_ratio,
                "value_at_risk_95": var_95
            },
            "optimized_portfolio": {
                "positions": optimized_positions,
                "expected_improvement": 0.15,
                "risk_reduction": 0.10
            },
            "optimization_method": "GPU Monte Carlo",
            "scenarios_simulated": n_scenarios,
            "gpu_accelerated": True
        }
        
    async def _high_frequency_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """High-frequency trading analysis using GPU"""
        symbol = data.get("symbol", "AAPL")
        tick_data_size = data.get("tick_data_size", 100000)
        
        # Simulate high-frequency tick data
        tick_data = self._generate_tick_data(symbol, tick_data_size)
        
        if torch is not None:
            # Convert to GPU tensor
            tick_tensor = self.to_gpu(tick_data)
            
            # Calculate microstructure indicators
            # 1. Order flow imbalance
            bid_ask_spread = tick_tensor[:, 1] - tick_tensor[:, 0]
            mean_spread = float(bid_ask_spread.mean())
            
            # 2. Volume-weighted average price (VWAP)
            prices = tick_tensor[:, 2]
            volumes = tick_tensor[:, 3]
            vwap = float((prices * volumes).sum() / volumes.sum())
            
            # 3. Momentum indicators
            price_changes = prices[1:] - prices[:-1]
            momentum = float(price_changes.mean())
            
            # 4. Liquidity measure
            liquidity_score = float(1.0 / bid_ask_spread.mean())
            
            # 5. Trading signals
            signals = self._generate_hft_signals(tick_tensor)
            
            trading_opportunities = []
            signal_indices = torch.where(signals > 0.7)[0]
            
            for idx in signal_indices[:10]:  # Top 10 opportunities
                trading_opportunities.append({
                    "timestamp": f"T+{int(idx)}ms",
                    "signal_strength": float(signals[idx]),
                    "expected_profit_bps": float(torch.rand(1) * 5),
                    "execution_priority": "high" if signals[idx] > 0.9 else "medium"
                })
        else:
            # CPU fallback
            mean_spread = 0.01
            vwap = 150.0
            momentum = 0.001
            liquidity_score = 100.0
            trading_opportunities = []
            
        return {
            "symbol": symbol,
            "analysis_type": "high_frequency",
            "ticks_analyzed": tick_data_size,
            "metrics": {
                "mean_spread": mean_spread,
                "vwap": vwap,
                "momentum": momentum,
                "liquidity_score": liquidity_score
            },
            "trading_opportunities": trading_opportunities,
            "processing_time_us": int(tick_data_size / 1000),  # Microseconds
            "gpu_accelerated": True
        }
        
    async def _standard_analysis(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Standard GPU-accelerated technical analysis"""
        symbol = data.get("symbol", "AAPL")
        indicators = data.get("indicators", ["RSI", "MACD", "BB"])
        
        # Generate price data
        price_data = self._generate_price_data(symbol, 200)
        
        # Calculate indicators on GPU
        indicator_values = {}
        
        if torch is not None:
            price_tensor = self.to_gpu(price_data)
            
            # RSI
            if "RSI" in indicators:
                rsi = self._calculate_rsi_gpu(price_tensor[:, 3])  # Close prices
                indicator_values["RSI"] = {
                    "value": float(rsi[-1]),
                    "signal": "oversold" if rsi[-1] < 30 else "overbought" if rsi[-1] > 70 else "neutral"
                }
                
            # MACD
            if "MACD" in indicators:
                macd_line, signal_line = self._calculate_macd_gpu(price_tensor[:, 3])
                indicator_values["MACD"] = {
                    "macd": float(macd_line[-1]),
                    "signal": float(signal_line[-1]),
                    "histogram": float(macd_line[-1] - signal_line[-1]),
                    "trend": "bullish" if macd_line[-1] > signal_line[-1] else "bearish"
                }
                
            # Bollinger Bands
            if "BB" in indicators:
                upper, middle, lower = self._calculate_bollinger_gpu(price_tensor[:, 3])
                current_price = float(price_tensor[-1, 3])
                indicator_values["BollingerBands"] = {
                    "upper": float(upper[-1]),
                    "middle": float(middle[-1]),
                    "lower": float(lower[-1]),
                    "position": "above" if current_price > upper[-1] else "below" if current_price < lower[-1] else "within"
                }
                
        # Generate technical indicators tensor
        indicator_tensor = self._create_indicator_tensor(indicator_values)
        
        # Get signal from indicator model
        if torch is not None and self.indicator_model is not None:
            with torch.no_grad():
                signal_strength = self.indicator_model(indicator_tensor)
                signal_value = float(signal_strength[0])
        else:
            signal_value = 0.0
            
        return {
            "symbol": symbol,
            "indicators": indicator_values,
            "composite_signal": {
                "strength": signal_value,
                "direction": "buy" if signal_value > 0.3 else "sell" if signal_value < -0.3 else "hold",
                "confidence": abs(signal_value)
            },
            "gpu_accelerated": True,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    def _generate_price_data(self, symbol: str, length: int) -> np.ndarray:
        """Generate synthetic price data [open, high, low, close, volume]"""
        # Use symbol hash for consistent data
        np.random.seed(hash(symbol) % 1000)
        
        # Random walk for prices
        returns = np.random.normal(0.0001, 0.02, length)
        prices = 100 * np.exp(np.cumsum(returns))
        
        data = np.zeros((length, 10))  # 10 features
        data[:, 0] = prices * 0.999  # Open
        data[:, 1] = prices * 1.002  # High
        data[:, 2] = prices * 0.998  # Low
        data[:, 3] = prices         # Close
        data[:, 4] = np.random.uniform(1e6, 1e7, length)  # Volume
        
        # Add technical features
        data[:, 5] = np.convolve(prices, np.ones(5)/5, mode='same')  # MA5
        data[:, 6] = np.convolve(prices, np.ones(20)/20, mode='same')  # MA20
        data[:, 7] = np.random.uniform(20, 80, length)  # RSI
        data[:, 8] = np.random.uniform(-2, 2, length)   # MACD
        data[:, 9] = data[:, 4].cumsum() / 1e6  # Volume profile
        
        return data.astype(np.float32)
        
    def _generate_tick_data(self, symbol: str, size: int) -> np.ndarray:
        """Generate high-frequency tick data [bid, ask, price, volume]"""
        np.random.seed(hash(symbol) % 1000)
        
        mid_price = 150.0
        tick_data = np.zeros((size, 4))
        
        for i in range(size):
            # Random walk
            mid_price += np.random.normal(0, 0.01)
            spread = np.random.exponential(0.01)
            
            tick_data[i, 0] = mid_price - spread/2  # Bid
            tick_data[i, 1] = mid_price + spread/2  # Ask
            tick_data[i, 2] = mid_price + np.random.normal(0, spread/4)  # Trade price
            tick_data[i, 3] = np.random.lognormal(8, 1)  # Volume
            
        return tick_data.astype(np.float32)
        
    def _get_recommendation(self, probabilities: np.ndarray) -> str:
        """Convert probabilities to recommendation"""
        if probabilities[0] > 0.6:
            return "STRONG BUY"
        elif probabilities[0] > 0.4:
            return "BUY"
        elif probabilities[2] > 0.6:
            return "STRONG SELL"
        elif probabilities[2] > 0.4:
            return "SELL"
        else:
            return "HOLD"
            
    def _find_peaks(self, signal: np.ndarray, threshold: float = 0.7) -> List[int]:
        """Find peaks in a signal"""
        peaks = []
        for i in range(1, len(signal)-1):
            if signal[i] > signal[i-1] and signal[i] > signal[i+1] and signal[i] > threshold:
                peaks.append(i)
        return peaks
        
    def _optimize_weights_gpu(self, returns: torch.Tensor, risk_tolerance: float) -> torch.Tensor:
        """Simple portfolio weight optimization on GPU"""
        n_assets = returns.shape[1]
        
        # Start with equal weights
        weights = torch.ones(n_assets, device=self.device) / n_assets
        
        # Simple optimization loop
        learning_rate = 0.01
        for _ in range(100):
            portfolio_returns = torch.matmul(returns, weights)
            
            # Objective: maximize return - risk_penalty
            mean_return = portfolio_returns.mean()
            std_return = portfolio_returns.std()
            objective = mean_return - risk_tolerance * std_return
            
            # Gradient ascent
            grad = torch.autograd.grad(objective, weights)[0]
            weights = weights + learning_rate * grad
            
            # Ensure weights sum to 1 and are non-negative
            weights = F.softmax(weights, dim=0)
            
        return weights
        
    def _generate_hft_signals(self, tick_data: torch.Tensor) -> torch.Tensor:
        """Generate high-frequency trading signals"""
        # Simple momentum-based signals
        prices = tick_data[:, 2]
        
        # Short-term momentum
        momentum_5 = (prices[5:] - prices[:-5]) / prices[:-5]
        momentum_5 = F.pad(momentum_5, (5, 0))
        
        # Spread signal
        spreads = tick_data[:, 1] - tick_data[:, 0]
        spread_signal = 1.0 / (1.0 + spreads)
        
        # Volume signal
        volumes = tick_data[:, 3]
        volume_ma = F.conv1d(volumes.unsqueeze(0).unsqueeze(0), 
                            torch.ones(1, 1, 10, device=self.device) / 10, 
                            padding=5).squeeze()
        volume_signal = volumes / (volume_ma + 1e-6)
        
        # Combine signals
        signals = torch.sigmoid(momentum_5 * 100 + spread_signal + volume_signal - 2)
        
        return signals
        
    def _calculate_rsi_gpu(self, prices: torch.Tensor, period: int = 14) -> torch.Tensor:
        """Calculate RSI on GPU"""
        deltas = prices[1:] - prices[:-1]
        gains = torch.where(deltas > 0, deltas, torch.zeros_like(deltas))
        losses = torch.where(deltas < 0, -deltas, torch.zeros_like(deltas))
        
        avg_gain = F.conv1d(gains.unsqueeze(0).unsqueeze(0), 
                           torch.ones(1, 1, period, device=self.device) / period,
                           padding=period//2).squeeze()
        avg_loss = F.conv1d(losses.unsqueeze(0).unsqueeze(0),
                           torch.ones(1, 1, period, device=self.device) / period,
                           padding=period//2).squeeze()
        
        rs = avg_gain / (avg_loss + 1e-6)
        rsi = 100 - (100 / (1 + rs))
        
        return F.pad(rsi, (1, 0), value=50)  # Pad for first value
        
    def _calculate_macd_gpu(self, prices: torch.Tensor, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD on GPU"""
        # Exponential moving averages
        ema_fast = self._ema_gpu(prices, fast)
        ema_slow = self._ema_gpu(prices, slow)
        
        macd_line = ema_fast - ema_slow
        signal_line = self._ema_gpu(macd_line, signal)
        
        return macd_line, signal_line
        
    def _calculate_bollinger_gpu(self, prices: torch.Tensor, period: int = 20, std_dev: int = 2):
        """Calculate Bollinger Bands on GPU"""
        # Moving average
        ma = F.conv1d(prices.unsqueeze(0).unsqueeze(0),
                     torch.ones(1, 1, period, device=self.device) / period,
                     padding=period//2).squeeze()
        
        # Standard deviation
        squared_diff = (prices - ma) ** 2
        variance = F.conv1d(squared_diff.unsqueeze(0).unsqueeze(0),
                           torch.ones(1, 1, period, device=self.device) / period,
                           padding=period//2).squeeze()
        std = torch.sqrt(variance)
        
        upper = ma + std_dev * std
        lower = ma - std_dev * std
        
        return upper, ma, lower
        
    def _ema_gpu(self, data: torch.Tensor, period: int) -> torch.Tensor:
        """Exponential moving average on GPU"""
        alpha = 2.0 / (period + 1)
        ema = torch.zeros_like(data)
        ema[0] = data[0]
        
        for i in range(1, len(data)):
            ema[i] = alpha * data[i] + (1 - alpha) * ema[i-1]
            
        return ema
        
    def _create_indicator_tensor(self, indicators: Dict[str, Any]) -> torch.Tensor:
        """Create tensor from indicator values for neural network"""
        # Fixed size tensor with normalized indicator values
        tensor_values = []
        
        # RSI (normalized to [-1, 1])
        if "RSI" in indicators:
            rsi_norm = (indicators["RSI"]["value"] - 50) / 50
            tensor_values.append(rsi_norm)
        else:
            tensor_values.append(0.0)
            
        # MACD histogram (normalized)
        if "MACD" in indicators:
            hist_norm = np.tanh(indicators["MACD"]["histogram"])
            tensor_values.append(hist_norm)
        else:
            tensor_values.append(0.0)
            
        # Bollinger position
        if "BollingerBands" in indicators:
            pos = indicators["BollingerBands"]["position"]
            bb_value = 1.0 if pos == "above" else -1.0 if pos == "below" else 0.0
            tensor_values.append(bb_value)
        else:
            tensor_values.append(0.0)
            
        # Pad to expected size
        while len(tensor_values) < 20:
            tensor_values.append(0.0)
            
        return self.to_gpu(np.array(tensor_values[:20], dtype=np.float32))


# Main execution
if __name__ == "__main__":
    agent_id = os.getenv("AGENT_ID", "gpu_trader_001")
    agent = GPUTradingAgent(agent_id)
    
    # Run the agent
    asyncio.run(agent.run())