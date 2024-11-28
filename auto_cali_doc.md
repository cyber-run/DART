# Mirror Calibration System Documentation

## System Overview
The mirror calibration system determines:
1. The transformation between camera and motion capture coordinate systems
2. The center of rotation of a tilting mirror used for tracking

## Hardware Components
- Camera with view of ArUco marker
- Motion capture system tracking L-shaped marker
- Dynamixel servo motor controlling mirror tilt
- Mirror mounted on tilt motor
- ArUco marker mounted on L-shaped mocap marker

## Coordinate Systems & Transformations

### 1. Camera Space
- Origin: Camera optical center
- Units: Meters (from ArUco detection)
- ArUco marker pose given as (R_cam, t_cam) relative to camera

### 2. Mocap Space  
- Origin: Motion capture system origin
- Units: Millimeters
- L-marker pose defines coordinate frame (R_mocap, t_mocap)

### 3. Transformation
- Maps points from camera to mocap space:
  ```
  p_mocap = R @ p_camera + T
  ```
- R and T found using corresponding ArUco and L-marker poses

## Calibration Process

### 1. Initial Setup
1. Initialize hardware connections
2. Move mirror to center position (26.4°)
3. Create calibration manager instance

### 2. Capture Static Poses
1. Record L-marker positions (p₀, p₁, p₂)
2. Compute mocap coordinate frame:
   ```
   x = (p₁ - p₀)/‖p₁ - p₀‖  # Long edge direction
   z = normalize(cross(p₁ - p₀, p₂ - p₀))
   y = cross(z, x)
   R_mocap = [x y z]
   t_mocap = (p₀ + p₁)/2  # Center of long edge
   ```
3. Detect ArUco marker to get camera frame pose
4. Compute camera-mocap transformation (R, T)

### 3. Mirror Scan
For angles from (center - 2°) to (center + 2°) in 0.1° steps:
1. Move motor to angle
2. Verify position within 0.1° tolerance
3. Detect ArUco to get new camera pose
4. Compute ray in camera space:
   ```
   origin = -R_cam.T @ t_cam * 1000  # Convert to mm
   direction = R_cam[:, 2]  # Camera Z-axis
   ```
5. Transform ray to mocap space
6. Store ray data with tilt angle

### 4. Mirror Center Computation
1. For each ray i, form projection matrix:
   ```
   P_i = I - d_i @ d_i.T  # d_i is ray direction
   ```
2. Solve least squares system:
   ```
   [P₁]         [P₁o₁]
   [P₂] x = [P₂o₂]
   [...]       [...]
   [Pₙ]         [Pₙoₙ]
   ```
3. Solution x is mirror center
4. Compute RMS error from ray distances
5. Generate 3D visualization
6. Save calibration results

## Error Handling
- Retry logic for motor movements
- Validation of ArUco detections
- Position tolerance checking
- Minimum data point requirements
- Hardware cleanup on exit

## Output
- Mirror center position in mocap space
- RMS error of ray intersection fit
- Camera-mocap transformation matrices
- 3D visualization of calibration
- Saved calibration file

## Key Parameters
- Motor center position: 26.4°
- Scan range: ±2° from center
- Step size: 0.1°
- Position tolerance: 0.1°
- Minimum mirror points: 5
- ArUco marker size: 0.04m
