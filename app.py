import streamlit as st
import pandas as pd
import numpy as np

st.set_page_config("PV Module Development Simulator", layout="wide")
st.title("🔬 PVDevSim – PV Module Development Simulator")

# --- Material Selection ---
st.sidebar.header("🧪 Material Selection")
encapsulant = st.sidebar.selectbox("Encapsulant Type", ["EVA", "POE", "TPU"])
backsheet = st.sidebar.selectbox("Backsheet Type", ["TPT", "PET", "Co-ex"])
glass_type = st.sidebar.selectbox("Glass Type", ["Standard", "AR-coated", "Glass-Glass"])
cell_type = st.sidebar.selectbox("Cell Type", ["PERC", "TOPCon", "HJT", "IBC"])
interconnect = st.sidebar.selectbox("Interconnection", ["Ribbon", "Wire", "Shingled"])

# --- Supplier Selection ---
st.sidebar.header("🏭 Supplier / BOM")
encapsulant_supplier = st.sidebar.selectbox("Encapsulant Supplier", ["DuPont", "Mitsui", "Hangzhou First"])
backsheet_supplier = st.sidebar.selectbox("Backsheet Supplier", ["3M", "Cybrid", "Coveme"])
glass_supplier = st.sidebar.selectbox("Glass Supplier", ["Xinyi", "Flat Glass", "CNBM"])

# --- Environmental Simulation ---
st.sidebar.header("🌤️ Environmental Conditions")
location = st.sidebar.selectbox("Deployment Location", ["Arizona", "India", "Germany", "China", "Middle East"])
damp_heat_hours = st.sidebar.slider("Damp Heat (Hours)", 0, 5000, 2000)
thermal_cycles = st.sidebar.slider("Thermal Cycles", 0, 1000, 200)

# --- Simulation Trigger ---
simulate = st.sidebar.button("Run Simulation")

if simulate:
    st.subheader("📈 Simulation Results")

    # Dummy performance & reliability estimation logic
    degradation = 2 + (0.001 * damp_heat_hours) + (0.002 * thermal_cycles)
    reliability_score = 100 - degradation

    # Material impact
    if encapsulant == "POE":
        degradation -= 0.5
        reliability_score += 0.5
    if backsheet == "PET":
        degradation += 0.5
        reliability_score -= 1

    base_power = 420  # W
    est_power_year_1 = base_power * (1 - degradation / 100)
    pr = 80 + (np.random.rand() * 5 - 2.5)  # Random variation in PR

    # Result table
    df = pd.DataFrame({
        "Metric": ["Estimated Power (Year 1)", "Degradation (%)", "Reliability Score", "Performance Ratio"],
        "Value": [f"{est_power_year_1:.1f} W", f"{degradation:.2f}%", f"{reliability_score:.1f}/100", f"{pr:.1f}%"]
    })

    st.table(df)

    # BOM & Summary
    st.subheader("🛠️ Component Summary")
    st.markdown(f"""
    - **Encapsulant**: {encapsulant} ({encapsulant_supplier})  
    - **Backsheet**: {backsheet} ({backsheet_supplier})  
    - **Glass**: {glass_type} ({glass_supplier})  
    - **Cell Type**: {cell_type}  
    - **Interconnect**: {interconnect}  
    - **Location**: {location}  
    - **Test Conditions**: {damp_heat_hours}h Damp Heat, {thermal_cycles} Thermal Cycles  
    """)
