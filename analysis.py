"""
Spike Detection and Thermal Stratification Analysis Module

Functions for detecting temperature anomalies and analyzing temperature
differences between location pairs.
"""

import pandas as pd
import numpy as np

# Default spike detection parameters
UP_JUMP_THRESHOLD = 0.5
UP_RELAX_OFFSET = 0.2
DOWN_JUMP_THRESHOLD = 0.5
DOWN_RELAX_OFFSET = 0.2


def find_spikes(timestamps, values, direction="up",
                up_threshold=None, up_offset=None,
                down_threshold=None, down_offset=None):
    """
    Find spikes (rapid changes) in temperature data.

    Parameters:
        timestamps: DateTime index
        values: Temperature values
        direction: "up" or "down"
        up_threshold: UP spike threshold (°C)
        up_offset: UP spike termination offset (°C)
        down_threshold: DOWN spike threshold (°C)
        down_offset: DOWN spike termination offset (°C)

    Returns:
        List of spike dicts with start/end times and values

    Note:
        - Spikes are only detected when data points are in proper time sequence
        - Time intervals must be approximately 1 hour (0.5-1.5 hours tolerance)
        - If a time gap is detected within a spike, spike tracking stops
        - This prevents false spike detection from data gaps or missing values
        - Inner spikes are detected recursively and also require continuous data
    """
    if up_threshold is None:
        up_threshold = UP_JUMP_THRESHOLD
    if up_offset is None:
        up_offset = UP_RELAX_OFFSET
    if down_threshold is None:
        down_threshold = DOWN_JUMP_THRESHOLD
    if down_offset is None:
        down_offset = DOWN_RELAX_OFFSET

    spikes = []
    i = 0

    while i < len(values) - 1:
        delta = values[i + 1] - values[i]

        # Check time interval between consecutive points (should be ~1 hour)
        # Skip spike detection if time gap is too large (indicates missing data)
        try:
            time_diff = (timestamps[i + 1] - timestamps[i]).total_seconds() / 3600.0  # hours
        except (AttributeError, TypeError):
            # Handle numpy datetime64
            time_diff = (timestamps[i + 1] - timestamps[i]) / np.timedelta64(1, 'h')

        # Only consider valid spikes if time interval is close to 1 hour (0.5 to 1.5 hours tolerance)
        valid_time_interval = 0.5 <= time_diff <= 1.5

        if direction == "up":
            start_condition = (delta >= up_threshold) and valid_time_interval
            cutoff_value = values[i] + up_offset
        elif direction == "down":
            start_condition = (delta <= -down_threshold) and valid_time_interval
            cutoff_value = values[i] - down_offset
        else:
            break

        if start_condition:
            # Start of spike
            start_idx = i
            base_value = values[start_idx]

            # Find end of spike
            end_idx = start_idx + 1
            max_value = values[end_idx]
            min_value = values[end_idx]
            time_gap_detected = False  # Flag to break if time continuity is lost

            while end_idx < len(values):
                # Check time interval at each step to ensure data continuity
                try:
                    step_time_diff = (timestamps[end_idx] - timestamps[end_idx - 1]).total_seconds() / 3600.0
                except (AttributeError, TypeError):
                    step_time_diff = (timestamps[end_idx] - timestamps[end_idx - 1]) / np.timedelta64(1, 'h')

                # If time gap is too large, stop tracking this spike
                if not (0.5 <= step_time_diff <= 1.5):
                    time_gap_detected = True
                    end_idx -= 1  # Step back to last valid point
                    break

                if direction == "up" and values[end_idx] <= cutoff_value:
                    break
                elif direction == "down" and values[end_idx] >= cutoff_value:
                    break

                max_value = max(max_value, values[end_idx])
                min_value = min(min_value, values[end_idx])
                end_idx += 1

            if end_idx == len(values):
                end_idx = len(values) - 1

            # Only record spike if it has at least 2 consecutive points (spike + relaxation)
            if end_idx > start_idx:
                spike = {
                    "direction": direction,
                    "start_datetime": timestamps[start_idx],
                    "end_datetime": timestamps[end_idx],
                    "start_idx": start_idx,
                    "end_idx": end_idx,
                    "base_value": base_value,
                    "max_value": max_value,
                    "min_value": min_value,
                    "num_measurements": end_idx - start_idx + 1,
                    "times": timestamps[start_idx:end_idx + 1],
                    "values": values[start_idx:end_idx + 1],
                }
                spikes.append(spike)
            i = end_idx + 1
        else:
            i += 1

    return spikes


def add_inner_spike_info(outer_spikes, direction, up_jump_threshold=None, up_relax_offset=None,
                         down_jump_threshold=None, down_relax_offset=None):
    """
    Find inner spikes within each outer spike.

    Parameters:
        outer_spikes: List of outer spike dicts
        direction: "up" or "down"
        up_jump_threshold, up_relax_offset, down_jump_threshold, down_relax_offset: Thresholds
    """
    for outer_spike in outer_spikes:
        inner_timestamps = pd.to_datetime(outer_spike["times"]).to_numpy()
        inner_values = pd.Series(outer_spike["values"]).to_numpy()

        inner_spikes = find_spikes(inner_timestamps, inner_values, direction=direction,
                                   up_threshold=up_jump_threshold, up_offset=up_relax_offset,
                                   down_threshold=down_jump_threshold, down_offset=down_relax_offset)

        outer_spike["inner_spikes"] = inner_spikes
        outer_spike["inner_spike_count"] = len(inner_spikes)

        if inner_spikes:
            for s in inner_spikes:
                if direction == "up":
                    s["amplitude"] = s["max_value"] - s["base_value"]
                else:
                    s["amplitude"] = s["base_value"] - s["min_value"]

            strongest = max(inner_spikes, key=lambda x: x["amplitude"])
            outer_spike["strongest_inner_spike"] = strongest
            outer_spike["strongest_inner_amplitude"] = strongest["amplitude"]
        else:
            # Initialize with None/0 when no inner spikes found
            outer_spike["strongest_inner_spike"] = None
            outer_spike["strongest_inner_amplitude"] = 0.0


def compute_cross_correlation_with_ships(temperatures, timestamps, eta_series, etd_series, location_name, max_lag_hours=72):
    """
    Compute cross-correlation between temperature time series and ship presence.

    Shows if temperature changes correlate with ship arrivals/departures at various time lags.

    Parameters:
        temperatures: Temperature array (°C)
        timestamps: DateTime array
        eta_series: Ship arrival times (pandas Series)
        etd_series: Ship departure times (pandas Series)
        location_name: Location label for output
        max_lag_hours: Maximum lag to check (in hours)

    Returns:
        Dict with:
            - 'lags': Lag values in hours
            - 'correlation': Cross-correlation values
            - 'max_correlation': Peak correlation value
            - 'max_lag': Lag at peak correlation (hours)
            - 'ship_presence': Binary ship presence signal (1=ship present, 0=absent)
    """
    import numpy as np
    from scipy import signal

    if eta_series is None or etd_series is None or len(eta_series) == 0:
        print(f"  [Debug] No ship data available for {location_name}")
        return None

    try:
        # Convert timestamps to pandas datetime for consistent comparison
        timestamps_pd = pd.to_datetime(timestamps)
        eta_series_pd = pd.to_datetime(eta_series)
        etd_series_pd = pd.to_datetime(etd_series)

        # Create binary ship presence signal aligned with temperature timestamps
        ship_presence = np.zeros(len(temperatures), dtype=int)
        ship_count = 0

        for idx_ship, (eta, etd) in enumerate(zip(eta_series_pd, etd_series_pd)):
            if pd.isna(eta) or pd.isna(etd):
                continue

            # Find indices where ship is present
            # Compare as datetime objects
            mask = (timestamps_pd >= eta) & (timestamps_pd <= etd)
            if np.any(mask):
                ship_presence[mask] = 1
                ship_count += 1
                print(f"  [Debug] Ship {idx_ship+1}: {eta} to {etd}, found {np.sum(mask)} matching time points")

        if np.sum(ship_presence) == 0:
            print(f"  [Debug] No ship presence detected for {location_name} - ships may be outside temperature data range")
            return None

        print(f"  [Debug] Total ships with presence: {ship_count}, total presence points: {np.sum(ship_presence)}")

        # Normalize temperature to zero mean for correlation
        temp_normalized = temperatures - np.mean(temperatures)
        ship_normalized = ship_presence.astype(float) - np.mean(ship_presence)

        # Compute cross-correlation
        # This shows how temperature correlates with ship presence at different lags
        correlation = signal.correlate(temp_normalized, ship_normalized, mode='full')

        # Get lag values in hours
        max_lag_samples = min(int(max_lag_hours / 1), len(temperatures) // 2)  # Assume ~1 hour sampling
        center = len(correlation) // 2
        lags_samples = np.arange(center - max_lag_samples, center + max_lag_samples + 1) - center
        correlation_subset = correlation[center - max_lag_samples:center + max_lag_samples + 1]

        # Convert samples to hours (assuming hourly data)
        lags_hours = lags_samples * 1.0  # 1 hour per sample

        # Normalize correlation
        max_corr_value = np.max(np.abs(correlation_subset))
        if max_corr_value > 0:
            correlation_normalized = correlation_subset / max_corr_value
        else:
            correlation_normalized = correlation_subset

        # Find peak
        max_corr_idx = np.argmax(np.abs(correlation_normalized))
        max_corr = correlation_normalized[max_corr_idx]
        max_lag = lags_hours[max_corr_idx]

        print(f"  [Debug] Cross-correlation computed: peak={max_corr:.3f} at lag={max_lag:.1f}h")

        return {
            'lags': lags_hours,
            'correlation': correlation_normalized,
            'max_correlation': max_corr,
            'max_lag': max_lag,
            'ship_presence': ship_presence,
            'ship_presence_percentage': 100 * np.sum(ship_presence) / len(ship_presence),
        }

    except Exception as e:
        print(f"  [Error] Computing cross-correlation for {location_name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return None


def compute_stratification(loc1_name, loc1_temps, loc1_times, loc2_name, loc2_temps, loc2_times):
    """
    Compute temperature difference between two locations.
    Handles cases where timestamps may not be perfectly aligned.

    Returns:
        Dict with differences, timestamps, and statistics, or None if data unavailable
    """
    if loc1_temps is None or loc2_temps is None or len(loc1_temps) == 0 or len(loc2_temps) == 0:
        print(f"  [Debug] Missing temperature data for {loc1_name} or {loc2_name}")
        return None

    try:
        # Convert to pandas Series for easier handling
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