# Combined Plot Selection Guide

**NEW FEATURE:** You can now select which locations to combine in a single plot directly from the GUI!

---

## How to Use

### Step 1: Open GUI
```bash
python main.py
```

### Step 2: Configure Data Sources
- Add your Excel files as usual
- Click Preview to verify columns
- Set column indices

### Step 3: Set Analysis Options
- Choose Fourier filtering type
- Choose overlay type
- Check visualization options

### Step 4: NEW - Select Locations to Combine
**Look for the new section:** "Combined Plot Selection (Optional)"

Enter the locations you want to combine in one plot:
- **Example 1:** `erinia_5, erinia_15` (combines erinia_5 and erinia_15)
- **Example 2:** `erinia_5, erinia_15, erinia_25` (combines all three)
- **Example 3:** Leave empty to skip combined plot

**Format:**
- Separate location names with commas
- Spaces are optional (will be trimmed)
- Location names are case-sensitive

### Step 5: Run Analysis
1. Click "Run Analysis"
2. The combined plot will be generated automatically
3. **NO terminal prompts!**

---

## Examples

### Combine Two Locations
Input: `erinia_5, erinia_15`

Result: One plot with both locations overlaid

### Combine All Locations
Input: `erinia_5, erinia_15, erinia_25, apothikes_5, apothikes_15, apothikes_25`

Result: Single plot with all locations

### Skip Combined Plot
Input: (leave empty)

Result: No combined plot generated

---

## Saving Your Selection

When you click "Run Analysis":
1. Your combined location selection is automatically saved
2. Next time you run the GUI, your selection will be remembered
3. You can modify it and click "Run Analysis" again

---

## What Gets Saved

The GUI saves your selection to **analysis_config.json** with:
- Combined locations list
- All other analysis settings

The selection persists between runs and is automatically loaded when you next open the GUI.

---

## Tips

### Tip 1: Check Available Locations
When you run analysis, the console will show available locations.
Copy these exact names into the "Combined Plot Selection" field.

### Tip 2: Order Doesn't Matter
These produce the same result:
- `erinia_5, erinia_15`
- `erinia_15, erinia_5`

### Tip 3: Typos Are Silently Ignored
If you enter `erinia_5, erinia_999`:
- erinia_5 will be combined
- erinia_999 doesn't exist, so it's skipped
- Check console to verify which locations were actually used

---

## Complete Workflow Example

1. **Run:** `python main.py`
2. **Configure Data Sources** (with preview)
3. **Set Analysis Options**
4. **Combined Plot Selection:** Enter `erinia_5, erinia_15`
5. **Click "Run Analysis"**
6. **Results:** Combined plot appears automatically!

---

## Summary

✓ Specify locations to combine directly in GUI
✓ No more terminal prompts
✓ Settings automatically saved
✓ Completely integrated workflow

