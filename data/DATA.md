# Data Files

This folder contains Excel files with temperature data.

## File Naming Convention

Use descriptive names following the pattern:
```
location_depth.xlsx
location_depth_version.xlsx
```

### Examples
- `erinia_5_a.xlsx` - Erinia station, 5m depth, version A
- `erinia_15_b.xlsx` - Erinia station, 15m depth, version B
- `apothikes_25.xlsx` - Apothikes station, 25m depth

## File Structure

Each Excel file should contain:

| Column | Name | Format | Example |
|--------|------|--------|---------|
| 0 | DateTime | ISO 8601 / Excel Date | 2025-05-04 11:28:34 |
| 1 | Temperature | Numeric (°C) | 15.23 |
| 2+ | Optional (Lux, etc.) | Numeric | 450 |

### Sheet Name
Default: `Data` (configurable in GUI)

## Configuration in GUI

When adding a data source in the GUI:

1. **Browse** to file in this `data/` folder
2. **Location** auto-fills from filename (edit if needed)
3. **Sheet** defaults to "Data"
4. **DateTime Col**: 0 (first column)
5. **Temperature Col**: 1 (second column)
6. **Lux Col**: 2 or -1 to skip

## Notes

- Excel files are **NOT committed to Git** (see `.gitignore`)
- Keep data files organized in this folder
- Use consistent naming for easy identification
- Ensure timestamps don't have timezone issues
- Temperature values should be numeric (no text)

## Supported Formats

- `.xlsx` - Excel 2007+ (recommended)
- `.xls` - Excel 97-2003
- Both are supported automatically