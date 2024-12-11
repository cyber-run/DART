import cv2
import numpy as np
import rerun as rr
import re
import pandas as pd
from pathlib import Path
import json
from scipy.spatial.transform import Rotation

# Get the recordings directory
recordings_dir = Path("static/recordings")

# Find most recent video and parquet files
video_files = list(recordings_dir.glob("*.mp4"))
parquet_files = list(recordings_dir.glob("*.parquet"))

if not video_files or not parquet_files:
    raise FileNotFoundError("No video or parquet files found in recordings directory")

newest_video = max(video_files, key=lambda x: x.stat().st_mtime)
newest_parquet = max(parquet_files, key=lambda x: x.stat().st_mtime)

print(f"Loading newest files:")
print(f"Video: {newest_video.name}")
print(f"Data: {newest_parquet.name}")

# Extract original FPS from filename
fps_match = re.search(r'FPS(\d+\.?\d*)', newest_video.name)
original_fps = float(fps_match.group(1)) if fps_match else 200.9
print(f"Original recording FPS from filename: {original_fps}")

# Get video information using OpenCV
cap = cv2.VideoCapture(str(newest_video))
frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
encoded_fps = cap.get(cv2.CAP_PROP_FPS)
cap.release()

print(f"Video encoded at: {encoded_fps} FPS")
print(f"Total frames: {frame_count}")

# Initialize Rerun
rr.init("DART Data Viewer", spawn=True)

# Set up styling for the plots
rr.log("angles/desired/pan", rr.SeriesLine(color=[255, 0, 0], name="Desired Pan"), timeless=True)
rr.log("angles/desired/tilt", rr.SeriesLine(color=[0, 255, 0], name="Desired Tilt"), timeless=True)
rr.log("angles/encoder/pan", rr.SeriesLine(color=[0, 0, 255], name="Encoder Pan"), timeless=True)
rr.log("angles/encoder/tilt", rr.SeriesLine(color=[255, 255, 0], name="Encoder Tilt"), timeless=True)

# Load and process tracking data
df = pd.read_parquet(newest_parquet)
df = df[df['sync_error_ms'] <= 3].sort_values('relative_time_ms')

# Process trajectory data
trajectory_points = []
positions = []  # For current position
for pos in df['target_position']:
    try:
        pos_str = str(pos).strip('[]')
        pos_array = np.fromstring(pos_str, sep=' ')
        if pos_array.shape[-1] == 3:
            trajectory_points.append(pos_array)
            positions.append(pos_array)  # Keep track of current positions
    except:
        continue

trajectory_points = np.array(trajectory_points)
positions = np.array(positions)

# Calculate bounds for scene setup
min_bounds = trajectory_points.min(axis=0)
max_bounds = trajectory_points.max(axis=0)
center = 2*(min_bounds + max_bounds)
size = np.max(max_bounds - min_bounds)

# Set up World structure with calculated bounds
rr.log("World", rr.ViewCoordinates.RIGHT_HAND_Z_UP, timeless=True)
rr.log("World", rr.Transform3D(translation=center.tolist()), timeless=True)

# Set up the coordinate arrows
rr.log("World", rr.Arrows3D(
    vectors=[[200, 0, 0], [0, 200, 0], [0, 0, 200]],
    origins=[[0, 0, 0], [0, 0, 0], [0, 0, 0]],
    colors=[[255, 100, 100], [100, 255, 100], [100, 100, 255]],
    labels=['X', 'Y', 'Z']
), timeless=True)

# Log video asset which is referred to by frame references
video_asset = rr.AssetVideo(path=str(newest_video))
rr.log("Tracker_Camera", video_asset, static=True)

# Get the encoded timestamps
frame_timestamps_ns = video_asset.read_frame_timestamps_ns()

# Calculate timestamps as they would have been at recording time
period_ns = int(1e9 / original_fps)  # nanoseconds between frames
start_time_ns = frame_timestamps_ns[0]  # keep same start time
original_timestamps_ns = start_time_ns + np.arange(frame_count, dtype=np.int64) * period_ns

# Log video frames with correct timing
rr.send_columns(
    "Tracker_Camera",
    times=[rr.TimeNanosColumn("video_time", original_timestamps_ns)],
    components=[
        rr.VideoFrameReference.indicator(),
        rr.components.VideoTimestamp.nanoseconds(frame_timestamps_ns)
    ],
)

# Convert tracking data timestamps to nanoseconds
tracking_timestamps_ns = (df['relative_time_ms'] * 1_000_000).astype(np.int64)

# Send all angle data as columns
rr.send_columns(
    "angles/desired/pan",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[rr.components.ScalarBatch(df['desired_pan'].to_numpy())]
)

rr.send_columns(
    "angles/desired/tilt",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[rr.components.ScalarBatch(df['desired_tilt'].to_numpy())]
)

rr.send_columns(
    "angles/encoder/pan",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[rr.components.ScalarBatch(df['encoder_pan'].to_numpy())]
)

rr.send_columns(
    "angles/encoder/tilt",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[rr.components.ScalarBatch(df['encoder_tilt'].to_numpy())]
)

# Send trajectory data - one point at each timestamp
rr.send_columns(
    "World/trajectory",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[
        rr.Points3D.indicator(),
        rr.components.Position3DBatch(trajectory_points),
        rr.components.ColorBatch([(200, 200, 200)] * len(trajectory_points)),
        rr.components.RadiusBatch([2.0] * len(trajectory_points))
    ]
)

# Send current position data and update view transform
rr.send_columns(
    "World/current_position",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[
        rr.Points3D.indicator(),
        rr.components.Position3DBatch(positions),
        rr.components.ColorBatch([(255, 255, 255)] * len(positions)),
        rr.components.RadiusBatch([10.0] * len(positions))
    ]
)

# Add transform updates to follow current position
rr.send_columns(
    "World",
    times=[rr.TimeNanosColumn("video_time", tracking_timestamps_ns)],
    components=[
        rr.Transform3D.indicator(),
        rr.components.Translation3DBatch(positions)  # Update transform to follow position
    ]
)

# Load camera calibration data
with open('config/app_config.json', 'r') as f:
    config = json.load(f)

tilt_origin = np.array(config['calibration']['tilt_origin'])
rotation_matrix = np.array(config['calibration']['rotation_matrix'])

# Convert calibration rotation matrix to camera view matrix
# Rearrange axes to match camera view (Z = Forward, X = Right, Y = Down)
camera_rotation = np.column_stack([
    -rotation_matrix[:, 1],  # Right = -Y axis from calibration
    rotation_matrix[:, 2],   # Down = Z axis from calibration
    rotation_matrix[:, 0]    # Forward = X axis from calibration (pan direction)
])

# Convert to axis-angle
r = Rotation.from_matrix(camera_rotation)
axis_angle = r.as_rotvec()
angle = np.linalg.norm(axis_angle)
axis = axis_angle / angle if angle > 0 else np.array([0, 0, 1])

# Camera parameters
image_width = 1440
image_height = 1000
fov_y_degrees = 18.0
aspect = image_width / image_height

# Create the camera entity with RDF coordinates
rr.log("World/camera_frustum", 
    rr.Pinhole(
        resolution=[image_width, image_height],
        fov_y=np.radians(fov_y_degrees),
        aspect_ratio=aspect,
        camera_xyz=rr.ViewCoordinates.RDF,  # Right-Down-Forward to match standard camera coordinates
        image_plane_distance=100.0
    ),
    timeless=True
)

# Create list to store transforms
transforms = []

# Generate transforms for each timestamp
for pan_angle, tilt_angle in zip(df['encoder_pan'], df['encoder_tilt']):
    # First apply the base camera orientation
    base_rotation = Rotation.from_matrix(camera_rotation)
    
    # Convert encoder angles to optical angles
    optical_pan = (pan_angle - 45) * 2   # negative = left, positive = right
    optical_tilt = (tilt_angle - 45) * 2  # negative = down, positive = up
    
    # Pan is around Y axis (left-right rotation)
    pan_rot = Rotation.from_euler('y', optical_pan, degrees=True)
    
    # Apply pan rotation after base rotation
    intermediate_rot = base_rotation * pan_rot
    
    # Tilt is around X axis (up-down rotation)
    tilt_rot = Rotation.from_euler('x', optical_tilt, degrees=True)
    
    # Apply tilt rotation last
    final_rotation = intermediate_rot * tilt_rot
    
    # Convert to axis-angle for Rerun
    axis_angle = final_rotation.as_rotvec()
    angle = np.linalg.norm(axis_angle)
    axis = axis_angle / angle if angle > 0 else np.array([0, 0, 1])
    
    # Create transform
    transform = rr.Transform3D(
        translation=tilt_origin.tolist(),
        rotation=rr.RotationAxisAngle(
            axis=axis.tolist(),
            radians=float(angle)
        )
    )
    transforms.append(transform)

# Send camera transforms for each timestamp
for t, transform in zip(tracking_timestamps_ns, transforms):
    rr.set_time_nanos("video_time", t)
    rr.log("World/camera_frustum", transform)
