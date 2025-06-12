import streamlit as st
import pandas as pd
import numpy as np

# --- App Config ---
st.set_page_config("PVDevSim – Advanced Failure Risk", layout="wide")
st.title("🔬 PVDevSim — Failure-Aware PV Module Simulation")

# --- Load Data ---
try:
    bom_df = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("failure_risk_matrix_v2.csv")
except FileNotFoundError as e:
    st.error(f"Missing file: {e}")
    st.stop()

# --- Sidebar Inputs ---
st.sidebar.header("🧪 Encapsulants")
selections = {}
for side in ["Encapsulant - Front", "Encapsulant - Rear"]:
    options = bom_df[bom_df["Component"] == side]["Type"].unique()
    selected = st.sidebar.selectbox(side, options, key=side)
    row = bom_df[(bom_df["Component"] == side) & (bom_df["Type"] == selected)].iloc[0]
    selections[side] = row

st.sidebar.header("📦 Other Materials")
for comp in bom_df["Component"].unique():
    if "Encapsulant" in comp:
        continue
    options = bom_df[bom_df["Component"] == comp]["Type"].unique()
    selected = st.sidebar.selectbox(comp, options, key=comp)
    row = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == selected)].iloc[0]
    selections[comp] = row

# --- Stress and Test Conditions ---
st.sidebar.header("🌡️ Environment & Test Conditions")
temp = st.sidebar.slider("Operating Temp (°C)", 25, 85, 45)
uv    = st.sidebar.slider("UV Dosage (kWh/m²)", 0, 1000, 400)
dh    = st.sidebar.slider("Damp Heat Hours", 0, 5000, 2000)

st.sidebar.header("📋 Test Protocol")
profile = st.sidebar.selectbox("Test Standard", ["None", "IEC Basic", "PVEL Scorecard", "RETC MQI"])
test_profiles = {
    "None": {},
    "IEC Basic": {"UV": 0.3, "DH1000": 1.0, "TC200": 0.5},
    "PVEL Scorecard": {"UV": 0.5, "DH2000": 1.4, "PID": 1.0, "HF": 0.6, "LID": 0.4},
    "RETC MQI": {"UV": 0.4, "HF": 0.8, "Dynamic Load": 0.6, "PID": 0.8}
}
selected_tests = test_profiles.get(profile, {})
total_score = sum(selected_tests.values())

# --- Degradation Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel = arrhenius(temp)
base_deg = 0.5
deg_rate = base_deg * accel + dh * 0.0001 + total_score * 0.05
year1_deg = deg_rate
year25_loss = year1_deg * 25 * 0.95
reliability = max(0, 100 - year25_loss)

# --- Failure Risk Lookup ---
def get_failures(material, stress_keys):
    rows = []
    for stress in stress_keys:
        match = risk_df[
            (risk_df["Material"].str.contains(material, case=False)) &
            (risk_df["Stress"].str.contains(stress.split()[0], case=False))
        ]
        if not match.empty:
            match = match.copy()
            rows.append(match)
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# --- Simulation Output ---
if st.sidebar.button("▶️ Run Simulation"):

    st.subheader("📋 Bill of Materials")
    bom_table = pd.DataFrame([
        {
            "Component": k,
            "Material": v["Type"],
            "Supplier": v["Supplier"],
            "Region": v["Region"],
            "Certifications": v["Certifications"]
        } for k, v in selections.items()
    ])
    st.dataframe(bom_table)

    st.subheader("📉 Degradation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Arrhenius Factor", f"{accel:.2f}")
    col2.metric("Year-1 Degradation", f"{year1_deg:.2f}%")
    col3.metric("25-Year Loss", f"{year25_loss:.2f}%")
    col4.metric("Reliability Index", f"{reliability:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    if selected_tests:
        risk_entries = []
        for comp, row in selections.items():
            material = row["Type"]
            risk_data = get_failures(material, selected_tests.keys())
            if not risk_data.empty:
                if "Component" not in risk_data.columns:
                    risk_data.insert(0, "Component", comp)
                else:
                    risk_data["Component"] = comp
                risk_entries.append(risk_data)

        if risk_entries:
            risk_df_final = pd.concat(risk_entries, ignore_index=True)
            st.dataframe(risk_df_final[["Component", "Material", "Stress", "Failure Mode", "Risk Score"]])
        else:
            st.info("✅ No matching failure risks found for selected materials.")
    else:
        st.info("ℹ️ Select a test standard to enable risk analysis.")
