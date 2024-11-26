# DART Project Documentation

## Project Structure

```
main.py                      # Application entry point - initializes DART and GUI

_vendor/                     # Third-party dependencies
└── wheels/                 # Python wheel files for dependencies
    └── *.whl

assets/                      # Static assets
└── icons/                  # GUI icons for the application
    └── *.png

config/                      # Configuration files
├── style.json             # CustomTkinter theme and UI styling
└── app_config.json        # Application configuration (devices, calibration)

src/                         # Main source code directory
├── app.py                 # Main application class and core logic
├── core/                  # Core application components
│   ├── image_processor.py # Image processing and analysis functions
│   ├── state_manager.py  # Application state management
│   └── config_manager.py # Configuration management
├── data/
│   └── data_handler.py    # Data logging and management (Parquet format)
├── hardware/              # Hardware interface modules
│   ├── camera/
│   │   └── camera_manager.py    # Camera control and video feed management
│   ├── mocap/
│   │   └── qtm_mocap.py        # QTM motion capture system interface
│   └── motion/
│       ├── dyna_controller.py   # Dynamixel servo motor control (pan/tilt)
│       └── theia_controller.py  # Theia lens control (focus/zoom)
├── tracking/              # Target tracking and calibration
│   ├── calibrate.py      # System calibration and coordinate transforms
│   ├── dart_track.py     # Basic tracking implementation
│   └── kalman_filter.py  # Advanced tracking with Adaptive Kalman Filter
├── ui/                    # User interface components
│   ├── main_window.py    # Main window management and layout
│   ├── ui_controller.py  # UI state updates and management
│   ├── components/       # Reusable UI components
│   │   ├── menu_bar.py  # Application menu
│   │   ├── navbar.py    # Navigation sidebar
│   │   └── status_bar.py # Status display
│   └── views/           # Application views
│       ├── base_view.py # Base view class
│       ├── track_view.py # Main tracking view
│       ├── dashboard_view.py # Data analysis view
│       └── theia_control_window.py # Lens control interface
└── utils/                 # Utility functions
    ├── misc_funcs.py     # General helper functions
    └── perf_timings.py   # High-precision performance timing utilities
    
static/                     # Static files and recordings
└── recordings/           # Storage for recorded data
    └── *.mp4            # Video recordings
    └── *.parquet        # Tracking data in Parquet format

```

## Core Components

### 1. Configuration Management (`config_manager.py`)
- Centralized configuration storage in JSON format
- Manages device settings and calibration data
- Handles configuration persistence
- Provides type-safe configuration access

### 2. Hardware Management
#### Camera System (`camera_manager.py`)
- Auto-connects to configured FLIR cameras
- Manages video feed capture and display
- Supports video recording functionality
- Controls exposure and gain settings

#### Motion Control
##### Dynamixel Controller (`dyna_controller.py`)
- Auto-connects to configured COM port
- Controls pan/tilt servo motors
- Handles motor calibration and positioning
- Manages motor gains and operating modes

##### Theia Controller (`theia_controller.py`)
- Auto-connects to configured COM port
- Controls lens focus and zoom
- Provides lens calibration functionality
- Manages lens movement and positioning

##### Motion Capture (`qtm_mocap.py`)
- Manual connection to QTM system
- Provides real-time position tracking
- Handles data streaming and synchronization

### 3. User Interface
#### Main Window (`main_window.py`)
- Manages application layout
- Handles view switching
- Coordinates UI components

#### Views
- Track View: Main tracking interface
- Dashboard View: Data analysis interface
- Component-based architecture
- Consistent styling and behavior

#### UI Controller (`ui_controller.py`)
- Centralizes UI updates
- Manages UI state
- Provides type-safe UI operations

### 4. Process Management
- Main process handles:
  - User interface
  - Camera operations
  - Configuration
- Tracking process handles:
  - Motion capture
  - Motor control
  - Real-time tracking

## Key Features
- Automatic device detection and configuration
- Persistent device settings
- Component-based UI architecture
- Real-time target tracking
- Video recording and playback
- Motion capture integration
- Adaptive tracking algorithms
- System calibration tools
- Data logging and analysis

## Technical Specifications
- Built with Python 3.8+
- Uses CustomTkinter for GUI
- JSON-based configuration
- Real-time performance optimization
- Data logging in Parquet format
- Hardware synchronization capabilities

---

> This project is a sophisticated tracking system combining motion capture, servo control, and video processing for real-time target tracking and analysis.