import numpy as np
import math

def smoothing_factor(t_e, cutoff):
    r = 2 * math.pi * cutoff * t_e
    return r / (r + 1)

def exponential_smoothing(a, x, x_prev):
    return a * x + (1 - a) * x_prev

class OneEuroFilter:
    """
    OneEuroFilter implemented to handle numpy arrays for multi-coordinate tracking.
    """
    def __init__(self, t0, x0, dx0=None, min_cutoff=1.0, beta=0.007, d_cutoff=1.0):
        """
        Initialize the one euro filter.
        """
        self.min_cutoff = float(min_cutoff)
        self.beta = float(beta)
        self.d_cutoff = float(d_cutoff)

        self.x_prev = x0.copy()
        if dx0 is None:
            self.dx_prev = np.zeros_like(x0)
        else:
            self.dx_prev = dx0.copy()
            
        self.t_prev = float(t0)

    def __call__(self, t, x):
        """
        Compute the filtered signal.
        """
        t_e = t - self.t_prev
        
        # Avoid division by zero on very first frame or duplicate timestamps
        if t_e <= 0.0:
            return x

        # The filtered derivative of the signal.
        a_d = smoothing_factor(t_e, self.d_cutoff)
        dx = (x - self.x_prev) / t_e
        dx_hat = exponential_smoothing(a_d, dx, self.dx_prev)

        # The filtered signal.
        cutoff = self.min_cutoff + self.beta * np.abs(dx_hat)
        a = smoothing_factor(t_e, cutoff)
        x_hat = exponential_smoothing(a, x, self.x_prev)

        # Memorize the previous values.
        self.x_prev = x_hat
        self.dx_prev = dx_hat
        self.t_prev = t

        return x_hat
