import logging
import numpy as np
from typing import List, Dict, Optional
import plotly.graph_objects as go

class CalibrationVisualizer:
    def __init__(self):
        self.logger = logging.getLogger("CalibrationVisualizer")

    def visualize_calibration(self, 
                            mirror_data: List[Dict],
                            mirror_center: Optional[np.ndarray] = None,
                            show: bool = True,
                            save_html: Optional[str] = None):
        """Create 3D visualization of calibration data"""
        # Print raw data for debugging
        print("\n=== Visualization Debug Info ===")
        print(f"Number of mirror points: {len(mirror_data)}")
        if mirror_data:
            print("\nFirst mirror point data:")
            print(f"Ray origin: {mirror_data[0]['ray_origin']}")
            print(f"Ray direction: {mirror_data[0]['ray_direction']}")
            print(f"Mocap positions: {mirror_data[0]['mocap_pos']}")
            print(f"Tilt angle: {mirror_data[0]['tilt_angle']}")
        
        # Create figure
        fig = go.Figure()
        
        if not mirror_data:
            print("ERROR: No mirror data provided for visualization")
            return fig
            
        # Plot the stationary L-shaped mocap marker (use first data point)
        mocap_pos = mirror_data[0]['mocap_pos']
        print(f"\nMocap positions shape: {mocap_pos.shape}")
        
        # Plot L-shape markers
        fig.add_trace(go.Scatter3d(
            x=mocap_pos[:, 0],
            y=mocap_pos[:, 1],
            z=mocap_pos[:, 2],
            mode='lines+markers',
            name='Mocap L-Marker',
            line=dict(color='green', width=2),
            marker=dict(size=5, color='green'),
        ))
        
        # Calculate and plot ArUco origin
        aruco_origin = (mocap_pos[0] + mocap_pos[1]) / 2
        print(f"\nArUco origin: {aruco_origin}")
        
        fig.add_trace(go.Scatter3d(
            x=[aruco_origin[0]],
            y=[aruco_origin[1]],
            z=[aruco_origin[2]],
            mode='markers',
            name='ArUco Origin',
            marker=dict(size=8, color='purple', symbol='cross'),
        ))
        
        # Collect and plot camera positions
        camera_positions = np.array([data['ray_origin'] for data in mirror_data])
        # Take the first row of each 3x3 array since they're all the same
        camera_positions = camera_positions[:, 0, :]
        print(f"\nCamera positions shape after reshape: {camera_positions.shape}")
        print(f"First few camera positions:\n{camera_positions[:3]}")
        
        # Plot camera positions as a single trace
        fig.add_trace(go.Scatter3d(
            x=camera_positions[:, 0],
            y=camera_positions[:, 1],
            z=camera_positions[:, 2],
            mode='markers',
            name='Camera Positions',
            marker=dict(size=5, color='red'),
            showlegend=True
        ))
        
        # Plot all rays as a single trace
        ray_x = []
        ray_y = []
        ray_z = []
        
        for data in mirror_data:
            origin = data['ray_origin'][0]
            ray_x.extend([origin[0], aruco_origin[0], None])  # None creates a break in the line
            ray_y.extend([origin[1], aruco_origin[1], None])
            ray_z.extend([origin[2], aruco_origin[2], None])
        
        fig.add_trace(go.Scatter3d(
            x=ray_x,
            y=ray_y,
            z=ray_z,
            mode='lines',
            name='Camera Rays',
            line=dict(color='blue', width=1),
            showlegend=True
        ))
        
        if mirror_center is not None:
            print(f"\nMirror center: {mirror_center}")
            fig.add_trace(go.Scatter3d(
                x=[mirror_center[0]],
                y=[mirror_center[1]],
                z=[mirror_center[2]],
                mode='markers',
                name='Mirror Center',
                marker=dict(size=10, color='red', symbol='diamond'),
            ))
        
        # Update layout
        fig.update_layout(
            title='Mirror Calibration Visualization',
            scene=dict(
                xaxis_title='X (mm)',
                yaxis_title='Y (mm)',
                zaxis_title='Z (mm)',
                aspectmode='data'
            ),
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=0.99,
                xanchor="left",
                x=0.01
            )
        )
        
        print("\n=== End Debug Info ===\n")
        
        # Save if requested
        if save_html:
            fig.write_html(save_html)
            print(f"Visualization saved to {save_html}")
        
        # Show if requested
        if show:
            fig.show()
            
        return fig
