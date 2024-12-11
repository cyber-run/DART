import numpy as np
from typing import Tuple

class AdaptiveKalmanFilter:
    """
    Adaptive Kalman Filter for 3D position tracking with velocity and acceleration estimation.
    Implements an adaptive process noise adjustment based on innovation monitoring.
    """
    def __init__(self):
        # State vector dimension (position, velocity, acceleration in 3D)
        self.dim_x = 9
        # Measurement vector dimension (position in 3D)
        self.dim_z = 3

        # Initialize state estimate and covariance
        self.state_estimate = np.zeros((self.dim_x, 1))
        self.estimate_covariance = np.eye(self.dim_x) * 1e-3

        # Initialize matrices
        self.F = np.eye(self.dim_x)  # State transition matrix
        self.H = np.zeros((self.dim_z, self.dim_x))  # Observation matrix
        self.H[:3, :3] = np.eye(3)

        # Process and measurement noise
        self.Q0 = np.eye(self.dim_x) * 1e-4  # Increased from 1e-6 for faster response
        self.Q = self.Q0.copy()  # Current process noise
        self.R = np.eye(self.dim_z) * 1e-5   # Decreased from 1e-4 to trust measurements more

        # Adaptive parameters
        self.alpha = 1.0  # Adaptive factor
        self.alpha_min = 0.2  # Increased minimum to maintain some responsiveness
        self.alpha_max = 20.0  # Increased from 10.0 to allow more aggressive adaptation
        self.expected_innovation_variance = 1e-4  # Decreased from 1e-3 for faster adaptation

    def create_F(self, delta_t: float) -> np.ndarray:
        """
        Create state transition matrix for given time step.
        
        Args:
            delta_t: Time step in seconds
            
        Returns:
            Updated state transition matrix
        """
        dt = delta_t
        dt2 = 0.5 * dt ** 2
        F = np.eye(self.dim_x)
        F[:3, 3:6] = np.eye(3) * dt
        F[:3, 6:9] = np.eye(3) * dt2
        F[3:6, 6:9] = np.eye(3) * dt
        return F

    def update_F(self, delta_t: float) -> None:
        """Update state transition matrix with new time step."""
        self.F = self.create_F(delta_t)

    def predict(self) -> None:
        """Perform Kalman filter prediction step."""
        self.state_estimate = self.F @ self.state_estimate
        self.estimate_covariance = (
            self.F @ self.estimate_covariance @ self.F.T + self.Q
        )

    def update(self, measurement: np.ndarray) -> None:
        """
        Perform Kalman filter update step with new measurement.
        
        Args:
            measurement: 3D position measurement vector
        """
        S = self.H @ self.estimate_covariance @ self.H.T + self.R
        K = self.estimate_covariance @ self.H.T @ np.linalg.inv(S)
        y = measurement - self.H @ self.state_estimate
        
        self.state_estimate = self.state_estimate + K @ y
        I = np.eye(self.dim_x)
        self.estimate_covariance = (I - K @ self.H) @ self.estimate_covariance

    def compute_alpha(self, normalized_innovation: float) -> float:
        """
        Compute adaptive factor based on normalized innovation.
        
        Args:
            normalized_innovation: Innovation normalized by its covariance
            
        Returns:
            Updated adaptive factor
        """
        alpha = 1 + (normalized_innovation - self.expected_innovation_variance) / self.expected_innovation_variance
        return max(self.alpha_min, min(alpha, self.alpha_max))

    def adapt_Q(self, measurement: np.ndarray) -> None:
        """
        Adapt process noise based on measurement innovation.
        
        Args:
            measurement: Current measurement vector
        """
        innovation = measurement - self.H @ self.state_estimate
        innovation_covariance = self.H @ self.estimate_covariance @ self.H.T + self.R
        normalized_innovation = (
            innovation.T @ np.linalg.inv(innovation_covariance) @ innovation
        )

        self.alpha = self.compute_alpha(normalized_innovation)
        self.Q = self.alpha * self.Q0

    def predict_latency(self, latency_duration: float) -> None:
        """
        Predict state forward to compensate for system latency.
        
        Args:
            latency_duration: Time to predict forward in seconds
        """
        F_latency = self.create_F(latency_duration)
        self.state_estimate = F_latency @ self.state_estimate
        self.estimate_covariance = (
            F_latency @ self.estimate_covariance @ F_latency.T + self.Q
        )

    def get_position(self) -> np.ndarray:
        """
        Get current estimated position.
        
        Returns:
            3D position vector
        """
        return self.state_estimate[:3].flatten() 