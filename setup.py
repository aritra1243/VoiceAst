"""
Setup script for VoiceAst
Downloads Vosk model and prepares the environment
"""
import os
import sys
import urllib.request
import zipfile
from pathlib import Path

# Vosk model URL (small English model ~40MB)
VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
VOSK_MODEL_NAME = "vosk-model-small-en-us-0.15"

def download_vosk_model():
    """Download and extract Vosk speech recognition model"""
    models_dir = Path(__file__).parent / "models"
    models_dir.mkdir(exist_ok=True)
    
    model_path = models_dir / VOSK_MODEL_NAME
    
    if model_path.exists():
        print(f"✓ Vosk model already exists at: {model_path}")
        return True
    
    print("Downloading Vosk speech recognition model...")
    print(f"URL: {VOSK_MODEL_URL}")
    print("This may take a few minutes (approx 40MB)...")
    
    zip_path = models_dir / f"{VOSK_MODEL_NAME}.zip"
    
    try:
        # Download with progress
        def download_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            sys.stdout.write(f"\rDownload progress: {percent:.1f}%")
            sys.stdout.flush()
        
        urllib.request.urlretrieve(VOSK_MODEL_URL, zip_path, download_progress)
        print("\n✓ Download complete!")
        
        # Extract
        print(f"Extracting to {models_dir}...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(models_dir)
        
        print("✓ Extraction complete!")
        
        # Clean up zip file
        zip_path.unlink()
        print("✓ Cleaned up temporary files")
        
        return True
        
    except Exception as e:
        print(f"\n✗ Error downloading model: {e}")
        print("\nPlease download manually from:")
        print(VOSK_MODEL_URL)
        print(f"Extract to: {models_dir}")
        return False

def create_directories():
    """Create necessary directories"""
    base_dir = Path(__file__).parent
    
    directories = [
        base_dir / "backend",
        base_dir / "frontend",
        base_dir / "models",
        base_dir / "logs",
    ]
    
    for directory in directories:
        directory.mkdir(exist_ok=True)
        print(f"✓ Created directory: {directory.name}")

def check_dependencies():
    """Check if required packages are installed"""
    required_packages = [
        "fastapi",
        "uvicorn",
        "vosk",
        "pyttsx3",
        "pyautogui",
        "pymongo",
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print("\n⚠ Missing packages:")
        for package in missing_packages:
            print(f"  - {package}")
        print("\nPlease run: pip install -r requirements.txt")
        return False
    
    print("✓ All required packages are installed")
    return True

def create_env_file():
    """Create .env file if it doesn't exist"""
    base_dir = Path(__file__).parent
    env_file = base_dir / ".env"
    env_example = base_dir / ".env.example"
    
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy(env_example, env_file)
        print("✓ Created .env file from template")
    elif env_file.exists():
        print("✓ .env file already exists")

def main():
    """Main setup function"""
    print("=" * 60)
    print("VoiceAst Setup")
    print("=" * 60)
    print()
    
    # Create directories
    print("Creating project directories...")
    create_directories()
    print()
    
    # Check dependencies
    print("Checking dependencies...")
    if not check_dependencies():
        sys.exit(1)
    print()
    
    # Create .env file
    print("Setting up environment...")
    create_env_file()
    print()
    
    # Download Vosk model
    print("Setting up Vosk speech recognition model...")
    if not download_vosk_model():
        sys.exit(1)
    print()
    
    print("=" * 60)
    print("✓ Setup complete!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Review and edit .env file if needed")
    print("2. Start backend: cd backend && python main.py")
    print("3. Open frontend/index.html in browser")
    print()

if __name__ == "__main__":
    main()
