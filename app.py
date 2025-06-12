import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config("PVDevSim – Material-Specific Modeling", layout="wide")
st.title("🔬 PVDevSim – Realistic Module Simulation with Material-Level Insights")

# --- Load BOM ---
try:
    bom_df = pd.read_csv("full_material_bom.csv")
    st.sidebar.success("✅ Loaded BOM data")
except FileNotFoundError:
    st.error("❌ 'full_material_bom.csv' not found!")
    st.stop()

components = bom_df["Component"].unique()
selections = {}

st.sidebar.header("🔧 Select BOM Components")
for component in components:
    options = bom_df[bom_df["Component"] == component]["Type"].unique()
    selection = st.sidebar.selectbox(f"{component}", options, key=component)
    selected_row = bom_df[(bom_df["Component"] == component) & (bom_df["Type"] == selection)].iloc[0]
    selections[component] = selected_row

# --- Degradation Conditions ---
st.sidebar.header("🌡️ Degradation Parameters")
avg_temp = st.sidebar.slider("Avg Operating Temp (°C)", 25, 85, 45)
damp_heat_hours = st.sidebar.slider("Damp Heat (Hours)", 0, 5000, 2000)
thermal_cycles = st.sidebar.slider("Thermal Cycles", 0, 1000, 200)
uv_dosage = st.sidebar.slider("UV Dosage (kWh/m²)", 0, 1000, 300)

# --- Select Test Profile ---
st.sidebar.header("🧪 Select Test Protocol")
profile = st.sidebar.selectbox("Standard", ["None", "IEC Basic", "PVEL Scorecard", "RETC MQI"])

test_profiles = {
    "None": {},
    "IEC Basic": {"TC200": 0.5, "DH1000": 1.0, "UV": 0.3},
    "PVEL Scorecard": {"TC600": 0.7, "DH2000": 1.4, "PID": 1.0, "UV": 0.5, "LID": 0.4, "HF": 0.6},
    "RETC MQI": {"TC200 + DH2000 + HF": 2.5, "Dynamic Load": 0.6, "PID": 0.8, "UV": 0.4}
}
selected_tests = test_profiles.get(profile, {})
total_test_impact = sum(selected_tests.values())

# --- Real Material-Specific Adjustments ---
encap_factors = {
    "EVA": {"UV": 1.2, "PID": 1.3},
    "POE": {"UV": 0.7, "PID": 0.5},
    "EPE": {"UV": 1.0, "PID": 1.0}
}

backsheet_factors = {
    "TPT": {"DH": 1.0},
    "PET": {"DH": 1.3},
    "Co-extruded": {"DH": 0.9}
}

def get_material_factor(component_type, stress):
    if component_type == "Encapsulant":
        mat = selections["Encapsulant"]["Type"]
        for key in encap_factors:
            if key in mat:
                return encap_factors[key].get(stress, 1.0)
    elif component_type == "Backsheet":
        mat = selections["Backsheet"]["Type"]
        for key in backsheet_factors:
            if key in mat:
                return backsheet_factors[key].get(stress, 1.0)
    return 1.0

# --- Arrhenius Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel_factor = arrhenius(avg_temp)
base_deg_rate = 0.5

# Apply material modifiers
uv_factor = get_material_factor("Encapsulant", "UV")
pid_factor = get_material_factor("Encapsulant", "PID")
dh_factor = get_material_factor("Backsheet", "DH")

# Calculate enhanced degradation
deg_rate = (
    base_deg_rate * accel_factor +
    (damp_heat_hours * 0.0001 * dh_factor) +
    (total_test_impact * 0.05 * np.mean([uv_factor, pid_factor]))
)

simulate = st.sidebar.button("Run Simulation")

if simulate:
    st.subheader("📋 Bill of Materials")
    bom_summary = pd.DataFrame([
        {
            "Component": c,
            "Material": row["Type"],
            "Supplier": row["Supplier"],
            "Region": row["Region"],
            "Certifications": row["Certifications"]
        }
        for c, row in selections.items()
    ])
    st.table(bom_summary)

    st.subheader("📉 Degradation & Reliability")
    year_1_deg = deg_rate
    year_25_loss = year_1_deg * 25 * 0.95
    reliability_score = max(0, 100 - year_25_loss)

    st.metric("Arrhenius Factor", f"{accel_factor:.2f}")
    st.metric("Year 1 Degradation", f"{year_1_deg:.2f}%")
    st.metric("Total Loss by Year 25", f"{year_25_loss:.2f}%")
    st.metric("Reliability Score", f"{reliability_score:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    risk_matrix = pd.DataFrame({
        "Test": list(selected_tests.keys()),
        "Impact Score": list(selected_tests.values()),
        "Failure Risk (%)": [min(impact * 20, 100) for impact in selected_tests.values()]
    })
    st.dataframe(risk_matrix)
