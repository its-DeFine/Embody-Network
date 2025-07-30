#!/usr/bin/env python3
"""
MCP-like tool for automatic architecture diagram updates.
Run this after any code changes to regenerate the architecture diagram.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.diagram_generator import DiagramGenerator
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'  # Simple format for tool output
)

def main():
    """Main entry point for diagram update tool."""
    print("🎨 Architecture Diagram Updater")
    print("=" * 40)
    
    generator = DiagramGenerator()
    
    # Analyze current architecture
    arch = generator.analyze_architecture()
    
    print(f"📊 Architecture Analysis:")
    print(f"  - AI Enabled: {'✅' if arch['has_ai'] else '❌'}")
    print(f"  - AutoGen Teams: {'✅' if arch['has_autogen'] else '❌'}")
    print(f"  - Event Handlers: {len(arch['event_handlers'])}")
    print(f"  - AI Handlers: {len(arch['ai_handlers'])}")
    print()
    
    # Check for changes and generate
    print("🔍 Checking for changes...")
    
    if generator.generate_diagram():
        print("✅ Architecture diagram updated successfully!")
        print(f"📍 Location: architecture_ai.png")
    else:
        print("✅ Diagram is already up to date")
        
    print("\n💡 Tip: Add --watch flag to monitor changes continuously")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update architecture diagram based on code changes"
    )
    parser.add_argument(
        '--watch', 
        action='store_true', 
        help="Watch for changes and auto-update"
    )
    parser.add_argument(
        '--force', 
        action='store_true', 
        help="Force update even if no changes detected"
    )
    
    args = parser.parse_args()
    
    if args.watch:
        print("👀 Watching for changes... (Ctrl+C to stop)")
        generator = DiagramGenerator()
        generator.watch_and_generate()
    elif args.force:
        generator = DiagramGenerator()
        generator.generate_diagram(force=True)
        print("✅ Diagram forcefully regenerated")
    else:
        main()