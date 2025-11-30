# Project Architecture

## Module Organization

The Temperature Analysis Tool is organized into separate, focused modules for maintainability and clarity.

### Core Modules

#### `main.py` (~1900 lines)
**Entry point and orchestration**
- `load_config_from_gui()` - Load configuration from GUI-generated JSON
- `load_location_data()` - Load and merge temperature data from Excel
- `process_location()` - Main analysis pipeline for each location
- `build_spike_ship_relations()` - Relate spikes to ship schedules
- `main()` - Orchestrate complete analysis workflow

#### `analysis.py` (~230 lines)
**Spike Detection and Thermal Stratification**
- `find_spikes()` - Detect temperature jumps and anomalies
- `add_inner_spike_info()` - Detect spikes within spikes
- `compute_stratification()` - Calculate temperature differences between locations
- Constants: Default threshold values

Key Features:
- Configurable spike detection thresholds
- Automatic timestamp alignment with 1-minute tolerance
- Inner spike detection support

#### `filtering.py` (~130 lines)
**Fourier-Based Data Filtering**
- `analyze_seasonality_fft()` - FFT spectrum analysis
- `remove_seasonality_fft()` - Remove seasonal trends
- `remove_diurnal_cycle()` - Extract/remove 24-hour cycle
- `apply_filter()` - Apply selected filter type

Supported Filters:
- None (raw data)
- Diurnal (remove 24-hour cycle)
- Seasonal (remove long-term trends)
- Both (apply both filters)

#### `gui_config.py` (~525 lines)
**User Interface and Configuration**
- `DataSourceRow` - Individual data source configuration widget
- `ConfigWindow` - Main GUI application
- `start_analysis()` - Run analysis with GUI parameters
- `load_config()` - Restore previous settings
- `save_config()` - Persist settings

Features:
- Scrollable interface with all options accessible
- File browser with preview functionality
- Real-time validation
- Configuration persistence

### Supporting Files

- `README.md` - User documentation
- `data/` - Folder for Excel data files
- `data/DATA.md` - Data format documentation
- `.gitignore` - Repository exclusion rules

## Data Flow

```
┌─────────────────┐
│   User Opens    │
│   python main.py │
└────────┬────────┘
         │
    ┌────▼─────┐
    │  GUI     │
    │ (Tkinter)│
    └────┬─────┘
         │
    ┌────▼──────────────────────┐
    │ data_sources_config.json   │
    │ analysis_config.json       │
    └────┬──────────────────────┘
         │
    ┌────▼──────────────────┐
    │ main.py               │
    │ (Load & Orchestrate)  │
    └────┬──────────────────┘
         │
    ┌────▼────────────────────────────┐
    │ load_location_data()             │
    │ (Load Excel + merge locations)   │
    └────┬─────────────────────────────┘
         │
    ┌────▼──────────────────┐
    │ plot_temperature_     │
    │ time_series()         │ ─────── RAW DATA PLOTS
    └──────────────────────┘
         │
    ┌────▼──────────────────────────────┐
    │ process_location()                 │
    │ ├─ apply_filter()                 │ ─── filtering.py
    │ ├─ find_spikes()                  │ ─── analysis.py
    │ ├─ compute_stratification()       │ ─── analysis.py
    │ └─ plot_location_with_ships()     │ ─── main.py (for now)
    └────┬───────────────────────────────┘
         │
    ┌────▼──────────────────┐
    │ Combined Plots        │
    │ (if selected)         │
    └──────────────────────┘
         │
    ┌────▼──────────────────────┐
    │ Thermal Stratification    │
    │ Plots (if configured)     │
    └──────────────────────────┘
         │
    ┌────▼──────────────────┐
    │ Final plt.show()      │
    │ (Blocking call)       │
    └──────────────────────┘
```

## Module Dependencies

```
gui_config.py
    └─ main.py
        ├─ analysis.py
        │   └─ pandas, numpy
        ├─ filtering.py
        │   └─ numpy, scipy
        └─ (plotting functions in main.py for now)
            └─ matplotlib
```

## Import Structure

### analysis.py
```python
import pandas as pd
import numpy as np
```

### filtering.py
```python
import numpy as np
from scipy import signal
import matplotlib.pyplot as plt
```

### main.py
```python
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from analysis import find_spikes, add_inner_spike_info, compute_stratification
from filtering import apply_filter, analyze_seasonality_fft, ...
```

### gui_config.py
Standalone, imports only tkinter and standard library

## Function Categories

### Analysis Functions (analysis.py)
- Spike detection
- Inner spike detection
- Thermal stratification computation

### Filtering Functions (filtering.py)
- FFT-based spectrum analysis
- Seasonal component removal
- Diurnal cycle removal
- Filter application

### Data Processing (main.py)
- Configuration loading
- Data loading and merging
- Location processing pipeline
- Ship relation building

### Visualization (main.py - candidate for extraction)
- Time series plots
- Location plots with spikes
- Combined location plots
- Thermal stratification plots
- Comparison plots (ACF, power spectrum)

### UI (gui_config.py)
- Configuration entry
- File browsing
- Data preview
- Settings persistence

## Future Refactoring

### Potential Modules
1. **plotting.py** - Extract all visualization functions
2. **config.py** - Extract configuration handling
3. **data_loader.py** - Extract data loading functions
4. **utils.py** - Extract utility functions (build relations, etc.)

### Size Reduction Target
- main.py: 2000 lines → ~800 lines (orchestration only)
- New plotting.py: ~600 lines
- New config.py: ~200 lines
- New data_loader.py: ~300 lines

## Design Principles

1. **Single Responsibility** - Each module has one clear purpose
2. **Low Coupling** - Modules are independent and loosely coupled
3. **High Cohesion** - Related functions grouped together
4. **Clear Interfaces** - Public functions documented with docstrings
5. **Type Hints** - Parameters clearly specified
6. **Error Handling** - Graceful handling with informative messages

## Testing Approach

Each module can be tested independently:

```python
# Test analysis.py
from analysis import find_spikes
test_temps = [15, 16.2, 16.5, ...]
test_times = [...]
spikes = find_spikes(test_times, test_temps)

# Test filtering.py
from filtering import remove_diurnal_cycle
filtered = remove_diurnal_cycle(test_temps, test_times)

# Test main.py functions
from main import load_location_data
df, times, temps = load_location_data(...)
```

## Documentation

- **README.md** - User-facing documentation
- **ARCHITECTURE.md** - This file (developer documentation)
- **data/DATA.md** - Data format requirements
- **Inline Comments** - Key logic explained in code

## Maintenance

- Keep modules focused and small
- Extract functions when a module exceeds 500 lines
- Update this document when adding new modules
- Maintain consistent naming conventions
- Document new public functions with docstrings