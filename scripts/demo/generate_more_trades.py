import sys
sys.path.append('/app')
from app.db_models import get_db, record_trade, record_portfolio_snapshot, update_position
import random
from datetime import datetime, timedelta

# Get database session
for db in get_db():
    print('Generating more recent trades...')
    
    symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'NVDA']
    
    # Generate 10 trades with timestamps in the last hour
    base_time = datetime.utcnow()
    
    for i in range(10):
        symbol = random.choice(symbols)
        side = random.choice(['buy', 'sell'])
        quantity = random.randint(5, 50)
        price = round(random.uniform(150, 250), 2)
        
        # Set trade time to be within the last hour
        trade_time = base_time - timedelta(minutes=random.randint(0, 60))
        
        trade_data = {
            'symbol': symbol,
            'side': side,
            'quantity': quantity,
            'price': price,
            'strategy': random.choice(['momentum', 'scalping', 'swing']),
            'agent_id': f'bot_{random.randint(1, 3)}',
            'reason': f'{side.upper()} signal - {random.choice(["RSI oversold", "MACD crossover", "Breakout detected", "Support bounce"])}'
        }
        
        # Record trade
        trade = record_trade(db, trade_data)
        # Manually update the timestamp
        trade.executed_at = trade_time
        db.commit()
        
        print(f'Trade {i+1}: {trade_time.strftime("%H:%M:%S")} - {symbol} {side} {quantity} @ ${price}')
    
    # Update position current prices (simulate market prices)
    from app.db_models import Position
    positions = db.query(Position).all()
    for pos in positions:
        # Simulate current price with some variance from average
        variance = random.uniform(-0.1, 0.1)  # +/- 10%
        pos.current_price = round(pos.average_price * (1 + variance), 2)
        pos.last_updated = datetime.utcnow()
    db.commit()
    
    # Record new snapshot
    snapshot = record_portfolio_snapshot(db)
    print(f'\nUpdated portfolio snapshot at {datetime.utcnow().strftime("%H:%M:%S")}')
    print(f'Total positions: {snapshot.num_positions}')
    
    break

print('\nMore trades generated successfully!')