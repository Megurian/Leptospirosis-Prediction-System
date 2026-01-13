# Leptospirosis Risk Prediction System - User Manual

## Introduction
The **Leptospirosis Risk Prediction System** is a data-driven application designed to help local health units and barangay officials predict potential leptospirosis outbreaks. It uses historical data, environmental risk factors, and mathematical modeling (SEIWR) to forecast cases and suggest mitigation strategies.

## Getting Started
Upon launching the application, you will see a window with six main tabs at the top:
1.  **Barangay Management**
2.  **Yearly Data Entry**
3.  **Import CSV Data** (New!)
4.  **SEIWR Simulation**
5.  **Trend Prediction** (Main Feature)
6.  **View All Data**

---

## 1. Barangay Management
Before inputting case data, you must register the barangays first.

### Adding a Barangay
1.  Go to the **Barangay Management** tab.
2.  Enter the **Barangay Name**.
3.  Enter the **Initial Population**.
4.  Click **Add Barangay**.
5.  The barangay will appear in the "Existing Barangays" list below.

---

## 2. Yearly Data Entry
To generate accurate predictions, the system needs historical data. Use this tab to log past records.

### Adding Annual Data
1.  Select the **Barangay** from the dropdown list.
2.  Enter the **Year** (e.g., 2024).
3.  Enter the **Population** for that specific year.
4.  Enter the **Total Leptospirosis Cases** recorded for that year.

### Risk Factor Assessment
This section calculates a "Composite Risk Index" based on environmental conditions during that year.
*   **Flood Factors:** Check the boxes that applied to that year (Flooded area, Evacuation needed, Damage).
*   **Vector / Sanitation Factors:** Check if there were issues with garbage, rodents, or drainage.

**Note:** The system uses these factors to learn the relationship between environmental risks and case spikes.

5.  Click **Save Data** to store the record.

### Editing Existing Data
1.  If you need to modify existing data, go to the **View All Data** tab.
2.  Select the record you want to edit.
3.  Click **Edit Selected**.
4.  The system will automatically switch to the **Yearly Data Entry** tab with all fields pre-filled.
5.  Make your changes.
6.  Click **Update Data** (the button changes from "Save Data" when in edit mode).
7.  Click **Clear** to exit edit mode and return to adding new data.

---

## 3. Import CSV Data (Bulk Data Entry)
For large datasets or historical records, you can import data from CSV files instead of entering them manually.

### CSV File Format
Your CSV file must contain these columns (order doesn't matter):
- **Barangay** - Name of the barangay
- **Year** - Year of the data (e.g., 2023)
- **Population** - Population for that year
- **Cases** - Total leptospirosis cases
- **Flooded** - Was area flooded? (Yes/No or 1/0)
- **Evacuation** - Evacuation needed? (Yes/No or 1/0)
- **Infrastructure_Damage** - Infrastructure/Agriculture damage? (Yes/No or 1/0)
- **Irregular_Garbage** - Irregular garbage collection? (Yes/No or 1/0)
- **High_Rodents** - High rodent/stray presence? (Yes/No or 1/0)
- **Clogged_Drainage** - Clogged/open drainage? (Yes/No or 1/0)

### Example CSV Format
```
Barangay,Year,Population,Cases,Flooded,Evacuation,Infrastructure_Damage,Irregular_Garbage,High_Rodents,Clogged_Drainage
San Jose,2022,15000,12,Yes,No,Yes,Yes,No,Yes
San Jose,2023,15500,8,Yes,No,No,No,No,Yes
Santa Maria,2022,12000,5,No,No,No,Yes,Yes,No
```

### How to Import
1.  Go to the **Import CSV Data** tab.
2.  Click **Download Template** to get a pre-formatted CSV file (optional).
3.  Click **Browse...** and select your CSV file.
4.  Click **Load & Preview** to validate the data.
5.  Review the preview table - check for any errors or warnings.
6.  If everything looks good, click **Import Data to Database**.
7.  The system will automatically:
   - Create barangays that don't exist
   - Update existing records (same barangay + year)
   - Calculate composite risk indices automatically

**Note:** Accepted values for Yes/No fields: Yes/No, Y/N, 1/0, True/False (case-insensitive)

---

## 4. Viewing and Managing Data
Use the **View All Data** tab to review the database.
*   **Filter:** specific barangay data using the dropdown menu.
*   **Refresh:** Click if recent changes aren't showing.
*   **Edit Selected:** Select a row and click to edit existing data (switches to Yearly Data Entry tab with pre-filled fields).
*   **Delete Selected:** Select a row and click to remove erroneous entries.

---

## 5. Trend Prediction (Main Feature)
This module predicts cases for the *next year* based on historical trends and potential risk scenarios.

### How to Run a Prediction
1.  Go to the **Trend Prediction** tab.
2.  **Select Barangay**.
3.  Enter the **Projected Population** for the coming year.

### Scenario Settings (What-If Analysis)
Adjust these settings to simulate different future conditions:
*   **Flood Risk Scenario:** Select the expected severity of flooding (from "No Flood" to "Severe").
*   **Sanitation Scenario:** Check boxes if you expect sanitation issues (Garbage, Rodents, Drainage).
*   Observe the **Composite Risk Index** change as you adjust settings.

### Generating Results
1.  Click **Generate Prediction**.
2.  **Prediction Results:** The system displays the projected number of cases.
    *   **Green:** Low Risk
    *   **Orange:** Moderate Risk
    *   **Red:** High/Critical Risk
3.  **Mitigation Recommendations:** A generated list of actionable steps (e.g., "Clear drainage," "Conduct drills") tailored to the specific risk factors you selected.
4.  **Trend Visualization:** A graph on the right shows historical cases (blue line) versus the predicted future scenario (red dotted line). It also shows a "Best Case" scenario (green dotted line) if optimal interventions are applied.

**Prerequisite:** You need at least **2 years of historical data** for a barangay to run a prediction.

---

## 6. SEIWR Simulation (Advanced)
This tab uses a mathematical compartmental model (Susceptible-Exposed-Infected-Water-Recovered) to simulate daily transmission dynamics.

1.  Select **Barangay** and **Year**.
2.  Set **Simulation Days** (default is 365).
3.  **Advanced Parameters:** Recommended for users with epidemiological background. You can adjust infection coefficients, incubation rates, and decay factors.
4.  Click **Run Simulation**.
5.  The graph shows the curve of the outbreak risk over time based on the selected year's data.

---

## Troubleshooting
*   **"Insufficient Data" Error:** The prediction engine requires at least 2 years of historical data for the specific barangay to calculate a trend. Go to the *Yearly Data Entry* tab and add more years, or use the *Import CSV Data* feature for bulk entry.
*   **Negative Numbers:** The system will prevent negative population or cases. Ensure inputs are valid positive integers.
*   **CSV Import Errors:** Make sure your CSV file has all required columns and uses accepted formats for Yes/No fields (Yes/No, Y/N, 1/0, True/False).
*   **Database File:** The application creates a `leptospirosis_sim.db` file in the same folder. Do not delete this file, or you will lose your saved data.
*   **Edit Mode Stuck:** If you're in edit mode and want to add new data instead, simply click the **Clear** button in the Yearly Data Entry tab.

---

## Tips for Best Results
*   **Consistent Data Entry:** Enter data for multiple consecutive years to improve prediction accuracy.
*   **Use CSV Import:** For historical data spanning many years, use the CSV import feature to save time.
*   **Regular Updates:** Keep your database updated with the latest year's data for more accurate future predictions.
*   **Risk Factor Accuracy:** Be as accurate as possible when marking risk factors - they directly influence predictions.
*   **What-If Analysis:** Use the Trend Prediction tab's scenario settings to plan for different risk levels (e.g., "What if we have severe flooding next year?").
*   **Backup Your Data:** Regularly backup the `leptospirosis_sim.db` file to prevent data loss.
