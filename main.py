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

# --- MODERN THEME COLORS ---
class ThemeColors:
    """Modern, eye-friendly color palette for long duration usage"""
    # Primary colors - Soft blues and teals
    PRIMARY = "#4A90A4"          # Muted teal blue
    PRIMARY_DARK = "#3D7A8C"     # Darker shade for hover
    PRIMARY_LIGHT = "#6BA8B9"    # Lighter shade
    
    # Background colors - Warm neutrals
    BG_MAIN = "#F5F6F8"          # Very light gray-blue
    BG_CARD = "#FFFFFF"          # Pure white for cards
    BG_SECONDARY = "#E8EAED"     # Light gray for secondary areas
    BG_INPUT = "#FAFBFC"         # Slightly off-white for inputs
    
    # Text colors
    TEXT_PRIMARY = "#2C3E50"     # Dark blue-gray for main text
    TEXT_SECONDARY = "#5D6D7E"   # Medium gray for secondary text
    TEXT_MUTED = "#8E99A4"       # Light gray for placeholders
    
    # Accent colors
    SUCCESS = "#27AE60"          # Green for success states
    WARNING = "#F39C12"          # Amber for warnings
    DANGER = "#E74C3C"           # Red for errors/critical
    INFO = "#3498DB"             # Blue for information
    
    # Border colors
    BORDER = "#DDE2E8"           # Light border
    BORDER_FOCUS = "#4A90A4"     # Focus state border
    
    # Special UI elements
    DEMO_BAR = "#E67E22"         # Orange for demo indicator
    TAB_ACTIVE = "#4A90A4"       # Active tab indicator
    TREEVIEW_ALT = "#F8F9FA"     # Alternating row color

# --- TKINTER GUI APPLICATION ---
class LeptospirosisApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Leptospirosis Risk Prediction System")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=ThemeColors.BG_MAIN)
        
        # Initialize Demo Manager
        self.demo_manager = DemoManager(APP_DIR)
        
        if not self.demo_manager.initialize_demo():
            self.show_demo_expired_screen()
            return
        
        self.db = Database()
        self.edit_mode = False
        self.edit_data = None
        self.current_recommendations = None
        
        self.setup_modern_theme()
        
        self.main_container = tk.Frame(root, bg=ThemeColors.BG_MAIN)
        self.main_container.pack(fill='both', expand=True, padx=15, pady=15)
        
        self.create_demo_indicator()
        
        self.notebook = ttk.Notebook(self.main_container, style='Modern.TNotebook')
        self.notebook.pack(fill='both', expand=True, pady=(0, 5))
        
        # Create all tabs
        self.create_barangay_tab()
        self.create_yearly_data_tab()
        self.create_import_csv_tab()
        self.create_simulation_tab()
        self.create_prediction_tab()
        self.create_view_data_tab()
    
    # --- HELPER METHODS ---
    def create_tab_header(self, parent, title, subtitle):
        """Create standard tab header with title and subtitle"""
        header = ttk.Frame(parent, style='Card.TFrame')
        header.pack(fill='x', pady=(0, 15))
        ttk.Label(header, text=title, style='Header.TLabel').pack(side='left')
        ttk.Label(header, text=subtitle, style='Muted.TLabel').pack(side='left', padx=(15, 0))
        return header
    
    def create_scrollable_tree(self, parent, columns, col_widths=None, height=12):
        """Create treeview with scrollbar"""
        container = ttk.Frame(parent)
        container.pack(fill='both', expand=True)
        
        tree = ttk.Treeview(container, columns=columns, show='headings', height=height)
        for col in columns:
            tree.heading(col, text=col, anchor='w')
            width = col_widths.get(col, 120) if col_widths else 120
            tree.column(col, width=width, anchor='w')
        
        scrollbar = ttk.Scrollbar(container, orient='vertical', command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        return tree
    
    def calc_composite_risk(self, is_flooded, is_evac, is_damage, garbage, rodents, drainage):
        """Calculate composite risk index from risk factors"""
        f_score = 0.0
        if is_flooded:
            f_score = 2.0
            if is_evac: f_score += 3.0
            if is_damage: f_score += 5.0
        v_score = 1.0 + (0.5 if garbage else 0) + (0.5 if rodents else 0) + (0.5 if drainage else 0)
        return f_score * v_score, f_score, v_score
    
    def refresh_all_combos(self):
        """Refresh all barangay comboboxes"""
        barangays = [b[1] for b in self.db.get_barangays()]
        for combo in [self.year_brgy_combo, self.sim_brgy_combo, self.pred_brgy_combo]:
            combo['values'] = barangays
            if barangays: combo.current(0)
        self.view_brgy_combo['values'] = ['All'] + barangays
        self.view_brgy_combo.current(0)
        if barangays: self.load_baseline_data()
    
    def setup_modern_theme(self):
        """Configure modern, minimal ttk styles"""
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except:
            pass
        
        # Base configuration
        style.configure('.', background=ThemeColors.BG_MAIN, foreground=ThemeColors.TEXT_PRIMARY, font=('Segoe UI', 10))
        
        # Notebook
        style.configure('Modern.TNotebook', background=ThemeColors.BG_MAIN, borderwidth=0, padding=[0, 5])
        style.configure('Modern.TNotebook.Tab', background=ThemeColors.BG_SECONDARY, 
                       foreground=ThemeColors.TEXT_SECONDARY, padding=[20, 10], font=('Segoe UI', 10))
        style.map('Modern.TNotebook.Tab',
            background=[('selected', ThemeColors.BG_CARD), ('active', ThemeColors.BG_CARD)],
            foreground=[('selected', ThemeColors.PRIMARY), ('active', ThemeColors.PRIMARY_DARK)],
            expand=[('selected', [0, 0, 0, 2])])
        
        # Frames
        style.configure('TFrame', background=ThemeColors.BG_MAIN)
        style.configure('Card.TFrame', background=ThemeColors.BG_CARD)
        style.configure('TLabelframe', background=ThemeColors.BG_CARD, borderwidth=1, relief='flat')
        style.configure('TLabelframe.Label', background=ThemeColors.BG_CARD, foreground=ThemeColors.PRIMARY,
                       font=('Segoe UI', 11, 'bold'), padding=[10, 5])
        
        # Labels
        style.configure('TLabel', background=ThemeColors.BG_CARD, foreground=ThemeColors.TEXT_PRIMARY, font=('Segoe UI', 10))
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'), foreground=ThemeColors.TEXT_PRIMARY)
        style.configure('Muted.TLabel', foreground=ThemeColors.TEXT_MUTED, font=('Segoe UI', 9))
        
        # Entry & Combobox
        style.configure('TEntry', fieldbackground=ThemeColors.BG_INPUT, foreground=ThemeColors.TEXT_PRIMARY,
                       borderwidth=1, relief='solid', padding=[8, 6])
        style.configure('TCombobox', fieldbackground=ThemeColors.BG_INPUT, background=ThemeColors.BG_CARD,
                       foreground=ThemeColors.TEXT_PRIMARY, arrowcolor=ThemeColors.PRIMARY, borderwidth=1, padding=[6, 4])
        style.map('TCombobox', fieldbackground=[('readonly', ThemeColors.BG_INPUT)])
        
        # Buttons
        style.configure('TButton', background=ThemeColors.BG_SECONDARY, foreground=ThemeColors.TEXT_PRIMARY,
                       borderwidth=0, padding=[15, 8], font=('Segoe UI', 10))
        style.map('TButton', background=[('active', ThemeColors.BORDER), ('pressed', ThemeColors.BORDER)])
        
        style.configure('Primary.TButton', background=ThemeColors.PRIMARY, foreground='white',
                       borderwidth=0, padding=[20, 10], font=('Segoe UI', 10, 'bold'))
        style.map('Primary.TButton', background=[('active', ThemeColors.PRIMARY_DARK), ('pressed', ThemeColors.PRIMARY_DARK)])
        
        style.configure('Success.TButton', background=ThemeColors.SUCCESS, foreground='white', padding=[15, 8])
        style.map('Success.TButton', background=[('active', '#229954'), ('pressed', '#229954')])
        
        style.configure('Danger.TButton', background=ThemeColors.DANGER, foreground='white', padding=[15, 8])
        style.map('Danger.TButton', background=[('active', '#C0392B'), ('pressed', '#C0392B')])
        
        # Checkbutton & Radiobutton
        for widget in ['TCheckbutton', 'TRadiobutton']:
            style.configure(widget, background=ThemeColors.BG_CARD, foreground=ThemeColors.TEXT_PRIMARY,
                           font=('Segoe UI', 10), padding=[5, 3])
            style.map(widget, background=[('active', ThemeColors.BG_CARD)])
        
        # Treeview
        style.configure('Treeview', background=ThemeColors.BG_CARD, foreground=ThemeColors.TEXT_PRIMARY,
                       fieldbackground=ThemeColors.BG_CARD, borderwidth=0, font=('Segoe UI', 10), rowheight=32)
        style.configure('Treeview.Heading', background=ThemeColors.BG_SECONDARY, foreground=ThemeColors.TEXT_PRIMARY,
                       font=('Segoe UI', 10, 'bold'), borderwidth=0, padding=[10, 8])
        style.map('Treeview', background=[('selected', ThemeColors.PRIMARY_LIGHT)], foreground=[('selected', 'white')])
        
        # Scrollbar & Progressbar
        style.configure('TScrollbar', background=ThemeColors.BG_SECONDARY, troughcolor=ThemeColors.BG_CARD, borderwidth=0)
        style.configure('TProgressbar', background=ThemeColors.PRIMARY, troughcolor=ThemeColors.BG_SECONDARY, thickness=8)
        style.configure('TSeparator', background=ThemeColors.BORDER)
    
    def create_demo_indicator(self):
        """Create demo indicator banner"""
        demo_frame = tk.Frame(self.main_container, bg=ThemeColors.DEMO_BAR, height=36)
        demo_frame.pack(fill='x', side='top', pady=(0, 12))
        demo_frame.pack_propagate(False)
        
        demo_info = self.demo_manager.get_demo_info()
        tk.Label(demo_frame, text=f"⏱  DEMO VERSION  •  {demo_info['remaining_hours']}h {demo_info['remaining_minutes']}m remaining",
                bg=ThemeColors.DEMO_BAR, fg='white', font=('Segoe UI', 10, 'bold')).pack(expand=True)
    
    def show_demo_expired_screen(self):
        """Show demo expired lock screen"""
        for widget in self.root.winfo_children():
            widget.destroy()
        self.root.geometry("600x400")
        
        lock_frame = tk.Frame(self.root, bg='#2C3E50')
        lock_frame.pack(fill='both', expand=True)
        
        tk.Label(lock_frame, text="🔒", font=('Arial', 72), bg='#2C3E50', fg='white').pack(pady=40)
        tk.Label(lock_frame, text="Demo Period Ended", font=('Arial', 24, 'bold'), bg='#2C3E50', fg='white').pack(pady=10)
        tk.Label(lock_frame, text="Please contact the developer to continue using this application.",
                font=('Arial', 12), bg='#2C3E50', fg='#BDC3C7', wraplength=400).pack(pady=20)
        tk.Button(lock_frame, text="Close", command=self.root.destroy, font=('Arial', 12),
                 bg='#E74C3C', fg='white', padx=30, pady=10, relief='flat', cursor='hand2').pack(pady=20)

        
    def create_barangay_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  📍 Barangay  ")
        
        content = ttk.Frame(tab, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "Barangay Management", "Add and manage barangay profiles")
        
        # Input frame
        input_frame = ttk.LabelFrame(content, text="Add / Update Barangay", padding=25)
        input_frame.pack(fill='x', pady=(0, 15))
        
        form_frame = ttk.Frame(input_frame)
        form_frame.pack(fill='x')
        
        ttk.Label(form_frame, text="Barangay Name:").grid(row=0, column=0, sticky='w', pady=10)
        self.brgy_name_entry = ttk.Entry(form_frame, width=35)
        self.brgy_name_entry.grid(row=0, column=1, pady=10, padx=(15, 0))
        
        ttk.Label(form_frame, text="Initial Population:").grid(row=1, column=0, sticky='w', pady=10)
        self.brgy_pop_entry = ttk.Entry(form_frame, width=35)
        self.brgy_pop_entry.grid(row=1, column=1, pady=10, padx=(15, 0))
        
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(pady=(15, 5))
        ttk.Button(btn_frame, text="✓  Add Barangay", command=self.add_barangay, style='Primary.TButton').pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear_barangay_form).pack(side='left', padx=5)
        
        # List frame
        list_frame = ttk.LabelFrame(content, text="Registered Barangays", padding=20)
        list_frame.pack(fill='both', expand=True)
        
        self.brgy_tree = self.create_scrollable_tree(list_frame, ('ID', 'Name', 'Initial Population'), 
                                                      {'ID': 180, 'Name': 180, 'Initial Population': 180})
        
        action_bar = ttk.Frame(list_frame)
        action_bar.pack(fill='x', pady=(15, 0))
        ttk.Button(action_bar, text="⟳  Refresh List", command=self.refresh_barangay_list).pack(side='left')
        
        self.refresh_barangay_list()
    
    def create_yearly_data_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  📊 Data Entry  ")
        
        content = ttk.Frame(tab, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "Yearly Data Entry", "Record annual leptospirosis data and risk factors")
        
        # Main form
        input_frame = ttk.LabelFrame(content, text="Record Data", padding=25)
        input_frame.pack(fill='x')
        
        # Two-column layout
        basic_frame = ttk.Frame(input_frame)
        basic_frame.pack(fill='x', pady=(0, 15))
        
        left_col = ttk.Frame(basic_frame)
        left_col.pack(side='left', fill='x', expand=True, padx=(0, 20))
        
        ttk.Label(left_col, text="Barangay:").pack(anchor='w', pady=(0, 5))
        self.year_brgy_combo = ttk.Combobox(left_col, width=30, state='readonly')
        self.year_brgy_combo.pack(fill='x', pady=(0, 12))
        
        ttk.Label(left_col, text="Year:").pack(anchor='w', pady=(0, 5))
        self.year_entry = ttk.Entry(left_col, width=30)
        self.year_entry.pack(fill='x', pady=(0, 12))
        
        right_col = ttk.Frame(basic_frame)
        right_col.pack(side='left', fill='x', expand=True)
        
        ttk.Label(right_col, text="Population:").pack(anchor='w', pady=(0, 5))
        self.year_pop_entry = ttk.Entry(right_col, width=30)
        self.year_pop_entry.pack(fill='x', pady=(0, 12))
        
        ttk.Label(right_col, text="Total Cases:").pack(anchor='w', pady=(0, 5))
        self.cases_entry = ttk.Entry(right_col, width=30)
        self.cases_entry.pack(fill='x', pady=(0, 12))
        
        ttk.Separator(input_frame, orient='horizontal').pack(fill='x', pady=15)
        
        # Risk factors
        risk_frame = ttk.Frame(input_frame)
        risk_frame.pack(fill='x')
        ttk.Label(risk_frame, text="Risk Factor Assessment", font=('Segoe UI', 11, 'bold'), 
                 foreground=ThemeColors.PRIMARY).pack(anchor='w', pady=(0, 15))
        
        risk_columns = ttk.Frame(risk_frame)
        risk_columns.pack(fill='x')
        
        # Flood factors
        flood_subframe = ttk.LabelFrame(risk_columns, text="🌊 Flood Factors", padding=15)
        flood_subframe.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        self.is_flooded_var, self.is_evac_var, self.is_damaged_var = tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()
        for text, var in [("Flooded area (+2.0)", self.is_flooded_var), 
                         ("Evacuation needed (+3.0)", self.is_evac_var),
                         ("Infrastructure damage (+5.0)", self.is_damaged_var)]:
            ttk.Checkbutton(flood_subframe, text=text, variable=var, command=self.update_composite_risk).pack(anchor='w', pady=4)
        
        # Sanitation factors
        vector_subframe = ttk.LabelFrame(risk_columns, text="🐀 Sanitation Factors", padding=15)
        vector_subframe.pack(side='left', fill='both', expand=True, padx=(10, 0))
        
        self.irregular_garbage_var, self.high_rodents_var, self.clogged_drainage_var = tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()
        for text, var in [("Irregular garbage collection (+0.5×)", self.irregular_garbage_var),
                         ("High rodent/stray presence (+0.5×)", self.high_rodents_var),
                         ("Clogged/open drainage (+0.5×)", self.clogged_drainage_var)]:
            ttk.Checkbutton(vector_subframe, text=text, variable=var, command=self.update_composite_risk).pack(anchor='w', pady=4)
        
        # Results display
        results_frame = ttk.Frame(input_frame)
        results_frame.pack(fill='x', pady=20)
        
        scores_row = ttk.Frame(results_frame)
        scores_row.pack()
        
        ttk.Label(scores_row, text="Flood Score:", style='Muted.TLabel').pack(side='left', padx=(0, 5))
        self.flood_score_label = ttk.Label(scores_row, text="0.0", font=('Segoe UI', 10, 'bold'))
        self.flood_score_label.pack(side='left', padx=(0, 30))
        ttk.Label(scores_row, text="Multiplier:", style='Muted.TLabel').pack(side='left', padx=(0, 5))
        self.vector_score_label = ttk.Label(scores_row, text="1.0×", font=('Segoe UI', 10, 'bold'))
        self.vector_score_label.pack(side='left')
        
        composite_row = ttk.Frame(results_frame)
        composite_row.pack(pady=(10, 0))
        ttk.Label(composite_row, text="Composite Risk Index:", font=('Segoe UI', 11)).pack(side='left', padx=(0, 10))
        self.composite_risk_label = ttk.Label(composite_row, text="0.0", font=('Segoe UI', 16, 'bold'), foreground=ThemeColors.DANGER)
        self.composite_risk_label.pack(side='left')
        
        # Buttons
        btn_frame = ttk.Frame(input_frame)
        btn_frame.pack(pady=(20, 5))
        self.save_data_btn = ttk.Button(btn_frame, text="✓  Save Data", command=self.add_yearly_data, style='Primary.TButton')
        self.save_data_btn.pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear Form", command=self.clear_yearly_form).pack(side='left', padx=5)
        
        self.refresh_barangay_combo()
    
    def create_import_csv_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  📁 Import CSV  ")
        
        # Scrollable canvas
        canvas = tk.Canvas(tab, bg=ThemeColors.BG_MAIN, highlightthickness=0)
        scrollbar = ttk.Scrollbar(tab, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Card.TFrame')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        content = ttk.Frame(scrollable_frame, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "Import CSV Data", "Bulk import data from CSV files")
        
        # Instructions
        instructions_frame = ttk.LabelFrame(content, text="📋 CSV Format Guide", padding=15)
        instructions_frame.pack(fill='x', pady=(0, 15))
        
        guide_text = """Required Columns: Barangay, Year, Population, Cases, Flooded, Evacuation, Infrastructure_Damage, Irregular_Garbage, High_Rodents, Clogged_Drainage

Example: San Jose,2022,15000,12,Yes,No,Yes,Yes,No,Yes

Notes: Use Yes/No or 1/0 for risk factors • Composite Risk Index calculated automatically"""
        
        guide_label = tk.Text(instructions_frame, height=4, width=110, wrap='word', font=('Consolas', 9), relief='flat')
        guide_label.insert('1.0', guide_text)
        guide_label.config(state='disabled', bg=ThemeColors.BG_INPUT)
        guide_label.pack(fill='both', expand=True)
        
        # File selection
        file_frame = ttk.LabelFrame(content, text="📂 Select CSV File", padding=20)
        file_frame.pack(fill='x', pady=(0, 15))
        
        file_control = ttk.Frame(file_frame)
        file_control.pack(fill='x')
        
        ttk.Label(file_control, text="File:").pack(side='left', padx=(0, 10))
        self.csv_file_path = tk.StringVar()
        ttk.Entry(file_control, textvariable=self.csv_file_path, width=55, state='readonly').pack(side='left', padx=(0, 10))
        ttk.Button(file_control, text="Browse...", command=self.browse_csv_file).pack(side='left', padx=(0, 10))
        ttk.Button(file_control, text="📥 Download Template", command=self.download_csv_template).pack(side='left')
        
        progress_frame = ttk.Frame(file_frame)
        progress_frame.pack(fill='x', pady=(15, 0))
        self.csv_progress = ttk.Progressbar(progress_frame, mode='determinate', length=400)
        self.csv_progress.pack(side='left', padx=(0, 15))
        self.csv_progress_label = ttk.Label(progress_frame, text="", foreground=ThemeColors.INFO)
        self.csv_progress_label.pack(side='left')
        
        # Preview
        preview_frame = ttk.LabelFrame(content, text="👁 Data Preview", padding=20)
        preview_frame.pack(fill='both', expand=True)
        
        preview_controls = ttk.Frame(preview_frame)
        preview_controls.pack(fill='x', pady=(0, 15))
        ttk.Button(preview_controls, text="⚡ Load & Preview", command=self.load_csv_preview, style='Primary.TButton').pack(side='left', padx=(0, 10))
        ttk.Button(preview_controls, text="Clear Preview", command=self.clear_csv_preview).pack(side='left')
        self.csv_status_label = ttk.Label(preview_controls, text="No file loaded", style='Muted.TLabel')
        self.csv_status_label.pack(side='left', padx=(25, 0))
        
        columns = ('Row', 'Barangay', 'Year', 'Population', 'Cases', 'Composite_Risk', 'Status')
        col_widths = {'Row': 50, 'Status': 180}
        self.csv_preview_tree = self.create_scrollable_tree(preview_frame, columns, col_widths, height=6)
        
        # Import button
        import_frame = ttk.Frame(preview_frame)
        import_frame.pack(fill='x', pady=(15, 0))
        self.import_btn = ttk.Button(import_frame, text="✓  Import Data to Database", command=self.import_csv_data, 
                                    state='disabled', style='Success.TButton')
        self.import_btn.pack(side='left', padx=(0, 15))
        ttk.Label(import_frame, text="⚠ This will add/update records in the database", 
                 foreground=ThemeColors.WARNING, font=('Segoe UI', 9, 'italic')).pack(side='left')
        
        self.csv_parsed_data = []
    
    def browse_csv_file(self):
        """Open file dialog to select CSV file"""
        filename = filedialog.askopenfilename(title="Select CSV File", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if filename:
            self.csv_file_path.set(filename)
            self.csv_status_label.config(text="File selected. Click 'Load & Preview' to validate.", foreground=ThemeColors.INFO)
            self.import_btn.config(state='disabled')
    
    def download_csv_template(self):
        """Download a CSV template file"""
        filename = filedialog.asksaveasfilename(title="Save CSV Template", defaultextension=".csv",
                                                filetypes=[("CSV Files", "*.csv")], initialfile="leptospirosis_data_template.csv")
        if filename:
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(['Barangay', 'Year', 'Population', 'Cases', 'Flooded', 'Evacuation', 
                                   'Infrastructure_Damage', 'Irregular_Garbage', 'High_Rodents', 'Clogged_Drainage'])
                    writer.writerow(['Sample Barangay', '2023', '10000', '5', 'Yes', 'No', 'No', 'Yes', 'No', 'Yes'])
                    writer.writerow(['Sample Barangay', '2024', '10200', '3', 'No', 'No', 'No', 'No', 'No', 'No'])
                messagebox.showinfo("Success", f"Template saved to:\n{filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save template:\n{str(e)}")
    
    def clear_csv_preview(self):
        """Clear the preview tree"""
        for item in self.csv_preview_tree.get_children():
            self.csv_preview_tree.delete(item)
        self.csv_status_label.config(text="Preview cleared", foreground='gray')
        self.csv_parsed_data = []
        self.import_btn.config(state='disabled')
        self.csv_progress['value'] = 0
        self.csv_progress_label.config(text="")
    
    def _parse_bool(self, value):
        """Parse boolean values from CSV"""
        return str(value).strip().lower() in ('yes', 'y', '1', 'true', 't') if value else False
    
    def load_csv_preview(self):
        """Load and validate CSV file, show preview"""
        filepath = self.csv_file_path.get()
        if not filepath:
            messagebox.showwarning("No File", "Please select a CSV file first")
            return
        
        self.clear_csv_preview()
        self.csv_progress_label.config(text="Reading file...")
        self.root.update_idletasks()
        
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                total_rows = sum(1 for _ in f) - 1
            
            self.csv_progress_label.config(text=f"Validating {total_rows} rows...")
            self.root.update_idletasks()
            
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                reader.fieldnames = [h.strip().lower().replace(' ', '_') for h in reader.fieldnames]
                
                required = {'barangay', 'year', 'population', 'cases', 'flooded', 'evacuation', 
                           'infrastructure_damage', 'irregular_garbage', 'high_rodents', 'clogged_drainage'}
                missing = required - set(reader.fieldnames)
                if missing:
                    self.csv_progress['value'] = 0
                    self.csv_progress_label.config(text="")
                    messagebox.showerror("Invalid Format", f"Missing columns: {', '.join(missing)}")
                    return
                
                valid_count, error_count, parsed_data = 0, 0, []
                
                for row_num, row in enumerate(reader, 2):
                    if row_num % 10 == 0 or row_num == total_rows + 1:
                        self.csv_progress['value'] = (row_num / max(total_rows, 1)) * 100
                        self.csv_progress_label.config(text=f"Processing {row_num-1}/{total_rows} rows...")
                        self.root.update_idletasks()
                    
                    if not any(row.values()):
                        continue
                    
                    try:
                        brgy, year = row['barangay'].strip(), int(row['year'])
                        population, cases = int(row['population']), int(row['cases'])
                        
                        if not brgy or population <= 0 or cases < 0:
                            raise ValueError("Invalid data")
                        
                        risk_factors = {k: self._parse_bool(row[k]) for k in 
                                       ['flooded', 'evacuation', 'infrastructure_damage', 'irregular_garbage', 'high_rodents', 'clogged_drainage']}
                        composite, _, _ = self.calc_composite_risk(risk_factors['flooded'], risk_factors['evacuation'],
                                                                   risk_factors['infrastructure_damage'], risk_factors['irregular_garbage'],
                                                                   risk_factors['high_rodents'], risk_factors['clogged_drainage'])
                        
                        parsed_data.append({'row_num': row_num, 'barangay': brgy, 'year': year, 'population': population,
                                           'cases': cases, 'composite_risk': composite, **{f'is_{k}' if k in ['flooded', 'evacuation'] else k: v 
                                           for k, v in risk_factors.items()}, 'is_infrastructure_damage': risk_factors['infrastructure_damage']})
                        self.csv_preview_tree.insert('', 'end', values=(row_num, brgy, year, population, cases, f"{composite:.2f}", 'Valid ✓'), tags=('valid',))
                        valid_count += 1
                    except Exception as e:
                        error_count += 1
                        self.csv_preview_tree.insert('', 'end', values=(row_num, row.get('barangay', '?'), row.get('year', '?'), 
                                                                        row.get('population', '?'), row.get('cases', '?'), '?', f'Error: {e}'), tags=('error',))
                
                self.csv_preview_tree.tag_configure('valid', background='#d4edda')
                self.csv_preview_tree.tag_configure('error', background='#f8d7da')
                self.csv_progress['value'] = 100
                self.csv_progress_label.config(text="Validation complete!")
                
                if error_count > 0:
                    self.csv_status_label.config(text=f"Loaded: {valid_count} valid, {error_count} errors", foreground='red')
                else:
                    self.csv_status_label.config(text=f"Loaded: {valid_count} valid rows. Ready to import.", foreground='green')
                    self.import_btn.config(state='normal')
                    self.csv_parsed_data = parsed_data
                    
        except Exception as e:
            self.csv_progress['value'] = 0
            self.csv_progress_label.config(text="Error occurred")
            messagebox.showerror("File Error", f"Failed to read CSV file:\n{str(e)}")
    
    def _parse_bool(self, value):
        """Parse boolean values from CSV"""
        return str(value).strip().lower() in ('yes', 'y', '1', 'true', 't') if value else False
    
    def import_csv_data(self):
        """Import validated CSV data into database"""
        if not self.csv_parsed_data:
            messagebox.showwarning("No Data", "No valid data to import")
            return
        
        if not messagebox.askyesno("Confirm Import", f"Import {len(self.csv_parsed_data)} records?\nExisting records will be updated."):
            return
        
        self.csv_progress['value'] = 0
        self.csv_progress_label.config(text="Starting import...")
        
        success_count, errors = 0, []
        
        try:
            for idx, data in enumerate(self.csv_parsed_data, 1):
                self.csv_progress['value'] = (idx / len(self.csv_parsed_data)) * 100
                self.csv_progress_label.config(text=f"Importing {idx}/{len(self.csv_parsed_data)}...")
                self.root.update_idletasks()
                
                try:
                    self.db.cursor.execute("SELECT id FROM barangays WHERE name=?", (data['barangay'],))
                    if not self.db.cursor.fetchone():
                        self.db.add_barangay(data['barangay'], data['population'])
                    
                    success, msg = self.db.add_year_data(data['barangay'], data['year'], data['population'], data['cases'],
                        data['composite_risk'], int(data.get('is_flooded', 0)), int(data.get('is_evacuation', 0)),
                        int(data.get('is_infrastructure_damage', 0)), int(data.get('irregular_garbage', 0)),
                        int(data.get('high_rodents', 0)), int(data.get('clogged_drainage', 0)))
                    
                    if success:
                        success_count += 1
                    else:
                        errors.append(f"Row {data['row_num']}: {msg}")
                except Exception as e:
                    errors.append(f"Row {data['row_num']}: {str(e)}")
            
            self.csv_progress['value'] = 100
            self.csv_progress_label.config(text="Import complete!")
            
            msg = f"✓ Imported: {success_count} records"
            if errors:
                msg += f"\n✗ Failed: {len(errors)}\n\n" + "\n".join(errors[:5])
                messagebox.showwarning("Import Completed with Errors", msg)
            else:
                messagebox.showinfo("Import Successful", msg)
            
            self.refresh_all_combos()
            self.refresh_barangay_list()
            self.refresh_data_view()
            self.clear_csv_preview()
            self.csv_file_path.set('')
            
        except Exception as e:
            self.csv_progress['value'] = 0
            messagebox.showerror("Import Failed", str(e))
    
    def create_simulation_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  🔬 Simulation  ")
        
        content = ttk.Frame(tab, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "SEIWR Simulation", "Run epidemiological model simulations")
        
        control_frame = ttk.LabelFrame(content, text="Simulation Parameters", padding=25)
        control_frame.pack(fill='x', pady=(0, 15))
        
        # Basic parameters
        basic_frame = ttk.Frame(control_frame)
        basic_frame.pack(fill='x', pady=(0, 15))
        
        left_col = ttk.Frame(basic_frame)
        left_col.pack(side='left', fill='x', expand=True, padx=(0, 30))
        
        ttk.Label(left_col, text="Barangay:").pack(anchor='w', pady=(0, 5))
        self.sim_brgy_combo = ttk.Combobox(left_col, width=30, state='readonly')
        self.sim_brgy_combo.pack(fill='x', pady=(0, 12))
        
        ttk.Label(left_col, text="Year (for initial data):").pack(anchor='w', pady=(0, 5))
        self.sim_year_entry = ttk.Entry(left_col, width=30)
        self.sim_year_entry.pack(fill='x', pady=(0, 12))
        
        right_col = ttk.Frame(basic_frame)
        right_col.pack(side='left', fill='x', expand=True)
        
        ttk.Label(right_col, text="Simulation Days:").pack(anchor='w', pady=(0, 5))
        self.sim_days_entry = ttk.Entry(right_col, width=30)
        self.sim_days_entry.insert(0, "365")
        self.sim_days_entry.pack(fill='x', pady=(0, 12))
        
        ttk.Separator(control_frame, orient='horizontal').pack(fill='x', pady=15)
        ttk.Label(control_frame, text="⚙ Advanced Parameters", font=('Segoe UI', 10, 'bold'), 
                 foreground=ThemeColors.TEXT_SECONDARY).pack(anchor='w', pady=(0, 15))
        
        param_grid = ttk.Frame(control_frame)
        param_grid.pack(fill='x')
        
        params = [("Infection Coefficient:", "0.00005", 0, 0), ("Incubation Rate (σ):", "0.1", 0, 2),
                  ("Water Contamination (ξ):", "0.01", 1, 0), ("Flood Decay (δ):", "0.1", 1, 2)]
        
        self.i_coef_entry, self.sigma_entry, self.xi_entry, self.delta_entry = [None]*4
        entries = [self.i_coef_entry, self.sigma_entry, self.xi_entry, self.delta_entry]
        
        for i, (label, default, row, col) in enumerate(params):
            ttk.Label(param_grid, text=label).grid(row=row, column=col, sticky='w', pady=8, padx=(0, 10))
            entry = ttk.Entry(param_grid, width=18)
            entry.insert(0, default)
            entry.grid(row=row, column=col+1, pady=8, padx=(0, 30) if col == 0 else 0)
            if i == 0: self.i_coef_entry = entry
            elif i == 1: self.sigma_entry = entry
            elif i == 2: self.xi_entry = entry
            else: self.delta_entry = entry
        
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack(pady=(20, 5))
        ttk.Button(btn_frame, text="▶  Run Simulation", command=self.run_simulation, style='Primary.TButton').pack()
        
        self.plot_frame = ttk.LabelFrame(content, text="📈 Simulation Results", padding=20)
        self.plot_frame.pack(fill='both', expand=True)
        ttk.Label(self.plot_frame, text="Configure parameters and click 'Run Simulation' to see results", style='Muted.TLabel').pack(expand=True)
        
        self.refresh_sim_combo()
    
    def create_entry_var(self, default_value):
        return default_value
    
    def create_prediction_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  📉 Prediction  ")
        
        content = ttk.Frame(tab, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "Trend Prediction", "Forecast future cases with scenario analysis")
        
        main_container = ttk.Frame(content, style='Card.TFrame')
        main_container.pack(fill='both', expand=True)
        
        # Left side
        left_frame = ttk.Frame(main_container, style='Card.TFrame')
        left_frame.pack(side='left', fill='both', padx=(0, 15), expand=False)
        left_frame.configure(width=380)
        
        control_frame = ttk.LabelFrame(left_frame, text="Scenario Settings", padding=20)
        control_frame.pack(fill='x', pady=(0, 15))
        
        ttk.Label(control_frame, text="Barangay:").pack(anchor='w', pady=(0, 5))
        self.pred_brgy_combo = ttk.Combobox(control_frame, width=35, state='readonly')
        self.pred_brgy_combo.pack(fill='x', pady=(0, 12))
        self.pred_brgy_combo.bind('<<ComboboxSelected>>', lambda e: self.load_baseline_data())
        
        ttk.Label(control_frame, text="Projected Population:").pack(anchor='w', pady=(0, 5))
        self.pred_pop_entry = ttk.Entry(control_frame, width=35)
        self.pred_pop_entry.pack(fill='x', pady=(0, 15))
        
        # Flood scenario
        flood_frame = ttk.LabelFrame(control_frame, text="🌊 Flood Risk Scenario", padding=15)
        flood_frame.pack(fill='x', pady=(0, 15))
        
        self.pred_flood_score_var = tk.DoubleVar(value=0.0)
        for text, val in [("No Flood (0)", 0.0), ("Minor Flood (2)", 2.0), 
                          ("Moderate + Evacuation (5)", 5.0), ("Severe + Damage (10)", 10.0)]:
            ttk.Radiobutton(flood_frame, text=text, variable=self.pred_flood_score_var, 
                           value=val, command=self.update_pred_composite).pack(anchor='w', pady=3)
        
        # Sanitation scenario
        vector_frame = ttk.LabelFrame(control_frame, text="🐀 Sanitation Scenario", padding=15)
        vector_frame.pack(fill='x', pady=(0, 15))
        
        self.pred_garbage_var, self.pred_rodents_var, self.pred_drainage_var = tk.BooleanVar(), tk.BooleanVar(), tk.BooleanVar()
        for text, var in [("Irregular Garbage Collection", self.pred_garbage_var),
                          ("High Rodent/Stray Presence", self.pred_rodents_var), 
                          ("Clogged/Open Drainage", self.pred_drainage_var)]:
            ttk.Checkbutton(vector_frame, text=text, variable=var, command=self.update_pred_composite).pack(anchor='w', pady=3)
        
        composite_row = ttk.Frame(control_frame)
        composite_row.pack(pady=10)
        ttk.Label(composite_row, text="Composite Risk Index:", font=('Segoe UI', 10)).pack(side='left', padx=(0, 10))
        self.pred_composite_label = ttk.Label(composite_row, text="0.0", font=('Segoe UI', 14, 'bold'), foreground=ThemeColors.DANGER)
        self.pred_composite_label.pack(side='left')
        
        ttk.Button(control_frame, text="▶  Generate Prediction", command=self.run_prediction, style='Primary.TButton').pack(fill='x', pady=(15, 0))
        
        results_frame = ttk.LabelFrame(left_frame, text="📊 Prediction Results", padding=20)
        results_frame.pack(fill='both', expand=True)
        
        self.pred_result_label = ttk.Label(results_frame, text="Configure scenario and generate prediction",
                                          font=('Segoe UI', 12, 'bold'), foreground=ThemeColors.TEXT_SECONDARY)
        self.pred_result_label.pack(pady=(10, 15))
        
        # Right side
        right_frame = ttk.Frame(main_container, style='Card.TFrame')
        right_frame.pack(side='right', fill='both', expand=True)
        
        self.pred_plot_frame = ttk.LabelFrame(right_frame, text="📈 Trend Visualization", padding=15)
        self.pred_plot_frame.pack(fill='both', expand=True)
        ttk.Label(self.pred_plot_frame, text="Generate a prediction to view the trend chart", style='Muted.TLabel').pack(expand=True)
        
        # Mitigation button
        mitigation_btn_frame = ttk.Frame(right_frame, style='Card.TFrame')
        mitigation_btn_frame.pack(fill='x', pady=(15, 0))
        
        self.view_mitigation_btn = ttk.Button(mitigation_btn_frame, text="💡 View Mitigation Actions",
                                             command=self.show_mitigation_modal, state='disabled', style='Success.TButton')
        self.view_mitigation_btn.pack(pady=5)
        ttk.Label(mitigation_btn_frame, text="Click to view detailed risk reduction strategies",
                 style='Muted.TLabel', font=('Segoe UI', 9, 'italic')).pack()
        
        self.refresh_pred_combo()
    
    def create_view_data_tab(self):
        tab = ttk.Frame(self.notebook, style='Card.TFrame')
        self.notebook.add(tab, text="  📋 View Data  ")
        
        content = ttk.Frame(tab, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=25, pady=20)
        
        self.create_tab_header(content, "Data Overview", "View, filter, and manage all recorded data")
        
        # Filter bar
        filter_frame = ttk.LabelFrame(content, text="🔍 Filter & Actions", padding=15)
        filter_frame.pack(fill='x', pady=(0, 15))
        
        filter_row = ttk.Frame(filter_frame)
        filter_row.pack(fill='x')
        
        ttk.Label(filter_row, text="Filter by Barangay:").pack(side='left', padx=(0, 10))
        self.view_brgy_combo = ttk.Combobox(filter_row, width=25, state='readonly')
        self.view_brgy_combo.pack(side='left', padx=(0, 15))
        self.view_brgy_combo.bind('<<ComboboxSelected>>', lambda e: self.refresh_data_view())
        
        ttk.Button(filter_row, text="Show All", command=self.show_all_data).pack(side='left', padx=5)
        ttk.Button(filter_row, text="⟳  Refresh", command=self.refresh_data_view).pack(side='left', padx=5)
        ttk.Frame(filter_row).pack(side='left', expand=True)
        ttk.Button(filter_row, text="✎  Edit Selected", command=self.edit_selected_data).pack(side='left', padx=5)
        ttk.Button(filter_row, text="🗑  Delete Selected", command=self.delete_selected_data, style='Danger.TButton').pack(side='left', padx=5)
        
        # Data display
        list_frame = ttk.LabelFrame(content, text="📊 Recorded Data", padding=20)
        list_frame.pack(fill='both', expand=True)
        
        col_widths = {'Barangay': 200, 'Year': 100, 'Population': 150, 'Cases': 100, 'Composite Risk': 150}
        self.data_tree = self.create_scrollable_tree(list_frame, tuple(col_widths.keys()), col_widths, height=18)
        
        self.refresh_view_combo()
        self.refresh_data_view()
    
    # --- CALLBACK METHODS ---
    
    def add_barangay(self):
        name, pop_str = self.brgy_name_entry.get().strip(), self.brgy_pop_entry.get().strip()
        if not name or not pop_str:
            messagebox.showwarning("Input Error", "Please fill all fields")
            return
        try:
            population = int(pop_str)
            if population <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Population must be a positive integer")
            return
        
        success, message = self.db.add_barangay(name, population)
        if success:
            messagebox.showinfo("Success", message)
            self.clear_barangay_form()
            self.refresh_barangay_list()
            self.refresh_all_combos()
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
        if barangays: self.year_brgy_combo.current(0)
    
    def refresh_sim_combo(self):
        barangays = [b[1] for b in self.db.get_barangays()]
        self.sim_brgy_combo['values'] = barangays
        if barangays: self.sim_brgy_combo.current(0)
    
    def refresh_pred_combo(self):
        barangays = [b[1] for b in self.db.get_barangays()]
        self.pred_brgy_combo['values'] = barangays
        if barangays:
            self.pred_brgy_combo.current(0)
            self.load_baseline_data()
    
    def refresh_view_combo(self):
        self.view_brgy_combo['values'] = ['All'] + [b[1] for b in self.db.get_barangays()]
        self.view_brgy_combo.current(0)
    
    def update_pred_composite(self):
        """Update composite risk index for prediction scenario"""
        _, _, v_score = self.calc_composite_risk(False, False, False, self.pred_garbage_var.get(),
                                                  self.pred_rodents_var.get(), self.pred_drainage_var.get())
        composite = self.pred_flood_score_var.get() * v_score
        self.pred_composite_label.config(text=f"{composite:.2f}")
    
    def update_composite_risk(self):
        """Calculate composite risk index based on flood and sanitation factors"""
        composite, f_score, v_score = self.calc_composite_risk(
            self.is_flooded_var.get(), self.is_evac_var.get(), self.is_damaged_var.get(),
            self.irregular_garbage_var.get(), self.high_rodents_var.get(), self.clogged_drainage_var.get())
        self.flood_score_label.config(text=f"{f_score:.1f}")
        self.vector_score_label.config(text=f"{v_score:.1f}x")
        self.composite_risk_label.config(text=f"{composite:.2f}")
    
    def add_yearly_data(self):
        brgy, year_str = self.year_brgy_combo.get(), self.year_entry.get().strip()
        pop_str, cases_str = self.year_pop_entry.get().strip(), self.cases_entry.get().strip()
        
        if not all([brgy, year_str, pop_str, cases_str]):
            messagebox.showwarning("Input Error", "Please fill all required fields")
            return
        try:
            year, population, cases = int(year_str), int(pop_str), int(cases_str)
            if cases < 0 or population <= 0: raise ValueError
        except ValueError:
            messagebox.showerror("Input Error", "Invalid input. Population must be positive, Cases non-negative")
            return
        
        composite, f_score, v_score = self.calc_composite_risk(
            self.is_flooded_var.get(), self.is_evac_var.get(), self.is_damaged_var.get(),
            self.irregular_garbage_var.get(), self.high_rodents_var.get(), self.clogged_drainage_var.get())
        
        risk_flags = [int(v.get()) for v in [self.is_flooded_var, self.is_evac_var, self.is_damaged_var,
                                              self.irregular_garbage_var, self.high_rodents_var, self.clogged_drainage_var]]
        
        success, message = self.db.add_year_data(brgy, year, population, cases, composite, *risk_flags)
        if success:
            msg = f"Data for {brgy} ({year}) updated successfully." if self.edit_mode else message
            messagebox.showinfo("Success", msg)
            self.clear_yearly_form()
            self.refresh_data_view()
        else:
            messagebox.showerror("Error", message)
    
    def clear_yearly_form(self):
        for entry in [self.year_entry, self.year_pop_entry, self.cases_entry]:
            entry.delete(0, tk.END)
        for var in [self.is_flooded_var, self.is_evac_var, self.is_damaged_var,
                    self.irregular_garbage_var, self.high_rodents_var, self.clogged_drainage_var]:
            var.set(False)
        self.flood_score_label.config(text="0.0")
        self.vector_score_label.config(text="1.0x")
        self.composite_risk_label.config(text="0.0")
        self.edit_mode, self.edit_data = False, None
        self.save_data_btn.config(text="Save Data")
    
    def refresh_data_view(self):
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
        selected = self.view_brgy_combo.get()
        data = self.db.get_yearly_data() if selected == 'All' else self.db.get_yearly_data(selected)
        for row in data:
            self.data_tree.insert('', 'end', values=row[:5])
    
    def show_all_data(self):
        self.view_brgy_combo.current(0)
        self.refresh_data_view()
    
    def delete_selected_data(self):
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a record to delete")
            return
        values = self.data_tree.item(selection[0])['values']
        brgy_name, year = values[0], values[1]
        if messagebox.askyesno("Confirm Delete", f"Delete data for {brgy_name} ({year})?\n\nThis cannot be undone."):
            success, message = self.db.delete_yearly_data(brgy_name, year)
            if success:
                messagebox.showinfo("Success", message)
                self.refresh_data_view()
            else:
                messagebox.showerror("Error", message)
    
    def edit_selected_data(self):
        selection = self.data_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a record to edit")
            return
        values = self.data_tree.item(selection[0])['values']
        brgy_name, year = values[0], values[1]
        
        full_data = self.db.get_yearly_data(brgy_name)
        record = next((r for r in full_data if r[1] == year), None)
        if not record:
            messagebox.showerror("Error", "Could not find record data")
            return
        
        self.edit_mode = True
        self.edit_data = dict(zip(['barangay', 'year', 'population', 'cases', 'composite_risk',
                                    'is_flooded', 'is_evacuation', 'is_infrastructure_damage',
                                    'irregular_garbage', 'high_rodents', 'clogged_drainage'], record))
        self.notebook.select(1)
        self.populate_yearly_form()
        self.save_data_btn.config(text="Update Data")
    
    def populate_yearly_form(self):
        if not self.edit_data: return
        temp_data = self.edit_data.copy()
        
        for entry in [self.year_entry, self.year_pop_entry, self.cases_entry]:
            entry.delete(0, tk.END)
        for var in [self.is_flooded_var, self.is_evac_var, self.is_damaged_var,
                    self.irregular_garbage_var, self.high_rodents_var, self.clogged_drainage_var]:
            var.set(False)
        
        self.edit_data, self.edit_mode = temp_data, True
        
        barangays = [b[1] for b in self.db.get_barangays()]
        if self.edit_data['barangay'] in barangays:
            self.year_brgy_combo.current(barangays.index(self.edit_data['barangay']))
        
        self.year_entry.insert(0, str(self.edit_data['year']))
        self.year_pop_entry.insert(0, str(self.edit_data['population']))
        self.cases_entry.insert(0, str(self.edit_data['cases']))
        
        self.is_flooded_var.set(bool(self.edit_data.get('is_flooded', 0)))
        self.is_evac_var.set(bool(self.edit_data.get('is_evacuation', 0)))
        self.is_damaged_var.set(bool(self.edit_data.get('is_infrastructure_damage', 0)))
        self.irregular_garbage_var.set(bool(self.edit_data.get('irregular_garbage', 0)))
        self.high_rodents_var.set(bool(self.edit_data.get('high_rodents', 0)))
        self.clogged_drainage_var.set(bool(self.edit_data.get('clogged_drainage', 0)))
        self.update_composite_risk()
    
    def load_baseline_data(self):
        brgy = self.pred_brgy_combo.get()
        if not brgy: return
        history = self.db.get_barangay_history(brgy)
        if history:
            last_data = history[-1]
            self.pred_pop_entry.delete(0, tk.END)
            self.pred_pop_entry.insert(0, str(last_data[1]))
            composite = last_data[2]
            score = 0.0 if composite <= 2.0 else (2.0 if composite <= 5.0 else (5.0 if composite <= 10.0 else 10.0))
            self.pred_flood_score_var.set(score)
            self.update_pred_composite()
    
    def run_prediction(self):
        brgy, pop_str = self.pred_brgy_combo.get(), self.pred_pop_entry.get().strip()
        if not all([brgy, pop_str]):
            messagebox.showwarning("Input Error", "Please fill all required fields")
            return
        try:
            future_pop = int(pop_str)
            _, f_score, v_score = self.calc_composite_risk(False, False, False, self.pred_garbage_var.get(),
                                                           self.pred_rodents_var.get(), self.pred_drainage_var.get())
            f_score = self.pred_flood_score_var.get()
            future_composite = f_score * v_score
        except ValueError:
            messagebox.showerror("Input Error", "Invalid population value")
            return
        
        history = self.db.get_barangay_history(brgy)
        if len(history) < 2:
            messagebox.showerror("Insufficient Data", "Need at least 2 years of historical data")
            return
        
        predicted_cases, model = predict_next_year(history, future_pop, future_composite)
        if predicted_cases is None:
            messagebox.showerror("Prediction Error", model)
            return
        
        color = ThemeColors.DANGER if predicted_cases > 20 else (ThemeColors.WARNING if predicted_cases > 10 else ThemeColors.SUCCESS)
        self.pred_result_label.config(text=f"📊 Predicted Cases: {int(predicted_cases)}\n(Risk Index: {future_composite:.2f})", foreground=color)
        
        self.generate_recommendations(predicted_cases, f_score, v_score, future_pop, model)
        self.view_mitigation_btn.config(state='normal')
        
        for w in self.pred_plot_frame.winfo_children(): w.destroy()
        
        years, cases = [r[0] for r in history], [r[3] for r in history]
        next_year = years[-1] + 1
        
        plt.style.use('seaborn-v0_8-whitegrid')
        fig, ax = plt.subplots(figsize=(7, 5), facecolor='white')
        ax.set_facecolor('#FAFBFC')
        
        ax.plot(years, cases, 'o-', label='Historical Cases', color='#4A90A4', linewidth=2.5, markersize=9, markerfacecolor='white', markeredgewidth=2)
        ax.plot([years[-1], next_year], [cases[-1], predicted_cases], 'o--', color='#E74C3C', label=f'Prediction ({int(predicted_cases)} cases)', linewidth=2.5, markersize=9, markerfacecolor='white', markeredgewidth=2)
        
        best_case_pred, _ = predict_next_year(history, future_pop, 0.0)
        ax.plot([years[-1], next_year], [cases[-1], best_case_pred], 'o:', color='#27AE60', label=f'Best Case ({int(best_case_pred)} cases)', linewidth=2, markersize=7, markerfacecolor='white', markeredgewidth=2, alpha=0.8)
        
        ax.set_xlabel('Year', fontsize=11, fontweight='medium', color='#2C3E50')
        ax.set_ylabel('Total Cases', fontsize=11, fontweight='medium', color='#2C3E50')
        ax.set_title(f'Leptospirosis Trend: {brgy}', fontsize=13, fontweight='bold', color='#2C3E50', pad=15)
        ax.set_xticks(years + [next_year])
        ax.grid(True, alpha=0.4, linestyle='--')
        ax.legend(loc='best', fontsize=9, framealpha=0.95, edgecolor='#DDE2E8')
        for spine in ax.spines.values(): spine.set_color('#DDE2E8')
        fig.tight_layout(pad=1.5)
        
        canvas = FigureCanvasTkAgg(fig, master=self.pred_plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_recommendations(self, predicted_cases, f_score, v_score, population, model):
        rec = ["=" * 50, f"MITIGATION STRATEGY FOR {int(predicted_cases)} PREDICTED CASES", "=" * 50, ""]
        
        risk_level = "CRITICAL" if predicted_cases > 30 else ("HIGH" if predicted_cases > 15 else ("MODERATE" if predicted_cases > 5 else "LOW"))
        symbol = "⚠️" if predicted_cases > 5 else "✓"
        rec.extend([f"{symbol} {risk_level} RISK LEVEL", "", "PRIORITY INTERVENTIONS:", ""])
        
        priority = 1
        flood_actions = {
            10.0: ("FLOOD MANAGEMENT (Critical)", ["Improve drainage infrastructure", "Establish early warning system", "Prepare evacuation centers", "Stock emergency medical supplies"]),
            5.0: ("FLOOD PREPAREDNESS (High Priority)", ["Clear drainage systems before rainy season", "Conduct community drills", "Pre-position medical resources"]),
            0.1: ("FLOOD MITIGATION (Moderate)", ["Regular drainage maintenance", "Monitor weather forecasts"])
        }
        for threshold, (title, actions) in flood_actions.items():
            if f_score >= threshold:
                rec.append(f"{priority}. {title}")
                rec.extend([f"   • {a}" for a in actions])
                rec.append("")
                priority += 1
                break
        
        if v_score > 1.5:
            level = "Critical" if v_score > 2.0 else "High Priority"
            rec.append(f"{priority}. SANITATION {'IMPROVEMENT' if v_score > 2.0 else 'ENHANCEMENT'} ({level})")
            san_map = [(self.pred_garbage_var, "garbage collection", ["Establish regular garbage collection", "Set up community waste segregation"] if v_score > 2.0 else ["Improve garbage collection frequency"]),
                       (self.pred_rodents_var, "rodent control", ["Launch rodent control program", "Reduce food sources for pests", "Control stray animal population"] if v_score > 2.0 else ["Conduct rodent monitoring"]),
                       (self.pred_drainage_var, "drainage", ["Clear clogged drainage systems", "Cover open drainage channels"] if v_score > 2.0 else ["Schedule drainage cleaning"])]
            for var, _, actions in san_map:
                if var.get(): rec.extend([f"   • {a}" for a in actions])
            rec.append("")
            priority += 1
        
        rec.extend([f"{priority}. PUBLIC HEALTH MEASURES", "   • Conduct health education campaigns", "   • Distribute protective equipment (boots, gloves)",
                    "   • Offer doxycycline prophylaxis to high-risk groups", "   • Set up surveillance system", ""])
        
        sensitivity = model.coef_[0]
        cases_per_risk = (sensitivity / 100000) * population
        rec.extend(["IMPACT ANALYSIS:", f"• For every +1.0 Composite Risk increase:", f"  ~{int(abs(cases_per_risk))} additional cases expected", ""])
        
        best_pred, _ = predict_next_year(self.db.get_barangay_history(self.pred_brgy_combo.get()), population, 0.0)
        reduction = int(predicted_cases - best_pred)
        if reduction > 0:
            rec.extend(["POTENTIAL OUTCOME:", "✓ With optimal interventions (zero composite risk):",
                       f"  Expected cases: {int(best_pred)}", f"  Cases prevented: {reduction}",
                       f"  Reduction: {int((reduction/predicted_cases)*100)}%"])
        rec.extend(["", "=" * 50])
        self.current_recommendations = '\n'.join(rec)
    
    def show_mitigation_modal(self):
        if not self.current_recommendations:
            messagebox.showinfo("No Recommendations", "Generate a prediction first to view mitigation actions.")
            return
        
        modal = tk.Toplevel(self.root)
        modal.title("Mitigation Actions - Risk Reduction Strategies")
        modal.geometry("750x600")
        modal.transient(self.root)
        modal.grab_set()
        modal.configure(bg=ThemeColors.BG_MAIN)
        
        header = ttk.Frame(modal, style='Card.TFrame')
        header.pack(fill='x', padx=20, pady=(20, 10))
        ttk.Label(header, text="💡 Mitigation Actions & Recommendations", font=('Segoe UI', 14, 'bold'), foreground=ThemeColors.PRIMARY).pack(anchor='w')
        ttk.Label(header, text="Evidence-based strategies to reduce leptospirosis risk", font=('Segoe UI', 10), foreground=ThemeColors.TEXT_SECONDARY).pack(anchor='w', pady=(5, 0))
        
        ttk.Frame(modal, height=2, style='Card.TFrame').pack(fill='x', padx=20)
        
        content = ttk.Frame(modal, style='Card.TFrame')
        content.pack(fill='both', expand=True, padx=20, pady=(10, 10))
        
        text_frame = ttk.Frame(content)
        text_frame.pack(fill='both', expand=True)
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side='right', fill='y')
        
        text = tk.Text(text_frame, wrap='word', font=('Consolas', 10), bg='#FFFFFF', fg=ThemeColors.TEXT_PRIMARY, relief='flat', borderwidth=0, padx=15, pady=15, yscrollcommand=scrollbar.set)
        text.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=text.yview)
        text.insert('1.0', self.current_recommendations)
        text.config(state='disabled')
        
        btns = ttk.Frame(modal, style='Card.TFrame')
        btns.pack(fill='x', padx=20, pady=(10, 20))
        ttk.Button(btns, text="✓  Close", command=modal.destroy, style='Primary.TButton').pack(side='right')
        ttk.Button(btns, text="📋 Copy to Clipboard", command=lambda: self.copy_to_clipboard(self.current_recommendations), style='Success.TButton').pack(side='right', padx=(0, 10))
        
        modal.update_idletasks()
        x, y = (modal.winfo_screenwidth() - modal.winfo_width()) // 2, (modal.winfo_screenheight() - modal.winfo_height()) // 2
        modal.geometry(f"+{x}+{y}")
    
    def copy_to_clipboard(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        messagebox.showinfo("Copied", "Mitigation recommendations copied to clipboard!")
    
    def run_simulation(self):
        brgy, year_str, days_str = self.sim_brgy_combo.get(), self.sim_year_entry.get().strip(), self.sim_days_entry.get().strip()
        if not all([brgy, year_str, days_str]):
            messagebox.showwarning("Input Error", "Please fill required fields")
            return
        try:
            year, days = int(year_str), int(days_str)
            i_coef, sigma = float(self.i_coef_entry.get()), float(self.sigma_entry.get())
            xi, delta = float(self.xi_entry.get()), float(self.delta_entry.get())
        except ValueError:
            messagebox.showerror("Input Error", "Invalid parameter values")
            return
        
        data = self.db.get_data_for_sim(brgy, year)
        if not data:
            messagebox.showerror("Error", f"No data found for {brgy} in {year}")
            return
        
        pop, cases, flood_sev = data
        t = np.linspace(0, days, days)
        y0 = [float(pop), 0.0, float(cases) if cases > 0 else 0.1, float(flood_sev)]
        Lambda = (pop * 0.01) / 365
        
        try:
            solution = odeint(seiwr_ode, y0, t, args=(Lambda, i_coef, sigma, xi, delta))
            S, E, I, W = solution.T
            
            for w in self.plot_frame.winfo_children(): w.destroy()
            
            plt.style.use('seaborn-v0_8-whitegrid')
            fig, ax1 = plt.subplots(figsize=(9, 5), facecolor='white')
            ax1.set_facecolor('#FAFBFC')
            
            ax1.set_xlabel('Time (Days)', fontsize=11, fontweight='medium', color='#2C3E50')
            ax1.set_ylabel('Susceptible Population', color='#4A90A4', fontsize=11, fontweight='medium')
            ax1.plot(t, S, color='#4A90A4', label='Susceptible', linewidth=2.5)
            ax1.tick_params(axis='y', labelcolor='#4A90A4')
            ax1.grid(True, alpha=0.4, linestyle='--')
            
            ax2 = ax1.twinx()
            ax2.set_ylabel('Risk Index / Exposed', color='#E74C3C', fontsize=11, fontweight='medium')
            ax2.plot(t, I, color='#E74C3C', label='Cumulative Risk (I)', linewidth=2.5)
            ax2.plot(t, E, color='#F39C12', label='Exposed (E)', linestyle='--', linewidth=2)
            ax2.plot(t, W, color='#27AE60', label='Water Contamination (W)', linestyle=':', linewidth=2)
            ax2.tick_params(axis='y', labelcolor='#E74C3C')
            
            plt.title(f"SEIWR Model: {brgy} ({year})", fontsize=13, fontweight='bold', color='#2C3E50', pad=15)
            for spine in list(ax1.spines.values()) + list(ax2.spines.values()): spine.set_color('#DDE2E8')
            
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right', framealpha=0.95, edgecolor='#DDE2E8', fontsize=9)
            fig.tight_layout(pad=1.5)
            
            canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
            messagebox.showinfo("Simulation Complete", f"SEIWR simulation for {brgy} ({year}) completed!")
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
