# main.py
import sys
from pathlib import Path
import customtkinter as ctk

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.append(str(src_path))

from DART import DART

if __name__ == "__main__":
    ctk.set_default_color_theme("config/style.json")
    window = ctk.CTk()  # Create main window
    app = DART(window)  # Initialize application