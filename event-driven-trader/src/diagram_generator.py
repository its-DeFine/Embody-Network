#!/usr/bin/env python3
"""
Automatic Architecture Diagram Generator
Monitors codebase changes and regenerates architecture diagrams dynamically.
Acts like an MCP (Model Context Protocol) tool for diagram generation.
"""

import os
import hashlib
import json
import subprocess
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend

logger = logging.getLogger(__name__)


class DiagramGenerator:
    """
    Automatically generates architecture diagrams when code changes.
    Monitors Python files and regenerates diagrams to keep them in sync.
    """
    
    def __init__(self, project_root: str = None):
        self.project_root = Path(project_root or os.getcwd())
        self.src_dir = self.project_root / "src"
        self.cache_file = self.project_root / ".diagram_cache.json"
        self.diagram_script = self.project_root / "architecture_diagram_ai.py"
        self.file_hashes = {}
        self.load_cache()
        
    def load_cache(self):
        """Load cached file hashes."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self.file_hashes = json.load(f)
            except:
                self.file_hashes = {}
                
    def save_cache(self):
        """Save file hashes to cache."""
        with open(self.cache_file, 'w') as f:
            json.dump(self.file_hashes, f, indent=2)
            
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate hash of a file."""
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
            
    def scan_python_files(self) -> Set[Path]:
        """Find all Python files in the project."""
        python_files = set()
        
        # Scan src directory
        if self.src_dir.exists():
            for file in self.src_dir.rglob("*.py"):
                python_files.add(file)
                
        # Include key files from root
        for pattern in ["*.py", "config.yaml", "requirements.txt"]:
            for file in self.project_root.glob(pattern):
                python_files.add(file)
                
        return python_files
        
    def detect_changes(self) -> List[Path]:
        """Detect which files have changed."""
        changed_files = []
        current_files = self.scan_python_files()
        
        for file in current_files:
            current_hash = self.get_file_hash(file)
            cached_hash = self.file_hashes.get(str(file))
            
            if cached_hash != current_hash:
                changed_files.append(file)
                self.file_hashes[str(file)] = current_hash
                
        # Check for deleted files
        cached_files = set(Path(f) for f in self.file_hashes.keys())
        deleted_files = cached_files - current_files
        
        for file in deleted_files:
            del self.file_hashes[str(file)]
            changed_files.append(file)
            
        return changed_files
        
    def analyze_architecture(self) -> Dict[str, any]:
        """Analyze the codebase to understand architecture."""
        components = {
            'has_ai': False,
            'has_autogen': False,
            'event_handlers': [],
            'ai_handlers': [],
            'has_trading_engine': False,
            'has_api_monitor': False
        }
        
        # Check for AI components
        ai_files = ['autogen_teams.py', 'ai_handlers.py']
        for ai_file in ai_files:
            if (self.src_dir / ai_file).exists():
                components['has_ai'] = True
                components['has_autogen'] = 'autogen' in ai_file
                
        # Scan for handlers
        handlers_file = self.src_dir / 'handlers.py'
        if handlers_file.exists():
            content = handlers_file.read_text()
            
            # Find traditional handlers
            import re
            handler_pattern = r'class\s+(\w*Handler)\s*\('
            handlers = re.findall(handler_pattern, content)
            
            for handler in handlers:
                if 'AI' in handler:
                    components['ai_handlers'].append(handler)
                else:
                    components['event_handlers'].append(handler)
                    
        # Check for other components
        if (self.src_dir / 'trading.py').exists():
            components['has_trading_engine'] = True
        if (self.src_dir / 'monitor.py').exists():
            components['has_api_monitor'] = True
            
        return components
        
    def generate_diagram(self, force: bool = False) -> bool:
        """Generate architecture diagram if needed."""
        changed_files = self.detect_changes()
        
        if not changed_files and not force:
            logger.info("No changes detected, diagram is up to date")
            return False
            
        logger.info(f"Detected {len(changed_files)} changed files")
        
        # Analyze current architecture
        arch = self.analyze_architecture()
        
        # Run the appropriate diagram generator
        if self.diagram_script.exists():
            logger.info("Generating architecture diagram...")
            
            try:
                # Run the diagram script
                result = subprocess.run(
                    ['python3', str(self.diagram_script)],
                    capture_output=True,
                    text=True,
                    cwd=str(self.project_root)
                )
                
                if result.returncode == 0:
                    logger.info("Architecture diagram generated successfully")
                    self.save_cache()
                    
                    # Log what was generated
                    if arch['has_ai']:
                        logger.info("Generated AI-powered architecture diagram")
                    else:
                        logger.info("Generated standard architecture diagram")
                        
                    return True
                else:
                    logger.error(f"Diagram generation failed: {result.stderr}")
                    
            except Exception as e:
                logger.error(f"Error generating diagram: {e}")
                
        return False
        
    def watch_and_generate(self):
        """Watch for changes and regenerate diagram automatically."""
        logger.info("Starting diagram auto-generation watch...")
        
        import time
        last_check = time.time()
        
        while True:
            try:
                # Check every 10 seconds
                time.sleep(10)
                
                # Generate if changes detected
                if self.generate_diagram():
                    logger.info(f"Diagram updated at {datetime.now()}")
                    
            except KeyboardInterrupt:
                logger.info("Stopping diagram watch")
                break
            except Exception as e:
                logger.error(f"Watch error: {e}")
                

def integrate_with_event_loop():
    """
    Integration function to add diagram generation to the event loop.
    This can be called from the main application to enable auto-generation.
    """
    from events import create_periodic_event
    
    # Create a periodic event for diagram checking
    diagram_event = create_periodic_event(
        name="diagram_update_check",
        handler="DiagramUpdateHandler",
        data={'generator': DiagramGenerator()}
    )
    
    return diagram_event


class DiagramUpdateHandler:
    """Event handler for automatic diagram updates."""
    
    def __init__(self):
        self.generator = DiagramGenerator()
        
    async def handle(self, event, event_loop):
        """Check and update diagram if needed."""
        updated = self.generator.generate_diagram()
        
        if updated:
            logger.info("Architecture diagram updated automatically")
            
        return None


# CLI interface for manual generation
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Architecture Diagram Generator")
    parser.add_argument('--watch', action='store_true', help="Watch for changes")
    parser.add_argument('--force', action='store_true', help="Force regeneration")
    parser.add_argument('--analyze', action='store_true', help="Analyze architecture only")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    generator = DiagramGenerator()
    
    if args.analyze:
        arch = generator.analyze_architecture()
        print("Architecture Analysis:")
        print(json.dumps(arch, indent=2))
    elif args.watch:
        generator.watch_and_generate()
    else:
        generator.generate_diagram(force=args.force)