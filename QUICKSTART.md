# Temperature Analysis Tool - Quick Start

## 🚀 5-Minute Setup

### Step 1: Start the GUI Configuration Tool
```bash
python gui_config.py
```

A window will appear with a user-friendly interface.

---

## Step 2: Add Temperature Data Files

1. **Click "+ Add Data Source"**

2. **For each temperature file:**
   - Click "Browse" → select your Excel file (e.g., `erinia_5_a.xlsx`)
   - **Location**: Enter location name (e.g., `erinia_5`)
   - **Sheet**: Usually "Data" (check your Excel file)
   - **DateTime Col**: Column number with dates (0-based indexing)
   - **Temp Col**: Column number with temperature values
   - **Lux Col**: Optional light sensor column (use -1 to skip)

3. **Click "Preview"** to verify columns are correct
   - See column names and numbers
   - First few rows displayed

4. **Repeat** for each data source

---

## Step 3: Configure Ship Schedule (Optional)

1. **Click "Browse"** under "Ship Schedule Data"
2. **Select** Excel file with ship times
3. **Verify sheet name** (usually "schedule")

---

## Step 4: Choose Analysis Options

**Fourier Filtering:**
- Select `both` for anomaly detection (removes daily & seasonal patterns)
- Select `none` to keep all original data
- Select `diurnal` or `seasonal` to remove only one type

**Overlay:**
- `ships` - Show ship presence on plots
- `lux` - Show light intensity
- `none` - No overlay

**Checkboxes:**
- ☑ Show FFT Components (recommended)
- ☑ Show ACF Analysis (recommended for comparison)
- ☑ Show Power Spectrum (recommended)

---

## Step 5: Run Analysis

1. **Click "Save Config"** - saves your settings for next time
2. **Click "Start Analysis →"**
3. **Running...**
   - Monitor console for progress
   - Plots will appear as analysis completes

---

## Understanding the Output

### What You'll See

1. **Spike Detection Plots** - Temperature jumps marked on time series
2. **ACF Plots** - Temporal patterns (if you selected that option)
3. **Power Spectrum** - Which frequencies are important
4. **Station Comparisons** - How different locations behave differently

### Abnormality Summary Table
```
      location  up_abnormal_count  down_abnormal_count
0     erinia_5                  45                   43
1    erinia_15                 108                  117
2    erinia_25                 208                  235
3  apothikes_5                  32                   31
4 apothikes_15                  95                  118
5 apothikes_25                 215                  194
```
- **up_abnormal_count**: Temperature jumps ≥ +0.5°C
- **down_abnormal_count**: Temperature drops ≤ -0.5°C

---

## Example: Typical Configuration

**For Erinia data (3 depths):**

| Step | Action | Value |
|------|--------|-------|
| 1 | Browse | `erinia_5_a.xlsx` |
| 2 | Location | `erinia_5` |
| 3 | Sheet | `Data` |
| 4 | DateTime Col | `2` |
| 5 | Temp Col | `4` |
| 6 | Lux Col | `5` |
| 7 | Preview | ✓ Looks good |
| 8 | Save & Add Next | |

**Repeat for:**
- `erinia_5_b.xlsx`
- `erinia_15_a.xlsx`, `erinia_15_b.xlsx`
- `erinia_25_a.xlsx`, `erinia_25_b.xlsx`
- `apothikes_5.xlsx`
- `apothikes_15.xlsx`
- `apothikes_25.xlsx`

**Ship Data:**
- File: `2.xlsx`
- Sheet: `schedule`

---

## Column Index Tips

Use **Preview** button to see column numbering:

```
Column indices and names:
  [0] DateTime
  [1] Sensor_ID
  [2] Temperature (°C)
  [3] Lux_Value
  [4] Status
```

- DateTime Col = `0`
- Temp Col = `2`
- Lux Col = `3`

---

## Common Questions

### Q: What if I don't have ship data?
**A:** The ship schedule is optional. Leave it blank or skip that step.

### Q: What do the analysis options mean?

- **Filter Type "both"**: Removes predictable patterns (daily cycle + seasonal changes), leaving only unusual variations
- **Show FFT Components**: Displays the extracted daily/seasonal patterns
- **Show ACF**: Shows if current temperature depends on past temperatures
- **Show Power Spectrum**: Shows what frequencies have the most "energy"

### Q: Can I reuse configurations?
**A:** Yes! Click "Load Config" to restore previous settings.

### Q: What if columns are wrong?
**A:** Use "Preview" button immediately to verify, or reload and select different column numbers.

### Q: How long does analysis take?
**A:** Usually 30 seconds to 2 minutes depending on data size and selected options.

---

## Next Steps

1. ✅ Configure data sources
2. ✅ Run analysis
3. 📊 View generated plots
4. 📈 Check abnormality summary
5. 📋 For detailed analysis, check console output
6. 💾 Configuration saved for next run

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "File not found" | Check file path, use browse button |
| "Column index out of range" | Run Preview to see actual columns |
| No plots appear | Check matplotlib is installed: `pip install matplotlib` |
| GUI won't open | Install: `pip install tkinter pandas openpyxl` |
| Unicode errors | Unlikely, but try: `pip install --upgrade pandas` |

---

## File Requirements Checklist

- [ ] Temperature Excel files (can have multiple per location)
- [ ] Ship schedule Excel file (optional)
- [ ] Files in same directory as script OR full path specified
- [ ] Valid datetime columns
- [ ] Valid numeric temperature columns
- [ ] Correct sheet names

---

## That's It!

You're now ready to analyze your temperature data. The GUI handles all the complexity - just:
1. Point to your files
2. Specify columns
3. Click "Start Analysis"

All plots and analysis are generated automatically!
