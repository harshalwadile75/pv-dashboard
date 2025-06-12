# app.py - Enhanced PVDevSim with real-world modeling

import streamlit as st
import pandas as pd
import numpy as np
import requests
import datetime
import matplotlib.pyplot as plt
from io import BytesIO

# --- Page Config ---
st.set_page_config("PVDevSim – Realistic Simulator", layout="wide")
st.title("☀️ PVDevSim – Real-World Simulation & Risk Analysis")

# --- Load Data ---
try:
    bom_df = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("enhanced_failure_risk_matrix.csv")
    weibull_df = pd.read_csv("weibull_parameters_by_supplier.csv")
except Exception as e:
    st.error(f"❌ Missing CSV files: {e}")
    st.stop()

# --- City and Weather ---
st.sidebar.header("🌍 Select Project Location")
city_coords = {
    "Phoenix, USA": (33.4484, -112.0740),
    "Munich, Germany": (48.1351, 11.5820),
    "Chennai, India": (13.0827, 80.2707),
    "Dubai, UAE": (25.2048, 55.2708),
    "São Paulo, Brazil": (-23.5505, -46.6333)
}
city = st.sidebar.selectbox("City", list(city_coords.keys()))
lat, lon = city_coords[city]

@st.cache_data
def get_pvgis_weather(lat, lon):
    url = f"https://re.jrc.ec.europa.eu/api/tmy?lat={lat}&lon={lon}&outputformat=json"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    try:
        df = pd.DataFrame(r.json()["outputs"]["tmy_hourly"])
        df["time"] = pd.date_range("2023-01-01", periods=len(df), freq="H")
        return df
    except:
        return None

weather_df = get_pvgis_weather(lat, lon)
if weather_df is None or weather_df.empty:
    st.error("⚠️ Weather data fetch failed.")
    st.stop()

# --- Environmental Stats ---
avg_temp = weather_df["T2m"].mean()
avg_rh = weather_df["RH"].mean()
avg_irr = weather_df["G(h)"].mean()
uv_index = avg_irr / 50

# --- BOM Selection ---
st.sidebar.header("🔧 Module BOM")
selections = {}

for encap in ["Encapsulant - Front", "Encapsulant - Rear"]:
    options = bom_df[bom_df["Component"] == encap]["Type"].unique()
    sel = st.sidebar.selectbox(encap, options, key=encap)
    row = bom_df[(bom_df["Component"] == encap) & (bom_df["Type"] == sel)].iloc[0]
    selections[encap] = row

for comp in bom_df["Component"].unique():
    if "Encapsulant" in comp:
        continue
    options = bom_df[bom_df["Component"] == comp]["Type"].unique()
    sel = st.sidebar.selectbox(comp, options, key=comp)
    row = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == sel)].iloc[0]
    selections[comp] = row

# --- Test Profile Selection ---
st.sidebar.header("🧪 Test Profile")
test_profiles = {
    "None": {},
    "IEC Basic": {"UV": 0.3, "DH2000": 1.0, "TC200": 0.5},
    "PVEL Scorecard": {"UV": 0.5, "DH2000": 1.4, "PID": 1.0, "HF": 0.6, "LID": 0.4},
    "RETC MQI": {"UV": 0.4, "HF": 0.8, "Dynamic Load": 0.6, "PID": 0.8}
}
profile = st.sidebar.selectbox("Standard", list(test_profiles.keys()))
selected_tests = test_profiles.get(profile, {})
total_score = sum(selected_tests.values())

# --- Multi-Factor Degradation ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

def degradation_rate(material, temp, rh, uv, profile_score):
    base_deg = 0.45  # Default
    Ea = 0.7 if 'EVA' in material else 0.65
    temp_factor = arrhenius(temp, Ea)
    rh_factor = 1 + 0.01 * (rh - 50)
    uv_factor = 1 + 0.02 * (uv - 5)
    stress_factor = 1 + 0.04 * profile_score
    return base_deg * temp_factor * rh_factor * uv_factor * stress_factor

deg_rate = degradation_rate(selections['Encapsulant - Front']['Type'], avg_temp, avg_rh, uv_index, total_score)
year1 = deg_rate
year25 = year1 * 25 * 0.95
reliability = max(0, 100 - year25)

# --- Weibull Reliability Chart ---
def weibull_plot(material):
    try:
        row = weibull_df[weibull_df['Material'].str.contains(material, case=False)].iloc[0]
        beta = row['Beta']
        eta = row['Base_Lifetime'] / arrhenius(avg_temp, row['Ea'])
        years = np.arange(1, 26)
        survival = np.exp(-(years / eta) ** beta)
        fig, ax = plt.subplots()
        ax.plot(years, survival * 100, label=f"{material} Survival")
        ax.set_ylabel("Survival Probability (%)")
        ax.set_xlabel("Year")
        ax.set_title("Weibull Reliability")
        st.pyplot(fig)
    except Exception as e:
        st.warning(f"Weibull model not available: {e}")

# --- Failure Risk Matrix Lookup ---
def get_failures(material, test_keys):
    rows = []
    for t in test_keys:
        match = risk_df[(risk_df["Material"].str.contains(material, case=False)) &
                        (risk_df["Stress"].str.contains(t.split()[0], case=False))]
        if not match.empty:
            match = match.copy()
            match["Component"] = ""
            rows.append(match)
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# --- Run Simulation ---
if st.sidebar.button("▶️ Simulate"):
    st.subheader(f"📍 Environmental Summary – {city}")
    st.write(f"**Temp:** {avg_temp:.1f}°C | **RH:** {avg_rh:.1f}% | **Irradiance:** {avg_irr:.1f} W/m²")

    st.subheader("📋 Selected BOM")
    st.dataframe(pd.DataFrame([{"Component": k, **v} for k, v in selections.items()]))

    st.subheader("📉 Degradation & Reliability")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Year 1 Loss", f"{year1:.2f}%")
    col2.metric("25-Year Loss", f"{year25:.2f}%")
    col3.metric("Reliability", f"{reliability:.1f}/100")
    col4.metric("UV Index", f"{uv_index:.2f}")

    weibull_plot(selections['Encapsulant - Front']['Type'])

    st.subheader("🚨 Failure Risk Matrix")
    if selected_tests:
        risks = []
        for comp, row in selections.items():
            fails = get_failures(row['Type'], selected_tests.keys())
            if not fails.empty:
                fails["Component"] = comp
                risks.append(fails)
        if risks:
            df = pd.concat(risks)
            st.dataframe(df[["Component", "Material", "Stress", "Failure Mode", "Risk Score", "Field Insight"]])
        else:
            st.success("✅ No major risks found.")
    else:
        st.info("ℹ️ Select a test profile to enable failure analysis.")
