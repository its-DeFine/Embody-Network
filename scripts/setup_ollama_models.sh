#!/bin/bash

# Script to automatically pull Ollama models based on available GPU memory

echo "==========================================="
echo "OLLAMA MODEL SETUP"
echo "==========================================="

# Wait for Ollama to be ready
echo "Waiting for Ollama service..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    echo "Ollama not ready, waiting..."
    sleep 5
done

echo "Ollama service is ready!"

# Check if we have models already
EXISTING_MODELS=$(curl -s http://localhost:11434/api/tags | jq -r '.models[].name' 2>/dev/null)

if [ -n "$EXISTING_MODELS" ]; then
    echo "Found existing models:"
    echo "$EXISTING_MODELS"
else
    echo "No models found. Pulling recommended models for 16GB GPU..."
    
    # Pull models suitable for 16GB GPU
    # These are ordered by usefulness for trading/analysis
    
    echo "1. Pulling llama2:13b (General purpose, 13B params)..."
    docker exec operation-ollama-1 ollama pull llama2:13b
    
    echo "2. Pulling codellama:13b (Code analysis, 13B params)..."
    docker exec operation-ollama-1 ollama pull codellama:13b
    
    echo "3. Pulling neural-chat:7b (Optimized for analysis)..."
    docker exec operation-ollama-1 ollama pull neural-chat:7b
    
    echo "4. Pulling mistral:7b-instruct (Fast and efficient)..."
    docker exec operation-ollama-1 ollama pull mistral:7b-instruct
    
    # Optional: Pull quantized version of larger model
    echo "5. Pulling mixtral (8x7B MoE, quantized for 16GB)..."
    docker exec operation-ollama-1 ollama pull mixtral:8x7b-instruct-v0.1-q4_0
fi

echo ""
echo "Model setup complete!"
echo ""
echo "Available models:"
curl -s http://localhost:11434/api/tags | jq -r '.models[].name'

echo ""
echo "To use different models, run:"
echo "  docker exec operation-ollama-1 ollama pull <model-name>"
echo ""
echo "Popular models for 16GB GPU:"
echo "  - llama2:13b (recommended for trading)"
echo "  - codellama:13b (for code analysis)"
echo "  - mixtral:8x7b-instruct-v0.1-q4_0 (most capable)"
echo "  - solar:10.7b (good balance)"
echo "  - deepseek-coder:6.7b (specialized for code)"