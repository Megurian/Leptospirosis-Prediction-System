"""
Build script for Leptospirosis Risk Prediction System
Creates a standalone executable for Windows
"""
import subprocess
import sys
import os

def build():
    print("=" * 60)
    print("Building Leptospirosis Risk Prediction System")
    print("=" * 60)
    
    # Install PyInstaller if not present
    print("\n[1/3] Checking PyInstaller...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller is installed")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Build command
    print("\n[2/3] Building executable...")
    
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=LeptospirosisPredictor",
        "--onefile",              # Single executable
        "--windowed",             # No console window
        "--noconfirm",            # Overwrite without asking
        "--clean",                # Clean cache
        "--add-data=leptospirosis_sim.db;.",  # Include database if exists
        "main.py"
    ]
    
    # Check if database exists
    if not os.path.exists("leptospirosis_sim.db"):
        # Remove the add-data flag if no database
        build_cmd = [x for x in build_cmd if "leptospirosis_sim.db" not in x]
        print("  Note: No existing database found. A new one will be created on first run.")
    
    try:
        subprocess.check_call(build_cmd)
        print("\n  ✓ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Build failed: {e}")
        return False
    
    print("\n[3/3] Build Complete!")
    print("=" * 60)
    print("\nOutput location: dist/LeptospirosisPredictor.exe")
    print("\nTo distribute:")
    print("  1. Copy 'dist/LeptospirosisPredictor.exe' to target machine")
    print("  2. Optionally copy 'leptospirosis_sim.db' for existing data")
    print("  3. Run the executable")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    build()
