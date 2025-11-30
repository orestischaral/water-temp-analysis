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

        if direction == "up":
            start_condition = (delta >= up_threshold)
            cutoff_value = values[i] + up_offset
        elif direction == "down":
            start_condition = (delta <= -down_threshold)
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

            while end_idx < len(values):
                if direction == "up" and values[end_idx] <= cutoff_value:
                    break
                elif direction == "down" and values[end_idx] >= cutoff_value:
                    break

                max_value = max(max_value, values[end_idx])
                min_value = min(min_value, values[end_idx])
                end_idx += 1

            if end_idx == len(values):
                end_idx = len(values) - 1

            spike = {
                "start_datetime": timestamps[start_idx],
                "end_datetime": timestamps[end_idx],
                "start_idx": start_idx,
                "end_idx": end_idx,
                "base_value": base_value,
                "max_value": max_value,
                "min_value": min_value,
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