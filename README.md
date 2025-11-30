# Temperature Analysis Tool

A comprehensive temperature data analysis tool with GUI configuration, spike detection, and thermal stratification analysis. Designed for oceanographic and environmental temperature monitoring.

## Features

### 🎯 Core Analysis
- **Temperature Time Series Visualization** - Raw temperature data plots for each location (displayed first, before any analysis)
- **Spike Detection** - Automatic detection of temperature jumps with configurable thresholds
- **FFT-Based Filtering** - Remove diurnal cycles, seasonal trends, or both
- **Thermal Stratification** - Compare temperature differences between location pairs
- **Ship Schedule Integration** - Overlay vessel schedules on temperature analysis
- **ACF & Power Spectrum** - Advanced time-series analysis options

### 🖥️ User Interface
- **Interactive GUI** - Tkinter-based configuration tool (no manual JSON editing)
- **File Browser** - Easy data source selection with preview functionality
- **Scrollable Interface** - All options accessible in compact, scrollable window
- **Configuration Persistence** - Settings automatically saved and restored

### 📊 Visualization Features
- **Individual Location Plots** - Temperature and spike analysis per location
- **Combined Plots** - Multiple locations on single plot for comparison
- **Dynamic Titles** - Automatically reflect analysis type and data source
- **Statistics Boxes** - Mean, max, min, standard deviation on all plots
- **Non-Blocking Display** - Plots appear as analysis progresses

## Installation

### Requirements
- Python 3.7+
- pandas
- numpy
- matplotlib
- openpyxl
- statsmodels

### Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install dependencies
pip install pandas numpy matplotlib openpyxl statsmodels
```

## Quick Start

```bash
python main.py
```

This opens the GUI where you can:

### 1. **Add Data Sources**
   - Click "+ Add Data Source"
   - Select Excel file with temperature data
   - Specify location name, sheet name, and column indices
   - Click "Preview" to verify columns

### 2. **Configure Analysis Options**
   - Choose Fourier filtering: none, diurnal, seasonal, or both
   - Select overlay type: ships, lux, or none
   - Enable/disable FFT, ACF, and power spectrum analysis

### 3. **Add Advanced Options**
   - **Combined Plot Selection**: Comma-separated location names
   - **Thermal Stratification**: Location pairs (e.g., `erinia_5-erinia_15`)
   - **Spike Detection Parameters**: Adjust thresholds and offsets

### 4. **Run Analysis**
   - Click "Run Analysis"
   - Results appear in sequence:
     1. Raw temperature time series (each location)
     2. Filtered analysis plots
     3. Spike detection results
     4. Combined plots (if selected)
     5. Thermal stratification (if configured)

## Data Format

### Excel File Requirements
- **DateTime Column**: Pandas-readable datetime format
- **Temperature Column**: Numeric values in °C
- **Lux Column** (optional): Light intensity measurements

### Example
```
DateTime              | Temperature | Lux
2025-05-04 11:28:34 | 15.23      | 450
2025-05-04 11:29:42 | 15.45      | 455
...
```

## Configuration Files

### data_sources_config.json
Stores data source locations and settings:
```json
{
  "temperature_sources": [
    {
      "location": "erinia_5",
      "excel_file": "path/to/file.xlsx",
      "sheet_name": "Data",
      "dt_col": 0,
      "temp_col": 1,
      "lux_col": -1
    }
  ],
  "ships_file": null,
  "overlay_type": "lux",
  "filter_type": "both",
  "show_fft": true,
  "show_acf": false,
  "show_power_spectrum": false
}
```

### analysis_config.json
Generated during analysis, contains runtime parameters (not typically edited manually).

## Key Analysis Concepts

### Spike Detection
Identifies sudden temperature changes:
- **UP_JUMP_THRESHOLD**: Minimum positive change to detect (default: 0.5°C)
- **UP_RELAX_OFFSET**: Threshold for spike termination (default: 0.2°C)
- **DOWN_JUMP_THRESHOLD**: Minimum negative change (default: 0.5°C)
- **DOWN_RELAX_OFFSET**: Threshold for spike termination (default: 0.2°C)

### Thermal Stratification
Compares temperature differences between location pairs:
- Automatically handles timestamp misalignment (1-minute tolerance)
- Shows mean, max, min differences
- Indicates which location is warmer and how often
- Color-coded visualization (red = location 1 warmer, blue = location 2 warmer)

### Fourier Filtering
- **Diurnal**: Removes 24-hour temperature cycle
- **Seasonal**: Removes long-term seasonal trends
- **Both**: Applies both filters for anomaly detection

## File Structure

```
temperature-analysis/
├── main.py              # Analysis engine and core functions
├── gui_config.py        # GUI configuration tool
├── README.md            # This file
├── .gitignore           # Git ignore patterns
├── data/                # Data files folder
│   ├── DATA.md          # Data folder documentation
│   ├── .gitkeep         # Keeps folder in git (empty)
│   └── *.xlsx           # Excel files (not in git)
├── data_sources_config.json    # Persisted GUI configuration
└── analysis_config.json         # Runtime analysis parameters
```

**Note**: Excel data files are stored in the `data/` folder and are not committed to Git (see `.gitignore`). This keeps the repository clean and lightweight.

## Architecture

### Main Components

**main.py** (~2000 lines)
- `load_location_data()` - Load and merge temperature data
- `find_spikes()` - Detect temperature anomalies
- `compute_stratification()` - Calculate temperature differences between locations
- `plot_temperature_time_series()` - Raw data visualization
- `plot_location_with_ships()` - Individual location analysis plots
- `plot_thermal_stratification()` - Stratification comparison plots
- Fourier analysis functions (FFT, ACF, power spectrum)
- `process_location()` - Main analysis pipeline for each location

**gui_config.py** (~550 lines)
- `DataSourceRow` - Configuration for individual data source
- `ConfigWindow` - Main GUI application
- Tkinter-based scrollable interface
- File browsing and preview functionality
- Configuration save/load

### Data Flow

```
GUI Input
    ↓
data_sources_config.json
    ↓
main.py (load_config_from_gui)
    ↓
load_location_data() [raw temps, no filtering]
    ↓
plot_temperature_time_series() [first plots shown]
    ↓
process_location() [full analysis]
    ├─ Fourier filtering
    ├─ Spike detection
    ├─ Individual plots
    └─ Return processed data
    ↓
Combined plots (if selected)
    ↓
Thermal stratification (if configured)
    ↓
Final blocking show()
```

## Usage Examples

### Example 1: Basic Analysis
```
1. Run: python main.py
2. Add 2-3 Excel files with temperature data
3. Select "both" for Fourier filtering
4. Click "Run Analysis"
```

### Example 2: Thermal Stratification
```
1. Configure data sources (erinia_5, erinia_15, erinia_25)
2. In "Thermal Stratification": erinia_5-erinia_15, erinia_15-erinia_25
3. Adjust spike detection thresholds if needed
4. Click "Run Analysis"
```

### Example 3: Spike Detection with Ship Overlay
```
1. Add temperature data
2. Add ship schedule Excel file
3. Select "ships" overlay
4. Customize spike thresholds (e.g., 0.8 for UP_JUMP_THRESHOLD)
5. Click "Run Analysis"
```

## Troubleshooting

### "Location not found in results"
- Check spelling matches exactly in data_sources_config.json
- Verify location name from Excel filename matches configuration

### "No exact timestamp match" / "Data mismatch"
- Normal - tool uses 1-minute tolerance for timestamp matching
- If still failing, check both files have overlapping time ranges
- Use Preview to verify data format

### "Cannot select to combine locations"
- Use comma-separated format: `location1, location2, location3`
- No hyphens in combined plot names
- Leave empty to skip combined plots

### Plots not appearing
- Check matplotlib is installed: `pip install matplotlib`
- Try adjusting window focus (sometimes plots open behind other windows)
- Ensure analysis completes without errors in console

### GUI scrollbar not working
- All content should be scrollable - use mouse wheel or scrollbar
- If stuck, close window and restart

## Performance Notes

- **Load Time**: Depends on Excel file size (typically <30s per location)
- **Memory**: ~2-3MB per 1000 data points
- **Plot Generation**: Non-blocking, appears as analysis progresses
- **Filtering**: FFT-based (efficient for large datasets)

## Data Privacy

- **Local Processing**: All analysis runs locally, no data sent anywhere
- **Configuration Files**: Stored as JSON in project directory
- **Automatic Cleanup**: Temporary plots are memory-resident, not saved to disk

## License

This project is provided as-is for temperature data analysis.

## Support

For issues or questions:
1. Check the console output for detailed error messages
2. Use [Debug] messages to understand what's happening
3. Verify data format matches expected structure
4. Ensure all required Python packages are installed

---

**Version**: 1.0
**Last Updated**: November 30, 2024
**Python**: 3.7+