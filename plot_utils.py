import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D

class PlotUtils:
    @staticmethod
    def create_trajectory_plot(target_x, target_y, target_z, figsize=(6, 4)):
        fig = plt.figure(figsize=figsize)
        ax = fig.add_subplot(111, projection='3d')
        ax.plot(target_x, target_y, target_z, marker='', linestyle='-', label='Target Position')
        ax.set_xlabel('X (mm)')
        ax.set_ylabel('Y (mm)')
        ax.set_zlabel('Z (mm)')
        ax.legend()
        
        # Remove the axis fill
        ax.xaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.yaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.zaxis.set_pane_color((1.0, 1.0, 1.0, 0.0))
        ax.xaxis._axinfo["grid"]['color'] =  (1,1,1,0)
        ax.yaxis._axinfo["grid"]['color'] =  (1,1,1,0)
        ax.zaxis._axinfo["grid"]['color'] =  (1,1,1,0)

        return fig

    @staticmethod
    def create_pan_tilt_plots(time_stamps, desired_pan, encoder_pan, desired_tilt, encoder_tilt, figsize=(6, 6)):
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=figsize)
        
        # Pan plot
        ax1.plot(time_stamps, desired_pan, label='Desired', color='white', linestyle='-')
        ax1.plot(time_stamps, encoder_pan, label='Encoder', color='white', linestyle='--')
        ax1.set_ylabel('Pan (degrees)')
        ax1.legend()
        ax1.grid(True, color='gray', linestyle=':', linewidth=0.5)
        
        # Tilt plot
        ax2.plot(time_stamps, desired_tilt, label='Desired', color='white', linestyle='-')
        ax2.plot(time_stamps, encoder_tilt, label='Encoder', color='white', linestyle='--')
        ax2.set_xlabel('Time (s)')
        ax2.set_ylabel('Tilt (degrees)')
        ax2.legend()
        ax2.grid(True, color='gray', linestyle=':', linewidth=0.5)
                
        return fig