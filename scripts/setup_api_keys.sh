#!/bin/bash

echo "=== Market Data API Key Setup Guide ==="
echo ""
echo "To get real market data for all symbols, you need FREE API keys."
echo "This will take about 5 minutes to set up."
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Option 1: TWELVE DATA (Recommended - 800 calls/day)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Go to: https://twelvedata.com/"
echo "2. Click 'START FOR FREE' button"
echo "3. Sign up with email (no credit card required)"
echo "4. Confirm your email"
echo "5. Go to: https://twelvedata.com/account/api-keys"
echo "6. Copy your API key"
echo ""
echo "Your Twelve Data API Key: "
read -p "Paste key here (or press Enter to skip): " TWELVE_KEY
echo ""

echo "📊 Option 2: FINNHUB (60 calls/minute)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Go to: https://finnhub.io/"
echo "2. Click 'Get free API key'"
echo "3. Sign up with email"
echo "4. API key shown immediately after signup"
echo ""
echo "Your Finnhub API Key: "
read -p "Paste key here (or press Enter to skip): " FINNHUB_KEY
echo ""

echo "📊 Option 3: ALPHA VANTAGE (5 calls/minute)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "1. Go to: https://www.alphavantage.co/support/#api-key"
echo "2. Fill the form (name, email, organization)"
echo "3. API key shown immediately"
echo ""
echo "Your Alpha Vantage API Key: "
read -p "Paste key here (or press Enter to skip): " ALPHA_KEY
echo ""

# Update the configuration file
if [ ! -z "$TWELVE_KEY" ] || [ ! -z "$FINNHUB_KEY" ] || [ ! -z "$ALPHA_KEY" ]; then
    echo "Updating API keys..."
    
    # Create a backup
    cp /home/geo/operation/app/market_data_providers.py /home/geo/operation/app/market_data_providers.py.bak
    
    # Update the keys
    if [ ! -z "$TWELVE_KEY" ]; then
        sed -i "s/\"twelvedata\": \"demo\"/\"twelvedata\": \"$TWELVE_KEY\"/" /home/geo/operation/app/market_data_providers.py
        echo "✅ Twelve Data key updated"
    fi
    
    if [ ! -z "$FINNHUB_KEY" ]; then
        sed -i "s/\"finnhub\": \"demo\"/\"finnhub\": \"$FINNHUB_KEY\"/" /home/geo/operation/app/market_data_providers.py
        echo "✅ Finnhub key updated"
    fi
    
    if [ ! -z "$ALPHA_KEY" ]; then
        # Also update .env for Alpha Vantage
        echo "ALPHA_VANTAGE_API_KEY=$ALPHA_KEY" >> /home/geo/operation/.env
        echo "✅ Alpha Vantage key updated"
    fi
    
    echo ""
    echo "🔄 Restarting services with new API keys..."
    docker-compose restart app
    
    sleep 5
    
    echo ""
    echo "✅ API keys configured successfully!"
    echo ""
    echo "Testing with real API keys..."
    
    # Test the APIs
    TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
      -H "Content-Type: application/json" \
      -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')
    
    echo ""
    echo "📊 Testing Market Data:"
    echo -n "AAPL: $"
    curl -s http://localhost:8000/api/v1/market/price/AAPL -H "Authorization: Bearer $TOKEN" | jq -r '.price'
    echo -n "MSFT: $"
    curl -s http://localhost:8000/api/v1/market/price/MSFT -H "Authorization: Bearer $TOKEN" | jq -r '.price'
    echo -n "GOOGL: $"
    curl -s http://localhost:8000/api/v1/market/price/GOOGL -H "Authorization: Bearer $TOKEN" | jq -r '.price'
    
else
    echo "No API keys provided. Using demo keys (limited functionality)."
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Next step: Run ./real_market_pnl_demo.sh to see real P&L tracking!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"