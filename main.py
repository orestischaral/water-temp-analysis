import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from collections import defaultdict
from statsmodels.graphics.tsaplots import plot_acf

# =============================
# 0. PARAMETERS
# =============================

# UP spikes:
#   start when next - current >= +0.5
#   end   when value <= base + 0.2
UP_JUMP_THRESHOLD = 0.5
UP_RELAX_OFFSET = 0.2

# DOWN spikes:
#   start when next - current <= -0.5
#   end   when value >= base - 0.2
DOWN_JUMP_THRESHOLD = 0.5
DOWN_RELAX_OFFSET = 0.2


# =============================
# 1. SPIKE DETECTION FUNCTIONS
# =============================

def find_spikes(timestamps, values, direction="up",
                up_threshold=None, up_offset=None,
                down_threshold=None, down_offset=None):
    """
    Generic spike detector over a 1D values array.

    direction = "up":
        start when next - current >= +up_threshold
        end   when value <= base + up_offset

    direction = "down":
        start when next - current <= -down_threshold
        end   when value >= base - down_offset
    """
    # Use provided parameters or fall back to globals
    if up_threshold is None:
        up_threshold = UP_JUMP_THRESHOLD
    if up_offset is None:
        up_offset = UP_RELAX_OFFSET
    if down_threshold is None:
        down_threshold = DOWN_JUMP_THRESHOLD
    if down_offset is None:
        down_offset = DOWN_RELAX_OFFSET

    spikes = []
    n = len(values)
    i = 0

    while i < n - 1:
        delta = values[i + 1] - values[i]

        if direction == "up":
            # --- UP spike logic ---
            start_condition = (delta >= up_threshold)
            base_value = values[i]
            cutoff_value = base_value + up_offset

            def end_condition(v):
                return v <= cutoff_value

        elif direction == "down":
            # --- DOWN spike logic ---
            start_condition = (delta <= -down_threshold)
            base_value = values[i]
            cutoff_value = base_value - down_offset

            def end_condition(v):
                return v >= cutoff_value
        else:
            raise ValueError("direction must be 'up' or 'down'")

        # Start of a spike?
        if start_condition:
            start_idx = i

            # Find spike end
            j = i + 1
            end_idx = n - 1  # default: till the end if never relaxes

            while j < n:
                if end_condition(values[j]):
                    end_idx = j
                    break
                j += 1

            spike_values = values[start_idx:end_idx + 1]
            spike_times = timestamps[start_idx:end_idx + 1]

            spike = {
                "direction": direction,
                "start_index": start_idx,
                "end_index": end_idx,
                "start_datetime": spike_times[0],
                "end_datetime": spike_times[-1],
                "base_value": base_value,
                "max_value": float(np.max(spike_values)),
                "min_value": float(np.min(spike_values)),
                "num_measurements": len(spike_values),
                "values": spike_values.tolist(),
                "times": spike_times.tolist(),
            }
            spikes.append(spike)

            i = end_idx + 1  # jump past this spike
        else:
            i += 1

    return spikes


def add_inner_spike_info(outer_spikes, direction, up_jump_threshold=None, up_relax_offset=None, down_jump_threshold=None, down_relax_offset=None):
    """
    For each outer spike, find inner spikes of the same direction
    inside its own values/times.
    """
    for outer_spike in outer_spikes:
        inner_timestamps = pd.to_datetime(outer_spike["times"]).to_numpy()
        inner_values = pd.Series(outer_spike["values"]).to_numpy()

        inner_spikes = find_spikes(inner_timestamps, inner_values, direction=direction, up_threshold=up_jump_threshold, up_offset=up_relax_offset, down_threshold=down_jump_threshold, down_offset=down_relax_offset)

        outer_spike["inner_spikes"] = inner_spikes
        outer_spike["inner_spike_count"] = len(inner_spikes)

        if inner_spikes:
            # strongest inner spike by amplitude
            for s in inner_spikes:
                if direction == "up":
                    s["amplitude"] = s["max_value"] - s["base_value"]
                else:  # down
                    s["amplitude"] = s["base_value"] - s["min_value"]

            strongest_inner = max(inner_spikes, key=lambda s: s["amplitude"])
            outer_spike["highest_inner_max_value"] = strongest_inner["max_value"]
            outer_spike["highest_inner_min_value"] = strongest_inner["min_value"]
            outer_spike["highest_inner_amplitude"] = strongest_inner["amplitude"]
        else:
            outer_spike["highest_inner_max_value"] = None
            outer_spike["highest_inner_min_value"] = None
            outer_spike["highest_inner_amplitude"] = 0.0


def build_spike_ship_relations(spikes, eta_series, etd_series, ships_df, label):
    """
    For a list of spikes and ship ETA/ETD columns, build a table
    relating spikes to ships whose [ETA, ETD] overlaps the spike interval.
    """
    # Handle missing ship data
    if ships_df is None or eta_series is None or etd_series is None:
        return pd.DataFrame(columns=["series_label", "spike_id", "spike_start", "spike_end", "overlapping_ships"])

    rows = []
    for spike_idx, spike in enumerate(spikes, start=1):
        spike_start = spike["start_datetime"]
        spike_end = spike["end_datetime"]

        # Ship overlaps spike if [ETA, ETD] intersects [spike_start, spike_end]
        overlaps = ships_df[(eta_series <= spike_end) & (etd_series >= spike_start)]

        overlapping_ship_names = overlaps.iloc[:, 1].tolist()  # column 2 = ship name

        rows.append({
            "series_label": label,       # e.g. "erinia_25-UP"
            "spike_id": spike_idx,
            "spike_start": spike_start,
            "spike_end": spike_end,
            "overlapping_ships": overlapping_ship_names,
        })

    return pd.DataFrame(rows)


# =============================
# THERMAL STRATIFICATION ANALYSIS
# =============================

def compute_stratification(loc1_name, loc1_temps, loc1_times, loc2_name, loc2_temps, loc2_times):
    """
    Compute temperature difference between two locations.
    Handles cases where timestamps may not be perfectly aligned.
    Returns: dict with differences, timestamps, and statistics, or None if data unavailable
    """
    if loc1_temps is None or loc2_temps is None or len(loc1_temps) == 0 or len(loc2_temps) == 0:
        print(f"  [Debug] Missing temperature data for {loc1_name} or {loc2_name}")
        return None

    try:
        # Convert to pandas Series for easier handling
        # Handle both datetime64 and other timestamp formats
        loc1_times_dt = pd.to_datetime(loc1_times)
        loc2_times_dt = pd.to_datetime(loc2_times)

        loc1_series = pd.Series(loc1_temps, index=loc1_times_dt)
        loc2_series = pd.Series(loc2_temps, index=loc2_times_dt)

        # Find common timestamps (only compute for matching times)
        common_index = loc1_series.index.intersection(loc2_series.index)

        if len(common_index) == 0:
            # No exact match - try with tolerance matching (round to nearest minute)
            print(f"  [Debug] No exact timestamp match. Trying with 1-minute tolerance...")
            print(f"  [Debug] {loc1_name}: {len(loc1_times)} points ({loc1_times_dt[0]} to {loc1_times_dt[-1]})")
            print(f"  [Debug] {loc2_name}: {len(loc2_times)} points ({loc2_times_dt[0]} to {loc2_times_dt[-1]})")

            # Round timestamps to nearest minute for matching
            loc1_times_rounded = loc1_times_dt.round('1min')
            loc2_times_rounded = loc2_times_dt.round('1min')

            loc1_series_rounded = pd.Series(loc1_temps, index=loc1_times_rounded)
            loc2_series_rounded = pd.Series(loc2_temps, index=loc2_times_rounded)

            common_index = loc1_series_rounded.index.intersection(loc2_series_rounded.index)

            if len(common_index) == 0:
                print(f"  [Debug] Still no match even with 1-minute tolerance. Data is too misaligned.")
                return None

            # Use the rounded versions
            loc1_series = loc1_series_rounded
            loc2_series = loc2_series_rounded
            print(f"  [Debug] Success! Found {len(common_index)} matching points after rounding to nearest minute")
    except Exception as e:
        print(f"  [Debug] Error converting timestamps: {str(e)}")
        return None

    # Get the temperatures at common timestamps
    loc1_aligned = loc1_series.loc[common_index].values
    loc2_aligned = loc2_series.loc[common_index].values
    timestamps_aligned = common_index.to_numpy()

    # Compute temperature difference (loc1 - loc2)
    temp_diff = loc1_aligned - loc2_aligned

    # Compute statistics
    mean_diff = float(np.mean(temp_diff))
    max_diff = float(np.max(temp_diff))
    min_diff = float(np.min(temp_diff))
    std_diff = float(np.std(temp_diff))

    # Find where location 1 is warmer vs location 2
    loc1_warmer_count = int(np.sum(temp_diff > 0))
    loc2_warmer_count = int(np.sum(temp_diff < 0))

    # Count skipped points
    total_points_loc1 = len(loc1_temps)
    total_points_loc2 = len(loc2_temps)
    common_points = len(common_index)
    skipped_count = total_points_loc1 + total_points_loc2 - (2 * common_points)

    return {
        "loc1_name": loc1_name,
        "loc2_name": loc2_name,
        "timestamps": timestamps_aligned,
        "temp_diff": temp_diff,
        "mean_diff": mean_diff,
        "max_diff": max_diff,
        "min_diff": min_diff,
        "std_diff": std_diff,
        "loc1_warmer_count": loc1_warmer_count,
        "loc2_warmer_count": loc2_warmer_count,
        "common_points": common_points,
        "skipped_count": skipped_count,
    }


def plot_thermal_stratification(stratification_results):
    """
    Create visualization for thermal stratification analysis.
    stratification_results: list of dicts from compute_stratification()
    """
    if not stratification_results:
        print("No thermal stratification data to plot")
        return

    n_pairs = len(stratification_results)
    fig, axes = plt.subplots(n_pairs, 1, figsize=(14, 4 * n_pairs))

    # Handle case of single pair (axes is not a list)
    if n_pairs == 1:
        axes = [axes]

    for idx, strat_data in enumerate(stratification_results):
        ax = axes[idx]

        loc1_name = strat_data["loc1_name"]
        loc2_name = strat_data["loc2_name"]
        timestamps = strat_data["timestamps"]
        temp_diff = strat_data["temp_diff"]
        mean_diff = strat_data["mean_diff"]
        max_diff = strat_data["max_diff"]
        min_diff = strat_data["min_diff"]
        std_diff = strat_data["std_diff"]
        loc1_warmer = strat_data["loc1_warmer_count"]
        loc2_warmer = strat_data["loc2_warmer_count"]

        # Plot temperature difference
        colors = np.where(temp_diff > 0, '#e74c3c', '#3498db')  # Red for loc1 warmer, Blue for loc2 warmer

        for i in range(len(timestamps) - 1):
            ax.plot([timestamps[i], timestamps[i+1]], [temp_diff[i], temp_diff[i+1]],
                   color=colors[i], linewidth=1.5, alpha=0.7)

        # Add zero line
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.8, alpha=0.5)

        # Add mean line
        ax.axhline(y=mean_diff, color='green', linestyle='--', linewidth=1.5, alpha=0.7,
                  label=f"Mean: {mean_diff:.2f}°C")

        # Labels and title
        ax.set_xlabel('Date/Time', fontsize=10)
        ax.set_ylabel('Temperature Difference (°C)', fontsize=10)
        ax.set_title(f"Thermal Stratification: {loc1_name} minus {loc2_name}", fontsize=12, fontweight='bold')

        # Add statistics text box
        stats_text = (
            f"Mean: {mean_diff:.2f}°C | Max: {max_diff:.2f}°C | Min: {min_diff:.2f}°C | Std: {std_diff:.2f}°C\n"
            f"{loc1_name} warmer: {loc1_warmer} times | {loc2_name} warmer: {loc2_warmer} times"
        )
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes,
               fontsize=9, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        ax.legend(loc='upper right', fontsize=9)
        ax.grid(True, alpha=0.3)

        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.show(block=False)


def plot_temperature_time_series(results_by_location):
    """
    Plot temperature time series for each location.
    Creates individual plots showing raw temperature over time.
    """
    if not results_by_location:
        print("No location data to plot")
        return

    for location_name in sorted(results_by_location.keys()):
        result = results_by_location[location_name]
        timestamps = result.get("timestamps")
        temperatures = result.get("temperatures")
        label = result.get("label", location_name)

        if timestamps is None or temperatures is None:
            continue

        # Create figure
        fig, ax = plt.subplots(figsize=(14, 6))

        # Plot temperature time series
        ax.plot(timestamps, temperatures, linewidth=1.5, color='#2c3e50', label='Temperature')

        # Labels and title
        ax.set_xlabel('Date/Time', fontsize=11)
        ax.set_ylabel('Temperature (°C)', fontsize=11)
        ax.set_title(f"Temperature Time Series: {label}", fontsize=13, fontweight='bold')

        # Add grid
        ax.grid(True, alpha=0.3)

        # Statistics
        mean_temp = float(np.mean(temperatures))
        max_temp = float(np.max(temperatures))
        min_temp = float(np.min(temperatures))
        std_temp = float(np.std(temperatures))

        # Add statistics text box
        stats_text = (
            f"Mean: {mean_temp:.2f}°C | Max: {max_temp:.2f}°C | Min: {min_temp:.2f}°C | Std: {std_temp:.2f}°C"
        )
        ax.text(0.02, 0.95, stats_text, transform=ax.transAxes,
               fontsize=10, verticalalignment='top',
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # Rotate x-axis labels
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        ax.legend(loc='upper right', fontsize=10)
        plt.tight_layout()
        plt.show(block=False)


# =============================
# 2. FOURIER DESEASONALIZATION
# =============================

def analyze_seasonality_fft(temperatures, timestamps=None):
    """
    Analyze seasonality using FFT and return frequency spectrum.
    Returns: frequencies, magnitude spectrum
    """
    fft_values = np.fft.fft(temperatures)
    magnitude = np.abs(fft_values)

    if timestamps is not None:
        # Calculate frequency in cycles per unit time
        # Handle both numpy datetime64 and pandas Timestamp arrays
        try:
            time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600  # hours (pandas)
        except (AttributeError, TypeError):
            # For numpy datetime64
            time_diff = (timestamps[-1] - timestamps[0]) / np.timedelta64(1, 'h')

        frequencies = np.fft.fftfreq(len(temperatures), time_diff / len(temperatures))
    else:
        frequencies = np.fft.fftfreq(len(temperatures))

    return frequencies, magnitude, fft_values


def remove_seasonality_fft(temperatures, percentile_threshold=90):
    """
    Remove seasonal components from temperature data using FFT.

    Args:
        temperatures: 1D array of temperature values
        percentile_threshold: keep frequency components below this percentile
                            (removes high-magnitude seasonal peaks)

    Returns:
        deseasonalized_temps: Temperature data with seasonal components removed
        removed_magnitude: Magnitude of removed components (for visualization)
    """
    fft_values = np.fft.fft(temperatures)
    magnitude = np.abs(fft_values)

    # Find threshold for which components to remove
    threshold = np.percentile(magnitude, percentile_threshold)

    # Create mask: keep low-magnitude components, remove high-magnitude (seasonal)
    mask = magnitude < threshold

    # Zero out seasonal components
    fft_filtered = fft_values.copy()
    fft_filtered[~mask] = 0

    removed_magnitude = np.abs(fft_values - fft_filtered)

    # Transform back to time domain
    deseasonalized = np.fft.ifft(fft_filtered).real

    return deseasonalized, removed_magnitude


def remove_diurnal_cycle(temperatures, timestamps):
    """
    Remove diurnal (24-hour) cycle from temperature data using FFT.

    Args:
        temperatures: 1D array of temperature values
        timestamps: Array of datetime objects or numpy datetime64

    Returns:
        detrended_temps: Temperature data with diurnal cycle removed
        diurnal_component: The extracted 24-hour component
    """
    fft_values = np.fft.fft(temperatures)
    magnitude = np.abs(fft_values)

    # Calculate sampling rate (hours per sample)
    try:
        time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600  # hours (pandas)
    except (AttributeError, TypeError):
        time_diff = (timestamps[-1] - timestamps[0]) / np.timedelta64(1, 'h')  # numpy

    sampling_interval = time_diff / len(temperatures)  # hours per sample

    # Find frequency corresponding to 24-hour period
    frequencies = np.fft.fftfreq(len(temperatures), sampling_interval)
    diurnal_freq = 1.0 / 24.0  # 24-hour period in cycles per hour

    # Find the closest frequency component to 24-hour period
    freq_idx = np.argmin(np.abs(frequencies - diurnal_freq))

    # Create a mask to isolate the diurnal component (and its harmonic)
    diurnal_fft = fft_values.copy()
    # Zero out all but the diurnal frequency and its mirror
    diurnal_fft[~((np.arange(len(diurnal_fft)) == freq_idx) |
                   (np.arange(len(diurnal_fft)) == len(diurnal_fft) - freq_idx))] = 0

    # Extract the diurnal component
    diurnal_component = np.fft.ifft(diurnal_fft).real

    # Remove diurnal cycle from original signal
    detrended = temperatures - diurnal_component

    return detrended, diurnal_component


def plot_fft_analysis(temperatures, timestamps, label="Temperature"):
    """
    Visualize FFT spectrum and deseasonalized temperature.
    """
    frequencies, magnitude, fft_values = analyze_seasonality_fft(temperatures, timestamps)
    deseasonalized, removed_mag = remove_seasonality_fft(temperatures)

    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    # Original temperature
    axes[0, 0].plot(timestamps, temperatures, linewidth=1)
    axes[0, 0].set_title(f"Original {label}")
    axes[0, 0].set_ylabel("Temperature")

    # FFT spectrum
    axes[0, 1].plot(frequencies[:len(frequencies)//2], magnitude[:len(magnitude)//2], linewidth=0.5)
    axes[0, 1].set_title("FFT Spectrum (Frequency Domain)")
    axes[0, 1].set_ylabel("Magnitude")
    axes[0, 1].set_xlim(0, 0.5)

    # Deseasonalized temperature
    axes[1, 0].plot(timestamps, deseasonalized, linewidth=1, color='orange')
    axes[1, 0].set_title(f"Deseasonalized {label}")
    axes[1, 0].set_ylabel("Temperature")
    axes[1, 0].set_xlabel("Time")

    # Removed components
    axes[1, 1].plot(frequencies[:len(frequencies)//2], removed_mag[:len(removed_mag)//2], linewidth=0.5, color='red')
    axes[1, 1].set_title("Removed Seasonal Components")
    axes[1, 1].set_ylabel("Magnitude")
    axes[1, 1].set_xlabel("Frequency")
    axes[1, 1].set_xlim(0, 0.5)

    plt.tight_layout()
    plt.show(block=False)

    return deseasonalized


def plot_extracted_components(temperatures, timestamps, label="Temperature", filter_type="both"):
    """
    Visualize the extracted diurnal and/or seasonal components.
    Shows the original signal and the periodic components that were removed.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 8))

    # Original temperature
    axes[0, 0].plot(timestamps, temperatures, linewidth=1, color='black')
    axes[0, 0].set_title(f"Original {label}")
    axes[0, 0].set_ylabel("Temperature (°C)")
    axes[0, 0].grid(True, alpha=0.3)

    # Diurnal component
    if filter_type in ["diurnal", "both"]:
        _, diurnal_comp = remove_diurnal_cycle(temperatures, timestamps)
        axes[0, 1].plot(timestamps, diurnal_comp, linewidth=1, color='red')
        axes[0, 1].set_title("Extracted Diurnal (24-hour) Cycle")
        axes[0, 1].set_ylabel("Temperature Variation (°C)")
        axes[0, 1].grid(True, alpha=0.3)
    else:
        axes[0, 1].text(0.5, 0.5, "No diurnal component\n(not filtered)",
                       ha='center', va='center', transform=axes[0, 1].transAxes)
        axes[0, 1].set_title("Extracted Diurnal Cycle")

    # Seasonal component
    if filter_type in ["seasonal", "both"]:
        seasonal_removed, _ = remove_seasonality_fft(temperatures)
        seasonal_comp = temperatures - seasonal_removed
        axes[1, 0].plot(timestamps, seasonal_comp, linewidth=1, color='blue')
        axes[1, 0].set_title("Extracted Seasonal Components")
        axes[1, 0].set_ylabel("Temperature Variation (°C)")
        axes[1, 0].set_xlabel("Time")
        axes[1, 0].grid(True, alpha=0.3)
    else:
        axes[1, 0].text(0.5, 0.5, "No seasonal components\n(not filtered)",
                       ha='center', va='center', transform=axes[1, 0].transAxes)
        axes[1, 0].set_title("Extracted Seasonal Components")

    # Combined periodic components
    if filter_type == "both":
        _, diurnal_comp = remove_diurnal_cycle(temperatures, timestamps)
        seasonal_removed, _ = remove_seasonality_fft(temperatures)
        seasonal_comp = temperatures - seasonal_removed
        combined = diurnal_comp + seasonal_comp
        axes[1, 1].plot(timestamps, combined, linewidth=1, color='purple', label='Combined')
        axes[1, 1].plot(timestamps, diurnal_comp, linewidth=0.8, color='red', alpha=0.6, label='Diurnal')
        axes[1, 1].plot(timestamps, seasonal_comp, linewidth=0.8, color='blue', alpha=0.6, label='Seasonal')
        axes[1, 1].set_title("All Extracted Periodic Components")
        axes[1, 1].set_ylabel("Temperature Variation (°C)")
        axes[1, 1].set_xlabel("Time")
        axes[1, 1].legend(loc='best', fontsize=8)
        axes[1, 1].grid(True, alpha=0.3)
    elif filter_type == "diurnal":
        _, diurnal_comp = remove_diurnal_cycle(temperatures, timestamps)
        axes[1, 1].plot(timestamps, diurnal_comp, linewidth=1, color='red')
        axes[1, 1].set_title("Extracted Diurnal Cycle (detailed)")
        axes[1, 1].set_ylabel("Temperature Variation (°C)")
        axes[1, 1].set_xlabel("Time")
        axes[1, 1].grid(True, alpha=0.3)
    elif filter_type == "seasonal":
        seasonal_removed, _ = remove_seasonality_fft(temperatures)
        seasonal_comp = temperatures - seasonal_removed
        axes[1, 1].plot(timestamps, seasonal_comp, linewidth=1, color='blue')
        axes[1, 1].set_title("Extracted Seasonal Components (detailed)")
        axes[1, 1].set_ylabel("Temperature Variation (°C)")
        axes[1, 1].set_xlabel("Time")
        axes[1, 1].grid(True, alpha=0.3)
    else:
        axes[1, 1].text(0.5, 0.5, "No components extracted",
                       ha='center', va='center', transform=axes[1, 1].transAxes)
        axes[1, 1].set_title("Combined Components")

    plt.tight_layout()
    plt.show(block=False)


def plot_acf_analysis(original_temperatures, filtered_temperatures, timestamps, label="Temperature", filter_type="none"):
    """
    Visualize autocorrelation function (ACF) for temperature data.
    Shows ACF for original data and optionally for filtered data.

    Args:
        original_temperatures: Original temperature array before filtering
        filtered_temperatures: Filtered temperature array (same as original if no filtering)
        timestamps: Array of datetime objects
        label: Location label for title
        filter_type: "none", "diurnal", "seasonal", or "both"
    """
    # Calculate nlags based on data length (aim for ~72 lags for hourly data to see 3 days)
    nlags = min(len(original_temperatures) // 4, 72)

    if filter_type == "none":
        # Only show ACF for original data
        fig, ax = plt.subplots(figsize=(12, 5))
        plot_acf(original_temperatures, lags=nlags, ax=ax, title=f"ACF - {label} (Original Data)")
        ax.set_xlabel("Lag (hours)")
        ax.set_ylabel("Autocorrelation")

        # Add reference lines for 24-hour and weekly patterns
        ax.axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24-hour cycle')
        ax.axvline(x=168, color='blue', linestyle='--', alpha=0.5, label='Weekly cycle')
        ax.legend(loc='best', fontsize=9)
        ax.grid(True, alpha=0.3)
    else:
        # Show ACF for both original and filtered data
        fig, axes = plt.subplots(1, 2, figsize=(14, 5))

        # Original data ACF
        plot_acf(original_temperatures, lags=nlags, ax=axes[0],
                title=f"ACF - {label} (Original Data)")
        axes[0].set_xlabel("Lag (hours)")
        axes[0].set_ylabel("Autocorrelation")
        axes[0].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24-hour cycle')
        axes[0].axvline(x=168, color='blue', linestyle='--', alpha=0.5, label='Weekly cycle')
        axes[0].legend(loc='best', fontsize=8)
        axes[0].grid(True, alpha=0.3)

        # Filtered data ACF
        plot_acf(filtered_temperatures, lags=nlags, ax=axes[1],
                title=f"ACF - {label} (After {filter_type.title()} Filtering)")
        axes[1].set_xlabel("Lag (hours)")
        axes[1].set_ylabel("Autocorrelation")
        axes[1].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24-hour cycle')
        axes[1].axvline(x=168, color='blue', linestyle='--', alpha=0.5, label='Weekly cycle')
        axes[1].legend(loc='best', fontsize=8)
        axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show(block=False)


def plot_residual_power_spectrum(original_temperatures, filtered_temperatures, timestamps, label="Temperature", filter_type="none"):
    """
    Analyze residuals using power spectrum (log scale).

    Shows energy distribution across frequencies in cycles/day.
    Residuals = original - filtered (what's left after detrending).

    Args:
        original_temperatures: Original temperature array before filtering
        filtered_temperatures: Filtered temperature array
        timestamps: Array of datetime objects
        label: Location label for title
        filter_type: "none", "diurnal", "seasonal", or "both"
    """
    # Compute residuals
    residuals = original_temperatures - filtered_temperatures

    # Compute FFT
    fft_residuals = np.fft.fft(residuals)
    power_residuals = np.abs(fft_residuals) ** 2  # Power = magnitude squared

    fft_original = np.fft.fft(original_temperatures)
    power_original = np.abs(fft_original) ** 2

    # Calculate frequency in cycles per day
    try:
        time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600  # hours
    except (AttributeError, TypeError):
        time_diff = (timestamps[-1] - timestamps[0]) / np.timedelta64(1, 'h')

    # Frequency array in cycles per hour, then convert to cycles per day
    sampling_interval = time_diff / len(original_temperatures)  # hours per sample
    frequencies_cph = np.fft.fftfreq(len(original_temperatures), sampling_interval)  # cycles per hour
    frequencies_cpd = frequencies_cph * 24  # Convert to cycles per day

    # Only plot positive frequencies
    positive_freq_idx = frequencies_cpd > 0
    freq_cpd = frequencies_cpd[positive_freq_idx]
    power_orig = power_original[positive_freq_idx]
    power_resid = power_residuals[positive_freq_idx]

    # Create figure with subplots
    if filter_type == "none":
        # Only show original data spectrum
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.semilogy(freq_cpd, power_orig, linewidth=1, color='black', label='Original Data')
        ax.set_xlabel("Frequency (cycles/day)")
        ax.set_ylabel("Power (log scale)")
        ax.set_title(f"Power Spectrum - {label} (Original Data)")
        ax.grid(True, alpha=0.3, which='both')
        ax.set_xlim(0, min(10, freq_cpd.max()))  # Focus on lower frequencies
    else:
        # Show both original and residual spectra
        fig, axes = plt.subplots(1, 2, figsize=(14, 6))

        # Original power spectrum
        axes[0].semilogy(freq_cpd, power_orig, linewidth=1, color='black')
        axes[0].set_xlabel("Frequency (cycles/day)")
        axes[0].set_ylabel("Power (log scale)")
        axes[0].set_title(f"Power Spectrum - {label} (Original Data)")
        axes[0].grid(True, alpha=0.3, which='both')
        axes[0].set_xlim(0, min(10, freq_cpd.max()))

        # Residual power spectrum
        axes[1].semilogy(freq_cpd, power_resid, linewidth=1, color='red')
        axes[1].set_xlabel("Frequency (cycles/day)")
        axes[1].set_ylabel("Power (log scale)")
        axes[1].set_title(f"Residual Power Spectrum - {label}\n(After {filter_type.title()} Filtering)")
        axes[1].grid(True, alpha=0.3, which='both')
        axes[1].set_xlim(0, min(10, freq_cpd.max()))

    # Add reference lines for diurnal and sub-diurnal frequencies
    diurnal_freqs = {
        1.0: ('Diurnal', 'red', '--'),
        2.0: ('Semi-diurnal', 'blue', '--'),
        3.0: ('Terdiurnal', 'green', ':'),
        4.0: ('4-hourly', 'orange', ':'),
    }

    ax_list = [ax] if filter_type == "none" else axes
    for ax in ax_list:
        for freq, (name, color, style) in diurnal_freqs.items():
            if freq <= min(10, freq_cpd.max()):
                ax.axvline(x=freq, color=color, linestyle=style, alpha=0.5, linewidth=1)

        # Add legend
        lines = [plt.Line2D([0], [0], color=color, linestyle=style, linewidth=1, alpha=0.5)
                for freq, (name, color, style) in diurnal_freqs.items()]
        labels = [name for freq, (name, color, style) in diurnal_freqs.items()]
        ax.legend(lines, labels, loc='upper right', fontsize=8)

    plt.tight_layout()
    plt.show(block=False)


def plot_seasonality_comparison(results_by_location, erinia_locations):
    """
    Compare seasonal components across multiple erinia locations.
    Shows extracted seasonality for each depth side-by-side.

    Args:
        results_by_location: Dictionary of location results
        erinia_locations: List of erinia location names to compare (e.g., ["erinia_5", "erinia_15", "erinia_25"])
    """
    # Filter for requested erinia locations
    available_erinia = [loc for loc in erinia_locations if loc in results_by_location]

    if not available_erinia:
        print("No requested erinia locations found in results.")
        return

    n_locations = len(available_erinia)
    fig, axes = plt.subplots(n_locations, 2, figsize=(14, 5 * n_locations))

    # Handle single location case (axes won't be 2D)
    if n_locations == 1:
        axes = axes.reshape(1, -1)

    for idx, location in enumerate(available_erinia):
        result = results_by_location[location]
        timestamps = result["timestamps"]
        original_temps = result["temperatures"]  # These are already filtered if filtering was applied

        # For seasonality extraction, we need the original unfiltered data
        # We'll extract seasonality from the original data for comparison
        # Get original from the dataframe
        df = result["df"]
        original_temps_raw = df["temperature"].to_numpy()

        # Extract seasonal component
        seasonal_removed, removed_mag = remove_seasonality_fft(original_temps_raw)
        seasonal_comp = original_temps_raw - seasonal_removed

        # Extract frequencies for FFT
        try:
            time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        except (AttributeError, TypeError):
            time_diff = (timestamps[-1] - timestamps[0]) / np.timedelta64(1, 'h')

        frequencies, magnitude, _ = analyze_seasonality_fft(original_temps_raw, timestamps)

        # Time series plot
        axes[idx, 0].plot(timestamps, seasonal_comp, linewidth=1, color='blue')
        axes[idx, 0].set_title(f"Seasonal Component - {location}")
        axes[idx, 0].set_ylabel("Temperature Variation (°C)")
        axes[idx, 0].grid(True, alpha=0.3)
        if idx == n_locations - 1:
            axes[idx, 0].set_xlabel("Time")

        # FFT spectrum (power in frequency domain)
        power_spectrum = np.abs(magnitude) ** 2
        sampling_interval = time_diff / len(original_temps_raw)
        frequencies_cpd = frequencies * 24  # Convert to cycles per day

        positive_freq_idx = frequencies_cpd > 0
        freq_cpd = frequencies_cpd[positive_freq_idx]
        power_spec = power_spectrum[positive_freq_idx]

        axes[idx, 1].semilogy(freq_cpd, power_spec, linewidth=1, color='purple')
        axes[idx, 1].set_title(f"Power Spectrum - {location}")
        axes[idx, 1].set_ylabel("Power (log scale)")
        axes[idx, 1].grid(True, alpha=0.3, which='both')
        axes[idx, 1].set_xlim(0, min(10, freq_cpd.max()))

        # Add diurnal reference line
        axes[idx, 1].axvline(x=1.0, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Diurnal (1 cycle/day)')
        axes[idx, 1].legend(loc='upper right', fontsize=8)

        if idx == n_locations - 1:
            axes[idx, 1].set_xlabel("Frequency (cycles/day)")

    plt.suptitle("Erinia Seasonality Comparison", fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.show(block=False)


def plot_diurnal_comparison(results_by_location, location_list):
    """
    Compare diurnal (24-hour) cycles across multiple locations.
    Shows extracted diurnal component for each depth side-by-side.

    Args:
        results_by_location: Dictionary of location results
        location_list: List of location names to compare (e.g., ["erinia_5", "erinia_15", "erinia_25"])
    """
    # Filter for requested locations
    available_locs = [loc for loc in location_list if loc in results_by_location]

    if not available_locs:
        print("No requested locations found in results.")
        return

    n_locations = len(available_locs)
    fig, axes = plt.subplots(n_locations, 2, figsize=(14, 5 * n_locations))

    # Handle single location case (axes won't be 2D)
    if n_locations == 1:
        axes = axes.reshape(1, -1)

    for idx, location in enumerate(available_locs):
        result = results_by_location[location]
        timestamps = result["timestamps"]

        # Get original unfiltered data
        df = result["df"]
        original_temps_raw = df["temperature"].to_numpy()

        # Extract diurnal component
        _, diurnal_comp = remove_diurnal_cycle(original_temps_raw, timestamps)

        # Time series plot
        axes[idx, 0].plot(timestamps, diurnal_comp, linewidth=1, color='red')
        axes[idx, 0].set_title(f"Diurnal Component - {location}")
        axes[idx, 0].set_ylabel("Temperature Variation (°C)")
        axes[idx, 0].grid(True, alpha=0.3)
        if idx == n_locations - 1:
            axes[idx, 0].set_xlabel("Time")

        # FFT spectrum (power in frequency domain) of diurnal component
        fft_diurnal = np.fft.fft(diurnal_comp)
        power_spectrum = np.abs(fft_diurnal) ** 2

        try:
            time_diff = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
        except (AttributeError, TypeError):
            time_diff = (timestamps[-1] - timestamps[0]) / np.timedelta64(1, 'h')

        sampling_interval = time_diff / len(original_temps_raw)
        frequencies = np.fft.fftfreq(len(diurnal_comp), sampling_interval)
        frequencies_cpd = frequencies * 24  # Convert to cycles per day

        positive_freq_idx = frequencies_cpd > 0
        freq_cpd = frequencies_cpd[positive_freq_idx]
        power_spec = power_spectrum[positive_freq_idx]

        axes[idx, 1].semilogy(freq_cpd, power_spec, linewidth=1, color='red')
        axes[idx, 1].set_title(f"Power Spectrum - {location}")
        axes[idx, 1].set_ylabel("Power (log scale)")
        axes[idx, 1].grid(True, alpha=0.3, which='both')
        axes[idx, 1].set_xlim(0, min(10, freq_cpd.max()))

        # Add diurnal reference line (should peak here)
        axes[idx, 1].axvline(x=1.0, color='red', linestyle='--', alpha=0.5, linewidth=1, label='Diurnal (1 cycle/day)')
        axes[idx, 1].legend(loc='upper right', fontsize=8)

        if idx == n_locations - 1:
            axes[idx, 1].set_xlabel("Frequency (cycles/day)")

    plt.suptitle("Diurnal Cycle Comparison", fontsize=14, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.show(block=False)


def compare_stations_acf_power_spectrum(results_by_location):
    """
    Compare Erinia vs Apothikes stations using ACF and residual power spectra.
    Creates side-by-side comparisons at each depth (5m, 15m, 25m).

    Args:
        results_by_location: Dictionary of location results with ACF and power spectrum data
    """
    depths = ["5", "15", "25"]

    for depth in depths:
        erinia_loc = f"erinia_{depth}"
        apothikes_loc = f"apothikes_{depth}"

        # Check if both locations exist
        if erinia_loc not in results_by_location or apothikes_loc not in results_by_location:
            print(f"Skipping depth {depth}m - both stations not available")
            continue

        erinia_res = results_by_location[erinia_loc]
        apothikes_res = results_by_location[apothikes_loc]

        # Get data
        erinia_ts = erinia_res["timestamps"]
        erinia_original = erinia_res["df"]["temperature"].to_numpy()
        erinia_filtered = erinia_res["temperatures"]

        apothikes_ts = apothikes_res["timestamps"]
        apothikes_original = apothikes_res["df"]["temperature"].to_numpy()
        apothikes_filtered = apothikes_res["temperatures"]

        # Create comparison figure with 2 rows (ACF and Power Spectrum) x 2 columns (Erinia and Apothikes)
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))

        # Calculate ACF lags
        nlags = min(len(erinia_original) // 4, 72)

        # --- Row 1: ACF Comparison ---
        # Erinia ACF
        plot_acf(erinia_original, lags=nlags, ax=axes[0, 0],
                title=f"ACF - Erinia {depth}m (Original)")
        axes[0, 0].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24-hour')
        axes[0, 0].axvline(x=168, color='blue', linestyle='--', alpha=0.5, label='Weekly')
        axes[0, 0].legend(loc='best', fontsize=8)
        axes[0, 0].grid(True, alpha=0.3)
        axes[0, 0].set_xlabel("Lag (hours)")

        # Apothikes ACF
        plot_acf(apothikes_original, lags=nlags, ax=axes[0, 1],
                title=f"ACF - Apothikes {depth}m (Original)")
        axes[0, 1].axvline(x=24, color='red', linestyle='--', alpha=0.5, label='24-hour')
        axes[0, 1].axvline(x=168, color='blue', linestyle='--', alpha=0.5, label='Weekly')
        axes[0, 1].legend(loc='best', fontsize=8)
        axes[0, 1].grid(True, alpha=0.3)
        axes[0, 1].set_xlabel("Lag (hours)")

        # --- Row 2: Residual Power Spectrum Comparison ---
        # Compute residuals (after filtering)
        erinia_residuals = erinia_original - erinia_filtered
        apothikes_residuals = apothikes_original - apothikes_filtered

        # Compute power spectra
        erinia_fft_resid = np.fft.fft(erinia_residuals)
        erinia_power_resid = np.abs(erinia_fft_resid) ** 2

        apothikes_fft_resid = np.fft.fft(apothikes_residuals)
        apothikes_power_resid = np.abs(apothikes_fft_resid) ** 2

        # Calculate frequencies
        try:
            erinia_time_diff = (erinia_ts[-1] - erinia_ts[0]).total_seconds() / 3600
        except:
            erinia_time_diff = (erinia_ts[-1] - erinia_ts[0]) / np.timedelta64(1, 'h')

        try:
            apothikes_time_diff = (apothikes_ts[-1] - apothikes_ts[0]).total_seconds() / 3600
        except:
            apothikes_time_diff = (apothikes_ts[-1] - apothikes_ts[0]) / np.timedelta64(1, 'h')

        erinia_sampling = erinia_time_diff / len(erinia_original)
        erinia_freq = np.fft.fftfreq(len(erinia_residuals), erinia_sampling) * 24
        erinia_freq_pos = erinia_freq[erinia_freq > 0]
        erinia_power_pos = erinia_power_resid[erinia_freq > 0]

        apothikes_sampling = apothikes_time_diff / len(apothikes_original)
        apothikes_freq = np.fft.fftfreq(len(apothikes_residuals), apothikes_sampling) * 24
        apothikes_freq_pos = apothikes_freq[apothikes_freq > 0]
        apothikes_power_pos = apothikes_power_resid[apothikes_freq > 0]

        # Plot residual power spectra
        axes[1, 0].semilogy(erinia_freq_pos, erinia_power_pos, linewidth=1, color='darkblue')
        axes[1, 0].axvline(x=1.0, color='red', linestyle='--', alpha=0.5, label='Diurnal')
        axes[1, 0].axvline(x=24, color='green', linestyle='--', alpha=0.5, label='Daily')
        axes[1, 0].set_title(f"Residual Power Spectrum - Erinia {depth}m\n(After removing diurnal & seasonal)")
        axes[1, 0].set_xlabel("Frequency (cycles/day)")
        axes[1, 0].set_ylabel("Power (log scale)")
        axes[1, 0].set_xlim(0, 10)
        axes[1, 0].grid(True, alpha=0.3, which='both')
        axes[1, 0].legend(loc='upper right', fontsize=8)

        axes[1, 1].semilogy(apothikes_freq_pos, apothikes_power_pos, linewidth=1, color='darkgreen')
        axes[1, 1].axvline(x=1.0, color='red', linestyle='--', alpha=0.5, label='Diurnal')
        axes[1, 1].axvline(x=24, color='green', linestyle='--', alpha=0.5, label='Daily')
        axes[1, 1].set_title(f"Residual Power Spectrum - Apothikes {depth}m\n(After removing diurnal & seasonal)")
        axes[1, 1].set_xlabel("Frequency (cycles/day)")
        axes[1, 1].set_ylabel("Power (log scale)")
        axes[1, 1].set_xlim(0, 10)
        axes[1, 1].grid(True, alpha=0.3, which='both')
        axes[1, 1].legend(loc='upper right', fontsize=8)

        plt.suptitle(f"Station Comparison at {depth}m Depth: ACF & Residual Power Spectrum",
                    fontsize=14, fontweight='bold', y=0.995)
        plt.tight_layout()
        plt.show(block=False)


# =============================
# 3. HELPERS FOR MULTIPLE SOURCES
# =============================

def load_temperature_source(config):
    """
    Load one temperature source (file + sheet) and return a DataFrame with
    timestamp, temperature, location, series, and optionally lux.
    config keys:
      - location
      - series
      - excel_file
      - sheet_name
      - dt_col
      - temp_col
      - lux_col (optional)
    """
    df = pd.read_excel(config["excel_file"], sheet_name=config["sheet_name"])
    df = df.reset_index(drop=True)
    df = df.iloc[1:].reset_index(drop=True)  # drop first row

    timestamps = pd.to_datetime(df.iloc[:, config["dt_col"]])
    temps = df.iloc[:, config["temp_col"]].astype(float)

    combined = pd.DataFrame({
        "timestamp": timestamps,
        "temperature": temps,
        "location": config["location"],
        "series": config["series"],
    })

    # Load lux column if specified
    if "lux_col" in config:
        lux_values = df.iloc[:, config["lux_col"]].astype(float)
        combined["lux"] = lux_values

    return combined


def load_location_data(location, configs_for_location, filter_type="none", show_fft_analysis=False, show_acf_analysis=False, show_power_spectrum=False):
    """
    Merge all excel sources for a given location into a single time series.
    Optionally apply Fourier-based filtering (diurnal cycle, seasonality, or both).

    Args:
        location: Location name
        configs_for_location: List of data source configs
        filter_type: "none", "diurnal", "seasonal", or "both"
        show_fft_analysis: Whether to visualize FFT analysis
        show_acf_analysis: Whether to visualize ACF analysis
        show_power_spectrum: Whether to visualize residual power spectrum analysis

    Returns:
      combined_df with columns [timestamp, temperature, location, series, lux (optional)]
      timestamps (np.array)
      temperatures (np.array)
    """
    frames = []
    for cfg in configs_for_location:
        frames.append(load_temperature_source(cfg))

    combined_df = pd.concat(frames, ignore_index=True)
    combined_df = combined_df.sort_values("timestamp").reset_index(drop=True)

    timestamps = combined_df["timestamp"].to_numpy()
    temperatures = combined_df["temperature"].to_numpy()
    original_temperatures = temperatures.copy()  # Keep original for visualization

    # Apply filtering if requested
    if filter_type != "none":
        if filter_type == "diurnal":
            print(f"  Removing diurnal (24-hour) cycle from {location}...")
            temperatures, _ = remove_diurnal_cycle(temperatures, timestamps)
            combined_df["temperature"] = temperatures

        elif filter_type == "seasonal":
            print(f"  Removing seasonal components from {location}...")
            temperatures = remove_seasonality_fft(temperatures)[0]
            combined_df["temperature"] = temperatures

        elif filter_type == "both":
            print(f"  Removing diurnal cycle from {location}...")
            temperatures, _ = remove_diurnal_cycle(temperatures, timestamps)
            print(f"  Removing seasonal components from {location}...")
            temperatures = remove_seasonality_fft(temperatures)[0]
            combined_df["temperature"] = temperatures

        if show_fft_analysis:
            print(f"  Displaying extracted components for {location}...")
            # Visualize the extracted components from ORIGINAL data
            plot_extracted_components(original_temperatures,
                                    timestamps,
                                    label=location,
                                    filter_type=filter_type)

    # Display ACF analysis if requested
    if show_acf_analysis:
        print(f"  Computing autocorrelation function (ACF) for {location}...")
        plot_acf_analysis(original_temperatures, temperatures, timestamps, label=location, filter_type=filter_type)

    # Display residual power spectrum if requested
    if show_power_spectrum and filter_type != "none":
        print(f"  Computing residual power spectrum for {location}...")
        plot_residual_power_spectrum(original_temperatures, temperatures, timestamps, label=location, filter_type=filter_type)

    return combined_df, timestamps, temperatures


def process_location(location, configs_for_location, ships_df, eta_series, etd_series, filter_type="none", show_fft_analysis=False, show_acf_analysis=False, show_power_spectrum=False, up_jump_threshold=None, up_relax_offset=None, down_jump_threshold=None, down_relax_offset=None):
    """
    For one location (possibly multiple excel sources):
      - merge all its series
      - optionally apply Fourier-based filtering (diurnal, seasonal, or both)
      - detect up & down spikes (+ inner spikes)
      - build spike tables
      - build spike–ship relations
      - compute total abnormality counts (>= +0.5, <= -0.5)
    """
    label = location
    print(f"\n=== Processing location: {label} ===")

    df, timestamps, temperatures = load_location_data(location, configs_for_location, filter_type, show_fft_analysis, show_acf_analysis, show_power_spectrum)

    # --- Abnormality counters over the full time series ---
    deltas = np.diff(temperatures)
    up_abnormal_count = int((deltas >= UP_JUMP_THRESHOLD).sum())
    down_abnormal_count = int((deltas <= -DOWN_JUMP_THRESHOLD).sum())

    print(f"Total abnormal jumps for {label}: "
          f"up (>= +{UP_JUMP_THRESHOLD}) = {up_abnormal_count}, "
          f"down (<= -{DOWN_JUMP_THRESHOLD}) = {down_abnormal_count}")

    # Detect spikes
    outer_up_spikes = find_spikes(timestamps, temperatures, direction="up", up_threshold=up_jump_threshold, up_offset=up_relax_offset)
    outer_down_spikes = find_spikes(timestamps, temperatures, direction="down", down_threshold=down_jump_threshold, down_offset=down_relax_offset)

    add_inner_spike_info(outer_up_spikes, direction="up", up_jump_threshold=up_jump_threshold, up_relax_offset=up_relax_offset, down_jump_threshold=down_jump_threshold, down_relax_offset=down_relax_offset)
    add_inner_spike_info(outer_down_spikes, direction="down", up_jump_threshold=up_jump_threshold, up_relax_offset=up_relax_offset, down_jump_threshold=down_jump_threshold, down_relax_offset=down_relax_offset)

    # Build DataFrames
    upSpikes = pd.DataFrame([
        {
            "location": location,
            "direction": s["direction"],
            "start_datetime": s["start_datetime"],
            "end_datetime": s["end_datetime"],
            "base_value": s["base_value"],
            "max_value": s["max_value"],
            "min_value": s["min_value"],
            "num_measurements": s["num_measurements"],
            "values": s["values"],
            "inner_spike_count": s["inner_spike_count"],
            "highest_inner_max_value": s["highest_inner_max_value"],
            "highest_inner_min_value": s["highest_inner_min_value"],
            "highest_inner_amplitude": s["highest_inner_amplitude"],
        }
        for s in outer_up_spikes
    ])

    downSpikes = pd.DataFrame([
        {
            "location": location,
            "direction": s["direction"],
            "start_datetime": s["start_datetime"],
            "end_datetime": s["end_datetime"],
            "base_value": s["base_value"],
            "max_value": s["max_value"],
            "min_value": s["min_value"],
            "num_measurements": s["num_measurements"],
            "values": s["values"],
            "inner_spike_count": s["inner_spike_count"],
            "highest_inner_max_value": s["highest_inner_max_value"],
            "highest_inner_min_value": s["highest_inner_min_value"],
            "highest_inner_amplitude": s["highest_inner_amplitude"],
        }
        for s in outer_down_spikes
    ])

    print("\n--- Up Spikes ---")
    print(upSpikes)
    print("\n--- Down Spikes ---")
    print(downSpikes)

    # Spike–ship relations (labelled by location + direction)
    up_label = f"{label}-UP"
    down_label = f"{label}-DOWN"

    up_rel = build_spike_ship_relations(
        outer_up_spikes, eta_series, etd_series, ships_df, label=up_label
    )
    down_rel = build_spike_ship_relations(
        outer_down_spikes, eta_series, etd_series, ships_df, label=down_label
    )

    print("\n--- Spike–Ship Relations (UP) ---")
    print(up_rel)
    print("\n--- Spike–Ship Relations (DOWN) ---")
    print(down_rel)

    return {
        "location": location,
        "label": label,
        "df": df,
        "timestamps": timestamps,
        "temperatures": temperatures,
        "outer_up_spikes": outer_up_spikes,
        "outer_down_spikes": outer_down_spikes,
        "upSpikes": upSpikes,
        "downSpikes": downSpikes,
        "up_rel": up_rel,
        "down_rel": down_rel,
        "up_abnormal_count": up_abnormal_count,
        "down_abnormal_count": down_abnormal_count,
    }


# =============================
# 3. PLOTTING
# =============================

def plot_location_with_ships(result, ships_df, ship_name_series, eta_series, etd_series, overlay_type="ships"):
    """
    Plot UP & DOWN spikes of one location with overlay (ships, lux, or none).
    Also annotate total abnormality counts.
    overlay_type: "ships" (ETA-ETD intervals), "lux" (light values), or "none"
    """
    label = result["label"]
    timestamps = result["timestamps"]
    temperatures = result["temperatures"]
    outer_up_spikes = result["outer_up_spikes"]
    outer_down_spikes = result["outer_down_spikes"]
    up_abn = result["up_abnormal_count"]
    down_abn = result["down_abnormal_count"]

    # Build masked arrays
    masked_up = np.full_like(temperatures, fill_value=np.nan, dtype=float)
    for spike in outer_up_spikes:
        start_idx = spike["start_index"]
        end_idx = spike["end_index"]
        masked_up[start_idx:end_idx + 1] = temperatures[start_idx:end_idx + 1]

    masked_down = np.full_like(temperatures, fill_value=np.nan, dtype=float)
    for spike in outer_down_spikes:
        start_idx = spike["start_index"]
        end_idx = spike["end_index"]
        masked_down[start_idx:end_idx + 1] = temperatures[start_idx:end_idx + 1]

    fig, ax = plt.subplots(figsize=(12, 6))

    # Plot UP spikes
    ax.plot(
        timestamps,
        masked_up,
        marker="o",
        linewidth=1.2,
        label=f"{label} - UP spikes",
    )

    # Plot DOWN spikes
    ax.plot(
        timestamps,
        masked_down,
        marker="v",
        linestyle="--",
        linewidth=1.2,
        label=f"{label} - DOWN spikes",
    )

    # Get y-axis limits for later use
    ymin, ymax = ax.get_ylim()

    # Overlay ship ETA-ETD as shaded intervals
    if overlay_type == "ships" and ships_df is not None:
        for i in range(len(ships_df)):
            eta = eta_series.iloc[i]
            etd = etd_series.iloc[i]

            if pd.isna(eta) or pd.isna(etd):
                continue

            ship_name = ship_name_series.iloc[i]

            ax.axvspan(eta, etd, alpha=0.2)
            ax.text(
                eta,
                ymax,
                str(ship_name),
                rotation=90,
                va="top",
                ha="left",
                fontsize=8,
            )

    elif overlay_type == "lux":
        # Plot lux values as shaded intervals with opacity based on value
        combined_df = result["df"]
        if "lux" in combined_df.columns:
            lux_data = combined_df[["timestamp", "lux"]].dropna()
            if len(lux_data) > 0:
                max_lux = lux_data["lux"].max()
                if max_lux > 0:
                    for idx, row in lux_data.iterrows():
                        ts = row["timestamp"]
                        lux_val = row["lux"]
                        opacity = min(lux_val / max_lux, 1.0)
                        ts_end = ts + pd.Timedelta(hours=1)
                        ax.axvspan(ts, ts_end, alpha=opacity, color="yellow")

    # Abnormality annotation box
    text_str = (
        f"Up jumps ≥ +{UP_JUMP_THRESHOLD}: {up_abn}\n"
        f"Down jumps ≤ -{DOWN_JUMP_THRESHOLD}: {down_abn}"
    )
    ax.text(
        0.01,
        0.99,
        text_str,
        transform=ax.transAxes,
        va="top",
        ha="left",
        fontsize=9,
        bbox=dict(boxstyle="round", alpha=0.3)
    )

    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature")
    # Build overlay description for title
    if overlay_type == "ships":
        overlay_desc = "with Ship ETA-ETD"
    elif overlay_type == "lux":
        overlay_desc = "with Light Intensity"
    else:  # "none"
        overlay_desc = ""

    ax.set_title(
        f"{label}: UP and DOWN Spikes {overlay_desc} "
        f"(up={up_abn}, down={down_abn})"
    )
    ax.legend()
    plt.tight_layout()
    plt.show(block=False)  # non-blocking


def plot_multiple_locations_with_ships(results_by_location, selected_locations,
                                       ships_df, ship_name_series, eta_series, etd_series, overlay_type="ships"):
    """
    Plot UP & DOWN spikes for multiple locations on the SAME diagram.
    Also show a small table of total abnormality counts per location.
    """
    fig, ax = plt.subplots(figsize=(14, 7))

    # For building a small summary text
    summary_lines = []

    # Plot spikes for each selected location
    for location in selected_locations:
        if location not in results_by_location:
            continue

        res = results_by_location[location]
        label = res["label"]
        timestamps = res["timestamps"]
        temperatures = res["temperatures"]
        outer_up_spikes = res["outer_up_spikes"]
        outer_down_spikes = res["outer_down_spikes"]
        up_abn = res["up_abnormal_count"]
        down_abn = res["down_abnormal_count"]

        summary_lines.append(
            f"{label}: up={up_abn}, down={down_abn}"
        )

        masked_up = np.full_like(temperatures, fill_value=np.nan, dtype=float)
        for spike in outer_up_spikes:
            start_idx = spike["start_index"]
            end_idx = spike["end_index"]
            masked_up[start_idx:end_idx + 1] = temperatures[start_idx:end_idx + 1]

        masked_down = np.full_like(temperatures, fill_value=np.nan, dtype=float)
        for spike in outer_down_spikes:
            start_idx = spike["start_index"]
            end_idx = spike["end_index"]
            masked_down[start_idx:end_idx + 1] = temperatures[start_idx:end_idx + 1]

        ax.plot(
            timestamps,
            masked_up,
            marker="o",
            linewidth=1.2,
            label=f"{label} - UP",
        )

        ax.plot(
            timestamps,
            masked_down,
            marker="v",
            linestyle="--",
            linewidth=1.2,
            label=f"{label} - DOWN",
        )

    # Get y-axis limits for later use
    ymin, ymax = ax.get_ylim()

    # After plotting all locations, overlay ship intervals once
    if overlay_type == "ships" and ships_df is not None:
        for i in range(len(ships_df)):
            eta = eta_series.iloc[i]
            etd = etd_series.iloc[i]

            if pd.isna(eta) or pd.isna(etd):
                continue

            ship_name = ship_name_series.iloc[i]

            ax.axvspan(eta, etd, alpha=0.15)
            ax.text(
                eta,
                ymax,
                str(ship_name),
                rotation=90,
                va="top",
                ha="left",
                fontsize=8,
            )


    elif overlay_type == "lux":
        # Plot lux values as shaded intervals with opacity based on value
        all_lux_data = []
        for res in results_by_location.values():
            if "lux" in res["df"].columns:
                lux_df = res["df"][["timestamp", "lux"]].dropna()
                all_lux_data.append(lux_df)
        
        if all_lux_data:
            combined_lux = pd.concat(all_lux_data, ignore_index=True)
            max_lux = combined_lux["lux"].max()
            if max_lux > 0:
                for idx, row in combined_lux.iterrows():
                    ts = row["timestamp"]
                    lux_val = row["lux"]
                    opacity = min(lux_val / max_lux, 1.0)
                    ts_end = ts + pd.Timedelta(hours=1)
                    ax.axvspan(ts, ts_end, alpha=opacity, color="yellow")
    # Add summary of counts as a text box
    if summary_lines:
        summary_text = "Abnormal jumps per location:\n" + "\n".join(summary_lines)
        ax.text(
            0.01,
            0.99,
            summary_text,
            transform=ax.transAxes,
            va="top",
            ha="left",
            fontsize=9,
            bbox=dict(boxstyle="round", alpha=0.3)
        )

    ax.set_ylim(ymin, ymax)
    ax.set_xlabel("Time")
    ax.set_ylabel("Temperature")
    # Build overlay description for title
    if overlay_type == "ships":
        overlay_desc = "with Ship ETAETD Intervals"
    elif overlay_type == "lux":
        overlay_desc = "with Light Intensity"
    else:  # "none"
        overlay_desc = ""
    
    ax.set_title(f"Combined locations: UP and DOWN Spikes {overlay_desc}")
    ax.legend()
    plt.tight_layout()
    plt.show(block=False)  # non-blocking


# =============================
# 4. MAIN
# =============================

def load_config_from_gui():
    """Load configuration from GUI-generated JSON files if available"""
    import os
    import json

    config_file = "data_sources_config.json"
    analysis_file = "analysis_config.json"

    if not os.path.exists(config_file):
        return None, None

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)

        # Load analysis config if available
        analysis_config = None
        if os.path.exists(analysis_file):
            with open(analysis_file, 'r') as f:
                analysis_config = json.load(f)

        return config, analysis_config
    except Exception as e:
        print(f"Warning: Could not load GUI config: {str(e)}")
        return None, None


def main():
    # --- Load configuration from GUI or use defaults ---
    gui_config, analysis_config = load_config_from_gui()

    if gui_config:
        print("Loading configuration from GUI...")
        temperature_sources = gui_config.get("temperature_sources", [])
        ships_excel_file = gui_config.get("ships_file") or None  # None if not provided
        ships_sheet_name = gui_config.get("ships_sheet", "schedule")

        # Use GUI settings if available
        if analysis_config:
            overlay_type = analysis_config.get("overlay_type", "ships")
            filter_type = analysis_config.get("filter_type", "both")
            show_fft = analysis_config.get("show_fft", True)
            show_acf = analysis_config.get("show_acf", False)
            show_power_spectrum = analysis_config.get("show_power_spectrum", False)

            # Load spike detection parameters from config
            up_jump_threshold = float(analysis_config.get("up_jump_threshold", 0.5))
            up_relax_offset = float(analysis_config.get("up_relax_offset", 0.2))
            down_jump_threshold = float(analysis_config.get("down_jump_threshold", 0.5))
            down_relax_offset = float(analysis_config.get("down_relax_offset", 0.2))

            use_interactive = False
        else:
            use_interactive = True
            # Use hardcoded defaults if no config
            up_jump_threshold = UP_JUMP_THRESHOLD
            up_relax_offset = UP_RELAX_OFFSET
            down_jump_threshold = DOWN_JUMP_THRESHOLD
            down_relax_offset = DOWN_RELAX_OFFSET
    else:
        print("No GUI config found. Using default configuration...")
        # --- Define your temperature sources (location + sheet) ---
        # All entries with the same "location" will be merged into ONE time series.
        temperature_sources = [
            {
                "location": "erinia_25",
                "series": "A",
                "excel_file": "erinia_25_a.xlsx",
                "sheet_name": "Data",
                "dt_col": 2,
                "temp_col": 4,
                "lux_col": 5
            },
            {
                "location": "erinia_25",
                "series": "B",
                "excel_file": "erinia_25_b.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 2,
                "lux_col": 3
            },
            {
                "location": "erinia_15",
                "series": "B",
                "excel_file": "erinia_15_a.xlsx",
                "sheet_name": "Data",
                "dt_col": 2,
                "temp_col": 4,
                "lux_col": 5
            },
            {
                "location": "erinia_15",
                "series": "B",
                "excel_file": "erinia_15_b.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 2,
                "lux_col": 3
            },
            {
                "location": "erinia_5",
                "series": "B",
                "excel_file": "erinia_5_a.xlsx",
                "sheet_name": "Data",
                "dt_col": 2,
                "temp_col": 4
            },
            {
                "location": "erinia_5",
                "series": "B",
                "excel_file": "erinia_5_b.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 2
            },
            {
                "location": "apothikes_5",
                "series": "A",
                "excel_file": "apothikestotal.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 3
            },
            {
                "location": "apothikes_15",
                "series": "A",
                "excel_file": "apothikestotal.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 4,
                "lux_col": 5
            },
            {
                "location": "apothikes_25",
                "series": "A",
                "excel_file": "apothikestotal.xlsx",
                "sheet_name": "Data",
                "dt_col": 1,
                "temp_col": 6,
                "lux_col": 7
            },
        ]

        ships_excel_file = "2.xlsx"
        ships_sheet_name = "schedule"
        use_interactive = True

    # Group configs by location
    location_to_configs = defaultdict(list)
    for cfg in temperature_sources:
        location_to_configs[cfg["location"]].append(cfg)

    # --- Load ship schedule once (if provided) ---
    ships_df = None
    ship_name_series = None
    eta_series = None
    etd_series = None

    if ships_excel_file and os.path.exists(ships_excel_file):
        try:
            ships_df = pd.read_excel(ships_excel_file, sheet_name=ships_sheet_name)
            ships_df = ships_df.reset_index(drop=True)
            ship_name_series = ships_df.iloc[:, 1]
            eta_series = pd.to_datetime(ships_df.iloc[:, 2])
            etd_series = pd.to_datetime(ships_df.iloc[:, 3])
            print(f"Loaded ship schedule from {ships_excel_file}")
        except Exception as e:
            print(f"Warning: Could not load ship schedule: {str(e)}")
            print("Continuing without ship data...")
            # Only change overlay if it was set to ships
            if overlay_type == "ships":
                overlay_type = "none"
    else:
        if ships_excel_file:
            print(f"Warning: Ship file not found: {ships_excel_file}")
        else:
            print("No ship schedule file provided.")
        # Only disable ship overlay if that's what was requested
        if overlay_type == "ships":
            print("Skipping ship overlay.")
            overlay_type = "none"

    # --- Ask interactive prompts if not configured via GUI ---
    if use_interactive:
        # --- Ask what overlay to display in plots ---
        overlay_choice = input(
            "\nWhat to overlay on plots? (ships/lux/none, default: ships): "
        ).strip().lower()
        if overlay_choice in ["lux", "l"]:
            overlay_type = "lux"
        elif overlay_choice in ["none", "n"]:
            overlay_type = "none"
        else:
            overlay_type = "ships"  # default

        # --- Ask about Fourier filtering ---
        filter_choice = input(
            "\nApply Fourier-based filtering?\n"
            "  (none/diurnal/seasonal/both, default: none): "
        ).strip().lower()

        if filter_choice in ["diurnal", "d"]:
            filter_type = "diurnal"
        elif filter_choice in ["seasonal", "s"]:
            filter_type = "seasonal"
        elif filter_choice in ["both", "b"]:
            filter_type = "both"
        else:
            filter_type = "none"  # default

        show_fft = False
        if filter_type != "none":
            fft_viz = input(
                "Visualize extracted periodic components (diurnal/seasonal)? (yes/no, default: yes): "
            ).strip().lower()
            show_fft = fft_viz not in ["no", "n"]

        # --- Ask about ACF analysis ---
        show_acf = False
        acf_choice = input(
            "Compute Autocorrelation Function (ACF) for each location? (yes/no, default: no): "
        ).strip().lower()
        show_acf = acf_choice in ["yes", "y"]

        # --- Ask about residual power spectrum analysis ---
        show_power_spectrum = False
        if filter_type != "none":
            power_choice = input(
                "Analyze residual power spectrum (log scale, cycles/day)? (yes/no, default: no): "
            ).strip().lower()
            show_power_spectrum = power_choice in ["yes", "y"]

    # --- FIRST: Plot raw temperature time series for each location ---
    print("\n" + "="*70)
    print("TEMPERATURE TIME SERIES PLOTS (RAW DATA)")
    print("="*70)

    # Create a temporary results dict with just raw data for plotting
    raw_data_by_location = {}
    for location, cfgs in location_to_configs.items():
        # Load and merge data for this location (raw, no filtering)
        combined_df, timestamps, temperatures = load_location_data(
            location, cfgs, filter_type="none", show_fft_analysis=False, show_acf_analysis=False, show_power_spectrum=False
        )
        raw_data_by_location[location] = {
            "label": location,
            "timestamps": timestamps,
            "temperatures": temperatures,
        }

    # Plot the raw temperature time series
    plot_temperature_time_series(raw_data_by_location)

    # --- Process each LOCATION for analysis ---
    results_by_location = {}
    all_up_rel = []
    all_down_rel = []

    for location, cfgs in location_to_configs.items():
        result = process_location(location, cfgs, ships_df, eta_series, etd_series, filter_type, show_fft, show_acf, show_power_spectrum, up_jump_threshold, up_relax_offset, down_jump_threshold, down_relax_offset)
        results_by_location[location] = result
        all_up_rel.append(result["up_rel"])
        all_down_rel.append(result["down_rel"])

        # Individual plot per location (non-blocking)
        plot_location_with_ships(result, ships_df, ship_name_series, eta_series, etd_series, overlay_type=overlay_type)

    # Optional: merged relations
    if all_up_rel:
        all_up_rel_df = pd.concat(all_up_rel, ignore_index=True)
        print("\n=== ALL UP Spike–Ship Relations (all locations) ===")
        print(all_up_rel_df)

    if all_down_rel:
        all_down_rel_df = pd.concat(all_down_rel, ignore_index=True)
        print("\n=== ALL DOWN Spike–Ship Relations (all locations) ===")
        print(all_down_rel_df)

    # --- Abnormality summary per location ---
    if results_by_location:
        summary_rows = []
        for loc, res in results_by_location.items():
            summary_rows.append({
                "location": loc,
                "up_abnormal_count": res["up_abnormal_count"],
                "down_abnormal_count": res["down_abnormal_count"],
            })
        abnormal_summary = pd.DataFrame(summary_rows)
        print("\n=== Abnormality Summary (per location) ===")
        print(abnormal_summary)

    # --- Optional visualization prompts (only if interactive mode) ---
    if use_interactive:
        # --- Ask about seasonality comparison for erinia locations (only if seasonality not removed) ---
        erinia_locs = ["erinia_5", "erinia_15", "erinia_25"]
        erinia_available = [loc for loc in erinia_locs if loc in results_by_location]
        if len(erinia_available) > 0 and filter_type not in ["seasonal", "both"]:
            seasonality_choice = input(
                f"\nVisualize seasonality comparison for erinia locations? (yes/no, default: yes): "
            ).strip().lower()
            if seasonality_choice not in ["no", "n"]:
                print("Generating seasonality comparison diagram for erinia locations...")
                plot_seasonality_comparison(results_by_location, erinia_locs)
        # --- Ask about seasonality comparison for apothikes locations (only if seasonality not removed) ---
        apothikes_available = [loc for loc in apothikes_locs if loc in results_by_location]
        if len(apothikes_available) > 0 and filter_type not in ["seasonal", "both"]:
            seasonality_choice = input(
                f"\nVisualize seasonality comparison for apothikes locations? (yes/no, default: yes): "
            ).strip().lower()
            if seasonality_choice not in ["no", "n"]:
                print("Generating seasonality comparison diagram for apothikes locations...")
                plot_seasonality_comparison(results_by_location, apothikes_locs)

        # --- Ask about diurnal comparison for erinia locations (only if diurnal not removed) ---
        if len(erinia_available) > 0 and filter_type not in ["diurnal", "both"]:
            diurnal_choice = input(
                f"\nVisualize diurnal cycle comparison for erinia locations? (yes/no, default: no): "
            ).strip().lower()
            if diurnal_choice in ["yes", "y"]:
                print("Generating diurnal cycle comparison diagram for erinia locations...")
                plot_diurnal_comparison(results_by_location, erinia_locs)

        # --- Ask about diurnal comparison for apothikes locations (only if diurnal not removed) ---
        if len(apothikes_available) > 0 and filter_type not in ["diurnal", "both"]:
            diurnal_choice = input(
                f"\nVisualize diurnal cycle comparison for apothikes locations? (yes/no, default: no): "
            ).strip().lower()
            if diurnal_choice in ["yes", "y"]:
                print("Generating diurnal cycle comparison diagram for apothikes locations...")
                plot_diurnal_comparison(results_by_location, apothikes_locs)

        # --- Ask about station comparison (Erinia vs Apothikes) ---
        # Only offer if "both" filtering was applied (to have residual power spectra)
        if filter_type == "both":
            station_comparison_choice = input(
                f"\nCompare Erinia vs Apothikes stations using ACF and residual power spectra? (yes/no, default: yes): "
            ).strip().lower()
            if station_comparison_choice not in ["no", "n"]:
                print("Generating station comparison diagrams (ACF & Residual Power Spectra)...")
                compare_stations_acf_power_spectrum(results_by_location)
        # --- Ask which locations to combine on one diagram ---
        if not results_by_location:
            print("No locations processed, nothing to plot.")
            return

        print("\nAvailable locations:")
        for loc in results_by_location.keys():
            print(" -", loc)

        choice = input(
            "\nType a comma-separated list of locations to plot together "
            "(or 'all' for all, or just press Enter to skip combined plot): "
        ).strip()
    else:
        # Non-interactive mode: define variables and skip prompts
        erinia_locs = ["erinia_5", "erinia_15", "erinia_25"]
        apothikes_locs = ["apothikes_5", "apothikes_15", "apothikes_25"]

        # Try to get combined locations from analysis config
        if analysis_config and "combined_locations" in analysis_config:
            combined_list = analysis_config.get("combined_locations", [])
            if combined_list:
                choice = ",".join(combined_list)
            else:
                choice = ""
        else:
            choice = ""  # Skip combined plot if not configured

    if not choice:
        print("No combined plot selected.")
    else:
        if choice.lower() == "all":
            selected_locations = list(results_by_location.keys())
        else:
            # Parse comma-separated list
            selected_locations = [c.strip() for c in choice.split(",") if c.strip()]

        # Keep only valid ones
        selected_locations = [
            loc for loc in selected_locations if loc in results_by_location
        ]

        if not selected_locations:
            print("No valid locations selected for combined plot.")
        else:
            print("Combined plot for locations:", ", ".join(selected_locations))
            plot_multiple_locations_with_ships(
                results_by_location,
                selected_locations,
                ships_df,
                ship_name_series,
                eta_series,
                etd_series,
                overlay_type=overlay_type,
            )

    # --- THERMAL STRATIFICATION ANALYSIS ---
    thermal_pairs = analysis_config.get("thermal_stratification_pairs", []) if analysis_config else []

    print("\n" + "="*70)
    print("THERMAL STRATIFICATION ANALYSIS")
    print("="*70)
    print(f"Thermal pairs from config: {thermal_pairs}")
    print(f"Available locations: {list(results_by_location.keys())}")

    if thermal_pairs:
        stratification_results = []

        for loc1_name, loc2_name in thermal_pairs:
            print(f"\nProcessing pair: {loc1_name} - {loc2_name}")
            if loc1_name not in results_by_location:
                print(f"Warning: Location '{loc1_name}' not found. Skipping pair {loc1_name}-{loc2_name}")
                continue
            if loc2_name not in results_by_location:
                print(f"Warning: Location '{loc2_name}' not found. Skipping pair {loc1_name}-{loc2_name}")
                continue

            loc1_result = results_by_location[loc1_name]
            loc2_result = results_by_location[loc2_name]

            # Extract temperature and timestamp data
            loc1_temps = loc1_result.get("temperatures")
            loc2_temps = loc2_result.get("temperatures")
            loc1_times = loc1_result.get("timestamps")
            loc2_times = loc2_result.get("timestamps")

            # Compute stratification
            strat_data = compute_stratification(
                loc1_name, loc1_temps, loc1_times,
                loc2_name, loc2_temps, loc2_times
            )

            if strat_data:
                stratification_results.append(strat_data)
                print(f"\n{loc1_name} minus {loc2_name}:")
                print(f"  Common data points: {strat_data['common_points']} (skipped {strat_data['skipped_count']} misaligned points)")
                print(f"  Mean difference: {strat_data['mean_diff']:.2f}°C")
                print(f"  Max difference:  {strat_data['max_diff']:.2f}°C")
                print(f"  Min difference:  {strat_data['min_diff']:.2f}°C")
                print(f"  Std deviation:   {strat_data['std_diff']:.2f}°C")
                print(f"  {loc1_name} warmer: {strat_data['loc1_warmer_count']} times")
                print(f"  {loc2_name} warmer: {strat_data['loc2_warmer_count']} times")
            else:
                print(f"Warning: Could not compute stratification for {loc1_name}-{loc2_name} (data mismatch)")

        # Plot thermal stratification if we have valid results
        if stratification_results:
            print("\nGenerating thermal stratification plots...")
            plot_thermal_stratification(stratification_results)
        else:
            print("No valid thermal stratification pairs to plot.")

    # Keep all figures open until user closes them
    print("\nAll plots created. Close the figure windows to end the program.")
    plt.show()  # final blocking call so windows stay open


if __name__ == "__main__":
    import sys

    # Check if this is being called from the GUI or directly
    if len(sys.argv) > 1 and sys.argv[1] == "--run-analysis":
        # Called from GUI - run the analysis directly
        main()
    else:
        # Called directly - open the GUI
        try:
            import tkinter as tk
            from gui_config import ConfigurationGUI

            print("Opening Temperature Analysis Tool GUI...")
            root = tk.Tk()
            app = ConfigurationGUI(root)
            root.mainloop()
        except Exception as e:
            print(f"Error opening GUI: {e}")
            print("\nFalling back to direct analysis...")
            print("Make sure you have configured data sources.")
            main()
