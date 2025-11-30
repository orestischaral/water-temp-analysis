# Plot Title Fix - Dynamic Overlay Labels

**Issue:** Plot titles always said "Ships" even when the actual overlay was "Lux"
**Status:** FIXED ✓

---

## What Was Changed

### 1. Individual Location Plots
**Function:** `plot_location_with_ships()` (line 1143-1153)

**Before:**
```
Title: "erinia_5: UP and DOWN Spikes with Ship ETA-ETD (up=5, down=2)"
(Even when showing Lux data!)
```

**After:**
```python
if overlay_type == "ships":
    overlay_desc = "with Ship ETA-ETD"
elif overlay_type == "lux":
    overlay_desc = "with Light Intensity"
else:  # "none"
    overlay_desc = ""

ax.set_title(f"{label}: UP and DOWN Spikes {overlay_desc} (up={up_abn}, down={down_abn})")
```

**Result:**
- If overlay is "ships": `"erinia_5: UP and DOWN Spikes with Ship ETA-ETD (up=5, down=2)"`
- If overlay is "lux": `"erinia_5: UP and DOWN Spikes with Light Intensity (up=5, down=2)"`
- If overlay is "none": `"erinia_5: UP and DOWN Spikes (up=5, down=2)"`

---

### 2. Combined Location Plots
**Function:** `plot_multiple_locations_with_ships()` (line 1278-1287)

**Before:**
```
Title: "Combined locations: UP and DOWN Spikes with Ship ETA-ETD Intervals"
(Even when showing Lux data!)
```

**After:**
```python
if overlay_type == "ships":
    overlay_desc = "with Ship ETA-ETD Intervals"
elif overlay_type == "lux":
    overlay_desc = "with Light Intensity"
else:  # "none"
    overlay_desc = ""

ax.set_title(f"Combined locations: UP and DOWN Spikes {overlay_desc}")
```

**Result:**
- If overlay is "ships": `"Combined locations: UP and DOWN Spikes with Ship ETA-ETD Intervals"`
- If overlay is "lux": `"Combined locations: UP and DOWN Spikes with Light Intensity"`
- If overlay is "none": `"Combined locations: UP and DOWN Spikes"`

---

## Example

### Previous Behavior
```
User selects:
- Overlay type: LUX
- Runs analysis

Plot title shows:
"erinia_5: UP and DOWN Spikes with Ship ETA-ETD (up=5, down=2)"
                                    ↑
                              WRONG! Should say "Light Intensity"
```

### New Behavior
```
User selects:
- Overlay type: LUX
- Runs analysis

Plot title shows:
"erinia_5: UP and DOWN Spikes with Light Intensity (up=5, down=2)"
                                    ↑
                              CORRECT!
```

---

## Summary

✓ **Individual location plots** now show the correct overlay type in title
✓ **Combined location plots** now show the correct overlay type in title
✓ **All three overlay types** (ships, lux, none) properly labeled
✓ **Syntax verified** and code tested

The plot titles now accurately reflect what you configured!

