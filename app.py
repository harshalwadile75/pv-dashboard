import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config("PV Module Development Simulator", layout="wide")
st.title("🔬 PVDevSim – PV Module Development Simulator")

# --- Load Supplier & Material Data from CSV ---
try:
    materials_df = pd.read_csv("sample_material_suppliers.csv")
    st.sidebar.success("✅ Supplier database loaded.")
except FileNotFoundError:
    st.sidebar.error("❌ Supplier CSV not found. Using default list.")
    materials_df = pd.DataFrame({
        "Material": ["Encapsulant", "Backsheet", "Glass"],
        "Type": ["POE", "TPT", "Tempered"],
        "Supplier": ["Mitsui", "Cybrid", "Xinyi"],
        "Region": ["Japan", "China", "China"],
        "Certifications": ["IEC 61215", "IEC 61730", "IEC 61215"]
    })

# --- Material Selection ---
st.sidebar.header("🧪 Material Selection")
encapsulant = st.sidebar.selectbox("Encapsulant Type", materials_df[materials_df["Material"] == "Encapsulant"]["Type"].unique())
backsheet = st.sidebar.selectbox("Backsheet Type", materials_df[materials_df["Material"] == "Backsheet"]["Type"].unique())
glass_type = st.sidebar.selectbox("Glass Type", materials_df[materials_df["Material"] == "Glass"]["Type"].unique())
cell_type = st.sidebar.selectbox("Cell Type", ["PERC", "TOPCon", "HJT", "IBC"])
interconnect = st.sidebar.selectbox("Interconnection", ["Ribbon", "Wire", "Shingled"])

# --- Environmental Conditions ---
st.sidebar.header("🌤️ Environmental Conditions")
location = st.sidebar.selectbox("Deployment Location", ["Arizona", "India", "Germany", "China", "Middle East"])
damp_heat_hours = st.sidebar.slider("Damp Heat (Hours)", 0, 5000, 2000)
thermal_cycles = st.sidebar.slider("Thermal Cycles", 0, 1000, 200)

# --- IEC Reliability Tests ---
st.sidebar.header("📋 IEC Reliability Tests")
iec_tests = st.sidebar.multiselect(
    "Select Applied Tests",
    ["Thermal Cycling (TC200)", "Damp Heat (DH1000)", "UV Exposure", "Potential Induced Degradation (PID)",
     "Light Induced Degradation (LID)", "TC1000 + DH2000", "Humidity Freeze (HF)", "UV Preconditioning"]
)

# --- Degradation Logic for IEC Tests ---
test_impact = {
    "Thermal Cycling (TC200)": 0.5,
    "Damp Heat (DH1000)": 1.0,
    "UV Exposure": 0.3,
    "Potential Induced Degradation (PID)": 0.7,
    "Light Induced Degradation (LID)": 0.5,
    "TC1000 + DH2000": 1.8,
    "Humidity Freeze (HF)": 0.4,
    "UV Preconditioning": 0.2
}
iec_degradation = sum(test_impact[test] for test in iec_tests if test in test_impact)

# --- Simulate Button ---
simulate = st.sidebar.button("Run Simulation")

if simulate:
    st.subheader("📈 Simulation Results")

    # Base degradation from environment
    degradation = 2 + (0.001 * damp_heat_hours) + (0.002 * thermal_cycles) + iec_degradation
    reliability_score = 100 - degradation

    # Adjust for material quality (e.g., POE improves reliability)
    if encapsulant == "POE":
        degradation -= 0.5
        reliability_score += 0.5
    if backsheet == "PET":
        degradation += 0.5
        reliability_score -= 1

    base_power = 420  # W
    est_power_year_1 = base_power * (1 - degradation / 100)
    pr = 80 + (np.random.rand() * 5 - 2.5)

    df = pd.DataFrame({
        "Metric": ["Estimated Power (Year 1)", "Degradation (%)", "Reliability Score", "Performance Ratio"],
        "Value": [f"{est_power_year_1:.1f} W", f"{degradation:.2f}%", f"{reliability_score:.1f}/100", f"{pr:.1f}%"]
    })
    st.table(df)

    # 🔍 Show summary
    st.subheader("🛠️ Component & Test Summary")
    encapsulant_sup = materials_df[(materials_df["Material"] == "Encapsulant") & (materials_df["Type"] == encapsulant)]
    backsheet_sup = materials_df[(materials_df["Material"] == "Backsheet") & (materials_df["Type"] == backsheet)]
    glass_sup = materials_df[(materials_df["Material"] == "Glass") & (materials_df["Type"] == glass_type)]

    def format_supplier(row):
        return f"{row['Type']} ({row['Supplier']} - {row['Region']} - {row['Certifications']})"

    st.markdown(f"""
    - **Encapsulant**: {format_supplier(encapsulant_sup.iloc[0]) if not encapsulant_sup.empty else encapsulant}  
    - **Backsheet**: {format_supplier(backsheet_sup.iloc[0]) if not backsheet_sup.empty else backsheet}  
    - **Glass**: {format_supplier(glass_sup.iloc[0]) if not glass_sup.empty else glass_type}  
    - **Cell Type**: {cell_type}  
    - **Interconnect**: {interconnect}  
    - **Location**: {location}  
    - **DH Hours**: {damp_heat_hours} h  
    - **Thermal Cycles**: {thermal_cycles}  
    - **IEC Tests**: {', '.join(iec_tests) if iec_tests else "None"}
    """)
