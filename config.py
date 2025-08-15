import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont
import os # OS module is added

# ========== CONFIGURATION ==========
# customtkinter default settings 
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue") # default theme 

# Constants
SHM_NAME = "telemetry_shared"
SHM_SIZE = 4096
TIMEOUT_THRESHOLD = 3 

DRONE_IMAGE_PATH = "/home/arda/Masaüstü/SP-494/Flight_not_started.png"
DRONE_GIF_PATH = "/home/arda/Masaüstü/SP-494/Drone.gif"

# Card Size
CARD_WIDTH_SMALL = 300 
CARD_HEIGHT_SMALL = 380 
FEED_WIDTH_SMALL = CARD_WIDTH_SMALL - 40 
FEED_HEIGHT_SMALL = 150 

COLORS_DARK = {
    "primary": "#1E1E2E",      
    "secondary": "#2A2A3A",    
    "tertiary": "#272A3A",      
    "accent": "#4E9FEC",        
    "success": "#2ECC71",
    "success_hover": "#27AE60",
    "danger": "#E74C3C",
    "danger_hover": "#C0392B",
    "warning": "#F39C12",
    "dark": "#121212",          
    "card_bg": "#2C3E50",       
    "text_primary": "#FFFFFF",  
    "text_secondary": "#B8B8B8", 
    "gray": "#7F8C8D",          
    "disconnected": "#5B5B5B"   
}

# Light Theme
COLORS_LIGHT = {
    "primary": "#E0E0E0",       
    "secondary": "#F0F0F0",    
    "tertiary": "#E8E8E8",
    "accent": "#1ABC9C",        
    "success": "#28B463",
    "success_hover": "#239B56",
    "danger": "#CB4335",
    "danger_hover": "#B03A2E",
    "warning": "#F5B041",
    "dark": "#FFFFFF",          
    "card_bg": "#ECF0F1",       
    "text_primary": "#333333",   
    "text_secondary": "#666666", 
    "gray": "#AAAAAA",
    "disconnected": "#888888"
}


COLORS = COLORS_DARK #Color Dictionary


try:
    with Image.open(DRONE_IMAGE_PATH) as img:
        img.load()
except FileNotFoundError:
    print(f"INFO: At {DRONE_IMAGE_PATH} creating a fake placeholder image.")
    try:
        img_pl = Image.new('RGB', (FEED_WIDTH_SMALL, FEED_HEIGHT_SMALL), color = (18, 18, 18))
        draw = ImageDraw.Draw(img_pl)
        text = "Flight is not started"
        try:
            
            font_path = "arial.ttf"
            if not os.path.exists(font_path):
                if os.name == 'posix': # Linux/macOS
                    possible_paths = [
                        "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                        "/Library/Fonts/Arial.ttf", 
                    ]
                    for path in possible_paths:
                        if os.path.exists(path):
                            font_path = path
                            break
            font = ImageFont.truetype(font_path, 20)
        except IOError:
            font = ImageFont.load_default()
        bbox = draw.textbbox((0,0), text, font=font)
        textwidth = bbox[2] - bbox[0]
        textheight = bbox[3] - bbox[1]
        x = (img_pl.width - textwidth) / 2
        y = (img_pl.height - textheight) / 2
        draw.text((x, y), text, fill=(248, 248, 242), font=font)
        img_pl.save(DRONE_IMAGE_PATH)
    except Exception as e:
        print(f"ERROR: Failed to create fake placeholder image: {e}")

# Fonts
FONTS = {
    "title": ("Roboto", 24, "bold"),
    "subtitle": ("Roboto", 16, "bold"),
    "body": ("Roboto", 14),
    "small": ("Roboto", 12),
    "button": ("Roboto", 14, "bold"),
    "button_small": ("Roboto", 12, "bold") 
}

COMMANDS = {
    # QGC command: Launches the QGroundControl GUI application.
    "qgc": """
        cd ~/PX4-Autopilot || exit 1;
        export LIBGL_ALWAYS_SOFTWARE=1;
        ./QGroundControl.AppImage &
    """,

    # Starts Drone 1 (ID: 2, Position: 0,5)
    "drone2": """
        cd ~/PX4-Autopilot || exit 1;
        export LIBGL_ALWAYS_SOFTWARE=1;
        tmux kill-session -t drone2_session 2>/dev/null;
        tmux new-session -d -s drone2_session "export LIBGL_ALWAYS_SOFTWARE=1; cd ~/PX4-Autopilot; HEADLESS=1 PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500_mono_cam 	 	PX4_GZ_MODEL_POSE='0,5' ./build/px4_sitl_default/bin/px4 -i 1";
        sleep 50;
        tmux kill-session -t drone2_py 2>/dev/null;
        tmux new-session -d -s drone2_py "python3 /home/arda/Masaüstü/SP-494/drone1.py"
    """,

    # Starts Drone 2 (ID: 1, Position: default)
    "drone1": """
        cd ~/PX4-Autopilot || exit 1;
        export LIBGL_ALWAYS_SOFTWARE=1;
        tmux kill-session -t drone1_session 2>/dev/null;
        tmux new-session -d -s drone1_session "export LIBGL_ALWAYS_SOFTWARE=1; cd ~/PX4-Autopilot; HEADLESS=1 PX4_SYS_AUTOSTART=4001 PX4_SIM_MODEL=gz_x500_mono_cam  ./build/px4_sitl_default/bin/px4 -i 2";
        sleep 50;
        tmux kill-session -t drone1_py 2>/dev/null;
        tmux new-session -d -s drone1_py "python3 /home/arda/Masaüstü/SP-494/drone2.py"
    """
} 
