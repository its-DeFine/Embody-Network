#!/usr/bin/env python3
"""
Test script to verify Ollama integration with agent-net
Checks if Ollama is running and shows GPU/VRAM status
"""

import requests
import json
import sys

def test_ollama_status():
    """Test Ollama connection and GPU status"""
    print("🔍 Testing Ollama Integration\n")
    
    try:
        # Check Ollama API
        response = requests.get("http://localhost:11434/api/ps", timeout=5)
        
        if response.status_code != 200:
            print(f"❌ Failed to connect to Ollama: HTTP {response.status_code}")
            print("   Make sure Ollama container is running")
            return False
            
        data = response.json()
        models = data.get('models', [])
        
        print("✅ Successfully connected to Ollama")
        
        if not models:
            print("⚠️  No models currently loaded")
            print("   GPU Score would be: 85.0% (Poor)")
            print("\n💡 To load a model, run:")
            print("   curl -X POST localhost:11434/api/generate -d '{\"model\": \"tinyllama\", \"prompt\": \"test\", \"keep_alive\": \"5m\"}'")
        else:
            print(f"\n📊 Loaded Models: {len(models)}")
            total_vram = 0
            
            for model in models:
                name = model.get('name', 'unknown')
                size_vram = model.get('size_vram', 0)
                total_vram += size_vram
                
                print(f"\n   Model: {name}")
                print(f"   VRAM Usage: {size_vram / (1024**2):.0f} MB ({size_vram / (1024**3):.2f} GB)")
                
            # Calculate GPU score
            total_vram_mb = total_vram / (1024 * 1024)
            
            if total_vram_mb < 2000:
                gpu_score = 99.5
                rating = "Excellent"
            elif total_vram_mb < 4000:
                gpu_score = 98.0
                rating = "Good"
            elif total_vram_mb < 6000:
                gpu_score = 92.0
                rating = "Fair"
            else:
                gpu_score = 85.0
                rating = "Poor"
                
            print(f"\n📊 Total VRAM Usage: {total_vram_mb:.0f} MB")
            print(f"🎯 GPU Score: {gpu_score}% ({rating})")
            
            # Show job rate mapping
            if gpu_score >= 99.0:
                job_rate_pct = "100%"
            elif gpu_score >= 95.0:
                job_rate_pct = "50%"
            elif gpu_score >= 90.0:
                job_rate_pct = "10%"
            else:
                job_rate_pct = "0%"
                
            print(f"⚡ Job Rate: {job_rate_pct} of base rate")
            
        print("\n✨ Ollama integration test complete!")
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Ollama at localhost:11434")
        print("   Make sure the Ollama container is running:")
        print("   docker-compose up -d ollama ollama-loader")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_status()
    sys.exit(0 if success else 1)