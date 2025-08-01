#!/bin/bash

echo "=== Configure Free Market Data API Keys ==="
echo ""
echo "Get your FREE API keys from:"
echo "1. TwelveData (800 calls/day): https://twelvedata.com/apikey"
echo "2. Finnhub (60 calls/min): https://finnhub.io/register"
echo "3. MarketStack (1000/month): https://marketstack.com/signup/free"
echo "4. Polygon.io (5 calls/min): https://polygon.io/"
echo ""
echo "Once you have the keys, update them in:"
echo "/home/geo/operation/app/market_data_providers.py"
echo ""
echo "Current configuration:"
echo ""

grep -A 5 "FREE_API_KEYS" /home/geo/operation/app/market_data_providers.py

echo ""
echo "To update, edit the file and replace 'demo' with your actual keys."
echo "The system will work with demo keys but may have limitations."