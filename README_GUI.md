# Temperature Analysis Tool - GUI Configuration Guide

## Overview

This tool provides a complete pipeline for analyzing temperature data from multiple Excel sources, detecting anomalies, and comparing behavior between monitoring stations using advanced signal processing techniques (FFT, ACF, power spectrum analysis).

## Quick Start

### Method 1: Using the GUI (Recommended)

1. **Launch the GUI Configuration Tool:**
   ```bash
   python gui_config.py
   ```

2. **Configure Data Sources:**
   - Click "+ Add Data Source" to add temperature data files
   - For each source:
     - Click "Browse" to select an Excel file
     - Enter the location name (e.g., "erinia_5", "apothikes_15")
     - Specify the sheet name (default: "Data")
     - Set column indices for:
       - **DateTime Column**: The column containing timestamps
       - **Temperature Column**: The column containing temperature values
       - **Lux Column (optional)**: The column containing light intensity values (-1 to skip)
     - Click "Preview" to verify the data before proceeding

3. **Configure Ship Schedule:**
   - Click "Browse" under "Ship Schedule Data"
   - Select the Excel file containing ship ETA/ETD information
   - Verify the sheet name (default: "schedule")

4. **Set Analysis Options:**
   - **Fourier Filtering**: Choose from:
     - `none` - Keep original data
     - `diurnal` - Remove 24-hour cycle only
     - `seasonal` - Remove seasonal components only
     - `both` - Remove both (recommended for anomaly detection)

   - **Overlay**: Choose what to show on spike plots:
     - `ships` - Show ship presence intervals
     - `lux` - Show light intensity values
     - `none` - No overlay

   - **Checkboxes:**
     - ☑ Show FFT Components - Visualize extracted components
     - ☑ Show ACF Analysis - Compute autocorrelation function
     - ☑ Show Power Spectrum - Analyze residual variability

5. **Save Configuration:**
   - Click "Save Config" to save your settings
   - Configuration is saved to `data_sources_config.json`

6. **Start Analysis:**
   - Click "Start Analysis →" button
   - Or run `python main.py` in terminal

---

### Method 2: Using Command Line (For Automated Workflows)

1. **Create `data_sources_config.json` manually:**
   ```json
   {
     "temperature_sources": [
       {
         "location": "erinia_5",
         "series": "A",
         "excel_file": "erinia_5_a.xlsx",
         "sheet_name": "Data",
         "dt_col": 2,
         "temp_col": 4,
         "lux_col": 5
       },
       {
         "location": "erinia_5",
         "series": "B",
         "excel_file": "erinia_5_b.xlsx",
         "sheet_name": "Data",
         "dt_col": 1,
         "temp_col": 2,
         "lux_col": 3
       }
     ],
     "ships_file": "ships_schedule.xlsx",
     "ships_sheet": "schedule"
   }
   ```

2. **Create `analysis_config.json`:**
   ```json
   {
     "filter_type": "both",
     "overlay_type": "ships",
     "show_fft": true,
     "show_acf": true,
     "show_power_spectrum": true
   }
   ```

3. **Run Analysis:**
   ```bash
   python main.py
   ```

---

## Data Source Configuration Details

### Column Index Selection

Column indices are **0-based** (counting starts from 0):
- Column A = 0
- Column B = 1
- Column C = 2
- etc.

### Example Configuration

**If your Excel file looks like:**
```
| DateTime (Col 0) | Sensor ID (Col 1) | Temperature (Col 2) | Lux (Col 3) |
|------------------|-------------------|---------------------|-------------|
| 2024-01-01 12:00 | Sensor_A          | 18.5                | 450         |
| 2024-01-01 13:00 | Sensor_A          | 19.2                | 620         |
```

**Configuration would be:**
- DateTime Column: `0`
- Temperature Column: `2`
- Lux Column: `3`

---

## Analysis Options Explained

### Fourier Filtering

The tool uses **Fast Fourier Transform (FFT)** to remove periodic components:

- **none**: Analyze raw temperature data
- **diurnal**: Remove only the 24-hour cycle (useful for detecting anomalies independent of daily variation)
- **seasonal**: Remove only seasonal components (longer-term variations)
- **both**: Remove both cycles (best for anomaly detection - reveals residual variability)

### Visualizations Generated

#### 1. **Spike Detection Plots**
- Shows detected temperature jumps (up and down)
- Marks spike points with markers
- Overlays ship presence or light intensity

#### 2. **ACF (Autocorrelation Function) Analysis**
- Reveals temporal dependencies in data
- Shows 24-hour and weekly cycle strength
- Compares original vs. filtered data

#### 3. **Power Spectrum Analysis**
- Displays energy distribution across frequencies
- Shows which periodicities dominate
- Uses log scale to reveal weak patterns
- Helpful for identifying sub-daily or multi-day cycles

#### 4. **Station Comparison** (when filter_type="both")
- Side-by-side ACF plots for Erinia vs Apothikes
- Residual power spectra comparison
- Generated at each depth (5m, 15m, 25m)
- Highlights differences in temperature dynamics between locations

#### 5. **Component Visualization**
- Shows extracted diurnal cycle
- Shows extracted seasonal components
- Shows combined periodic components

---

## Output Files Generated

1. **Plots/Figures** - Multiple interactive matplotlib windows showing:
   - Individual location spike analysis
   - Combined multi-location comparisons
   - ACF analyses
   - Power spectra
   - Station comparisons
   - Component decompositions

2. **Console Output** - Displays:
   - Abnormality summary per location
   - Spike-to-ship relationships
   - Data quality information
   - Analysis parameters used

3. **Configuration Files**:
   - `data_sources_config.json` - Data source configuration
   - `analysis_config.json` - Analysis parameters

---

## Common Workflows

### Workflow 1: Detect Temperature Anomalies
```
Filter Type: "both"          (remove daily & seasonal patterns)
Show FFT Components: YES     (see what was removed)
Show ACF: YES               (understand temporal structure)
Show Power Spectrum: YES     (see remaining variability)
Overlay: "ships"            (correlate with ship presence)
```

### Workflow 2: Compare Station Characteristics
```
Filter Type: "both"
Show ACF: YES
Show Power Spectrum: YES
Station Comparison: YES      (automatically offered)
```

### Workflow 3: Analyze Diurnal & Seasonal Patterns
```
Filter Type: "none"         (keep all patterns)
Show FFT Components: YES
Show Diurnal Comparison: YES
Show Seasonality Comparison: YES
```

---

## Troubleshooting

### "File not found" Error
- Check that Excel file paths are correct
- Verify the sheet name exists in the file
- Use absolute paths if relative paths don't work

### "Column index out of range"
- Your Excel file has fewer columns than specified
- Run "Preview" to see available columns
- Adjust column indices accordingly

### No Data Loaded
- Verify DateTime column contains valid dates
- Ensure Temperature column contains numeric values
- Check that data hasn't been filtered in Excel

### Plots Don't Appear
- Ensure matplotlib backend is installed: `pip install matplotlib`
- On some systems, you may need: `pip install pyqt5` or `pip install tkinter`

### GUI Won't Start
- Install required packages: `pip install pandas openpyxl statsmodels`

---

## File Format Requirements

### Temperature Data Excel Files
- Columns can be in any order
- DateTime should be in recognizable format (ISO 8601, etc.)
- Temperature values should be numeric
- Lux values are optional

### Ship Schedule Excel File
- Column 0 (A): Ship ID or name identifier
- Column 1 (B): Ship name
- Column 2 (C): ETA (Estimated Time of Arrival)
- Column 3 (D): ETD (Estimated Time of Departure)
- Dates should be in datetime format

---

## Advanced Usage

### Load Previous Configuration
1. Run `gui_config.py`
2. Click "Load Config" to restore previous settings
3. Make any changes needed
4. Click "Start Analysis"

### Save Multiple Configurations
1. Configure data sources and options
2. Click "Save Config" - saves to `data_sources_config.json`
3. Manually copy the JSON file with a new name (e.g., `config_winter.json`)
4. To load: rename back to `data_sources_config.json` or edit `gui_config.py`

### Batch Processing
- Set up a configuration file
- Run: `python main.py` repeatedly for different data sources
- Only interactive prompts appear if no saved configuration exists

---

## Technical Details

### Signal Processing Methods

1. **FFT-based Filtering**:
   - Transforms data to frequency domain
   - Removes high-magnitude components (seasonal/diurnal)
   - Inverse transforms back to time domain
   - Preserves anomalies not explained by periodic patterns

2. **ACF Analysis**:
   - Computes Pearson correlation at different lags
   - Shows memory/persistence in temperature data
   - Helps identify cyclic patterns

3. **Power Spectrum**:
   - Computes power = |FFT(signal)|²
   - Log scale reveals weak patterns
   - Frequencies shown in cycles/day
   - Identifies dominant oscillations

---

## Contact & Support

For issues or questions:
1. Check that all Excel files have correct structure
2. Verify column indices using "Preview" button
3. Review console output for error messages
4. Ensure Python packages are up-to-date: `pip install --upgrade pandas openpyxl statsmodels matplotlib`

---

## Version History

- **v1.0** - Initial release with GUI configuration
  - Support for multiple data sources per location
  - FFT-based filtering (diurnal/seasonal)
  - Spike detection and ship correlation
  - ACF and power spectrum analysis
  - Station comparison features
