import streamlit as st
import pandas as pd
import numpy as np

# --- Config ---
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
    opts = bom_df[bom_df["Component"] == side]["Type"].unique()
    val = st.sidebar.selectbox(side, opts, key=side)
    row = bom_df[(bom_df["Component"] == side) & (bom_df["Type"] == val)].iloc[0]
    selections[side] = row

st.sidebar.header("📦 Other Materials")
for comp in bom_df["Component"].unique():
    if "Encapsulant" in comp: continue
    opts = bom_df[bom_df["Component"] == comp]["Type"].unique()
    val = st.sidebar.selectbox(comp, opts, key=comp)
    row = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == val)].iloc[0]
    selections[comp] = row

# --- Stress & Tests ---
st.sidebar.header("🌡️ Environment & Test")
temp = st.sidebar.slider("Operating Temp (°C)", 25, 85, 45)
uv    = st.sidebar.slider("UV Dosage (kWh/m²)", 0, 1000, 400)
dh    = st.sidebar.slider("Damp Heat Hours", 0, 5000, 2000)

st.sidebar.header("📋 Test Protocol")
profile = st.sidebar.selectbox("Test Standard", ["None", "IEC Basic", "PVEL Scorecard", "RETC MQI"])
test_profiles = {
    "None": {},
    "IEC Basic": {"UV":0.3, "DH1000":1.0, "TC200":0.5},
    "PVEL Scorecard": {"UV":0.5, "DH2000":1.4, "PID":1.0, "HF":0.6, "LID":0.4},
    "RETC MQI": {"UV":0.4, "HF":0.8, "Dynamic Load":0.6, "PID":0.8}
}
selected_tests = test_profiles.get(profile, {})
total_score = sum(selected_tests.values())

# --- Degradation Calc ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea/k)*(1/Tref - 1/T))

accel = arrhenius(temp)
base_deg = 0.5
deg_rate = base_deg * accel + dh * 0.0001 + total_score * 0.05
year1 = deg_rate
year25 = year1 * 25 * 0.95
reliability = max(0, 100 - year25)

# --- Risk Lookup ---
def get_failures(material, test_keys):
    rows = []
    for t in test_keys:
        match = risk_df[(risk_df["Material"].str.contains(material, case=False)) &
                        (risk_df["Stress"].str.contains(t.split()[0], case=False))]
        if not match.empty:
            rows.append(match.assign(Component=material))
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# --- Run Simulation ---
if st.sidebar.button("▶️ Run Simulation"):

    st.subheader("📋 Bill of Materials")
    bom_tbl = pd.DataFrame([
        {"Component": k, "Material": v["Type"], "Supplier": v["Supplier"],
         "Region": v["Region"], "Certifications": v["Certifications"]}
        for k, v in selections.items()
    ])
    st.dataframe(bom_tbl)

    st.subheader("📉 Degradation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Arrhenius F", f"{accel:.2f}")
    col2.metric("Year-1 Deg", f"{year1:.2f}%")
    col3.metric("25-Year Loss", f"{year25:.2f}%")
    col4.metric("Reliability", f"{reliability:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    if selected_tests:
        all_risks = []
        for comp, row in selections.items():
            material = row["Type"]
            failure_df = get_failures(material, selected_tests.keys())
            if not failure_df.empty:
                failure_df.insert(0, "Component", comp)
                all_risks.append(failure_df)
        if all_risks:
            risk_result = pd.concat(all_risks, ignore_index=True)
            st.dataframe(risk_result[["Component", "Material", "Stress", "Failure Mode", "Risk Score"]])
        else:
            st.info("No matching failure risks found for selected materials.")
    else:
        st.info("Select a test standard to activate risk analysis.")
