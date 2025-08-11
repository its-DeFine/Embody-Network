"""
Version management for VTuber Autonomy Platform
Automatically updated by CI/CD pipeline
"""
import os
from pathlib import Path

def get_version() -> str:
    """Get the current version from VERSION file or fallback"""
    version_file = Path(__file__).parent.parent / "VERSION"
    
    # Try to read from VERSION file
    if version_file.exists():
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
                if version:
                    return version
        except Exception:
            pass
    
    # Fallback to environment variable (set by CI/CD)
    if "APP_VERSION" in os.environ:
        return os.environ["APP_VERSION"]
    
    # Development fallback
    return "0.1.0-dev"

# Version string that can be imported
__version__ = get_version()

# Version components for programmatic access
def get_version_info():
    """Get version components as a dictionary"""
    version = get_version()
    
    # Parse semantic version (major.minor.patch[-prerelease][+build])
    parts = version.split('-')[0].split('.')
    
    return {
        "version": version,
        "major": int(parts[0]) if len(parts) > 0 and parts[0].isdigit() else 0,
        "minor": int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0,
        "patch": int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 0,
        "prerelease": version.split('-')[1] if '-' in version else None,
        "build": version.split('+')[1] if '+' in version else None
    }