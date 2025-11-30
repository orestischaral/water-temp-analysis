"""
Fourier-Based Filtering Module

Functions for FFT-based temperature data filtering including diurnal
cycle removal and seasonal trend removal.
"""

import numpy as np
from scipy import signal
import matplotlib.pyplot as plt


def analyze_seasonality_fft(temperatures, timestamps=None):
    """
    Analyze seasonality using FFT and return frequency spectrum.

    Returns:
        Tuple of (frequencies, magnitude spectrum)
    """
    fft_values = np.fft.fft(temperatures)
    magnitude = np.abs(fft_values)
    frequencies = np.fft.fftfreq(len(temperatures))
    return frequencies, magnitude


def remove_seasonality_fft(temperatures):
    """
    Remove seasonal components using FFT.

    Identifies and removes the largest frequency components (seasonal trends).

    Returns:
        Tuple of (deseasonalized temperatures, removed magnitudes)
    """
    n = len(temperatures)
    fft_vals = np.fft.fft(temperatures)
    magnitude = np.abs(fft_vals)

    # Smooth magnitude spectrum
    if n > 5:
        magnitude_smooth = np.convolve(magnitude, np.ones(5)/5, mode='same')
    else:
        magnitude_smooth = magnitude

    # Find peaks (high-magnitude frequencies)
    threshold = np.percentile(magnitude_smooth, 90)
    high_freq_indices = np.where(magnitude_smooth > threshold)[0]

    # Zero out high-magnitude frequencies
    fft_filtered = fft_vals.copy()
    removed_magnitude = np.zeros_like(magnitude)

    for idx in high_freq_indices:
        removed_magnitude[idx] = magnitude[idx]
        fft_filtered[idx] = 0

    # Inverse FFT to get deseasonalized signal
    deseasonalized = np.real(np.fft.ifft(fft_filtered))

    return deseasonalized, removed_magnitude


def remove_diurnal_cycle(temperatures, timestamps):
    """
    Remove the 24-hour diurnal cycle from temperature data.

    Uses FFT to identify and extract the 24-hour component.

    Returns:
        Tuple of (detrended temperatures, diurnal component)
    """
    n = len(temperatures)

    # Get sampling period
    if len(timestamps) > 1:
        dt = (timestamps[1] - timestamps[0]).total_seconds() / 3600.0  # in hours
    else:
        dt = 1.0

    # Perform FFT
    fft_vals = np.fft.fft(temperatures)
    frequencies_hz = np.fft.fftfreq(n, dt)

    magnitude = np.abs(fft_vals)

    # Find 24-hour (1/24 Hz) component
    target_freq = 1.0 / 24.0  # 1 cycle per 24 hours
    closest_idx = np.argmin(np.abs(frequencies_hz - target_freq))

    # Extract diurnal component
    diurnal_fft = np.zeros_like(fft_vals)
    diurnal_fft[closest_idx] = fft_vals[closest_idx]
    if closest_idx != 0:
        diurnal_fft[n - closest_idx] = fft_vals[n - closest_idx]  # Mirror for real signal

    diurnal_component = np.real(np.fft.ifft(diurnal_fft))

    # Remove diurnal component
    detrended = temperatures - diurnal_component

    return detrended, diurnal_component


def apply_filter(temperatures, timestamps, filter_type="none"):
    """
    Apply the specified filter to temperature data.

    Parameters:
        temperatures: Temperature array
        timestamps: DateTime array
        filter_type: "none", "diurnal", "seasonal", or "both"

    Returns:
        Filtered temperature array
    """
    if filter_type == "none":
        return temperatures
    elif filter_type == "diurnal":
        filtered, _ = remove_diurnal_cycle(temperatures, timestamps)
        return filtered
    elif filter_type == "seasonal":
        filtered, _ = remove_seasonality_fft(temperatures)
        return filtered
    elif filter_type == "both":
        # Apply both filters in sequence
        filtered, _ = remove_diurnal_cycle(temperatures, timestamps)
        filtered, _ = remove_seasonality_fft(filtered)
        return filtered
    else:
        return temperatures