# Zen MCP Usage Guide - GPT-5 Integration

## ✅ Configuration Complete!

Your Zen MCP Server is now configured with:
- **OpenAI API Key**: Configured and validated
- **Default Model**: GPT-5 (will use GPT-4 Turbo as fallback if GPT-5 isn't available)
- **Server Status**: Ready and running

## Available Zen Tools

The Zen MCP provides these powerful tools you can use in Claude Code:

### 1. **chat** - Direct conversation with GPT-5
```
Use zen chat to ask GPT-5: "Create a detailed implementation plan for a real-time collaborative editor"
```

### 2. **thinkdeep** - Deep reasoning and analysis
```
Use zen thinkdeep to analyze: "What are the architectural trade-offs between microservices and monolithic architecture for this project?"
```

### 3. **planner** - Strategic planning
```
Use zen planner to create: "A comprehensive roadmap for migrating from REST to GraphQL"
```

### 4. **consensus** - Get multiple model perspectives
```
Use zen consensus to evaluate: "Should we use PostgreSQL or MongoDB for this application?"
```

### 5. **codereview** - Code analysis and improvements
```
Use zen codereview to review: "Analyze this authentication module for security vulnerabilities and performance issues"
```

### 6. **refactor** - Code refactoring suggestions
```
Use zen refactor to improve: "Refactor this legacy code to use modern async/await patterns"
```

### 7. **secaudit** - Security auditing
```
Use zen secaudit to check: "Audit this API endpoint for potential security vulnerabilities"
```

### 8. **testgen** - Test generation
```
Use zen testgen to create: "Generate comprehensive unit tests for this service class"
```

### 9. **debug** - Debugging assistance
```
Use zen debug to solve: "Help me debug why this async function is causing a memory leak"
```

### 10. **docgen** - Documentation generation
```
Use zen docgen to create: "Generate API documentation for this REST service"
```

## Example Workflows

### Planning a New Feature
```
1. Use zen planner to create a high-level implementation strategy
2. Use zen thinkdeep to analyze potential challenges
3. Use Claude to implement the code
4. Use zen codereview to get GPT-5's perspective on the implementation
```

### Debugging Complex Issues
```
1. Use zen debug to analyze the problem
2. Use zen consensus to get multiple AI perspectives
3. Use Claude to implement the fix
4. Use zen secaudit to ensure no security issues were introduced
```

### Architecture Decisions
```
1. Use zen thinkdeep for architectural analysis
2. Use zen consensus for balanced perspectives
3. Use zen planner to create implementation roadmap
```

## Files Created

- `.zen-mcp.env` - Your API configuration (keep this secure!)
- `zen-mcp-wrapper.sh` - Wrapper script that loads your configuration
- `.mcp.json` - MCP server configuration for Claude Code

## Important Notes

1. **Model Availability**: GPT-5 will be used when available. The system will automatically fall back to GPT-4 Turbo if needed.

2. **API Usage**: Each call to Zen tools will use your OpenAI API credits. Monitor your usage at https://platform.openai.com/usage

3. **Security**: Never share or commit your `.zen-mcp.env` file. It contains your API key.

## Troubleshooting

If you encounter issues:

1. **Test the configuration**:
```bash
./zen-mcp-wrapper.sh
```

2. **Check API key validity**:
```bash
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

3. **View logs**:
```bash
tail -f ~/.cache/uv/archive-v0/*/lib/python*/site-packages/logs/mcp_server.log
```

## Quick Start Commands

Try these in Claude Code once Zen MCP is connected:

```
"Use zen chat to ask GPT-5 for its best practices on building scalable microservices"

"Use zen planner to create a detailed plan for implementing OAuth2 authentication"

"Use zen codereview to analyze the main.py file for improvements"

"Use zen consensus to compare React vs Vue for our new frontend project"
```

## Next Steps

1. In Claude Code, the Zen tools should now be available
2. Start with simple queries to test the integration
3. Gradually use more complex planning and analysis tasks
4. Combine Claude's implementation skills with GPT-5's planning capabilities

Your setup is complete and ready to use!