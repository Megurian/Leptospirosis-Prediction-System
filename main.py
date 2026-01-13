import sqlite3
import numpy as np
from scipy.integrate import odeint
import csv
from tkinter import filedialog
import matplotlib
matplotlib.use('TkAgg')  # Ensure correct backend for Tkinter
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from sklearn.linear_model import LinearRegression
import tkinter as tk
from tkinter import ttk, messagebox
import sys
import os
from demo_manager import DemoManager

# Get the directory where the script/exe is located
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    APP_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    APP_DIR = os.path.dirname(os.path.abspath(__file__))

# --- DATABASE HANDLER ---
class Database:
    def __init__(self, db_name="leptospirosis_sim.db"):
        # Use app directory for database to ensure portability
        db_path = os.path.join(APP_DIR, db_name)
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.create_tables()
    
    def close(self):
        """Close database connection properly"""
        if self.conn:
            self.conn.close()

    def create_tables(self):
        # Table for Barangay Profiles
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS barangays (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE,
                population INTEGER
            )
        """)
        # Table for Annual Data (History)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS yearly_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                barangay_id INTEGER,
                year INTEGER,
                population INTEGER,
                total_cases INTEGER,
                flood_severity REAL,
                is_flooded INTEGER DEFAULT 0,
                is_evacuation INTEGER DEFAULT 0,
                is_infrastructure_damage INTEGER DEFAULT 0,
                irregular_garbage INTEGER DEFAULT 0,
                high_rodents INTEGER DEFAULT 0,
                clogged_drainage INTEGER DEFAULT 0,
                FOREIGN KEY(barangay_id) REFERENCES barangays(id),
                UNIQUE(barangay_id, year)
            )
        """)
        self.conn.commit()
        
        # Migration: Add population column if it doesn't exist
        try:
            self.cursor.execute("SELECT population FROM yearly_data LIMIT 1")
        except sqlite3.OperationalError:
            # Column doesn't exist, add it
            self.cursor.execute("ALTER TABLE yearly_data ADD COLUMN population INTEGER")
            # Update existing records with barangay's default population
            self.cursor.execute("""
                UPDATE yearly_data 
                SET population = (
                    SELECT population 
                    FROM barangays 
                    WHERE barangays.id = yearly_data.barangay_id
                )
                WHERE population IS NULL
            """)
            self.conn.commit()
        
        # Migration: Add individual risk factor columns if they don't exist
        risk_columns = [
            'is_flooded', 'is_evacuation', 'is_infrastructure_damage',
            'irregular_garbage', 'high_rodents', 'clogged_drainage'
        ]
        for col in risk_columns:
            try:
                self.cursor.execute(f"SELECT {col} FROM yearly_data LIMIT 1")
            except sqlite3.OperationalError:
                self.cursor.execute(f"ALTER TABLE yearly_data ADD COLUMN {col} INTEGER DEFAULT 0")
        self.conn.commit()

    def add_barangay(self, name, population):
        try:
            self.cursor.execute("INSERT INTO barangays (name, population) VALUES (?, ?)", (name, population))
            self.conn.commit()
            return True, f"Success: {name} added."
        except sqlite3.IntegrityError:
            return False, f"Error: {name} already exists."

    def update_barangay(self, old_name, new_name, population):
        try:
            self.cursor.execute("UPDATE barangays SET name=?, population=? WHERE name=?", 
                              (new_name, population, old_name))
            self.conn.commit()
            return True, f"Success: {old_name} updated."
        except Exception as e:
            return False, f"Error: {e}"

    def add_year_data(self, b_name, year, population, cases, flood_severity, 
                     is_flooded=0, is_evac=0, is_damage=0, 
                     irregular_garbage=0, high_rodents=0, clogged_drainage=0):
        self.cursor.execute("SELECT id FROM barangays WHERE name=?", (b_name,))
        result = self.cursor.fetchone()
        if not result:
            return False, "Barangay not found!"
        b_id = result[0]
        
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO yearly_data 
                (barangay_id, year, population, total_cases, flood_severity,
                 is_flooded, is_evacuation, is_infrastructure_damage,
                 irregular_garbage, high_rodents, clogged_drainage)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (b_id, year, population, cases, flood_severity,
                  is_flooded, is_evac, is_damage, 
                  irregular_garbage, high_rodents, clogged_drainage))
            self.conn.commit()
            return True, f"Data for {b_name} ({year}) saved."
        except Exception as e:
            return False, f"Error: {e}"

    def get_barangays(self):
        self.cursor.execute("SELECT id, name, population FROM barangays")
        return self.cursor.fetchall()

    def get_yearly_data(self, b_name=None):
        if b_name:
            self.cursor.execute("""
                SELECT b.name, y.year, y.population, y.total_cases, y.flood_severity,
                       y.is_flooded, y.is_evacuation, y.is_infrastructure_damage,
                       y.irregular_garbage, y.high_rodents, y.clogged_drainage
                FROM yearly_data y
                JOIN barangays b ON y.barangay_id = b.id
                WHERE b.name = ?
                ORDER BY y.year DESC
            """, (b_name,))
        else:
            self.cursor.execute("""
                SELECT b.name, y.year, y.population, y.total_cases, y.flood_severity,
                       y.is_flooded, y.is_evacuation, y.is_infrastructure_damage,
                       y.irregular_garbage, y.high_rodents, y.clogged_drainage
                FROM yearly_data y
                JOIN barangays b ON y.barangay_id = b.id
                ORDER BY b.name, y.year DESC
            """)
        return self.cursor.fetchall()

    def get_barangay_history(self, name):
        """Get historical data for trend prediction"""
        self.cursor.execute("""
            SELECT y.year, y.population, y.flood_severity, y.total_cases
            FROM yearly_data y
            JOIN barangays b ON y.barangay_id = b.id
            WHERE b.name = ?
            ORDER BY y.year ASC
        """, (name,))
        return self.cursor.fetchall()

    def get_data_for_sim(self, b_name, year):
        self.cursor.execute("""
            SELECT b.population, y.total_cases, y.flood_severity
            FROM yearly_data y
            JOIN barangays b ON y.barangay_id = b.id
            WHERE b.name = ? AND y.year = ?
        """, (b_name, year))
        return self.cursor.fetchone()
    
    def delete_yearly_data(self, b_name, year):
        """Delete a specific year's data for a barangay"""
        try:
            self.cursor.execute("""
                DELETE FROM yearly_data 
                WHERE barangay_id = (SELECT id FROM barangays WHERE name = ?) 
                AND year = ?
            """, (b_name, year))
            self.conn.commit()
            return True, f"Data for {b_name} ({year}) deleted."
        except Exception as e:
            return False, f"Error: {e}"
    
    def delete_barangay(self, b_name):
        """Delete a barangay and all its data"""
        try:
            self.cursor.execute("SELECT id FROM barangays WHERE name=?", (b_name,))
            result = self.cursor.fetchone()
            if not result:
                return False, "Barangay not found!"
            
            b_id = result[0]
            # Delete all yearly data first
            self.cursor.execute("DELETE FROM yearly_data WHERE barangay_id=?", (b_id,))
            # Then delete the barangay
            self.cursor.execute("DELETE FROM barangays WHERE id=?", (b_id,))
            self.conn.commit()
            return True, f"Barangay {b_name} and all its data deleted."
        except Exception as e:
            return False, f"Error: {e}"

# --- THE MATH (SEIWR) ---
def seiwr_ode(y, t, Lambda, i_coef, sigma, xi, delta):
    S, E, I, W = y
    dSdt = Lambda - (i_coef * S * I) - (W * S)
    dEdt = (i_coef * S * I) + (W * S) - (sigma * E)
    dIdt = sigma * E  # Cumulative Risk
    dWdt = (xi * I) - (delta * W)
    return [dSdt, dEdt, dIdt, dWdt]

# --- PREDICTION ENGINE ---
def predict_next_year(history, future_pop, future_composite_risk):
    """
    Uses Linear Regression to find the relationship between composite risk and cases.
    Falls back to ratio-based estimation when historical data lacks variance.
    
    Key insight: We need variance in X (composite risk) for regression to learn a slope.
    If all historical risks are the same, we use a proportional scaling approach instead.
    """
    if len(history) < 2:
        return None, "Need at least 2 years of data to predict."

    years = [r[0] for r in history]
    pops = np.array([r[1] for r in history])
    composite_risks = np.array([r[2] for r in history])
    cases = np.array([r[3] for r in history])

    # Calculate incidence rate (cases per 100,000 population)
    incidence_rates = (cases / pops) * 100000
    
    # Check if there's variance in composite risks - Linear Regression needs this!
    risk_variance = np.var(composite_risks)
    avg_historical_risk = np.mean(composite_risks)
    avg_historical_rate = np.mean(incidence_rates)
    
    # Create model object to store metadata
    model = LinearRegression(fit_intercept=True)
    
    if risk_variance < 0.01 or avg_historical_risk == 0:
        # FALLBACK: No variance in historical risks, can't use regression slope
        # Use proportional scaling based on average data
        
        if avg_historical_risk > 0:
            # Calculate rate per unit of composite risk
            # This is the "cases per 100k per unit risk"
            rate_per_risk_unit = avg_historical_rate / avg_historical_risk
            
            # Baseline rate (endemic level when no floods/risk factors)
            # Assume 10% of observed rate is baseline endemic transmission
            baseline_rate = avg_historical_rate * 0.1
            
            # Prediction: baseline + (risk contribution)
            predicted_rate = baseline_rate + (rate_per_risk_unit * future_composite_risk)
            
            # Store the calculated sensitivity for recommendations
            model.coef_ = np.array([rate_per_risk_unit])
            model.intercept_ = baseline_rate
        else:
            # No risk in history either - use pure baseline
            baseline_rate = max(1.0, min(incidence_rates) * 0.5) if len(incidence_rates) > 0 else 1.0
            predicted_rate = baseline_rate + (future_composite_risk * 2.0)  # Assume 2 cases/100k per risk unit
            model.coef_ = np.array([2.0])
            model.intercept_ = baseline_rate
    else:
        # NORMAL CASE: Sufficient variance, use Linear Regression
        X = composite_risks.reshape(-1, 1)
        y = incidence_rates
        
        model.fit(X, y)
        
        # Predict using the trained model
        predicted_rate = model.predict([[future_composite_risk]])[0]
        
        # Ensure positive relationship: if coefficient is negative (unlikely in reality),
        # fall back to proportional method
        if model.coef_[0] < 0:
            rate_per_risk_unit = avg_historical_rate / max(avg_historical_risk, 1)
            baseline_rate = avg_historical_rate * 0.1
            predicted_rate = baseline_rate + (rate_per_risk_unit * future_composite_risk)
            model.coef_ = np.array([rate_per_risk_unit])
            model.intercept_ = baseline_rate
    
    # If composite risk is 0, use minimal baseline (endemic level)
    if future_composite_risk == 0:
        baseline_rate = max(0.5, avg_historical_rate * 0.1)
        predicted_rate = baseline_rate
    
    # Convert rate back to actual cases
    predicted_cases = (predicted_rate / 100000) * future_pop
    
    # Validation: Cases can't be negative
    predicted_cases = max(0, predicted_cases)
    
    # Store metadata for sensitivity analysis
    model.predicted_rate = predicted_rate
    model.incidence_rates = incidence_rates
    model.avg_historical_risk = avg_historical_risk
    model.risk_variance = risk_variance
    
    return predicted_cases, model

# --- TKINTER GUI APPLICATION ---
class LeptospirosisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Leptospirosis Risk Prediction System")
        self.root.geometry("1000x700")
        
        # Initialize Demo Manager
        self.demo_manager = DemoManager(APP_DIR)
        
        # Check demo status
        if not self.demo_manager.initialize_demo():
            # Demo expired - show lock screen
            self.show_demo_expired_screen()
            return
        
        self.db = Database()
        
        # Edit mode tracking
        self.edit_mode = False
        self.edit_data = None
        
        # Create demo indicator frame at the top
        self.create_demo_indicator()
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        # Create tabs
        self.create_barangay_tab()
        self.create_yearly_data_tab()
        self.create_import_csv_tab()
        self.create_simulation_tab()
        self.create_prediction_tab()
        self.create_view_data_tab()
    
    def create_demo_indicator(self):
        """Create a demo indicator banner at the top of the window"""
        demo_frame = tk.Frame(self.root, bg='#FF6B6B', height=30)
        demo_frame.pack(fill='x', side='top', padx=10, pady=(10, 5))
        demo_frame.pack_propagate(False)
        
        demo_info = self.demo_manager.get_demo_info()
        remaining_text = f"{demo_info['remaining_hours']}h {demo_info['remaining_minutes']}m remaining"
        
        label = tk.Label(
            demo_frame,
            text=f"⚠ DEMO VERSION - {remaining_text}",
            bg='#FF6B6B',
            fg='white',
            font=('Arial', 10, 'bold')
        )
        label.pack(expand=True)
    
    def show_demo_expired_screen(self):
        """Show demo expired lock screen"""
        # Clear the window
        for widget in self.root.winfo_children():
            widget.destroy()
        
        # Set window size
        self.root.geometry("600x400")
        
        # Create lock screen
        lock_frame = tk.Frame(self.root, bg='#2C3E50')
        lock_frame.pack(fill='both', expand=True)
        
        # Lock icon (using emoji)
        icon_label = tk.Label(
            lock_frame,
            text="🔒",
            font=('Arial', 72),
            bg='#2C3E50',
            fg='white'
        )
        icon_label.pack(pady=40)
        
        # Message
        message_label = tk.Label(
            lock_frame,
            text="Demo Period Ended",
            font=('Arial', 24, 'bold'),
            bg='#2C3E50',
            fg='white'
        )
        message_label.pack(pady=10)
        
        # Contact message
        contact_label = tk.Label(
            lock_frame,
            text="Please contact the developer to continue using this application.",
            font=('Arial', 12),
            bg='#2C3E50',
            fg='#BDC3C7',
            wraplength=400
        )
        contact_label.pack(pady=20)
        
        # Close button
        close_btn = tk.Button(
            lock_frame,
            text="Close",
            command=self.root.destroy,
            font=('Arial', 12),
            bg='#E74C3C',
            fg='white',
            padx=30,
            pady=10,
            relief='flat',
            cursor='hand2'
        )
        close_btn.pack(pady=20)

        
    def create_barangay_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Barangay Management")
        
        # Frame for input
        input_frame = ttk.LabelFrame(tab, text="Add/Update Barangay", padding=20)
        input_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Label(input_frame, text="Barangay Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.brgy_name_entry = ttk.Entry(input_frame, width=30)
        self.brgy_name_entry.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(input_frame, text="Initial Population:").grid(row=1, column=0, sticky='w', pady=5)
        self.brgy_pop_entry = ttk.Entry(input_frame, width=30)
        self.brgy_pop_entry.grid(row=1, column=1, pady=5, padx=10)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(btn_frame, text="Add Barangay", command=self.add_barangay).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_barangay_form).pack(side='left', padx=5)
        
        # List of barangays
        list_frame = ttk.LabelFrame(tab, text="Existing Barangays", padding=20)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Treeview
        columns = ('ID', 'Name', 'Initial Population')
        self.brgy_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.brgy_tree.heading(col, text=col)
            self.brgy_tree.column(col, width=150)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.brgy_tree.yview)
        self.brgy_tree.configure(yscrollcommand=scrollbar.set)
        
        self.brgy_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        ttk.Button(list_frame, text="Refresh List", command=self.refresh_barangay_list).pack(pady=10)
        
        self.refresh_barangay_list()
    
    def create_yearly_data_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Yearly Data Entry")
        
        input_frame = ttk.LabelFrame(tab, text="Add/Update Yearly Data", padding=20)
        input_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Label(input_frame, text="Barangay:").grid(row=0, column=0, sticky='w', pady=5)
        self.year_brgy_combo = ttk.Combobox(input_frame, width=28, state='readonly')
        self.year_brgy_combo.grid(row=0, column=1, pady=5, padx=10)
        self.refresh_barangay_combo()
        
        ttk.Label(input_frame, text="Year:").grid(row=1, column=0, sticky='w', pady=5)
        self.year_entry = ttk.Entry(input_frame, width=30)
        self.year_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(input_frame, text="Population (for this year):").grid(row=2, column=0, sticky='w', pady=5)
        self.year_pop_entry = ttk.Entry(input_frame, width=30)
        self.year_pop_entry.grid(row=2, column=1, pady=5, padx=10)
        
        ttk.Label(input_frame, text="Total Leptospirosis Cases:").grid(row=3, column=0, sticky='w', pady=5)
        self.cases_entry = ttk.Entry(input_frame, width=30)
        self.cases_entry.grid(row=3, column=1, pady=5, padx=10)
        
        # Risk Factor Calculator (Flood + Vector/Sanitation)
        risk_frame = ttk.LabelFrame(input_frame, text="Risk Factor Assessment", padding=10)
        risk_frame.grid(row=4, column=0, columnspan=2, pady=10, sticky='ew')
        
        # Flood Risk Factors
        flood_subframe = ttk.LabelFrame(risk_frame, text="Flood Factors", padding=5)
        flood_subframe.grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        
        self.is_flooded_var = tk.BooleanVar()
        self.is_evac_var = tk.BooleanVar()
        self.is_damaged_var = tk.BooleanVar()
        
        ttk.Checkbutton(flood_subframe, text="Flooded area? (+2.0)", 
                       variable=self.is_flooded_var, command=self.update_composite_risk).grid(row=0, column=0, sticky='w', pady=2)
        ttk.Checkbutton(flood_subframe, text="Evacuation needed? (+3.0)", 
                       variable=self.is_evac_var, command=self.update_composite_risk).grid(row=1, column=0, sticky='w', pady=2)
        ttk.Checkbutton(flood_subframe, text="Infrastructure/Agri damage? (+5.0)", 
                       variable=self.is_damaged_var, command=self.update_composite_risk).grid(row=2, column=0, sticky='w', pady=2)
        
        # Vector/Sanitation Risk Factors
        vector_subframe = ttk.LabelFrame(risk_frame, text="Vector / Sanitation Factors", padding=5)
        vector_subframe.grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        
        self.irregular_garbage_var = tk.BooleanVar()
        self.high_rodents_var = tk.BooleanVar()
        self.clogged_drainage_var = tk.BooleanVar()
        
        ttk.Checkbutton(vector_subframe, text="Irregular Garbage Collection? (+0.5x)", 
                       variable=self.irregular_garbage_var, command=self.update_composite_risk).grid(row=0, column=0, sticky='w', pady=2)
        ttk.Checkbutton(vector_subframe, text="High presence of Strays/Rodents? (+0.5x)", 
                       variable=self.high_rodents_var, command=self.update_composite_risk).grid(row=1, column=0, sticky='w', pady=2)
        ttk.Checkbutton(vector_subframe, text="Clogged/Open Drainage? (+0.5x)", 
                       variable=self.clogged_drainage_var, command=self.update_composite_risk).grid(row=2, column=0, sticky='w', pady=2)
        
        # Results display
        results_subframe = ttk.Frame(risk_frame)
        results_subframe.grid(row=1, column=0, columnspan=2, pady=10)
        
        ttk.Label(results_subframe, text="Flood Score:").grid(row=0, column=0, sticky='e', padx=5)
        self.flood_score_label = ttk.Label(results_subframe, text="0.0", font=('Arial', 9))
        self.flood_score_label.grid(row=0, column=1, sticky='w', padx=5)
        
        ttk.Label(results_subframe, text="Vector Multiplier:").grid(row=0, column=2, sticky='e', padx=5)
        self.vector_score_label = ttk.Label(results_subframe, text="1.0x", font=('Arial', 9))
        self.vector_score_label.grid(row=0, column=3, sticky='w', padx=5)
        
        ttk.Label(results_subframe, text="Composite Risk Index:").grid(row=1, column=0, columnspan=2, sticky='e', padx=5, pady=5)
        self.composite_risk_label = ttk.Label(results_subframe, text="0.0", font=('Arial', 11, 'bold'), foreground='red')
        self.composite_risk_label.grid(row=1, column=2, columnspan=2, sticky='w', padx=5, pady=5)
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        
        self.save_data_btn = ttk.Button(btn_frame, text="Save Data", command=self.add_yearly_data)
        self.save_data_btn.pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_yearly_form).pack(side='left', padx=5)
    
    def create_import_csv_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Import CSV Data")
        
        # Instructions Frame
        instructions_frame = ttk.LabelFrame(tab, text="CSV Format Guide", padding=15)
        instructions_frame.pack(fill='x', padx=20, pady=10)
        
        guide_text = """REQUIRED CSV FORMAT:

The CSV file must contain the following columns (in any order):

BASIC COLUMNS:
• Barangay - Name of the barangay (text)
• Year - Year of the data (integer, e.g., 2023)
• Population - Population for that year (positive integer)
• Cases - Total leptospirosis cases (non-negative integer)

RISK FACTOR COLUMNS (ALL REQUIRED):
• Flooded - Is area flooded? (Yes/No or 1/0)
• Evacuation - Evacuation needed? (Yes/No or 1/0)
• Infrastructure_Damage - Infrastructure/Agriculture damage? (Yes/No or 1/0)
• Irregular_Garbage - Irregular garbage collection? (Yes/No or 1/0)
• High_Rodents - High rodent/stray presence? (Yes/No or 1/0)
• Clogged_Drainage - Clogged/open drainage? (Yes/No or 1/0)

EXAMPLE CSV FORMAT:
Barangay,Year,Population,Cases,Flooded,Evacuation,Infrastructure_Damage,Irregular_Garbage,High_Rodents,Clogged_Drainage
San Jose,2022,15000,12,Yes,No,Yes,Yes,No,Yes
San Jose,2023,15500,8,Yes,No,No,No,No,Yes
Santa Maria,2022,12000,5,No,No,No,Yes,Yes,No
Santa Maria,2023,12300,3,No,No,No,No,No,No

NOTES:
• Column headers are case-insensitive
• Use Yes/No, Y/N, 1/0, or True/False for risk factors
• Composite Risk Index will be calculated automatically
• Barangays will be auto-created if they don't exist
• Existing data will be updated (not duplicated)
• Empty rows will be skipped
        """
        
        guide_label = tk.Text(instructions_frame, height=22, width=100, wrap='word', 
                             font=('Courier', 9), relief='solid', borderwidth=1)
        guide_label.insert('1.0', guide_text)
        guide_label.config(state='disabled', bg='#f5f5f5')
        guide_label.pack(fill='both', expand=True)
        
        # File selection frame
        file_frame = ttk.LabelFrame(tab, text="Select CSV File", padding=15)
        file_frame.pack(fill='x', padx=20, pady=10)
        
        file_control_frame = ttk.Frame(file_frame)
        file_control_frame.pack(fill='x')
        
        ttk.Label(file_control_frame, text="File:").pack(side='left', padx=5)
        self.csv_file_path = tk.StringVar()
        ttk.Entry(file_control_frame, textvariable=self.csv_file_path, width=60, state='readonly').pack(side='left', padx=5)
        ttk.Button(file_control_frame, text="Browse...", command=self.browse_csv_file).pack(side='left', padx=5)
        ttk.Button(file_control_frame, text="Download Template", command=self.download_csv_template).pack(side='left', padx=5)
        
        # Progress bar
        progress_frame = ttk.Frame(file_frame)
        progress_frame.pack(fill='x', pady=10)
        
        self.csv_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.csv_progress.pack(side='left', padx=5)
        
        self.csv_progress_label = ttk.Label(progress_frame, text="", foreground='blue')
        self.csv_progress_label.pack(side='left', padx=10)
        
        # Preview frame
        preview_frame = ttk.LabelFrame(tab, text="Data Preview", padding=15)
        preview_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Preview controls
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.pack(fill='x', pady=(0, 10))
        
        ttk.Button(preview_controls, text="Load & Preview", command=self.load_csv_preview, 
                  style='Accent.TButton').pack(side='left', padx=5)
        ttk.Button(preview_controls, text="Clear Preview", command=self.clear_csv_preview).pack(side='left', padx=5)
        
        self.csv_status_label = ttk.Label(preview_controls, text="No file loaded", foreground='gray')
        self.csv_status_label.pack(side='left', padx=20)
        
        # Preview tree
        preview_tree_frame = ttk.Frame(preview_frame)
        preview_tree_frame.pack(fill='both', expand=True)
        
        columns = ('Row', 'Barangay', 'Year', 'Population', 'Cases', 'Composite_Risk', 'Status')
        self.csv_preview_tree = ttk.Treeview(preview_tree_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.csv_preview_tree.heading(col, text=col)
            if col == 'Row':
                self.csv_preview_tree.column(col, width=50)
            elif col == 'Status':
                self.csv_preview_tree.column(col, width=200)
            else:
                self.csv_preview_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(preview_tree_frame, orient='vertical', command=self.csv_preview_tree.yview)
        self.csv_preview_tree.configure(yscrollcommand=scrollbar.set)
        
        self.csv_preview_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Import button
        import_frame = ttk.Frame(preview_frame)
        import_frame.pack(fill='x', pady=(10, 0))
        
        self.import_btn = ttk.Button(import_frame, text="Import Data to Database", 
                                    command=self.import_csv_data, state='disabled')
        self.import_btn.pack(side='left', padx=5)
        
        ttk.Label(import_frame, text="⚠ This will add/update records in the database", 
                 foreground='red', font=('Arial', 9, 'italic')).pack(side='left', padx=10)
        
        # Store parsed data for import
        self.csv_parsed_data = []
    
    def browse_csv_file(self):
        """Open file dialog to select CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if filename:
            self.csv_file_path.set(filename)
            self.csv_status_label.config(text="File selected. Click 'Load & Preview' to validate.", foreground='blue')
            self.import_btn.config(state='disabled')
    
    def download_csv_template(self):
        """Download a CSV template file"""
        filename = filedialog.asksaveasfilename(
            title="Save CSV Template",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile="leptospirosis_data_template.csv"
        )
        
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Write header with all risk factor columns
                    writer.writerow(['Barangay', 'Year', 'Population', 'Cases', 
                                   'Flooded', 'Evacuation', 'Infrastructure_Damage',
                                   'Irregular_Garbage', 'High_Rodents', 'Clogged_Drainage'])
                    # Write example rows
                    writer.writerow(['San Jose', '2022', '15000', '12', 'Yes', 'No', 'Yes', 'Yes', 'No', 'Yes'])
                    writer.writerow(['San Jose', '2023', '15500', '8', 'Yes', 'No', 'No', 'No', 'No', 'Yes'])
                    writer.writerow(['Santa Maria', '2022', '12000', '5', 'No', 'No', 'No', 'Yes', 'Yes', 'No'])
                    writer.writerow(['Santa Maria', '2023', '12300', '3', 'No', 'No', 'No', 'No', 'No', 'No'])
                
                messagebox.showinfo("Success", f"Template saved to:\n{filename}\n\nYou can now edit this file with your data.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template: {str(e)}")
    
    def clear_csv_preview(self):
        """Clear the preview tree"""
        for item in self.csv_preview_tree.get_children():
            self.csv_preview_tree.delete(item)
        self.csv_status_label.config(text="Preview cleared", foreground='gray')
        self.csv_parsed_data = []
        self.import_btn.config(state='disabled')
        self.csv_progress['value'] = 0
        self.csv_progress_label.config(text="")
    
    def load_csv_preview(self):
        """Load and validate CSV file, show preview"""
        filepath = self.csv_file_path.get()
        if not filepath:
            messagebox.showwarning("No File", "Please select a CSV file first")
            return
        
        # Clear previous preview
        self.clear_csv_preview()
        
        # Reset progress bar
        self.csv_progress['value'] = 0
        self.csv_progress_label.config(text="Reading file...")
        self.root.update_idletasks()
        
        try:
            # First pass: count total rows for progress tracking
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for line in f) - 1  # Exclude header
            
            self.csv_progress_label.config(text=f"Validating {total_rows} rows...")
            self.root.update_idletasks()
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
                reader = csv.DictReader(f)
                
                # Normalize headers (lowercase, strip spaces)
                reader.fieldnames = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames]
                
                # Validate required columns
                required_cols = {'barangay', 'year', 'population', 'cases', 
                               'flooded', 'evacuation', 'infrastructure_damage',
                               'irregular_garbage', 'high_rodents', 'clogged_drainage'}
                headers = set(reader.fieldnames)
                
                missing = required_cols - headers
                if missing:
                    self.csv_progress['value'] = 0
                    self.csv_progress_label.config(text="")
                    messagebox.showerror("Invalid Format", 
                                       f"Missing required columns: {', '.join(missing)}\n\n"
                                       "Please check the format guide. All risk factor columns are required.")
                    return
                
                # Parse rows
                valid_count = 0
                error_count = 0
                row_num = 1
                parsed_data = []
                processed_count = 0
                
                for row in reader:
                    row_num += 1  # Account for header
                    processed_count += 1
                    
                    # Update progress every 10 rows or on last row
                    if processed_count % 10 == 0 or processed_count == total_rows:
                        progress = (processed_count / max(total_rows, 1)) * 100
                        self.csv_progress['value'] = progress
                        self.csv_progress_label.config(text=f"Processing {processed_count}/{total_rows} rows...")
                        self.root.update_idletasks()
                    
                    # Skip empty rows
                    if not any(row.values()):
                        continue
                    
                    try:
                        # Extract and validate data
                        brgy = row['barangay'].strip()
                        year = int(row['year'])
                        population = int(row['population'])
                        cases = int(row['cases'])
                        
                        if not brgy:
                            raise ValueError("Barangay name cannot be empty")
                        if population <= 0:
                            raise ValueError("Population must be positive")
                        if cases < 0:
                            raise ValueError("Cases cannot be negative")
                        
                        # Parse individual risk factors
                        is_flooded = self._parse_bool(row['flooded'])
                        is_evacuation = self._parse_bool(row['evacuation'])
                        is_infrastructure = self._parse_bool(row['infrastructure_damage'])
                        irregular_garbage = self._parse_bool(row['irregular_garbage'])
                        high_rodents = self._parse_bool(row['high_rodents'])
                        clogged_drainage = self._parse_bool(row['clogged_drainage'])
                        
                        # Calculate composite risk from factors
                        f_score = 0.0
                        if is_flooded:
                            f_score += 2.0
                            if is_evacuation:
                                f_score += 3.0
                            if is_infrastructure:
                                f_score += 5.0
                        
                        v_score = 1.0
                        if irregular_garbage:
                            v_score += 0.5
                        if high_rodents:
                            v_score += 0.5
                        if clogged_drainage:
                            v_score += 0.5
                        
                        composite_risk = f_score * v_score
                        
                        # Store parsed data with individual risk factors
                        parsed_data.append({
                            'row_num': row_num,
                            'barangay': brgy,
                            'year': year,
                            'population': population,
                            'cases': cases,
                            'composite_risk': composite_risk,
                            'is_flooded': is_flooded,
                            'is_evacuation': is_evacuation,
                            'is_infrastructure_damage': is_infrastructure,
                            'irregular_garbage': irregular_garbage,
                            'high_rodents': high_rodents,
                            'clogged_drainage': clogged_drainage,
                            'status': 'Valid ✓'
                        })
                        
                        # Add to preview with success tag
                        item_id = self.csv_preview_tree.insert('', 'end', values=(
                            row_num, brgy, year, population, cases, f"{composite_risk:.2f}", 'Valid ✓'
                        ), tags=('valid',))
                        valid_count += 1
                        
                    except Exception as e:
                        error_count += 1
                        status = f'Error: {str(e)}'
                        self.csv_preview_tree.insert('', 'end', values=(
                            row_num, row.get('barangay', '?'), row.get('year', '?'), 
                            row.get('population', '?'), row.get('cases', '?'), '?', status
                        ), tags=('error',))
                
                # Configure tag colors
                self.csv_preview_tree.tag_configure('valid', background='#d4edda')
                self.csv_preview_tree.tag_configure('error', background='#f8d7da')
                
                # Complete progress
                self.csv_progress['value'] = 100
                self.csv_progress_label.config(text="Validation complete!")
                self.root.update_idletasks()
                
                # Update status
                if error_count > 0:
                    self.csv_status_label.config(
                        text=f"Loaded: {valid_count} valid, {error_count} errors. Fix errors before importing.",
                        foreground='red'
                    )
                    self.import_btn.config(state='disabled')
                else:
                    self.csv_status_label.config(
                        text=f"Loaded: {valid_count} valid rows. Ready to import.",
                        foreground='green'
                    )
                    self.import_btn.config(state='normal')
                    self.csv_parsed_data = parsed_data
                
                if valid_count == 0 and error_count == 0:
                    messagebox.showwarning("Empty File", "No data rows found in CSV file")
                    self.csv_progress['value'] = 0
                    self.csv_progress_label.config(text="")
                    
        except Exception as e:
            self.csv_progress['value'] = 0
            self.csv_progress_label.config(text="Error occurred")
            messagebox.showerror("File Error", f"Failed to read CSV file:\n{str(e)}")
    
    def _parse_bool(self, value):
        """Parse boolean values from CSV (Yes/No, 1/0, True/False)"""
        if not value:
            return False
        value = str(value).strip().lower()
        return value in ('yes', 'y', '1', 'true', 't')
    
    def import_csv_data(self):
        """Import validated CSV data into database"""
        if not self.csv_parsed_data:
            messagebox.showwarning("No Data", "No valid data to import")
            return
        
        # Confirm import
        confirm = messagebox.askyesno(
            "Confirm Import",
            f"You are about to import {len(self.csv_parsed_data)} records into the database.\n\n"
            "Existing records with the same Barangay and Year will be updated.\n"
            "New barangays will be created automatically.\n\n"
            "Do you want to proceed?"
        )
        
        if not confirm:
            return
        
        # Reset progress
        self.csv_progress['value'] = 0
        self.csv_progress_label.config(text="Starting import...")
        self.root.update_idletasks()
        
        success_count = 0
        error_count = 0
        errors = []
        total_records = len(self.csv_parsed_data)
        
        try:
            for idx, data in enumerate(self.csv_parsed_data, 1):
                # Update progress
                progress = (idx / total_records) * 100
                self.csv_progress['value'] = progress
                self.csv_progress_label.config(text=f"Importing {idx}/{total_records} records...")
                self.root.update_idletasks()
                try:
                    # First, ensure barangay exists
                    self.db.cursor.execute("SELECT id FROM barangays WHERE name=?", (data['barangay'],))
                    result = self.db.cursor.fetchone()
                    
                    if not result:
                        # Create barangay with initial population from first data point
                        self.db.add_barangay(data['barangay'], data['population'])
                    
                    # Add yearly data with individual risk factors
                    success, message = self.db.add_year_data(
                        data['barangay'], 
                        data['year'], 
                        data['population'], 
                        data['cases'], 
                        data['composite_risk'],
                        1 if data['is_flooded'] else 0,
                        1 if data['is_evacuation'] else 0,
                        1 if data['is_infrastructure_damage'] else 0,
                        1 if data['irregular_garbage'] else 0,
                        1 if data['high_rodents'] else 0,
                        1 if data['clogged_drainage'] else 0
                    )
                    
                    if success:
                        success_count += 1
                    else:
                        error_count += 1
                        errors.append(f"Row {data['row_num']}: {message}")
                        
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {data['row_num']}: {str(e)}")
            
            # Complete progress
            self.csv_progress['value'] = 100
            self.csv_progress_label.config(text="Import complete!")
            self.root.update_idletasks()
            
            # Show results
            result_message = f"Import completed:\n\n"
            result_message += f"✓ Successfully imported: {success_count} records\n"
            
            if error_count > 0:
                result_message += f"✗ Failed: {error_count} records\n\n"
                result_message += "Errors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    result_message += f"\n... and {len(errors) - 10} more errors"
                messagebox.showwarning("Import Completed with Errors", result_message)
            else:
                messagebox.showinfo("Import Successful", result_message)
            
            # Refresh all data views
            self.refresh_barangay_list()
            self.refresh_barangay_combo()
            self.refresh_sim_combo()
            self.refresh_view_combo()
            self.refresh_pred_combo()
            self.refresh_data_view()
            
            # Clear preview
            self.clear_csv_preview()
            self.csv_file_path.set('')
            
            # Reset progress after a short delay
            self.root.after(1500, lambda: (self.csv_progress.config(value=0), 
                                           self.csv_progress_label.config(text="")))
            
        except Exception as e:
            self.csv_progress['value'] = 0
            self.csv_progress_label.config(text="Import failed")
            messagebox.showerror("Import Failed", f"An error occurred during import:\n{str(e)}")
    
    def create_simulation_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="SEIWR Simulation")
        
        # Control frame
        control_frame = ttk.LabelFrame(tab, text="Simulation Parameters", padding=20)
        control_frame.pack(fill='x', padx=20, pady=20)
        
        ttk.Label(control_frame, text="Select Barangay:").grid(row=0, column=0, sticky='w', pady=5)
        self.sim_brgy_combo = ttk.Combobox(control_frame, width=28, state='readonly')
        self.sim_brgy_combo.grid(row=0, column=1, pady=5, padx=10)
        
        ttk.Label(control_frame, text="Year (for initial data):").grid(row=1, column=0, sticky='w', pady=5)
        self.sim_year_entry = ttk.Entry(control_frame, width=30)
        self.sim_year_entry.grid(row=1, column=1, pady=5, padx=10)
        
        ttk.Label(control_frame, text="Simulation Days:").grid(row=2, column=0, sticky='w', pady=5)
        self.sim_days_entry = ttk.Entry(control_frame, width=30)
        self.sim_days_entry.insert(0, "365")
        self.sim_days_entry.grid(row=2, column=1, pady=5, padx=10)
        
        # Advanced parameters
        advanced_frame = ttk.LabelFrame(control_frame, text="Advanced Parameters (Optional)", padding=10)
        advanced_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew')
        
        ttk.Label(advanced_frame, text="Infection Coefficient:").grid(row=0, column=0, sticky='w', pady=3)
        self.i_coef_entry = ttk.Entry(advanced_frame, width=15)
        self.i_coef_entry.insert(0, "0.00005")
        self.i_coef_entry.grid(row=0, column=1, pady=3, padx=5)
        
        ttk.Label(advanced_frame, text="Incubation Rate (σ):").grid(row=1, column=0, sticky='w', pady=3)
        self.sigma_entry = ttk.Entry(advanced_frame, width=15)
        self.sigma_entry.insert(0, "0.1")
        self.sigma_entry.grid(row=1, column=1, pady=3, padx=5)
        
        ttk.Label(advanced_frame, text="Water Contamination (ξ):").grid(row=0, column=2, sticky='w', pady=3, padx=(20,0))
        self.xi_entry = ttk.Entry(advanced_frame, width=15)
        self.xi_entry.insert(0, "0.01")
        self.xi_entry.grid(row=0, column=3, pady=3, padx=5)
        
        ttk.Label(advanced_frame, text="Flood Decay (δ):").grid(row=1, column=2, sticky='w', pady=3, padx=(20,0))
        self.delta_entry = ttk.Entry(advanced_frame, width=15)
        self.delta_entry.insert(0, "0.1")
        self.delta_entry.grid(row=1, column=3, pady=3, padx=5)
        
        ttk.Button(control_frame, text="Run Simulation", command=self.run_simulation, 
                  style='Accent.TButton').grid(row=4, column=0, columnspan=2, pady=15)
        
        # Plot frame
        self.plot_frame = ttk.Frame(tab)
        self.plot_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.refresh_sim_combo()
    
    def create_prediction_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Trend Prediction")
        
        # Main container with left and right sections
        main_container = ttk.Frame(tab)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Left side - Controls
        left_frame = ttk.Frame(main_container)
        left_frame.pack(side='left', fill='both', padx=(0, 5))
        
        # Control frame
        control_frame = ttk.LabelFrame(left_frame, text="Scenario Settings", padding=15)
        control_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(control_frame, text="Select Barangay:").grid(row=0, column=0, sticky='w', pady=5)
        self.pred_brgy_combo = ttk.Combobox(control_frame, width=25, state='readonly')
        self.pred_brgy_combo.grid(row=0, column=1, pady=5, padx=10, sticky='ew')
        self.pred_brgy_combo.bind('<<ComboboxSelected>>', lambda e: self.load_baseline_data())
        
        ttk.Label(control_frame, text="Projected Population:").grid(row=1, column=0, sticky='w', pady=5)
        self.pred_pop_entry = ttk.Entry(control_frame, width=25)
        self.pred_pop_entry.grid(row=1, column=1, pady=5, padx=10, sticky='ew')
        
        # Flood Risk Scenario
        flood_frame = ttk.LabelFrame(control_frame, text="Flood Risk Scenario", padding=5)
        flood_frame.grid(row=2, column=0, columnspan=2, pady=10, sticky='ew')
        
        self.pred_flood_score_var = tk.DoubleVar(value=0.0)
        ttk.Radiobutton(flood_frame, text="No Flood (0)", variable=self.pred_flood_score_var, 
                       value=0.0, command=self.update_pred_composite).grid(row=0, column=0, sticky='w', pady=2)
        ttk.Radiobutton(flood_frame, text="Minor Flood (2)", variable=self.pred_flood_score_var, 
                       value=2.0, command=self.update_pred_composite).grid(row=1, column=0, sticky='w', pady=2)
        ttk.Radiobutton(flood_frame, text="Moderate + Evac (5)", variable=self.pred_flood_score_var, 
                       value=5.0, command=self.update_pred_composite).grid(row=2, column=0, sticky='w', pady=2)
        ttk.Radiobutton(flood_frame, text="Severe + Damage (10)", variable=self.pred_flood_score_var, 
                       value=10.0, command=self.update_pred_composite).grid(row=3, column=0, sticky='w', pady=2)
        
        # Vector/Sanitation Scenario
        vector_frame = ttk.LabelFrame(control_frame, text="Sanitation Scenario", padding=5)
        vector_frame.grid(row=3, column=0, columnspan=2, pady=10, sticky='ew')
        
        self.pred_garbage_var = tk.BooleanVar()
        self.pred_rodents_var = tk.BooleanVar()
        self.pred_drainage_var = tk.BooleanVar()
        
        ttk.Checkbutton(vector_frame, text="Irregular Garbage Collection", 
                       variable=self.pred_garbage_var, command=self.update_pred_composite).grid(row=0, column=0, sticky='w', pady=2)
        ttk.Checkbutton(vector_frame, text="High Rodent/Stray Presence", 
                       variable=self.pred_rodents_var, command=self.update_pred_composite).grid(row=1, column=0, sticky='w', pady=2)
        ttk.Checkbutton(vector_frame, text="Clogged/Open Drainage", 
                       variable=self.pred_drainage_var, command=self.update_pred_composite).grid(row=2, column=0, sticky='w', pady=2)
        
        # Composite Risk Display
        composite_display = ttk.Frame(control_frame)
        composite_display.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Label(composite_display, text="Composite Risk Index:").pack(side='left', padx=5)
        self.pred_composite_label = ttk.Label(composite_display, text="0.0", 
                                             font=('Arial', 12, 'bold'), foreground='red')
        self.pred_composite_label.pack(side='left', padx=5)
        
        ttk.Button(control_frame, text="Generate Prediction", command=self.run_prediction, 
                  style='Accent.TButton').grid(row=5, column=0, columnspan=2, pady=15, sticky='ew')
        
        control_frame.columnconfigure(1, weight=1)
        
        # Results and recommendations frame
        results_frame = ttk.LabelFrame(left_frame, text="Prediction Results", padding=15)
        results_frame.pack(fill='both', expand=True)
        
        self.pred_result_label = ttk.Label(results_frame, text="No prediction yet", 
                                          font=('Arial', 13, 'bold'), foreground='blue')
        self.pred_result_label.pack(pady=10)
        
        # Mitigation recommendations
        ttk.Label(results_frame, text="Mitigation Recommendations:", 
                 font=('Arial', 10, 'bold')).pack(anchor='w', pady=(10, 5))
        
        self.recommendations_text = tk.Text(results_frame, height=12, width=45, wrap='word', 
                                           font=('Arial', 9), relief='solid', borderwidth=1)
        self.recommendations_text.pack(fill='both', expand=True, pady=5)
        self.recommendations_text.config(state='disabled')
        
        # Right side - Plot
        right_frame = ttk.Frame(main_container)
        right_frame.pack(side='right', fill='both', expand=True, padx=(5, 0))
        
        self.pred_plot_frame = ttk.LabelFrame(right_frame, text="Trend Visualization", padding=10)
        self.pred_plot_frame.pack(fill='both', expand=True)
        
        self.refresh_pred_combo()
    
    def create_view_data_tab(self):
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="View All Data")
        
        # Filter frame
        filter_frame = ttk.Frame(tab, padding=10)
        filter_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(filter_frame, text="Filter by Barangay:").pack(side='left', padx=5)
        self.view_brgy_combo = ttk.Combobox(filter_frame, width=25, state='readonly')
        self.view_brgy_combo.pack(side='left', padx=5)
        self.view_brgy_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_data_view())
        
        ttk.Button(filter_frame, text="Show All", command=self.show_all_data).pack(side='left', padx=5)
        ttk.Button(filter_frame, text="Refresh", command=self.refresh_data_view).pack(side='left', padx=5)
        ttk.Button(filter_frame, text="Edit Selected", command=self.edit_selected_data).pack(side='left', padx=5)
        ttk.Button(filter_frame, text="Delete Selected", command=self.delete_selected_data).pack(side='left', padx=5)
        
        # Data display
        list_frame = ttk.Frame(tab, padding=10)
        list_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        columns = ('Barangay', 'Year', 'Population', 'Cases', 'Composite Risk')
        self.data_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical', command=self.data_tree.yview)
        self.data_tree.configure(yscrollcommand=scrollbar.set)
        
        self.data_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        self.refresh_view_combo()
        self.refresh_data_view()
    
    # --- CALLBACK METHODS ---
    
    def add_barangay(self):
        name = self.brgy_name_entry.get().strip()
        pop_str = self.brgy_pop_entry.get().strip()
        
        if not name or not pop_str:
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        
        try:
            population = int(pop_str)
            if population <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Population must be a positive integer")
            return
        
        success, message = self.db.add_barangay(name, population)
        
        if success:
            messagebox.showinfo("Success", message)
            self.clear_barangay_form()
            self.refresh_barangay_list()
            self.refresh_barangay_combo()
            self.refresh_sim_combo()
            self.refresh_view_combo()
            self.refresh_pred_combo()
        else:
            messagebox.showerror("Error", message)
    
    def clear_barangay_form(self):
        self.brgy_name_entry.delete(0, tk.END)
        self.brgy_pop_entry.delete(0, tk.END)
    
    def refresh_barangay_list(self):
        for item in self.brgy_tree.get_children():
            self.brgy_tree.delete(item)
        
        for row in self.db.get_barangays():
            self.brgy_tree.insert('', 'end', values=row)
    
    def refresh_barangay_combo(self):
        barangays = [b[1] for b in self.db.get_barangays()]
        self.year_brgy_combo['values'] = barangays
        if barangays:
            self.year_brgy_combo.current(0)
    
    def refresh_sim_combo(self):
        barangays = [b[1] for b in self.db.get_barangays()]
        self.sim_brgy_combo['values'] = barangays
        if barangays:
            self.sim_brgy_combo.current(0)
    
    def refresh_pred_combo(self):
        barangays = [b[1] for b in self.db.get_barangays()]
        self.pred_brgy_combo['values'] = barangays
        if barangays:
            self.pred_brgy_combo.current(0)
            self.load_baseline_data()
    
    def update_pred_composite(self):
        """Update composite risk index for prediction scenario"""
        f_score = self.pred_flood_score_var.get()
        
        v_score = 1.0
        if self.pred_garbage_var.get():
            v_score += 0.5
        if self.pred_rodents_var.get():
            v_score += 0.5
        if self.pred_drainage_var.get():
            v_score += 0.5
        
        composite = f_score * v_score
        self.pred_composite_label.config(text=f"{composite:.2f}")
    
    def update_composite_risk(self):
        """Calculate composite risk index based on flood and vector/sanitation factors"""
        # Calculate Flood Score
        f_score = 0.0
        if self.is_flooded_var.get():
            f_score += 2.0
            if self.is_evac_var.get():
                f_score += 3.0
            if self.is_damaged_var.get():
                f_score += 5.0
        
        # Calculate Vector/Sanitation Multiplier
        v_score = 1.0  # Base multiplier
        if self.irregular_garbage_var.get():
            v_score += 0.5
        if self.high_rodents_var.get():
            v_score += 0.5
        if self.clogged_drainage_var.get():
            v_score += 0.5
        
        # Composite Risk Index = Flood Score × Vector Multiplier
        composite_risk = f_score * v_score
        
        # Update labels
        self.flood_score_label.config(text=f"{f_score:.1f}")
        self.vector_score_label.config(text=f"{v_score:.1f}x")
        self.composite_risk_label.config(text=f"{composite_risk:.2f}")
    
    def refresh_view_combo(self):
        barangays = ['All'] + [b[1] for b in self.db.get_barangays()]
        self.view_brgy_combo['values'] = barangays
        self.view_brgy_combo.current(0)
    
    def add_yearly_data(self):
        brgy = self.year_brgy_combo.get()
        year_str = self.year_entry.get().strip()
        pop_str = self.year_pop_entry.get().strip()
        cases_str = self.cases_entry.get().strip()
        
        if not all([brgy, year_str, pop_str, cases_str]):
            messagebox.showwarning("Input Error", "Please fill all required fields")
            return
        
        try:
            year = int(year_str)
            population = int(pop_str)
            cases = int(cases_str)
            
            if cases < 0 or population <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", 
                               "Invalid input. Population must be positive, Cases must be non-negative")
            return
        
        # Calculate composite risk index from checkboxes
        # Flood Score
        f_score = 0.0
        if self.is_flooded_var.get():
            f_score += 2.0
            if self.is_evac_var.get():
                f_score += 3.0
            if self.is_damaged_var.get():
                f_score += 5.0
        
        # Vector/Sanitation Multiplier
        v_score = 1.0
        if self.irregular_garbage_var.get():
            v_score += 0.5
        if self.high_rodents_var.get():
            v_score += 0.5
        if self.clogged_drainage_var.get():
            v_score += 0.5
        
        # Composite Risk Index
        composite_risk = f_score * v_score
        
        # Store individual risk factors
        is_flooded = 1 if self.is_flooded_var.get() else 0
        is_evac = 1 if self.is_evac_var.get() else 0
        is_damage = 1 if self.is_damaged_var.get() else 0
        irregular_garb = 1 if self.irregular_garbage_var.get() else 0
        high_rod = 1 if self.high_rodents_var.get() else 0
        clogged_drain = 1 if self.clogged_drainage_var.get() else 0
        
        success, message = self.db.add_year_data(brgy, year, population, cases, composite_risk,
                                                 is_flooded, is_evac, is_damage,
                                                 irregular_garb, high_rod, clogged_drain)
        
        if success:
            if self.edit_mode:
                messagebox.showinfo("Success", f"Data for {brgy} ({year}) updated successfully.")
            else:
                messagebox.showinfo("Success", message)
            self.clear_yearly_form()
            self.refresh_data_view()
        else:
            messagebox.showerror("Error", message)
    
    def clear_yearly_form(self):
        self.year_entry.delete(0, tk.END)
        self.year_pop_entry.delete(0, tk.END)
        self.cases_entry.delete(0, tk.END)
        self.is_flooded_var.set(False)
        self.is_evac_var.set(False)
        self.is_damaged_var.set(False)
        self.irregular_garbage_var.set(False)
        self.high_rodents_var.set(False)
        self.clogged_drainage_var.set(False)
        self.flood_score_label.config(text="0.0")
        self.vector_score_label.config(text="1.0x")
        self.composite_risk_label.config(text="0.0")
        
        # Reset edit mode
        self.edit_mode = False
        self.edit_data = None
        self.save_data_btn.config(text="Save Data")
    
    def refresh_data_view(self):
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        
        selected = self.view_brgy_combo.get()
        if selected == 'All':
            data = self.db.get_yearly_data()
        else:
            data = self.db.get_yearly_data(selected)
        
        for row in data:
            # row format: (name, year, population, cases, composite_risk, is_flooded, is_evac, is_damage, irregular_garb, high_rod, clogged_drain)
            # Display only first 5 columns: name, year, population, cases, composite_risk
            display_row = row[:5]
            self.data_tree.insert('', 'end', values=display_row)
    
    def show_all_data(self):
        self.view_brgy_combo.current(0)
        self.refresh_data_view()
    
    def delete_selected_data(self):
        """Delete the selected yearly data record"""
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a record to delete")
            return
        
        # Get the selected item's values
        item = self.data_tree.item(selection[0])
        values = item['values']
        brgy_name = values[0]
        year = values[1]
        
        # Confirm deletion
        confirm = messagebox.askyesno(
            "Confirm Delete", 
            f"Are you sure you want to delete data for {brgy_name} ({year})?\n\nThis action cannot be undone."
        )
        
        if confirm:
            success, message = self.db.delete_yearly_data(brgy_name, year)
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_data_view()
            else:
                messagebox.showerror("Error", message)
    
    def edit_selected_data(self):
        """Edit the selected yearly data record"""
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a record to edit")
            return
        
        # Get the selected item's values (displayed: name, year, pop, cases, composite)
        item = self.data_tree.item(selection[0])
        values = item['values']
        brgy_name = values[0]
        year = values[1]
        
        # Fetch full data from database including individual risk factors
        full_data = self.db.get_yearly_data(brgy_name)
        
        # Find the matching year
        selected_record = None
        for record in full_data:
            if record[1] == year:  # record[1] is year
                selected_record = record
                break
        
        if not selected_record:
            messagebox.showerror("Error", "Could not find record data")
            return
        
        # Store edit mode data with all individual risk factors
        # record format: (name, year, pop, cases, composite, is_flooded, is_evac, is_damage, irregular_garb, high_rod, clogged_drain)
        self.edit_mode = True
        self.edit_data = {
            'barangay': selected_record[0],
            'year': selected_record[1],
            'population': selected_record[2],
            'cases': selected_record[3],
            'composite_risk': selected_record[4],
            'is_flooded': selected_record[5],
            'is_evacuation': selected_record[6],
            'is_infrastructure_damage': selected_record[7],
            'irregular_garbage': selected_record[8],
            'high_rodents': selected_record[9],
            'clogged_drainage': selected_record[10]
        }
        
        # Switch to Yearly Data Entry tab
        self.notebook.select(1)  # Index 1 is the Yearly Data Entry tab
        
        # Populate the form
        self.populate_yearly_form()
        
        # Update button text
        self.save_data_btn.config(text="Update Data")
    
    def populate_yearly_form(self):
        """Populate yearly data form with edit data"""
        if not self.edit_data:
            return
        
        # Save edit data temporarily (clear_yearly_form resets it)
        temp_edit_data = self.edit_data.copy()
        
        # Clear form fields
        self.year_entry.delete(0, tk.END)
        self.year_pop_entry.delete(0, tk.END)
        self.cases_entry.delete(0, tk.END)
        self.is_flooded_var.set(False)
        self.is_evac_var.set(False)
        self.is_damaged_var.set(False)
        self.irregular_garbage_var.set(False)
        self.high_rodents_var.set(False)
        self.clogged_drainage_var.set(False)
        
        # Restore edit data and mode
        self.edit_data = temp_edit_data
        self.edit_mode = True
        
        # Set barangay
        barangays = [b[1] for b in self.db.get_barangays()]
        if self.edit_data['barangay'] in barangays:
            idx = barangays.index(self.edit_data['barangay'])
            self.year_brgy_combo.current(idx)
        
        # Set year, population, cases
        self.year_entry.insert(0, str(self.edit_data['year']))
        self.year_pop_entry.insert(0, str(self.edit_data['population']))
        self.cases_entry.insert(0, str(self.edit_data['cases']))
        
        # Set risk factors from stored data (no more guessing!)
        self.is_flooded_var.set(bool(self.edit_data.get('is_flooded', 0)))
        self.is_evac_var.set(bool(self.edit_data.get('is_evacuation', 0)))
        self.is_damaged_var.set(bool(self.edit_data.get('is_infrastructure_damage', 0)))
        self.irregular_garbage_var.set(bool(self.edit_data.get('irregular_garbage', 0)))
        self.high_rodents_var.set(bool(self.edit_data.get('high_rodents', 0)))
        self.clogged_drainage_var.set(bool(self.edit_data.get('clogged_drainage', 0)))
        
        # Update composite risk display
        self.update_composite_risk()
    
    def load_baseline_data(self):
        """Load baseline data from last year for the selected barangay"""
        brgy = self.pred_brgy_combo.get()
        if not brgy:
            return
        
        history = self.db.get_barangay_history(brgy)
        if history:
            last_data = history[-1]
            self.pred_pop_entry.delete(0, tk.END)
            self.pred_pop_entry.insert(0, str(last_data[1]))
            
            # Set baseline composite risk
            last_composite = last_data[2]
            # Estimate flood and vector scores from composite
            if last_composite <= 2.0:
                self.pred_flood_score_var.set(0.0)
            elif last_composite <= 5.0:
                self.pred_flood_score_var.set(2.0)
            elif last_composite <= 10.0:
                self.pred_flood_score_var.set(5.0)
            else:
                self.pred_flood_score_var.set(10.0)
            
            self.update_pred_composite()
    
    def run_prediction(self):
        """Run trend-based prediction using linear regression with mitigation analysis"""
        brgy = self.pred_brgy_combo.get()
        pop_str = self.pred_pop_entry.get().strip()
        
        if not all([brgy, pop_str]):
            messagebox.showwarning("Input Error", "Please fill all required fields")
            return
        
        try:
            future_pop = int(pop_str)
            
            # Calculate composite risk
            f_score = self.pred_flood_score_var.get()
            v_score = 1.0
            if self.pred_garbage_var.get():
                v_score += 0.5
            if self.pred_rodents_var.get():
                v_score += 0.5
            if self.pred_drainage_var.get():
                v_score += 0.5
            
            future_composite = f_score * v_score
            
        except ValueError:
            messagebox.showerror("Input Error", "Invalid population value")
            return
        
        history = self.db.get_barangay_history(brgy)
        
        if len(history) < 2:
            messagebox.showerror("Insufficient Data", 
                               "Need at least 2 years of historical data for prediction")
            return
        
        predicted_cases, model = predict_next_year(history, future_pop, future_composite)
        
        if predicted_cases is None:
            messagebox.showerror("Prediction Error", model)
            return
        
        # Update result label
        self.pred_result_label.config(
            text=f"Predicted Cases: {int(predicted_cases)} (Composite Risk: {future_composite:.2f})", 
            foreground='red' if predicted_cases > 20 else 'orange' if predicted_cases > 10 else 'green'
        )
        
        # Generate mitigation recommendations
        self.generate_recommendations(predicted_cases, f_score, v_score, future_pop, model)
        
        # Clear previous plot
        for widget in self.pred_plot_frame.winfo_children():
            widget.destroy()
        
        # Create prediction plot
        years = [r[0] for r in history]
        cases = [r[3] for r in history]
        next_year = years[-1] + 1
        
        fig, ax = plt.subplots(figsize=(7, 5))
        
        # Plot historical data
        ax.plot(years, cases, 'o-', label='Historical Cases', color='blue', linewidth=2, markersize=8)
        
        # Plot prediction
        ax.plot([years[-1], next_year], [cases[-1], predicted_cases], 
               'o--', color='red', label=f'Prediction ({int(predicted_cases)} cases)', linewidth=2, markersize=8)
        
        # Calculate best case scenario (no flood, good sanitation)
        best_case_composite = 0.0
        best_case_pred, _ = predict_next_year(history, future_pop, best_case_composite)
        ax.plot([years[-1], next_year], [cases[-1], best_case_pred], 
               'o:', color='green', label=f'Best Case ({int(best_case_pred)} cases)', linewidth=1.5, markersize=6, alpha=0.7)
        
        ax.set_xlabel('Year', fontsize=11)
        ax.set_ylabel('Total Cases', fontsize=11)
        ax.set_title(f'Leptospirosis Trend: {brgy}', fontsize=12, fontweight='bold')
        ax.set_xticks(years + [next_year])
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', fontsize=9)
        
        fig.tight_layout()
        
        # Embed in Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.pred_plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_recommendations(self, predicted_cases, f_score, v_score, population, model):
        """Generate actionable mitigation recommendations"""
        recommendations = []
        
        # Header
        recommendations.append("=" * 50)
        recommendations.append(f"MITIGATION STRATEGY FOR {int(predicted_cases)} PREDICTED CASES")
        recommendations.append("=" * 50)
        recommendations.append("")
        
        # Risk level assessment
        if predicted_cases > 30:
            risk_level = "CRITICAL"
            recommendations.append(f"⚠️ {risk_level} RISK LEVEL")
        elif predicted_cases > 15:
            risk_level = "HIGH"
            recommendations.append(f"⚠️ {risk_level} RISK LEVEL")
        elif predicted_cases > 5:
            risk_level = "MODERATE"
            recommendations.append(f"⚠ {risk_level} RISK LEVEL")
        else:
            risk_level = "LOW"
            recommendations.append(f"✓ {risk_level} RISK LEVEL")
        
        recommendations.append("")
        
        # Priority interventions based on factors
        recommendations.append("PRIORITY INTERVENTIONS:")
        recommendations.append("")
        
        priority_num = 1
        
        # Flood-related recommendations
        if f_score >= 10.0:
            recommendations.append(f"{priority_num}. FLOOD MANAGEMENT (Critical)")
            recommendations.append("   • Improve drainage infrastructure")
            recommendations.append("   • Establish early warning system")
            recommendations.append("   • Prepare evacuation centers")
            recommendations.append("   • Stock emergency medical supplies")
            recommendations.append("")
            priority_num += 1
        elif f_score >= 5.0:
            recommendations.append(f"{priority_num}. FLOOD PREPAREDNESS (High Priority)")
            recommendations.append("   • Clear drainage systems before rainy season")
            recommendations.append("   • Conduct community drills")
            recommendations.append("   • Pre-position medical resources")
            recommendations.append("")
            priority_num += 1
        elif f_score > 0:
            recommendations.append(f"{priority_num}. FLOOD MITIGATION (Moderate)")
            recommendations.append("   • Regular drainage maintenance")
            recommendations.append("   • Monitor weather forecasts")
            recommendations.append("")
            priority_num += 1
        
        # Sanitation-related recommendations
        if v_score > 2.0:
            recommendations.append(f"{priority_num}. SANITATION IMPROVEMENT (Critical)")
            if self.pred_garbage_var.get():
                recommendations.append("   • Establish regular garbage collection")
                recommendations.append("   • Set up community waste segregation")
            if self.pred_rodents_var.get():
                recommendations.append("   • Launch rodent control program")
                recommendations.append("   • Reduce food sources for pests")
                recommendations.append("   • Control stray animal population")
            if self.pred_drainage_var.get():
                recommendations.append("   • Clear clogged drainage systems")
                recommendations.append("   • Cover open drainage channels")
            recommendations.append("")
            priority_num += 1
        elif v_score > 1.5:
            recommendations.append(f"{priority_num}. SANITATION ENHANCEMENT (High Priority)")
            if self.pred_garbage_var.get():
                recommendations.append("   • Improve garbage collection frequency")
            if self.pred_rodents_var.get():
                recommendations.append("   • Conduct rodent monitoring")
            if self.pred_drainage_var.get():
                recommendations.append("   • Schedule drainage cleaning")
            recommendations.append("")
            priority_num += 1
        
        # Public health interventions
        recommendations.append(f"{priority_num}. PUBLIC HEALTH MEASURES")
        recommendations.append("   • Conduct health education campaigns")
        recommendations.append("   • Distribute protective equipment (boots, gloves)")
        recommendations.append("   • Offer doxycycline prophylaxis to high-risk groups")
        recommendations.append("   • Set up surveillance system")
        recommendations.append("")
        
        # Impact analysis
        sensitivity = model.coef_[0]  # Rate increase per composite risk unit
        cases_per_risk_unit = (sensitivity / 100000) * population
        recommendations.append("IMPACT ANALYSIS:")
        recommendations.append(f"• For every +1.0 Composite Risk increase:")
        recommendations.append(f"  ~{int(abs(cases_per_risk_unit))} additional cases expected")
        recommendations.append("")
        
        # Best case scenario
        best_case_composite = 0.0
        best_case_pred, _ = predict_next_year(self.db.get_barangay_history(self.pred_brgy_combo.get()), 
                                             population, best_case_composite)
        potential_reduction = int(predicted_cases - best_case_pred)
        
        if potential_reduction > 0:
            recommendations.append("POTENTIAL OUTCOME:")
            recommendations.append(f"✓ With optimal interventions (zero composite risk):")
            recommendations.append(f"  Expected cases: {int(best_case_pred)}")
            recommendations.append(f"  Cases prevented: {potential_reduction}")
            recommendations.append(f"  Reduction: {int((potential_reduction/predicted_cases)*100)}%")
        
        recommendations.append("")
        recommendations.append("=" * 50)
        
        # Display recommendations
        self.recommendations_text.config(state='normal')
        self.recommendations_text.delete('1.0', tk.END)
        self.recommendations_text.insert('1.0', '\n'.join(recommendations))
        self.recommendations_text.config(state='disabled')
    
    def run_simulation(self):
        """Run SEIWR simulation"""
        brgy = self.sim_brgy_combo.get()
        year_str = self.sim_year_entry.get().strip()
        days_str = self.sim_days_entry.get().strip()
        
        if not all([brgy, year_str, days_str]):
            messagebox.showwarning("Input Error", "Please fill required fields")
            return
        
        try:
            year = int(year_str)
            days = int(days_str)
            i_coef = float(self.i_coef_entry.get())
            sigma = float(self.sigma_entry.get())
            xi = float(self.xi_entry.get())
            delta = float(self.delta_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Invalid parameter values")
            return
        
        data = self.db.get_data_for_sim(brgy, year)
        if not data:
            messagebox.showerror("Error", f"No data found for {brgy} in {year}")
            return
        
        pop, cases, flood_sev = data
        
        # Run simulation
        t = np.linspace(0, days, days)
        
        S0 = float(pop)
        E0 = 0.0
        I0 = float(cases) if cases > 0 else 0.1
        W0 = float(flood_sev)
        
        Lambda = (pop * 0.01) / 365
        
        y0 = [S0, E0, I0, W0]
        
        try:
            solution = odeint(seiwr_ode, y0, t, args=(Lambda, i_coef, sigma, xi, delta))
            S, E, I, W = solution.T
            
            # Clear previous plot
            for widget in self.plot_frame.winfo_children():
                widget.destroy()
            
            # Create new plot
            fig, ax1 = plt.subplots(figsize=(8, 5))
            
            color = 'tab:blue'
            ax1.set_xlabel('Time (Days)')
            ax1.set_ylabel('Susceptible Population', color=color)
            ax1.plot(t, S, color=color, label='Susceptible')
            ax1.tick_params(axis='y', labelcolor=color)
            ax1.grid(True, alpha=0.3)
            
            ax2 = ax1.twinx()
            
            color = 'tab:red'
            ax2.set_ylabel('Risk Index / Exposed', color=color)
            ax2.plot(t, I, color=color, label='Cumulative Risk (I)', linewidth=2)
            ax2.plot(t, E, color='orange', label='Exposed (E)', linestyle='--')
            ax2.plot(t, W, color='green', label='Water Contamination (W)', linestyle=':')
            ax2.tick_params(axis='y', labelcolor=color)
            
            plt.title(f"SEIWR Model: {brgy} ({year})")
            
            # Add legends for both axes
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.9)
            
            fig.tight_layout()
            
            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            
            messagebox.showinfo("Success", "Simulation completed successfully!")
            
        except Exception as e:
            messagebox.showerror("Simulation Error", f"Error during simulation: {str(e)}")

def main():
    root = tk.Tk()
    app = LeptospirosisApp(root)
    
    # Proper cleanup on window close
    def on_closing():
        try:
            # Close all matplotlib figures to free memory
            plt.close('all')
            # Close database connection (only if it exists)
            if hasattr(app, 'db') and app.db:
                app.db.close()
        except Exception:
            pass
        root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
