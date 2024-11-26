## DART Implementation Guide

### Overview
The Theia lens controller in DART uses absolute positioning for precise control of zoom and focus. The system maintains state persistence between sessions and implements robust position verification.

### Control Architecture
1. **Position Management**
   - Uses absolute positioning (G90 mode)
   - Zoom range: 0-50000 steps
   - Focus range: 0-65000 steps
   - Positions stored in app_config.json

2. **Initialization Sequence**
   ```
   1. Reset and initialize controller ($B2)
   2. Configure microstepping (M243)
   3. Set normal move mode (M230)
   4. Set absolute positioning (G90)
   5. Configure motor parameters
   6. Load last positions from config
   ```

3. **Homing Procedure**
   ```
   Zoom Axis:
   1. Switch to relative mode (G91)
   2. Move forward 5000 steps
   3. Use forced mode to find home
   4. Set position to 0 (G92)
   5. Return to absolute mode (G90)

   Focus Axis:
   1. Switch to relative mode (G91)
   2. Move backward to find home
   3. Set position to 0
   4. Move to mechanical limit
   5. Return to absolute mode (G90)
   ```

### Position Management
1. **State Persistence**
   - Positions saved in config on window close
   - Loaded and set on startup
   - Updated only after motion complete

2. **Position Verification**
   ```
   1. Check motion flags
   2. Wait for motion complete
   3. Read position
   4. Verify with second read
   5. Update if stable
   ```

### Best Practices
1. **Motion Control**
   - Always use absolute positioning for normal operation
   - Only use relative mode during homing
   - Wait for motion completion before position updates

2. **Error Handling**
   - Verify motion completion
   - Validate position readings
   - Handle communication timeouts

3. **Configuration Updates**
   - Update config only when positions are stable
   - Save positions before shutdown
   - Verify loaded positions on startup

### Status Response Format
Status command (!1) returns 9 values:
```
[zoom_pos, focus_pos, iris_pos, zoom_pi, focus_pi, iris_pi, zoom_move, focus_move, iris_move]

Example: [496, 19936, 0, 1, 1, 1, 0, 0, 0]
         |    |      |  |  |    |  |  |  |
         |    |      |  |  |    |  |  |  └─ Iris moving
         |    |      |  |  |    |  |  └──── Focus moving
         |    |      |  |  |    |  └─────── Zoom moving
         |    |      |  |  |    └────────── Iris PI state
         |    |      |  |  └───────────── Focus PI state
         |    |      |  └──────────────── Zoom PI state
         |    |      └─────────────────── Iris position
         |    └────────────────────────── Focus position
         └───────────────────────────── Zoom position
```

### Common Issues
1. **Position Instability**
   - Cause: Reading position during motion
   - Solution: Wait for motion completion

2. **Homing Failures**
   - Cause: Mechanical limits not detected
   - Solution: Check PI LED settings and voltage

3. **Communication Errors**
   - Cause: Serial port timing issues
   - Solution: Implement command retry logic

   ## Supported G-code commands for Theia SCF4 Controller

| Category                       | Command | Description                                | Returns                          |
|--------------------------------|---------|--------------------------------------------|----------------------------------|
| **Version strings and identification commands** ||||
| -                              | $S      | Return version, SN, model, and brand strings | See details below              |
| **Controller initialization**  ||||
| -                              | $B1     | Reset motor driver                         | OK                               |
| -                              | $B2     | Reset and initialize motor driver          | OK                               |
| -                              | $B3     | Reset STM32F103 processor                  | OK                               |
| **Motion commands**            ||||
| -                              | G0      | Rapid positioning                          | OK                               |
| -                              | G4      | Wait / stall after complete                | OK                               |
| -                              | G90     | Absolute programming mode                  | OK                               |
| -                              | G91     | Incremental programming mode               | OK                               |
| -                              | G92     | Set position                               | OK                               |
| **Miscellaneous function**     ||||
| -                              | M0      | Compulsory stop                            | OK                               |
| -                              | M7      | DN function with filter (VIS)              | OK                               |
| -                              | M8      | DN function no filter (IR + VIS)           | OK                               |
| -                              | M230    | Set normal move                            | OK                               |
| -                              | M231    | Set normal + forced move                   | OK                               |
| -                              | M232    | Set PI low/high detection voltage          | OK                               |
| -                              | M234    | Set motor and DN drive current             | OK                               |
| -                              | M235    | Set motor idle current                     | OK                               |
| -                              | M238    | PI LED on (some lenses leak light into sensor) | OK                           |
| -                              | M239    | PI LED off                                 | OK                               |
| -                              | M240    | Set motor drive speed                      | OK                               |
| -                              | M245    | Drive AUX output to low (high resistance output) | OK                          |
| -                              | M246    | Drive AUX output to high (low resistance output) | OK                          |
| -                              | M247    | Read power supply voltage value            | ADC=xxxx                         |
| **Advanced function**          ||||
| -                              | M241    | Dividing setting 1                         | OK                               |
| -                              | M242    | Pulse generation control 1                 | OK                               |
| -                              | M243    | Microstepping                              | OK                               |
| -                              | M244    | Dividing setting 2                         | OK                               |
| **Status commands**            ||||
| -                              | !1      | Return motor position, limit switch, moving status | 4000, 20000, 0, 0, 0, 0, 0, 0 |

