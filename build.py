"""
Build script for Leptospirosis Risk Prediction System
Creates a standalone executable for Windows, Linux, or macOS
Supports cross-compilation (build for Windows from Linux)
"""
import subprocess
import sys
import os
import platform

def get_platform_info():
    """Get current system platform"""
    system = platform.system()
    return {
        'system': system,
        'is_windows': system == 'Windows',
        'is_linux': system == 'Linux',
        'is_macos': system == 'Darwin'
    }

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
    """Main build function"""
    platform_info = get_platform_info()
    system = platform_info['system']
    is_windows = platform_info['is_windows']
    is_linux = platform_info['is_linux']
    
    print("=" * 70)
    print("Leptospirosis Risk Prediction System - Build Script")
    print("=" * 70)
    print(f"\nDetected Platform: {system}")
    print(f"Python: {sys.version.split()[0]}")
    
    # Ask user which target platform to build for
    if is_linux or platform_info['is_macos']:
        print("\nBuild Target Options:")
        print("  1. Linux (current system)")
        print("  2. Windows (for client)")
        print("  3. macOS")
        
        choice = input("\nSelect target platform [1-3] (default: 1): ").strip() or "1"
        
        if choice == "1":
            target = "linux"
        elif choice == "2":
            target = "windows"
        elif choice == "3":
            target = "macos"
        else:
            print("Invalid choice. Defaulting to current platform.")
            target = "linux" if is_linux else "macos"
    else:
        target = "windows"
    
    print(f"\n✓ Target: {target.upper()}")
    
    # Select source file
    print("\nSource File Options:")
    print("  1. main.py (with demo manager)")
    print("  2. main_no_demo.py (production, no demo features)")
    
    source_choice = input("\nSelect source file [1-2] (default: 2): ").strip() or "2"
    main_file = "main.py" if source_choice == "1" else "main_no_demo.py"
    
    if not os.path.exists(main_file):
        print(f"✗ Error: {main_file} not found!")
        return False
    
    print(f"✓ Using: {main_file}")
    
    # 1. Install PyInstaller if not present
    print("\n[1/4] Checking PyInstaller...")
    try:
        import PyInstaller
        print("  ✓ PyInstaller is installed")
    except ImportError:
        print("  Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # 2. Generate Version Info (Windows only)
    version_file = None
    if target == "windows":
        print("\n[2/4] Generating Version Metadata (Windows)...")
        version_file = create_version_info()
        print("  ✓ Created version_info.txt")
    else:
        print("\n[2/4] Skipping version metadata (not needed for Linux/macOS)")
    
    # 3. Build command
    print("\n[3/4] Building executable...")
    
    # Platform-specific settings
    if target == "windows":
        if is_linux:
            print("\n" + "!" * 80)
            print("CRITICAL ERROR: direct Cross-Compilation not supported!")
            print("!" * 80)
            print("PyInstaller cannot build a valid Windows .exe while running on Linux Python.")
            print("The file you generated previously was actually a Linux binary named '.exe',")
            print("which is why your client saw 'This app can\\'t run on your PC'.")
            print("\nSOLUTIONS:")
            print("1. Use GitHub Actions (Recommended) - I have generated a workflow file for you.")
            print("   -> Push your code to GitHub, and it will build a real Windows .exe automatically.")
            print("2. Use Wine - You must install Python for Windows *inside* Wine.")
            print("   -> Then run: wine python build.py")
            print("\nExiting build process to prevent generating broken executable.")
            return False

        mode = "--onedir"
        exe_name = "LeptospirosisPredictor.exe"
        output_msg = "dist\\LeptospirosisPredictor\\LeptospirosisPredictor.exe"
    elif target == "linux":
        mode = "--onedir"
        exe_name = "LeptospirosisPredictor"
        output_msg = "dist/LeptospirosisPredictor/LeptospirosisPredictor"
    else:  # macOS
        mode = "--onedir"
        exe_name = "LeptospirosisPredictor"
        output_msg = "dist/LeptospirosisPredictor.app/Contents/MacOS/LeptospirosisPredictor"
    
    build_cmd = [
        sys.executable, "-m", "PyInstaller",
        f"--name={exe_name}",
        mode,
        "--noconfirm",
        "--clean",
    ]
    
    # Add windowed flag (GUI without console)
    if target in ["windows", "macos"]:
        build_cmd.append("--windowed")
    
    # Add version file only for Windows
    if target == "windows" and version_file:
        build_cmd.append(f"--version-file={version_file}")
    
    # Add data files if database exists
    if os.path.exists("leptospirosis_sim.db"):
        build_cmd.append("--add-data=leptospirosis_sim.db:.")
        print("  Note: Including existing database.")
    else:
        print("  Note: No existing database found. A new one will be created on first run.")
    
    # Add main file
    build_cmd.append(main_file)
    
    try:
        print(f"  Running: {' '.join(build_cmd)}\n")
        subprocess.check_call(build_cmd)
        print("\n  ✓ Build successful!")
    except subprocess.CalledProcessError as e:
        print(f"\n  ✗ Build failed: {e}")
        return False
    finally:
        # Cleanup temp version file
        if version_file and os.path.exists(version_file):
            os.remove(version_file)
    
    print("\n[4/4] Build Complete!")
    print("=" * 70)
    
    # Platform-specific instructions
    print(f"\n✓ Output location: {output_msg}")
    
    if target == "windows":
        print("\n📋 FOR YOUR CLIENT (Windows PC):")
        print("  1. Copy the entire 'dist/LeptospirosisPredictor' folder to their PC")
        print("  2. Run LeptospirosisPredictor.exe")
        print("\n⚠️  NOTE ON VIRUS WARNINGS:")
        print("  If Windows SmartScreen warns them, it's because the app is unsigned.")
        print("  They should click 'More Info' -> 'Run Keep/Run Anyway'")
        print("  If Antivirus deletes it, ask them to add an exclusion.")
    elif target == "linux":
        print("\n📋 FOR LINUX:")
        print(f"  1. Navigate to dist/LeptospirosisPredictor/")
        print(f"  2. Run: ./LeptospirosisPredictor")
        print(f"  3. Or make it executable: chmod +x LeptospirosisPredictor && ./LeptospirosisPredictor")
    else:  # macOS
        print("\n📋 FOR macOS:")
        print("  1. The app is in dist/LeptospirosisPredictor.app")
        print("  2. Double-click to run, or use Terminal:")
        print(f"  3. open dist/LeptospirosisPredictor.app")
    
    print("=" * 70)
    return True

if __name__ == "__main__":
    build()