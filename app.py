import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config("PVDevSim – Dual Encapsulant Modeling", layout="wide")
st.title("🔬 PVDevSim – Dual Encapsulant Simulation + Advanced Materials")

# --- Load BOM ---
try:
    bom_df = pd.read_csv("full_material_bom_v2.csv")
    st.sidebar.success("✅ Loaded Extended BOM")
except FileNotFoundError:
    st.error("❌ Missing 'full_material_bom_v2.csv'")
    st.stop()

components = bom_df["Component"].unique()
selections = {}

# --- Encapsulant Front & Rear Section (Clear Layout) ---
st.sidebar.header("🧪 Encapsulant Selection")
for encap_side in ["Encapsulant - Front", "Encapsulant - Rear"]:
    options = bom_df[bom_df["Component"] == encap_side]["Type"].unique()
    selection = st.sidebar.selectbox(f"{encap_side}", options, key=encap_side)
    selected_row = bom_df[(bom_df["Component"] == encap_side) & (bom_df["Type"] == selection)].iloc[0]
    selections[encap_side] = selected_row

# --- Other BOM Components ---
st.sidebar.header("🧱 Select Other BOM Components")
for component in components:
    if "Encapsulant" not in component:
        options = bom_df[bom_df["Component"] == component]["Type"].unique()
        selection = st.sidebar.selectbox(f"{component}", options, key=component)
        selected_row = bom_df[(bom_df["Component"] == component) & (bom_df["Type"] == selection)].iloc[0]
        selections[component] = selected_row

# --- Degradation Parameters ---
st.sidebar.header("🌡️ Degradation Settings")
avg_temp = st.sidebar.slider("Operating Temp (°C)", 25, 85, 45)
damp_heat = st.sidebar.slider("Damp Heat (Hours)", 0, 5000, 2000)
uv_dose = st.sidebar.slider("UV Dosage (kWh/m²)", 0, 1000, 300)

# --- Select Test Protocol ---
st.sidebar.header("📋 Test Protocol")
profile = st.sidebar.selectbox("Standard", ["None", "IEC Basic", "PVEL Scorecard", "RETC MQI"])
test_profiles = {
    "None": {},
    "IEC Basic": {"TC200": 0.5, "DH1000": 1.0, "UV": 0.3},
    "PVEL Scorecard": {"TC600": 0.7, "DH2000": 1.4, "PID": 1.0, "UV": 0.5, "LID": 0.4, "HF": 0.6},
    "RETC MQI": {"TC200 + DH2000 + HF": 2.5, "Dynamic Load": 0.6, "PID": 0.8, "UV": 0.4}
}
selected_tests = test_profiles.get(profile, {})
total_test_impact = sum(selected_tests.values())

# --- Material Factors ---
encap_degradation = {
    "EVA": {"UV": 1.2, "PID": 1.3},
    "POE": {"UV": 0.7, "PID": 0.5},
    "EPE": {"UV": 1.0, "PID": 1.0}
}
backsheet_degradation = {
    "TPT": {"DH": 1.0},
    "PET": {"DH": 1.3},
    "Co-extruded": {"DH": 0.9}
}

def get_encap_factor(material, stress):
    for key in encap_degradation:
        if key in material:
            return encap_degradation[key].get(stress, 1.0)
    return 1.0

def get_backsheet_factor(material):
    for key in backsheet_degradation:
        if key in material:
            return backsheet_degradation[key].get("DH", 1.0)
    return 1.0

# --- Arrhenius Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel_factor = arrhenius(avg_temp)
base_deg = 0.5

# --- Get Material-Based Multipliers ---
front_encap = selections["Encapsulant - Front"]["Type"]
rear_encap = selections["Encapsulant - Rear"]["Type"]
backsheet = selections["Backsheet"]["Type"]

uv_factor = (get_encap_factor(front_encap, "UV") + get_encap_factor(rear_encap, "UV")) / 2
pid_factor = (get_encap_factor(front_encap, "PID") + get_encap_factor(rear_encap, "PID")) / 2
dh_factor = get_backsheet_factor(backsheet)

# --- Calculate Final Degradation Rate ---
deg_rate = (
    base_deg * accel_factor +
    damp_heat * 0.0001 * dh_factor +
    total_test_impact * 0.05 * np.mean([uv_factor, pid_factor])
)

# --- Run Simulation ---
simulate = st.sidebar.button("▶️ Run Simulation")

if simulate:
    st.subheader("📋 Bill of Materials (Selected)")
    bom_table = pd.DataFrame([
        {
            "Component": comp,
            "Material": row["Type"],
            "Supplier": row["Supplier"],
            "Region": row["Region"],
            "Certifications": row["Certifications"]
        }
        for comp, row in selections.items()
    ])
    st.table(bom_table)

    st.subheader("📉 Degradation & Reliability Metrics")
    year_1_deg = deg_rate
    year_25_loss = year_1_deg * 25 * 0.95
    reliability = max(0, 100 - year_25_loss)

    st.metric("Arrhenius Factor", f"{accel_factor:.2f}")
    st.metric("Degradation (Year 1)", f"{year_1_deg:.2f}%")
    st.metric("Loss by Year 25", f"{year_25_loss:.2f}%")
    st.metric("Reliability Score", f"{reliability:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    if selected_tests:
        risk_df = pd.DataFrame({
            "Test": list(selected_tests.keys()),
            "Impact Score": list(selected_tests.values()),
            "Failure Risk (%)": [min(impact * 20, 100) for impact in selected_tests.values()]
        })
        st.dataframe(risk_df)
    else:
        st.info("No tests selected — failure risk analysis not applicable.")
