#!/bin/bash
# Consolidated API configuration script
# Combines functionality from configure_market_apis.sh and setup_api_keys.sh

set -e

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration files
MARKET_DATA_FILE="/home/geo/operation/app/market_data_providers.py"
ENV_FILE="/home/geo/operation/.env"

echo "=== Market Data API Configuration ==="
echo ""

# Show current configuration
show_current_config() {
    echo -e "${BLUE}Current API Configuration:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    if [ -f "$MARKET_DATA_FILE" ]; then
        grep -A 10 "FREE_API_KEYS" "$MARKET_DATA_FILE" | head -15 || echo "Configuration file not found"
    else
        echo -e "${RED}Configuration file not found at $MARKET_DATA_FILE${NC}"
    fi
    echo ""
}

# Interactive setup mode
interactive_setup() {
    echo -e "${GREEN}Interactive API Key Setup${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "Get your FREE API keys from these providers:"
    echo ""
    
    # TwelveData setup
    echo -e "${BLUE}📊 Option 1: TWELVE DATA (Recommended - 800 calls/day)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Go to: https://twelvedata.com/"
    echo "2. Click 'START FOR FREE' button"
    echo "3. Sign up with email (no credit card required)"
    echo "4. Confirm your email"
    echo "5. Go to: https://twelvedata.com/account/api-keys"
    echo "6. Copy your API key"
    echo ""
    read -p "Paste your Twelve Data API Key (or press Enter to skip): " TWELVE_KEY
    echo ""
    
    # Finnhub setup
    echo -e "${BLUE}📊 Option 2: FINNHUB (60 calls/minute)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Go to: https://finnhub.io/"
    echo "2. Click 'Get free API key'"
    echo "3. Sign up with email"
    echo "4. API key shown immediately after signup"
    echo ""
    read -p "Paste your Finnhub API Key (or press Enter to skip): " FINNHUB_KEY
    echo ""
    
    # Alpha Vantage setup
    echo -e "${BLUE}📊 Option 3: ALPHA VANTAGE (5 calls/minute)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Go to: https://www.alphavantage.co/support/#api-key"
    echo "2. Fill the form (name, email, organization)"
    echo "3. API key shown immediately"
    echo ""
    read -p "Paste your Alpha Vantage API Key (or press Enter to skip): " ALPHA_KEY
    echo ""
    
    # MarketStack setup (optional)
    echo -e "${BLUE}📊 Option 4: MARKETSTACK (1000 calls/month)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Go to: https://marketstack.com/signup/free"
    echo "2. Sign up for free account"
    echo "3. Get API key from dashboard"
    echo ""
    read -p "Paste your MarketStack API Key (or press Enter to skip): " MARKETSTACK_KEY
    echo ""
    
    # Polygon.io setup (optional)
    echo -e "${BLUE}📊 Option 5: POLYGON.IO (5 calls/minute)${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "1. Go to: https://polygon.io/"
    echo "2. Sign up for free tier"
    echo "3. Get API key from dashboard"
    echo ""
    read -p "Paste your Polygon.io API Key (or press Enter to skip): " POLYGON_KEY
    echo ""
    
    # Update configuration
    update_api_keys "$TWELVE_KEY" "$FINNHUB_KEY" "$ALPHA_KEY" "$MARKETSTACK_KEY" "$POLYGON_KEY"
}

# Update API keys in configuration files
update_api_keys() {
    local twelve_key=$1
    local finnhub_key=$2
    local alpha_key=$3
    local marketstack_key=$4
    local polygon_key=$5
    
    local any_key_provided=false
    
    # Check if any key was provided
    if [ ! -z "$twelve_key" ] || [ ! -z "$finnhub_key" ] || [ ! -z "$alpha_key" ] || [ ! -z "$marketstack_key" ] || [ ! -z "$polygon_key" ]; then
        any_key_provided=true
        echo -e "${YELLOW}Updating API keys...${NC}"
        
        # Create backups
        if [ -f "$MARKET_DATA_FILE" ]; then
            cp "$MARKET_DATA_FILE" "${MARKET_DATA_FILE}.bak"
            echo "✅ Backup created: ${MARKET_DATA_FILE}.bak"
        fi
        
        if [ -f "$ENV_FILE" ]; then
            cp "$ENV_FILE" "${ENV_FILE}.bak"
            echo "✅ Backup created: ${ENV_FILE}.bak"
        fi
        
        # Update keys in market_data_providers.py
        if [ ! -z "$twelve_key" ]; then
            sed -i "s/\"twelvedata\": \"[^\"]*\"/\"twelvedata\": \"$twelve_key\"/" "$MARKET_DATA_FILE"
            echo "✅ Twelve Data key updated"
        fi
        
        if [ ! -z "$finnhub_key" ]; then
            sed -i "s/\"finnhub\": \"[^\"]*\"/\"finnhub\": \"$finnhub_key\"/" "$MARKET_DATA_FILE"
            echo "✅ Finnhub key updated"
        fi
        
        if [ ! -z "$marketstack_key" ]; then
            sed -i "s/\"marketstack\": \"[^\"]*\"/\"marketstack\": \"$marketstack_key\"/" "$MARKET_DATA_FILE"
            echo "✅ MarketStack key updated"
        fi
        
        if [ ! -z "$polygon_key" ]; then
            sed -i "s/\"polygon\": \"[^\"]*\"/\"polygon\": \"$polygon_key\"/" "$MARKET_DATA_FILE"
            echo "✅ Polygon.io key updated"
        fi
        
        # Update Alpha Vantage in .env file
        if [ ! -z "$alpha_key" ]; then
            # Remove existing ALPHA_VANTAGE_API_KEY if present
            sed -i '/^ALPHA_VANTAGE_API_KEY=/d' "$ENV_FILE" 2>/dev/null || true
            # Add new key
            echo "ALPHA_VANTAGE_API_KEY=$alpha_key" >> "$ENV_FILE"
            echo "✅ Alpha Vantage key updated"
        fi
        
        echo ""
        echo -e "${YELLOW}🔄 Restarting services with new API keys...${NC}"
        
        # Restart services if Docker is running
        if docker ps | grep -q operation-app; then
            docker-compose restart app
            sleep 5
            echo -e "${GREEN}✅ Services restarted${NC}"
        else
            echo -e "${YELLOW}⚠️  Services not running. Start them with: docker-compose up -d${NC}"
        fi
        
        # Test the APIs if services are running
        if docker ps | grep -q operation-app; then
            test_api_keys
        fi
    else
        echo -e "${YELLOW}No API keys provided. Using demo keys (limited functionality).${NC}"
    fi
}

# Test API keys
test_api_keys() {
    echo ""
    echo -e "${BLUE}Testing API keys...${NC}"
    
    # Get auth token
    TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
        -H "Content-Type: application/json" \
        -d '{"email":"admin@example.com","password":"admin123"}' | jq -r '.access_token')
    
    if [ -z "$TOKEN" ] || [ "$TOKEN" = "null" ]; then
        echo -e "${RED}❌ Could not authenticate to test APIs${NC}"
        return
    fi
    
    echo ""
    echo "📊 Testing Market Data:"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Test symbols
    symbols=("AAPL" "MSFT" "GOOGL" "BTC-USD" "ETH-USD")
    
    for symbol in "${symbols[@]}"; do
        price=$(curl -s "http://localhost:8000/api/v1/market/price/$symbol" \
            -H "Authorization: Bearer $TOKEN" | jq -r '.price // "N/A"')
        
        if [ "$price" != "N/A" ] && [ "$price" != "null" ]; then
            echo -e "${GREEN}✅ $symbol: \$$price${NC}"
        else
            echo -e "${RED}❌ $symbol: Failed to get price${NC}"
        fi
    done
    
    echo ""
}

# Quick setup mode (non-interactive)
quick_setup() {
    echo -e "${BLUE}Quick Setup Guide${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""
    echo "To manually configure API keys:"
    echo ""
    echo "1. Get your FREE API keys from:"
    echo "   • TwelveData (800 calls/day): https://twelvedata.com/apikey"
    echo "   • Finnhub (60 calls/min): https://finnhub.io/register"
    echo "   • MarketStack (1000/month): https://marketstack.com/signup/free"
    echo "   • Polygon.io (5 calls/min): https://polygon.io/"
    echo "   • Alpha Vantage (5 calls/min): https://www.alphavantage.co/support/#api-key"
    echo ""
    echo "2. Update the keys in:"
    echo "   • $MARKET_DATA_FILE"
    echo "   • $ENV_FILE (for Alpha Vantage)"
    echo ""
    echo "3. Restart services:"
    echo "   • docker-compose restart app"
    echo ""
}

# Main script logic
main() {
    case "${1:-help}" in
        "show")
            show_current_config
            ;;
            
        "setup")
            interactive_setup
            ;;
            
        "quick")
            quick_setup
            ;;
            
        "test")
            if docker ps | grep -q operation-app; then
                test_api_keys
            else
                echo -e "${RED}❌ Services not running. Start with: docker-compose up -d${NC}"
                exit 1
            fi
            ;;
            
        "help")
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  show   - Show current API configuration"
            echo "  setup  - Interactive API key setup (recommended)"
            echo "  quick  - Show quick setup guide"
            echo "  test   - Test configured API keys"
            echo "  help   - Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 setup  # Interactive setup wizard"
            echo "  $0 show   # View current configuration"
            echo "  $0 test   # Test if APIs are working"
            ;;
            
        *)
            echo -e "${RED}Unknown command: $1${NC}"
            echo "Run '$0 help' for usage information"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"