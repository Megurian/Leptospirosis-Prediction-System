# Leptospirosis Risk Prediction System

A prototype application for predicting leptospirosis outbreak risk based on flood severity and sanitation factors.

## Features

- **Barangay Management**: Add and manage barangay profiles
- **Yearly Data Entry**: Record historical cases with composite risk factors
- **SEIWR Simulation**: Run epidemiological simulations
- **Trend Prediction**: ML-powered case prediction with mitigation recommendations

## Risk Assessment Model

The prediction uses a **Composite Risk Index** calculated as:

```
Composite Risk = Flood Score × Vector Multiplier
```

**Flood Score (0-10):**
- Flooded area: +2.0
- Evacuation needed: +3.0
- Infrastructure damage: +5.0

**Vector/Sanitation Multiplier (1.0-2.5x):**
- Irregular garbage collection: +0.5x
- High rodent/stray presence: +0.5x
- Clogged/open drainage: +0.5x

## Installation (Development)

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run application
python main.py
```

## Building Executable

```bash
python build.py
```

The executable will be created at `dist/LeptospirosisPredictor.exe`

## Files

- `main.py` - Main application
- `seeder.py` - Database seeder for test data
- `requirements.txt` - Python dependencies
- `build.py` - Build script for creating executable
- `leptospirosis_sim.db` - SQLite database (created on first run)

## Usage Notes

1. Add at least one barangay before entering yearly data
2. Enter at least 2 years of historical data per barangay for predictions
3. Varied composite risk values in historical data improve prediction accuracy
4. The prediction model uses Linear Regression on incidence rates

## Prototype Version

This is a prototype for demonstration purposes. For production use, additional validation and testing is recommended.
