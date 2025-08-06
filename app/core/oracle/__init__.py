"""
Oracle Management Module

This module provides centralized oracle functionality for the trading system.
The manager acts as the central oracle for off-chain data while supporting
Chainlink oracles for on-chain data needs.
"""

from .oracle_manager import OracleManager, oracle_manager

__all__ = ["OracleManager", "oracle_manager"]