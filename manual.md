# Leptospirosis Risk Prediction System - User Manual

## Introduction
The **Leptospirosis Risk Prediction System** is a data-driven application designed to help local health units and barangay officials predict potential leptospirosis outbreaks. It uses historical data, environmental risk factors, and mathematical modeling (SEIWR) to forecast cases and suggest mitigation strategies.

## Getting Started
Upon launching the application, you will see a window with five main tabs at the top:
1.  **Barangay Management**
2.  **Yearly Data Entry**
3.  **SEIWR Simulation**
4.  **Trend Prediction** (Main Feature)
5.  **View All Data**

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

---

## 3. Viewing and Managing Data
Use the **View All Data** tab to review the database.
*   **Filter:** specific barangay data using the dropdown menu.
*   **Refresh:** Click if recent changes aren't showing.
*   **Delete:** Select a row and click **Delete Selected** to remove erroneous entries.

---

## 4. Trend Prediction (Main Feature)
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

## 5. SEIWR Simulation (Advanced)
This tab uses a mathematical compartmental model (Susceptible-Exposed-Infected-Water-Recovered) to simulate daily transmission dynamics.

1.  Select **Barangay** and **Year**.
2.  Set **Simulation Days** (default is 365).
3.  **Advanced Parameters:** Recommended for users with epidemiological background. You can adjust infection coefficients, incubation rates, and decay factors.
4.  Click **Run Simulation**.
5.  The graph shows the curve of the outbreak risk over time based on the selected year's data.

---

## Troubleshooting
*   **"Insufficient Data" Error:** The prediction engine requires at least 2 years of historical data for the specific barangay to calculate a trend. Go to the *Yearly Data Entry* tab and add more years.
*   **Negative Numbers:** The system will prevent negative population or cases. Ensure inputs are valid positive integers.
*   **Database File:** The application creates a `leptospirosis_sim.db` file in the same folder. Do not delete this file, or you will lose your saved data.
