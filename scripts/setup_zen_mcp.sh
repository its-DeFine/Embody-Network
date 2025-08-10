#!/bin/bash

# Zen MCP Setup Script for Claude Code
# This script sets up Zen MCP with OpenAI API integration

echo "======================================"
echo "Zen MCP Server Setup for Claude Code"
echo "======================================"

# Check if OPENAI_API_KEY is already set
if [ -z "$OPENAI_API_KEY" ]; then
    echo ""
    echo "⚠️  OPENAI_API_KEY is not set in your environment."
    echo ""
    echo "To use GPT-5/GPT-4 with Zen MCP, you need to:"
    echo "1. Get your OpenAI API key from https://platform.openai.com/api-keys"
    echo "2. Set it as an environment variable:"
    echo ""
    echo "   export OPENAI_API_KEY='your-api-key-here'"
    echo ""
    echo "For permanent setup, add the export to your ~/.bashrc or ~/.zshrc"
    echo ""
    read -p "Enter your OpenAI API key (or press Enter to skip): " api_key
    
    if [ ! -z "$api_key" ]; then
        export OPENAI_API_KEY="$api_key"
        echo "✅ OPENAI_API_KEY set for this session"
    fi
fi

# Check for other optional API keys
echo ""
echo "Optional: You can also configure other AI providers:"
echo "- GEMINI_API_KEY for Google Gemini"
echo "- OPENROUTER_API_KEY for OpenRouter (access to multiple models)"
echo "- XAI_API_KEY for X.AI Grok"
echo "- CUSTOM_API_URL for local models (Ollama, etc.)"
echo ""

# Add Zen MCP to Claude Code
echo "Adding Zen MCP Server to Claude Code..."

# Create a temporary config file for the MCP server command
cat > /tmp/zen-mcp-config.sh << 'EOF'
#!/bin/bash
# Export API keys if they're set in .env file
if [ -f ~/.zen-mcp.env ]; then
    export $(cat ~/.zen-mcp.env | grep -v '^#' | xargs)
fi

# Run the Zen MCP server
exec $(which uvx || echo uvx) --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server
EOF

chmod +x /tmp/zen-mcp-config.sh

# Add the MCP server to Claude Code
echo "Configuring Zen MCP in Claude Code..."
claude mcp add zen /tmp/zen-mcp-config.sh --scope user 2>/dev/null || {
    echo "Note: 'claude' command not found or MCP already configured."
    echo "You may need to manually add Zen MCP using the Claude Code interface."
}

echo ""
echo "======================================"
echo "Setup Instructions Complete!"
echo "======================================"
echo ""
echo "To use Zen MCP with Claude Code:"
echo ""
echo "1. Make sure your API keys are set:"
echo "   export OPENAI_API_KEY='your-openai-key'"
echo ""
echo "2. If not already added, add Zen MCP to Claude Code:"
echo "   claude mcp add zen 'uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server' --scope user"
echo ""
echo "3. In Claude Code, you can now use the 'zen' tool to query GPT-4/5:"
echo "   Example: Use the zen tool to ask GPT-4 for planning advice"
echo ""
echo "4. Optional: Create a persistent config file ~/.zen-mcp.env with:"
echo "   OPENAI_API_KEY=your-key-here"
echo "   GEMINI_API_KEY=your-gemini-key"
echo "   OPENROUTER_API_KEY=your-openrouter-key"
echo ""
echo "For more details, visit: https://github.com/BeehiveInnovations/zen-mcp-server"