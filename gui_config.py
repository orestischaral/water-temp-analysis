"""
GUI Configuration Tool for Temperature Analysis
Allows users to load Excel files and configure data sources interactively
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import json
import os
from pathlib import Path


class DataSourceRow:
    """Represents one data source configuration in the GUI"""
    def __init__(self, parent_frame, row_num, on_remove=None):
        self.row_num = row_num
        self.on_remove = on_remove
        self.frame = ttk.LabelFrame(parent_frame, text=f"Data Source #{row_num + 1}", padding="10")
        self.frame.pack(fill=tk.X, pady=10, padx=5)

        # Row 1: File selection
        row1_frame = ttk.Frame(self.frame)
        row1_frame.pack(fill=tk.X, pady=5)

        ttk.Label(row1_frame, text="File:").pack(side=tk.LEFT, padx=5)
        self.file_var = tk.StringVar()
        ttk.Entry(row1_frame, textvariable=self.file_var, width=40).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Button(row1_frame, text="Browse", command=self.browse_file, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Preview", command=self.preview_file, width=10).pack(side=tk.LEFT, padx=5)
        ttk.Button(row1_frame, text="Remove", command=self.remove, width=10).pack(side=tk.LEFT, padx=5)

        # Row 2: Location and Sheet
        row2_frame = ttk.Frame(self.frame)
        row2_frame.pack(fill=tk.X, pady=5)

        ttk.Label(row2_frame, text="Location:").pack(side=tk.LEFT, padx=5)
        self.location_var = tk.StringVar()
        ttk.Entry(row2_frame, textvariable=self.location_var, width=20).pack(side=tk.LEFT, padx=5)

        ttk.Label(row2_frame, text="Sheet:").pack(side=tk.LEFT, padx=5)
        self.sheet_var = tk.StringVar(value="Data")
        ttk.Entry(row2_frame, textvariable=self.sheet_var, width=15).pack(side=tk.LEFT, padx=5)

        # Row 3: Column selections
        row3_frame = ttk.Frame(self.frame)
        row3_frame.pack(fill=tk.X, pady=5)

        ttk.Label(row3_frame, text="DateTime Col:").pack(side=tk.LEFT, padx=5)
        self.dt_col_var = tk.StringVar(value="0")
        dt_spin = ttk.Spinbox(row3_frame, from_=0, to=20, textvariable=self.dt_col_var, width=5)
        dt_spin.pack(side=tk.LEFT, padx=5)

        ttk.Label(row3_frame, text="Temp Col:").pack(side=tk.LEFT, padx=5)
        self.temp_col_var = tk.StringVar(value="1")
        temp_spin = ttk.Spinbox(row3_frame, from_=0, to=20, textvariable=self.temp_col_var, width=5)
        temp_spin.pack(side=tk.LEFT, padx=5)

        ttk.Label(row3_frame, text="Lux Col (opt):").pack(side=tk.LEFT, padx=5)
        self.lux_col_var = tk.StringVar(value="-1")
        lux_spin = ttk.Spinbox(row3_frame, from_=-1, to=20, textvariable=self.lux_col_var, width=5)
        lux_spin.pack(side=tk.LEFT, padx=5)

    def browse_file(self):
        """Open file browser to select Excel file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filename:
            self.file_var.set(filename)
            # Auto-update location from filename
            name = Path(filename).stem
            self.location_var.set(name)

    def preview_file(self):
        """Show preview of Excel file contents"""
        file_path = self.file_var.get()
        if not file_path or not os.path.exists(file_path):
            messagebox.showerror("Error", "Please select a valid file")
            return

        try:
            sheet = self.sheet_var.get()
            df = pd.read_excel(file_path, sheet_name=sheet)

            # Show first few rows in a preview window
            preview_window = tk.Toplevel()
            preview_window.title(f"Preview: {Path(file_path).name}")
            preview_window.geometry("800x400")

            # Create text widget with scrollbar
            text_frame = ttk.Frame(preview_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            scrollbar = ttk.Scrollbar(text_frame)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            text_widget = tk.Text(text_frame, yscrollcommand=scrollbar.set, wrap=tk.NONE)
            text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.config(command=text_widget.yview)

            # Display column names and first rows
            text_widget.insert(tk.END, "Column indices and names:\n")
            for idx, col in enumerate(df.columns):
                text_widget.insert(tk.END, f"  [{idx}] {col}\n")

            text_widget.insert(tk.END, f"\nFirst 5 rows (out of {len(df)} total):\n")
            text_widget.insert(tk.END, df.head().to_string())

            text_widget.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Error", f"Could not preview file: {str(e)}")

    def remove(self):
        """Remove this data source row"""
        self.frame.destroy()
        if self.on_remove:
            self.on_remove()

    def get_config(self):
        """Return configuration as dictionary"""
        file_path = self.file_var.get()
        if not file_path:
            return None

        lux_col = int(self.lux_col_var.get())

        config = {
            "location": self.location_var.get(),
            "series": "A",
            "excel_file": file_path,
            "sheet_name": self.sheet_var.get(),
            "dt_col": int(self.dt_col_var.get()),
            "temp_col": int(self.temp_col_var.get()),
        }

        if lux_col >= 0:
            config["lux_col"] = lux_col

        return config


class ConfigurationGUI:
    """Main GUI window for configuring data sources"""

    def __init__(self, root):
        self.root = root
        self.root.title("Temperature Analysis - Data Configuration")
        self.root.geometry("900x700")

        self.data_sources = []
        self.config_file = "data_sources_config.json"

        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Data Source Configuration",
                                font=("Arial", 14, "bold"))
        title_label.pack(pady=10)

        # Instructions
        instructions = ttk.Label(main_frame,
            text="Add Excel files containing temperature data. Specify location, sheet name, and column indices.",
            wraplength=850)
        instructions.pack(pady=5)

        # Scrollable frame for data sources
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True, pady=10)

        canvas = tk.Canvas(canvas_frame, height=400)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Button frame (outside scrollable area, so it's always visible)
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame, text="+ Add Data Source", command=self.add_source).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Load Config", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Config", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear All", command=self.clear_all).pack(side=tk.LEFT, padx=5)

        # Ship data frame (inside scrollable area)
        ship_frame = ttk.LabelFrame(self.scrollable_frame, text="Ship Schedule Data (Optional)", padding="10")
        ship_frame.pack(fill=tk.X, pady=10)

        self.ship_file_var = tk.StringVar()
        ttk.Entry(ship_frame, textvariable=self.ship_file_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(ship_frame, text="Browse", command=self.browse_ship_file).pack(side=tk.LEFT, padx=5)

        self.ship_sheet_var = tk.StringVar(value="schedule")
        ttk.Label(ship_frame, text="Sheet:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(ship_frame, textvariable=self.ship_sheet_var, width=15).pack(side=tk.LEFT, padx=5)

        # Analysis options frame (inside scrollable area)
        options_frame = ttk.LabelFrame(self.scrollable_frame, text="Analysis Options", padding="10")
        options_frame.pack(fill=tk.X, pady=10)

        self.filter_var = tk.StringVar(value="both")
        ttk.Label(options_frame, text="Fourier Filtering:").pack(side=tk.LEFT, padx=5)
        filter_combo = ttk.Combobox(options_frame, textvariable=self.filter_var,
                                     values=["none", "diurnal", "seasonal", "both"],
                                     state="readonly", width=15)
        filter_combo.pack(side=tk.LEFT, padx=5)

        self.overlay_var = tk.StringVar(value="ships")
        ttk.Label(options_frame, text="Overlay:").pack(side=tk.LEFT, padx=5)
        overlay_combo = ttk.Combobox(options_frame, textvariable=self.overlay_var,
                                     values=["ships", "lux", "none"],
                                     state="readonly", width=15)
        overlay_combo.pack(side=tk.LEFT, padx=5)

        # Checkboxes for analysis options
        self.show_fft_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(options_frame, text="Show FFT Components", variable=self.show_fft_var).pack(side=tk.LEFT, padx=5)

        self.show_acf_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Show ACF Analysis", variable=self.show_acf_var).pack(side=tk.LEFT, padx=5)

        self.show_power_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(options_frame, text="Show Power Spectrum", variable=self.show_power_var).pack(side=tk.LEFT, padx=5)

        # Combined plot selection frame (inside scrollable area)
        combined_frame = ttk.LabelFrame(self.scrollable_frame, text="Combined Plot Selection (Optional)", padding="10")
        combined_frame.pack(fill=tk.X, pady=10)

        ttk.Label(combined_frame, text="Locations to combine in one plot:").pack(side=tk.LEFT, padx=5)
        self.combined_var = tk.StringVar(value="")
        ttk.Entry(combined_frame, textvariable=self.combined_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(combined_frame, text="(comma-separated, or leave empty to skip)").pack(side=tk.LEFT, padx=5)

        # Thermal stratification analysis frame (inside scrollable area)
        strat_frame = ttk.LabelFrame(self.scrollable_frame, text="Thermal Stratification Analysis (Optional)", padding="10")
        strat_frame.pack(fill=tk.X, pady=10)

        ttk.Label(strat_frame, text="Location pairs to analyze:").pack(side=tk.LEFT, padx=5)
        self.thermal_strat_var = tk.StringVar(value="")
        ttk.Entry(strat_frame, textvariable=self.thermal_strat_var, width=50).pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        ttk.Label(strat_frame, text="(e.g., erinia_5-erinia_15, erinia_15-erinia_25, or leave empty to skip)").pack(side=tk.LEFT, padx=5)

        # Spike detection parameters frame (inside scrollable area)
        spike_frame = ttk.LabelFrame(self.scrollable_frame, text="Spike Detection Parameters (Advanced)", padding="10")
        spike_frame.pack(fill=tk.X, pady=10)

        # Create a grid layout for parameters
        param_inner = ttk.Frame(spike_frame)
        param_inner.pack(fill=tk.X)

        # Row 1: UP spike parameters
        ttk.Label(param_inner, text="UP Spike:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(param_inner, text="Jump Threshold:").grid(row=0, column=1, sticky="w", padx=5, pady=5)
        self.up_threshold_var = tk.StringVar(value="0.5")
        ttk.Entry(param_inner, textvariable=self.up_threshold_var, width=10).grid(row=0, column=2, padx=5, pady=5)

        ttk.Label(param_inner, text="Relax Offset:").grid(row=0, column=3, sticky="w", padx=5, pady=5)
        self.up_offset_var = tk.StringVar(value="0.2")
        ttk.Entry(param_inner, textvariable=self.up_offset_var, width=10).grid(row=0, column=4, padx=5, pady=5)

        # Row 2: DOWN spike parameters
        ttk.Label(param_inner, text="DOWN Spike:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        ttk.Label(param_inner, text="Jump Threshold:").grid(row=1, column=1, sticky="w", padx=5, pady=5)
        self.down_threshold_var = tk.StringVar(value="0.5")
        ttk.Entry(param_inner, textvariable=self.down_threshold_var, width=10).grid(row=1, column=2, padx=5, pady=5)

        ttk.Label(param_inner, text="Relax Offset:").grid(row=1, column=3, sticky="w", padx=5, pady=5)
        self.down_offset_var = tk.StringVar(value="0.2")
        ttk.Entry(param_inner, textvariable=self.down_offset_var, width=10).grid(row=1, column=4, padx=5, pady=5)

        # Start analysis button
        button_frame_bottom = ttk.Frame(main_frame)
        button_frame_bottom.pack(fill=tk.X, pady=10)

        ttk.Button(button_frame_bottom, text="Run Analysis",
                   command=self.start_analysis).pack(side=tk.RIGHT, padx=5)

        # Load previous config if exists
        if os.path.exists(self.config_file):
            self.load_config()

    def add_source(self):
        """Add a new data source row"""
        row = DataSourceRow(self.scrollable_frame, len(self.data_sources),
                           on_remove=self.update_row_positions)
        self.data_sources.append(row)

    def update_row_positions(self):
        """Update row numbers after removal"""
        # Remove destroyed frames from list (pack layout handles positioning automatically)
        self.data_sources = [s for s in self.data_sources if s.frame.winfo_exists()]
        # Update row numbers for display
        for idx, source in enumerate(self.data_sources):
            source.frame.configure(text=f"Data Source #{idx + 1}")
            source.row_num = idx

    def browse_ship_file(self):
        """Browse for ship schedule Excel file"""
        filename = filedialog.askopenfilename(
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if filename:
            self.ship_file_var.set(filename)

    def save_config(self):
        """Save current configuration to JSON file"""
        configs = []
        for source in self.data_sources:
            if source.frame.winfo_exists():
                config = source.get_config()
                if config:
                    configs.append(config)

        if not configs:
            messagebox.showwarning("Warning", "No data sources configured")
            return

        full_config = {
            "temperature_sources": configs,
            "ships_file": self.ship_file_var.get() if self.ship_file_var.get() else None,
            "ships_sheet": self.ship_sheet_var.get(),
            "filter_type": self.filter_var.get(),
            "overlay_type": self.overlay_var.get(),
            "show_fft": self.show_fft_var.get(),
            "show_acf": self.show_acf_var.get(),
            "show_power_spectrum": self.show_power_var.get(),
        }

        try:
            with open(self.config_file, 'w') as f:
                json.dump(full_config, f, indent=2)
            messagebox.showinfo("Success", f"Configuration saved to {self.config_file}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save config: {str(e)}")

    def load_config(self):
        """Load configuration from JSON file"""
        if not os.path.exists(self.config_file):
            return

        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)

            # Clear existing sources
            for source in self.data_sources:
                if source.frame.winfo_exists():
                    source.frame.destroy()
            self.data_sources = []

            # Load temperature sources
            for src_config in config.get("temperature_sources", []):
                row = DataSourceRow(self.scrollable_frame, len(self.data_sources),
                                   on_remove=self.update_row_positions)
                row.file_var.set(src_config.get("excel_file", ""))
                row.location_var.set(src_config.get("location", ""))
                row.sheet_var.set(src_config.get("sheet_name", "Data"))
                row.dt_col_var.set(str(src_config.get("dt_col", 0)))
                row.temp_col_var.set(str(src_config.get("temp_col", 1)))
                row.lux_col_var.set(str(src_config.get("lux_col", -1)))
                self.data_sources.append(row)

            # Load ship data (handle None and string "None")
            ships_file = config.get("ships_file", "")
            if ships_file is None or ships_file == "None":
                ships_file = ""
            self.ship_file_var.set(ships_file)
            self.ship_sheet_var.set(config.get("ships_sheet", "schedule"))

            # Load analysis options
            self.filter_var.set(config.get("filter_type", "both"))
            self.overlay_var.set(config.get("overlay_type", "ships"))
            self.show_fft_var.set(config.get("show_fft", True))
            self.show_acf_var.set(config.get("show_acf", False))
            self.show_power_var.set(config.get("show_power_spectrum", False))

            # Load combined locations
            combined_locs = config.get("combined_locations", [])
            if isinstance(combined_locs, list):
                self.combined_var.set(", ".join(combined_locs))
            else:
                self.combined_var.set("")

            # Load thermal stratification pairs
            thermal_pairs = config.get("thermal_stratification_pairs", [])
            if isinstance(thermal_pairs, list) and thermal_pairs:
                # Convert list of tuples/lists to formatted string
                pair_strs = [f"{pair[0]}-{pair[1]}" for pair in thermal_pairs if isinstance(pair, (list, tuple)) and len(pair) == 2]
                self.thermal_strat_var.set(", ".join(pair_strs))
            else:
                self.thermal_strat_var.set("")

            # Load spike detection parameters
            self.up_threshold_var.set(str(config.get("up_jump_threshold", 0.5)))
            self.up_offset_var.set(str(config.get("up_relax_offset", 0.2)))
            self.down_threshold_var.set(str(config.get("down_jump_threshold", 0.5)))
            self.down_offset_var.set(str(config.get("down_relax_offset", 0.2)))

        except Exception as e:
            messagebox.showerror("Error", f"Could not load config: {str(e)}")

    def clear_all(self):
        """Clear all configured data sources"""
        if messagebox.askyesno("Confirm", "Clear all data sources?"):
            for source in self.data_sources:
                if source.frame.winfo_exists():
                    source.frame.destroy()
            self.data_sources = []

    def start_analysis(self):
        """Run analysis with current configuration"""
        configs = []
        for source in self.data_sources:
            if source.frame.winfo_exists():
                config = source.get_config()
                if config:
                    configs.append(config)

        if not configs:
            messagebox.showerror("Error", "Please add at least one data source")
            return

        # Save configuration
        self.save_config()

        # Save analysis options to prevent interactive prompts
        # Parse combined locations: split by comma and strip whitespace
        combined_locs = self.combined_var.get().strip()
        if combined_locs:
            combined_list = [loc.strip() for loc in combined_locs.split(",") if loc.strip()]
        else:
            combined_list = []

        # Parse thermal stratification pairs: split by comma and parse loc1-loc2 format
        thermal_strat = self.thermal_strat_var.get().strip()
        thermal_pairs = []
        if thermal_strat:
            for pair_str in thermal_strat.split(","):
                pair_str = pair_str.strip()
                if pair_str and "-" in pair_str:
                    parts = [p.strip() for p in pair_str.split("-")]
                    if len(parts) == 2:
                        thermal_pairs.append((parts[0], parts[1]))

        # Parse spike detection parameters
        try:
            up_threshold = float(self.up_threshold_var.get())
            up_offset = float(self.up_offset_var.get())
            down_threshold = float(self.down_threshold_var.get())
            down_offset = float(self.down_offset_var.get())
        except ValueError:
            messagebox.showerror("Error", "Spike parameters must be valid numbers")
            return

        analysis_config = {
            "filter_type": self.filter_var.get(),
            "overlay_type": self.overlay_var.get(),
            "show_fft": self.show_fft_var.get(),
            "show_acf": self.show_acf_var.get(),
            "show_power_spectrum": self.show_power_var.get(),
            "combined_locations": combined_list,
            "thermal_stratification_pairs": thermal_pairs,
            "up_jump_threshold": up_threshold,
            "up_relax_offset": up_offset,
            "down_jump_threshold": down_threshold,
            "down_relax_offset": down_offset,
        }

        try:
            with open("analysis_config.json", 'w') as f:
                json.dump(analysis_config, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save analysis config: {str(e)}")
            return

        # Show message that analysis is starting
        print("\n" + "="*70)
        print("STARTING ANALYSIS")
        print("="*70)

        messagebox.showinfo("Analysis Started",
            "Analysis is starting. Check the console for progress.\n\n"
            "Plots will appear in separate windows.\n\n"
            "This window will close now.")

        # Close the GUI window to avoid threading conflicts with matplotlib
        # This prevents the fatal Python error when matplotlib tries to draw
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass  # Window might already be closing

        # Import and run the main analysis function
        try:
            from main import main as run_analysis
            # Run analysis directly (no thread needed after GUI closes)
            run_analysis()
        except Exception as e:
            print(f"Error during analysis: {e}")
            import traceback
            traceback.print_exc()


def main():
    root = tk.Tk()
    app = ConfigurationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()