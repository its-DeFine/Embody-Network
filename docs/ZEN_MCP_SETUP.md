# Zen MCP Setup Guide for Claude Code

## Overview
Zen MCP Server enables Claude Code to work with multiple AI models including GPT-4/5, Gemini, Grok, and others. This allows you to leverage different models for planning, code review, and complex problem-solving.

## Quick Setup

### 1. Set Your API Keys

First, set your OpenAI API key (required for GPT-4/5):

```bash
export OPENAI_API_KEY='your-openai-api-key-here'
```

Optional: Add other AI provider keys:
```bash
export GEMINI_API_KEY='your-gemini-key'
export OPENROUTER_API_KEY='your-openrouter-key'
export XAI_API_KEY='your-xai-key'
```

### 2. Add Zen MCP to Claude Code

Run this command to add Zen MCP to Claude Code:

```bash
claude mcp add zen "uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server" --scope user
```

### 3. Create Persistent Configuration (Optional)

Create a file `~/.zen-mcp.env` with your API keys:

```env
OPENAI_API_KEY=your-openai-key
GEMINI_API_KEY=your-gemini-key
OPENROUTER_API_KEY=your-openrouter-key
```

Then create a wrapper script at `~/zen-mcp-wrapper.sh`:

```bash
#!/bin/bash
# Load API keys from config file
if [ -f ~/.zen-mcp.env ]; then
    export $(cat ~/.zen-mcp.env | grep -v '^#' | xargs)
fi
# Run Zen MCP
exec uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server
```

Make it executable:
```bash
chmod +x ~/zen-mcp-wrapper.sh
```

Then add it to Claude Code:
```bash
claude mcp add zen ~/zen-mcp-wrapper.sh --scope user
```

## Usage in Claude Code

Once configured, you can use the Zen tool in Claude Code conversations:

### Example Commands

1. **Ask GPT-4 for planning advice:**
   ```
   "Use the zen tool to ask GPT-4 to create a detailed plan for implementing a real-time chat system"
   ```

2. **Get multiple perspectives:**
   ```
   "Use zen to get both GPT-4 and Gemini's opinion on this architecture design"
   ```

3. **Code review with GPT-4:**
   ```
   "Use the zen tool to have GPT-4 review this function for potential improvements"
   ```

### Available Models (with appropriate API keys)

- **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5
- **Google**: Gemini Pro, Gemini Ultra
- **X.AI**: Grok-1, Grok-2
- **OpenRouter**: Access to 100+ models including Claude, Llama, Mistral
- **Local**: Ollama models (via CUSTOM_API_URL)

## Troubleshooting

### Check MCP Status
```bash
claude mcp list
```

### View Server Details
```bash
claude mcp get zen
```

### Remove and Re-add
```bash
claude mcp remove zen
claude mcp add zen "uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server" --scope user
```

### Test Direct Installation
```bash
# Set API key first
export OPENAI_API_KEY='your-key'

# Test run
uvx --from git+https://github.com/BeehiveInnovations/zen-mcp-server.git zen-mcp-server
```

## Benefits of Using Zen MCP

1. **Multi-Model Orchestration**: Leverage different AI models' strengths
2. **Extended Context**: Use Gemini's 1M token context for large codebases
3. **Different Perspectives**: Get varied insights from multiple models
4. **Planning & Architecture**: Use GPT-4 for high-level planning while Claude handles implementation
5. **Context Revival**: Maintain conversation context across model switches

## Security Notes

- Never commit API keys to version control
- Use environment variables or secure config files
- Consider using tools like `direnv` for project-specific API keys
- Rotate API keys regularly

## Resources

- [Zen MCP GitHub Repository](https://github.com/BeehiveInnovations/zen-mcp-server)
- [Claude Code MCP Documentation](https://docs.anthropic.com/en/docs/claude-code/mcp)
- [OpenAI API Keys](https://platform.openai.com/api-keys)
- [Google AI Studio (Gemini)](https://makersuite.google.com/app/apikey)
- [OpenRouter](https://openrouter.ai/keys)