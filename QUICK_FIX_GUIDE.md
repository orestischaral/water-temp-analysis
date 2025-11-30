# Quick Fix Guide - Column Index Issue

**What Happened:**
Your analysis failed because column indices don't match your actual Excel files.

**The Error:**
```
TypeError: Cannot cast DatetimeArray to dtype float64
```

This means the Temperature column contains dates, not numbers!

---

## Quick Fix (5 minutes)

### Step 1: Run the GUI
```bash
python main.py
```
The GUI window will open.

### Step 2: Fix Each Data Source
For each of your data sources (erinia_5, erinia_15, etc.):

1. Find the data source in the list
2. **Click the "Preview" button**
3. A new window shows your actual data:
   ```
   Column indices and names:
   [0] DateTime
   [1] Temperature (or similar)
   [2] ... other columns ...
   ```
4. **Update the column numbers based on Preview:**
   - If Temperature is at column [2], set Temp Col: 2
   - If DateTime is at column [0], set DateTime Col: 0

### Step 3: Save and Run
1. Click "Save Config" (saves your settings)
2. Click "Run Analysis"
3. **NO PROMPTS** - analysis runs automatically!

---

## Example: What to Look For

### In Preview Window
You'll see something like:
```
[0] Date
[1] Time
[2] Temperature
[3] Humidity
```

### Then Set:
- DateTime Col: 0  (or 1 if combined column)
- Temp Col: 2     (where the temperature actually is)
- Lux Col: -1     (if not available)

---

## Common Issues

### "Column not found"
- The column index is too high
- Use Preview button to see real column count

### "All values are dates"
- You've selected the wrong column for temperature
- Temperature column usually contains numbers like 25.3, 26.1, etc.
- Use Preview to verify

### "It says NaN or text in column"
- That column doesn't have numeric temperature data
- Try a different column
- Use Preview to see the data

---

## Files That Were Fixed

1. **main.py** - No more terminal prompts during GUI analysis
2. **gui_config.py** - Proper GUI/analysis integration
3. All interactive prompts now controlled by use_interactive flag

---

## Next Steps

1. **Don't run main.py yet** - fix columns first!
2. **Use the Preview button** - very important!
3. **Verify column indices** - this is the issue
4. **Click "Run Analysis"** - it will work!

---

## Still Having Issues?

Check the detailed documentation:
- **BUG_FIXES.md** - What was fixed and why
- **README_GUI.md** - Detailed GUI guide
- **QUICKSTART.md** - Step-by-step walkthrough

