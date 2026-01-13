"""
Build script for Leptospirosis Risk Prediction System
Creates a standalone executable for Windows
"""
import subprocess
import sys
import os

def create_version_info():
    """Generates a version info file for Windows to establish 'reputation'"""
    version_content = """
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1, 0, 0, 0),
    prodvers=(1, 0, 0, 0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Megurian Dev'),
        StringStruct(u'FileDescription', u'Leptospirosis Risk Prediction System'),
        StringStruct(u'FileVersion', u'1.0.0.0'),
        StringStruct(u'InternalName', u'LeptoPredictor'),
        StringStruct(u'LegalCopyright', u'Copyright (c) 2026'),
        StringStruct(u'OriginalFilename', u'LeptospirosisPredictor.exe'),
        StringStruct(u'ProductName', u'Leptospirosis Prediction System'),
        StringStruct(u'ProductVersion', u'0.1.0.0')])
      ]), 
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
"""
    with open("version_info.txt", "w", encoding="utf-8") as f:
        f.write(version_content)
    return "version_info.txt"

def build():
    print("=" * 60)
    print("Building Leptospirosis Risk Prediction System")
    print("=" * 60)
    
    # 1. Install PyInstaller if not present
    print("\n[1/4] Checking PyInstaller...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller is installed")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 2. Generate Version Info
    print("\n[2/4] Generating Version Metadata...")
    version_file = create_version_info()
    print("  ✓ Created version_info.txt")

    # 3. Build command
    print("\n[3/4] Building executable...")
    
    # Check if we should use onedir (cleaner) or onefile (easier to share)
    # Using --onedir often reduces false positive virus warnings
    mode = "--onedir" 
    
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name=LeptospirosisPredictor",
        mode,                     # --onefile or --onedir
        "--windowed",             # No console window
        "--noconfirm",            # Overwrite without asking
        "--clean",                # Clean cache
        f"--version-file={version_file}", # Attach metadata
        "--add-data=leptospirosis_sim.db;.",  # Include database if exists
        "main.py"
    ]
    
    # Check if database exists
    if not os.path.exists("leptospirosis_sim.db"):
        build_cmd = [x for x in build_cmd if "leptospirosis_sim.db" not in x]
        print("  Note: No existing database found. A new one will be created on first run.")
    
    try:
        subprocess.check_call(build_cmd)
        print("\n  ✓ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Build failed: {e}")
        return False
    finally:
        # Cleanup temp version file
        if os.path.exists(version_file):
            os.remove(version_file)
    
    print("\n[4/4] Build Complete!")
    print("=" * 60)
    print(f"\nOutput location: dist/LeptospirosisPredictor.exe")
    print("\nNOTE ON VIRUS WARNINGS:")
    print("If Windows SmartScreen warns you, it is because this app is not")
    print("digitally signed with a paid certificate.")
    print("\nTo fix for local use:")
    print("  1. Click 'More Info' -> 'Run Keep/Run Anyway'")
    print("  2. If Antivirus deletes it, add an exclusion for the 'dist' folder.")
    print("=" * 60)
    
    return True

if __name__ == "__main__":
    build()