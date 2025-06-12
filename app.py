import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config("PVDevSim – Module Simulator", layout="wide")
st.title("🔬 PVDevSim – Full Module Configuration + Degradation Modeling")

# --- Load BOM ---
try:
    bom_df = pd.read_csv("full_material_bom.csv")
    st.sidebar.success("✅ Loaded material and supplier database")
except FileNotFoundError:
    st.error("❌ 'full_material_bom.csv' not found!")
    st.stop()

components = bom_df["Component"].unique()
selections = {}

st.sidebar.header("🔧 Select Materials by Component")
for component in components:
    options = bom_df[bom_df["Component"] == component]["Type"].unique()
    selection = st.sidebar.selectbox(f"{component}", options, key=component)
    selected_row = bom_df[(bom_df["Component"] == component) & (bom_df["Type"] == selection)].iloc[0]
    selections[component] = selected_row

# --- Degradation Modeling Inputs ---
st.sidebar.header("🌡️ Degradation Conditions")
avg_temp = st.sidebar.slider("Average Operating Temp (°C)", 25, 85, 45)
damp_heat_hours = st.sidebar.slider("Damp Heat (Hours)", 0, 5000, 2000)
thermal_cycles = st.sidebar.slider("Thermal Cycles", 0, 1000, 200)
uv_dosage = st.sidebar.slider("UV Dosage (kWh/m²)", 0, 1000, 300)

# --- IEC Test Selection ---
iec_tests = st.sidebar.multiselect(
    "IEC Stress Applied",
    ["TC200", "DH1000", "UV", "PID", "LID", "TC1000+DH2000", "HF", "UV Preconditioning"]
)
test_impact = {
    "TC200": 0.5, "DH1000": 1.0, "UV": 0.3, "PID": 0.7,
    "LID": 0.5, "TC1000+DH2000": 1.8, "HF": 0.4, "UV Preconditioning": 0.2
}
iec_degradation = sum(test_impact[t] for t in iec_tests if t in test_impact)

# --- Calculate Degradation using Arrhenius Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    """Arrhenius acceleration factor for temp in °C, Ea in eV"""
    k = 8.617e-5  # Boltzmann constant eV/K
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel_factor = arrhenius(avg_temp)
base_deg_rate = 0.5  # base annual degradation in %
total_deg_rate = base_deg_rate * accel_factor + (iec_degradation * 0.05) + (damp_heat_hours * 0.0001)

simulate = st.sidebar.button("Simulate Module Performance")

if simulate:
    st.subheader("📋 Bill of Materials (BOM)")
    bom_summary = pd.DataFrame([
        {
            "Component": comp,
            "Material": row["Type"],
            "Supplier": row["Supplier"],
            "Region": row["Region"],
            "Certifications": row["Certifications"]
        }
        for comp, row in selections.items()
    ])
    st.table(bom_summary)

    st.subheader("📉 Degradation Simulation")
    degradation_year_1 = total_deg_rate
    year_25_loss = degradation_year_1 * 25 * 0.95  # some improvement due to stabilization
    reliability_score = 100 - year_25_loss

    df = pd.DataFrame({
        "Metric": ["Arrhenius Factor", "Degradation Rate (Year 1)", "Loss by Year 25", "Reliability Score"],
        "Value": [f"{accel_factor:.2f}", f"{degradation_year_1:.2f}%", f"{year_25_loss:.2f}%", f"{reliability_score:.1f}/100"]
    })
    st.table(df)
