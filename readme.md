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
└── style.json             # CustomTkinter theme and UI styling

src/                         # Main source code directory
├── app.py                 # Main application class and core logic
├── core/                  # Core application components
│   ├── image_processor.py # Image processing and analysis functions
│   └── state_manager.py  # Application state management
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
│   └── dart_track_akf.py # Advanced tracking with Adaptive Kalman Filter
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

### 1. Main Application (`app.py`)
- Initializes the main application window
- Manages hardware connections (camera, motors, motion capture)
- Coordinates between different subsystems
- Handles user interface events

### 2. Hardware Integration

#### Camera System (`camera_manager.py`)
- Manages camera connections and settings
- Handles video feed capture and display
- Supports video recording functionality
- Controls exposure and gain settings

#### Motion Control
##### Dynamixel Controller (`dyna_controller.py`)
- Controls pan/tilt servo motors
- Handles motor calibration and positioning
- Manages motor gains and operating modes

##### Theia Controller (`theia_controller.py`)
- Controls lens focus and zoom
- Provides lens calibration functionality
- Manages lens movement and positioning

##### Motion Capture (`qtm_mocap.py`)
- Interfaces with QTM motion capture system
- Provides real-time position tracking
- Handles data streaming and synchronization

### 3. Tracking System

#### Adaptive Kalman Filter (`dart_track_akf.py`)
- Implements advanced target tracking
- Uses adaptive Kalman filtering for position prediction
- Handles latency compensation
- Provides real-time position estimation

#### Calibration (`calibrate.py`)
- Manages system calibration
- Handles coordinate transformations
- Stores and loads calibration data
- Provides verification and visualization tools

### 4. Data Management (`data_handler.py`)
- Handles data logging and storage
- Manages data queues and batch processing
- Supports Parquet file format for data storage
- Provides data merging and organization

### 5. User Interface

#### Main GUI (`main_window.py`)
- Provides main application interface
- Displays video feed and controls
- Manages motor control interface
- Handles recording and playback controls

#### Lens Control GUI (`theia_control_window.py`)
- Provides lens control interface
- Manages focus and zoom controls
- Displays lens status and settings

### 6. Utilities
- Performance timing and optimization
- High-precision timing controls
- System configuration management
- Miscellaneous helper functions

## Key Features
- Real-time target tracking
- Video recording and playback
- Motion capture integration
- Adaptive tracking algorithms
- System calibration tools
- Data logging and analysis
- Hardware control and monitoring
- User-friendly interface

## Technical Specifications
- Built with Python
- Uses CustomTkinter for GUI
- Supports high-speed camera integration
- Real-time performance optimization
- Data logging in Parquet format
- Hardware synchronization capabilities

---

> This project is a sophisticated tracking system combining motion capture, servo control, and video processing for real-time target tracking and analysis.