#!/usr/bin/env python3
"""
Build script for WordPress Publisher Native App
Creates a .app bundle for macOS distribution
"""
import PyInstaller.__main__
import os
import shutil
from pathlib import Path

def build_app():
    """Build the native macOS application"""
    
    print("🏗️  Building WordPress Publisher Native App...")
    
    # Get current directory
    current_dir = Path(__file__).parent
    
    # Create build directory
    build_dir = current_dir / "build"
    dist_dir = current_dir / "dist"
    
    # Clean previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # PyInstaller options
    options = [
        'native_app_improved.py',  # Main script with threading improvements
        '--name=WordPress Publisher',  # App name
        '--windowed',  # GUI app (no console)
        '--onedir',  # Create a directory bundle
        '--noconfirm',  # Don't ask for confirmation
        '--clean',  # Clean cache
        '--add-data=backend:backend',  # Include backend files
        '--add-data=frontend:frontend',  # Include frontend files
        '--add-data=static:static',  # Include static files
        '--hidden-import=uvicorn',  # Ensure uvicorn is included
        '--hidden-import=fastapi',  # Ensure fastapi is included
        '--hidden-import=main',  # Ensure our main module is included
        '--collect-all=fastapi',  # Collect all fastapi dependencies
        '--collect-all=uvicorn',  # Collect all uvicorn dependencies
        '--collect-all=pydantic',  # Collect pydantic dependencies
        '--osx-bundle-identifier=com.publicador.wordpress',  # Bundle ID
        '--icon=static/icon.icns' if (current_dir / 'static' / 'icon.icns').exists() else '',
        f'--distpath={dist_dir}',
        f'--workpath={build_dir}',
    ]
    
    # Remove empty icon option if no icon exists
    options = [opt for opt in options if opt]
    
    print(f"📦 PyInstaller options: {options}")
    
    try:
        # Run PyInstaller
        PyInstaller.__main__.run(options)
        
        print("✅ Build completed successfully!")
        print(f"📱 App location: {dist_dir / 'WordPress Publisher'}")
        print("\n🚀 To run the app:")
        print(f"   open '{dist_dir / 'WordPress Publisher' / 'WordPress Publisher.app'}'")
        print("\n📦 To create a DMG for distribution:")
        print("   Use Disk Utility or run: hdiutil create -volname 'WordPress Publisher' -srcfolder dist 'WordPress Publisher.dmg'")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")

if __name__ == "__main__":
    build_app()