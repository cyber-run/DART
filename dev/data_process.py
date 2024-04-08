#%%
import numpy as np
import matplotlib.pyplot as plt
from scipy.fft import fft
from scipy.signal import hann

def compute_response(frequency, time_data, input_data, output_data):
    """
    Compute the magnitude and phase response of the system at a specific frequency
    with windowing applied to reduce spectral leakage.
    """
    dt = np.mean(np.diff(time_data))
    window = hann(len(input_data))  # Apply a Hanning window

    # Apply window to both input and output data
    input_data_windowed = input_data * window
    output_data_windowed = output_data * window

    # Rest of the code remains the same...
    input_fft = fft(input_data_windowed)
    output_fft = fft(output_data_windowed)
    freqs = np.fft.fftfreq(len(input_data), dt)

    freq_idx = np.argmin(np.abs(freqs - frequency))
    input_mag = np.abs(input_fft[freq_idx])
    output_mag = np.abs(output_fft[freq_idx])
    magnitude_db = 20 * np.log10(output_mag / input_mag)

    input_phase = np.angle(input_fft[freq_idx])
    output_phase = np.angle(output_fft[freq_idx])
    phase_diff_deg = np.rad2deg(output_phase - input_phase)

    if phase_diff_deg > 180:
        phase_diff_deg += -360

    return magnitude_db, phase_diff_deg


def load_and_process_data(frequencies):
    """
    Load the data for each frequency and compute the magnitude and phase.

    Args:
        frequencies (np.ndarray): Frequencies at which the data was collected.

    Returns:
        tuple: pan_magnitudes and pan_phases for each frequency.
    """
    pan_magnitudes, pan_phases, tilt_magnitudes, tilt_phases = [], [], [], []
    
    for freq in frequencies:
        data_filename = f'data/data_{freq}Hz.npz'
        data = np.load(data_filename)
        time_list, theta_d_list, pan_pos_list, tilt_pos_list = [data[f] for f in data.files]

        pan_magnitude_db, pan_phase_diff_deg = compute_response(freq, time_list, theta_d_list, pan_pos_list)
        tilt_magnitude_db, tilt_phase_diff_deg = compute_response(freq, time_list, theta_d_list, tilt_pos_list)


        pan_magnitudes.append(pan_magnitude_db)
        pan_phases.append(pan_phase_diff_deg)
        tilt_magnitudes.append(tilt_magnitude_db)
        tilt_phases.append(tilt_phase_diff_deg)

    return np.array(pan_magnitudes), np.array(pan_phases), np.array(tilt_magnitudes), np.array(tilt_phases)

def plot_bode(frequencies, pan_magnitudes, pan_phases, tilt_magnitudes, tilt_phases):
    """
    Plot the Bode plot of magnitude and phase against frequencies.

    Args:
        frequencies (np.ndarray): Array of frequencies.
        pan_magnitudes (np.ndarray): Array of pan_magnitudes in dB.
        pan_phases (np.ndarray): Array of pan_phases in degrees.
    """
    plt.figure(figsize=(10, 8))
    
    plt.subplot(2, 1, 1)
    plt.semilogx(frequencies, pan_magnitudes, '-o')
    plt.semilogx(frequencies, tilt_magnitudes, '-o')
    plt.grid(True)
    plt.title('Bode Plot')
    plt.ylabel('Magnitude (dB)')
    plt.legend(['Pan', 'Tilt'])
    
    plt.subplot(2, 1, 2)
    plt.semilogx(frequencies, pan_phases, '-o')
    plt.semilogx(frequencies, tilt_phases, '-o')
    plt.grid(True)
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Phase (degrees)')
    plt.legend(['Pan', 'Tilt'])
    # Set y lim to -30
    plt.ylim(-30, 0)
    
    plt.tight_layout()
    plt.show()

frequencies = np.round(np.logspace(np.log10(0.2), np.log10(10), 30), 30)
pan_magnitudes, pan_phases, tilt_magnitudes, tilt_phases = load_and_process_data(frequencies)
plot_bode(frequencies, pan_magnitudes, pan_phases, tilt_magnitudes, tilt_phases)

#%%

def phase_delay_to_spatial_error(phase_delay, frequency, motion_speed, fov_width, resolution_x):
    """
    Convert phase delay to spatial tracking error.
    """
    # Convert phase delay to time delay
    time_delay = phase_delay / 360 / frequency
    
    # Calculate spatial error in degrees
    spatial_error_deg = motion_speed * time_delay
    
    # Convert spatial error to pixels
    error_pixels = spatial_error_deg * (resolution_x / fov_width)
    
    return error_pixels

def calculate_and_plot_errors(frequencies, pan_phases, tilt_phases, motion_speed, fov_width, fov_height, resolution_x, resolution_y):
    """
    Calculate the spatial tracking errors for all frequencies and plot.
    """
    pan_errors = [phase_delay_to_spatial_error(phase, freq, motion_speed, fov_width, resolution_x)
                  for phase, freq in zip(pan_phases, frequencies)]
    tilt_errors = [phase_delay_to_spatial_error(phase, freq, motion_speed, fov_height, resolution_y)
                   for phase, freq in zip(tilt_phases, frequencies)]
    
    total_error = np.sqrt(np.array(pan_errors) ** 2 + np.array(tilt_errors) ** 2)

    pixel_dist = np.sqrt(resolution_x ** 2 + resolution_y ** 2)

    tracking_error = total_error/pixel_dist
    
    plt.figure(figsize=(10, 6))
    plt.plot(frequencies, tracking_error, '-x')
    plt.xscale('log')
    plt.xlabel('Frequency (Hz)')
    plt.ylabel('Tracking Error (pixels)')
    plt.title('Spatial Tracking Error Across Frequencies')
    plt.grid(True)
    plt.show()

# Parameters for spatial error calculation
motion_speed = 100  # degrees/second
fov_width = 7  # degrees
fov_height = 5  # degrees
resolution_x = 1080  # pixels
resolution_y = 1440 # pixels

# Assuming pan_magnitudes, pan_phases, tilt_magnitudes, tilt_phases are obtained from load_and_process_data
calculate_and_plot_errors(frequencies, pan_phases, tilt_phases, motion_speed, fov_width, fov_height, resolution_x, resolution_y)

#%%

def calculate_spatial_error_for_velocity(velocity, phase_delay, fov_width, resolution_x):
    """
    Calculate the spatial error for a given target velocity.
    """
    # Assume a constant frequency or derive it from velocity if applicable
    frequency = 1.0  # Hz, example fixed frequency
    
    # Convert phase delay to time delay as before
    time_delay = phase_delay / 360 / frequency
    
    # Calculate spatial error in degrees assuming the motion speed equals the target velocity
    spatial_error_deg = velocity * time_delay
    
    # Convert spatial error to pixels
    error_pixels = spatial_error_deg * (resolution_x / fov_width)
    
    return error_pixels

def plot_error_against_velocity(velocities, phase_delay, fov_width, resolution_x):
    """
    Plot spatial tracking error as a function of tangential target velocity.
    """
    errors = [calculate_spatial_error_for_velocity(v, phase_delay, fov_width, resolution_x) for v in velocities]
    
    plt.figure(figsize=(10, 6))
    plt.plot(velocities, errors, '-x')
    plt.xlabel('Tangential Target Velocity (degrees/second)')
    plt.ylabel('Tracking Error (pixels)')
    plt.title('Tracking Error vs. Tangential Target Velocity')
    plt.grid(True)
    plt.show()

# Example parameters
phase_delay = 10  # degrees, example phase delay
fov_width = 90  # degrees
resolution_x = 1920  # pixels
velocities = np.linspace(0, 600, 20)  # Tangential target velocities in degrees/second

plot_error_against_velocity(velocities, phase_delay, fov_width, resolution_x)

#%%


def calculate_and_plot_errors_based_on_velocity(frequencies, pan_phases, tilt_phases, amplitude):
    """
    Calculate the spatial tracking errors based on target velocity and plot the errors against velocities.
    """
    velocities = 2 * amplitude * frequencies  # deg/sec

    # Assuming phase in degrees directly translates into angular error
    pan_errors_deg = amplitude * np.sin(np.radians(pan_phases))
    tilt_errors_deg = amplitude * np.sin(np.radians(tilt_phases))

    # Plotting the tracking error against tangential target velocities
    plt.figure(figsize=(10, 6))
    plt.plot(velocities, pan_errors_deg, '-x')
    plt.plot(velocities, tilt_errors_deg, '-x')
    plt.xlabel('Target Angular Velocity (degrees/second)')
    plt.ylabel('Tracking Error (deg)')
    plt.title('Tracking Error vs. Angular Target Velocity')
    plt.xlim(0, 100)
    plt.grid(True)
    plt.show()

# Parameters for spatial error calculation
amplitude = 30  # degrees

calculate_and_plot_errors_based_on_velocity(frequencies, pan_phases, tilt_phases, amplitude)

# %%

def calculate_angular_fov(distance: float, target_diameter: float) -> float:
    """
    Calculate the angular field of view (FOV) based on the target size and distance.
    Assumes the target occupies the central 25% of the FOV.

    :param distance: Distance to the target in meters.
    :param target_diameter: Diameter of the target in centimeters.
    :return: Angular FOV in degrees.
    """
    # FOV width in cm, since the target is 25% of FOV
    fov_cm = (target_diameter / 0.25)
    # Convert FOV width to angular FOV
    fov_degrees = 2 * np.rad2deg(np.arctan(fov_cm / (2 * distance * 100)))  # distance converted to cm

    print(f"Angular FOV for distance {distance}m: {fov_degrees:.2f} degrees")
    return fov_degrees

def calculate_tracking_error(encoder_resolution: int, angular_fov: float) -> float:
    """
    Calculate the tracking error based on encoder resolution and angular FOV.

    :param encoder_resolution: The resolution of the encoder in steps.
    :param angular_fov: The angular field of view in degrees.
    :return: Tracking error as a percentage.
    """
    # Calculate the angular error corresponding to half the encoder's resolution
    angular_error_per_step = 360 / encoder_resolution  # Total angular range divided by resolution
    half_angular_error = angular_error_per_step / 2
    # Relate this angular error to the angular FOV
    error_ratio = half_angular_error / (angular_fov / 2)  # Divide by 2 for the error on one side
    return error_ratio   # Convert to percentage for readability

# Parameters
encoder_resolution = 4096
target_diameter = 5  # cm
distances = np.linspace(2, 10, 20)  # From 2m to 10m

# Calculate FOV and Errors
angular_fovs = [calculate_angular_fov(distance, target_diameter) for distance in distances]
tracking_errors = [calculate_tracking_error(encoder_resolution, fov) for fov in angular_fovs]

# Plotting
plt.figure(figsize=(10, 6))
plt.plot(distances, tracking_errors, '-o')
plt.xlabel('Distance to Target (m)')
plt.ylabel('Tracking Error (FOV/Resolution')
plt.title('Tracking Error vs. Distance')
plt.grid(True)
plt.show()

