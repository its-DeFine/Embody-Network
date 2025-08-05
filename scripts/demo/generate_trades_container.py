import sys
sys.path.append('/app')
from app.db_models import get_db, record_trade, record_portfolio_snapshot
import random

# Get database session
for db in get_db():
    print('Connected to database')
    
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'AMZN', 'TSLA', 'META', 'NVDA']
    
    # Generate 15 sample trades
    for i in range(15):
        symbol = random.choice(symbols)
        side = random.choice(['buy', 'sell'])
        quantity = random.randint(10, 100)
        price = round(random.uniform(100, 300), 2)
        
        trade_data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'strategy': random.choice(['momentum', 'mean_reversion', 'breakout']),
            'agent_id': f'agent_{random.randint(1, 3)}',
            'reason': f'{side} signal - technical analysis'
        }
        
        trade = record_trade(db, trade_data)
        print(f'Trade {i+1}: {symbol} {side} {quantity} @ ${price}')
    
    # Record snapshot
    snapshot = record_portfolio_snapshot(db)
    print(f'\nPortfolio Summary:')
    print(f'Total value: ${snapshot.total_value:,.2f}')
    print(f'Cash: ${snapshot.cash_balance:,.2f}')
    print(f'Positions value: ${snapshot.positions_value:,.2f}')
    print(f'Active positions: {snapshot.num_positions}')
    break

print('\nTrades generated successfully!')