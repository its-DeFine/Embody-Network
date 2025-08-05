#!/usr/bin/env python3
"""
Generate sample trades directly in the database
"""
import sys
sys.path.append('/home/geo/operation')

from app.db_models import get_db, record_trade, record_portfolio_snapshot
import random
import time

def generate_sample_trades():
    """Generate sample trades for demonstration"""
    
    # Get database session
    for db in get_db():
        print("Connected to database")
        
        symbols = ["AAPL", "GOOGL", "MSFT", "AMZN", "TSLA", "META", "NVDA"]
        
        # Generate 20 sample trades
        for i in range(20):
            symbol = random.choice(symbols)
            side = random.choice(["buy", "sell"])
            quantity = random.randint(10, 100)
            price = random.uniform(100, 500)
            
            trade_data = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': round(price, 2),
                'strategy': random.choice(['momentum', 'mean_reversion', 'breakout', 'scalping']),
                'agent_id': f'agent_{random.randint(1, 5)}',
                'reason': f'Technical signal - {side} opportunity detected'
            }
            
            trade = record_trade(db, trade_data)
            print(f"Trade {i+1}: {symbol} {side} {quantity} @ ${price:.2f}")
            
            # Small delay between trades
            time.sleep(0.1)
        
        # Record a portfolio snapshot
        snapshot = record_portfolio_snapshot(db)
        print(f"\nPortfolio snapshot recorded:")
        print(f"Total value: ${snapshot.total_value:,.2f}")
        print(f"Positions value: ${snapshot.positions_value:,.2f}")
        print(f"Number of positions: {snapshot.num_positions}")
        
        break  # Exit after first db session

if __name__ == "__main__":
    generate_sample_trades()
    print("\nSample trades generated successfully!")