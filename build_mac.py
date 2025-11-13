#!/usr/bin/env python3
"""
Mac build script for busyWithFish application.
This script creates a macOS bundle using PyInstaller.
"""

import os
import sys
import subprocess
import shutil

def build_mac_app():
    """Build the macOS application bundle."""
    print("Building macOS application...")
    
    # Get the project root directory
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    # Change to project directory
    os.chdir(project_root)
    
    # Path to spec file
    spec_file = os.path.join(project_root, "build_mac.spec")
    
    # Check if spec file exists
    if not os.path.exists(spec_file):
        print("Error: build_mac.spec file not found!")
        return False
    
    # Run PyInstaller with the spec file
    try:
        cmd = [sys.executable, "-m", "PyInstaller", spec_file]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("Build successful!")
            print(result.stdout)
            return True
        else:
            print("Build failed!")
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"Error running PyInstaller: {e}")
        return False

def create_requirements_file():
    """Create requirements-mac.txt file with project dependencies."""
    requirements = [
        "PyQt6",
        "pynput",
        "netstruct"
    ]
    
    with open("requirements-mac.txt", "w") as f:
        for req in requirements:
            f.write(req + "\n")
    
    print("Created requirements-mac.txt")

if __name__ == "__main__":
    # Create requirements file
    create_requirements_file()
    
    # Build the app
    success = build_mac_app()
    
    if success:
        print("\nmacOS build completed successfully!")
        print("Output can be found in the 'dist' folder.")
    else:
        print("\nmacOS build failed!")
        sys.exit(1)