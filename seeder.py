"""
Database Seeder for Leptospirosis Prediction System
Populates database with realistic dummy data for testing
"""
import sqlite3
import random

def seed_database():
    conn = sqlite3.connect('leptospirosis_sim.db')
    cursor = conn.cursor()
    
    # Clear existing data for Lunzuran if it exists
    cursor.execute("DELETE FROM yearly_data WHERE barangay_id IN (SELECT id FROM barangays WHERE name = 'Lunzuran')")
    cursor.execute("DELETE FROM barangays WHERE name = 'Lunzuran'")
    conn.commit()
    
    # Add Lunzuran barangay
    barangay_name = "Lunzuran"
    initial_population = 28000
    
    cursor.execute("INSERT INTO barangays (name, population) VALUES (?, ?)", 
                  (barangay_name, initial_population))
    barangay_id = cursor.lastrowid
    
    print(f"✓ Created barangay: {barangay_name} (ID: {barangay_id})")
    print(f"  Initial population: {initial_population}")
    print()
    
    # Seed yearly data from 2020-2025 with varied risk scenarios
    yearly_data = [
        # Year, Population, Composite Risk, Cases
        # Varying flood severity and sanitation conditions for diverse training data
        (2020, 28000, 2.0,  5),   # Minor flood, no vector issues (Flood=2.0, Vector=1.0x)
        (2021, 28300, 12.5, 42),  # Moderate flood + evac + poor sanitation (Flood=5.0, Vector=2.5x)
        (2022, 28600, 4.0,  12),  # Minor flood + some sanitation issues (Flood=2.0, Vector=2.0x)
        (2023, 28900, 20.0, 68),  # Severe flood + damage + poor sanitation (Flood=10.0, Vector=2.0x)
        (2024, 29200, 7.5,  24),  # Moderate flood + some vectors (Flood=5.0, Vector=1.5x)
        (2025, 29500, 15.0, 51),  # Severe flood + moderate sanitation (Flood=10.0, Vector=1.5x)
    ]
    
    print("Adding yearly data:")
    print("-" * 70)
    print(f"{'Year':<6} {'Population':<12} {'Composite Risk':<16} {'Cases':<8}")
    print("-" * 70)
    
    for year, population, composite_risk, cases in yearly_data:
        cursor.execute("""
            INSERT INTO yearly_data (barangay_id, year, population, total_cases, flood_severity)
            VALUES (?, ?, ?, ?, ?)
        """, (barangay_id, year, population, cases, composite_risk))
        
        print(f"{year:<6} {population:<12} {composite_risk:<16.1f} {cases:<8}")
    
    conn.commit()
    print("-" * 70)
    print(f"✓ Successfully seeded {len(yearly_data)} years of data")
    print()
    
    # Verify the data
    cursor.execute("""
        SELECT y.year, y.population, y.flood_severity, y.total_cases
        FROM yearly_data y
        WHERE y.barangay_id = ?
        ORDER BY y.year ASC
    """, (barangay_id,))
    
    results = cursor.fetchall()
    print("Verification - Data in database:")
    print("-" * 70)
    for row in results:
        year, pop, risk, cases = row
        incidence_rate = (cases / pop) * 100000
        print(f"  {year}: Pop={pop}, Risk={risk}, Cases={cases} (Rate: {incidence_rate:.1f} per 100k)")
    
    conn.close()
    print()
    print("=" * 70)
    print("DATABASE SEEDING COMPLETE!")
    print("=" * 70)
    print()
    print("Summary:")
    print(f"  • Barangay: {barangay_name}")
    print(f"  • Years: 2020-2025 (6 years)")
    print(f"  • Composite Risk Range: 2.0 - 20.0")
    print(f"  • Cases Range: 5 - 68")
    print(f"  • This provides varied data for accurate trend prediction")
    print()

if __name__ == "__main__":
    seed_database()
