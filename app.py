import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- Setup Page ---
st.set_page_config("PVDevSim – City-Based PV Simulation", layout="wide")
st.title("☀️ PVDevSim – Weather-Based Reliability Simulation")

# --- Load Required Data ---
try:
    bom_df = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("failure_risk_matrix_v2.csv")
except Exception as e:
    st.error(f"❌ Missing required CSVs: {e}")
    st.stop()

# --- City Dropdown Selection ---
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

# --- Get TMY Weather Data ---
@st.cache_data
def get_pvgis_tmy(lat, lon):
    url = f"https://re.jrc.ec.europa.eu/api/tmy?lat={lat}&lon={lon}&outputformat=json"
    r = requests.get(url)
    if r.status_code != 200:
        return None
    try:
        data = r.json()["outputs"]["tmy_hourly"]
        df = pd.DataFrame(data)
        if "time" not in df.columns:
            df["time"] = pd.date_range("2023-01-01", periods=len(df), freq="H")
        else:
            df["time"] = pd.to_datetime(df["time"])
        return df
    except Exception as e:
        st.error(f"❌ Error parsing PVGIS data: {e}")
        return None

weather_df = get_pvgis_tmy(lat, lon)
if weather_df is None or weather_df.empty:
    st.error("⚠️ Could not retrieve weather data. Try another city.")
    st.stop()

# --- Environmental Averages ---
avg_temp = weather_df["T2m"].mean()
avg_irr = weather_df["G(h)"].mean()
uv_index = avg_irr / 50  # UV proxy

# --- BOM Selection ---
st.sidebar.header("🔧 Bill of Materials")
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

# --- Test Protocol Selection ---
st.sidebar.header("🧪 Test Profile")
test_profiles = {
    "None": {},
    "IEC Basic": {"UV": 0.3, "DH1000": 1.0, "TC200": 0.5},
    "PVEL Scorecard": {"UV": 0.5, "DH2000": 1.4, "PID": 1.0, "HF": 0.6, "LID": 0.4},
    "RETC MQI": {"UV": 0.4, "HF": 0.8, "Dynamic Load": 0.6, "PID": 0.8}
}
profile = st.sidebar.selectbox("Standard", list(test_profiles.keys()))
selected_tests = test_profiles.get(profile, {})
total_score = sum(selected_tests.values())

# --- Degradation Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel = arrhenius(avg_temp)
base_deg = 0.5
deg_rate = base_deg * accel + uv_index * 0.03 + total_score * 0.05
year1 = deg_rate
year25 = year1 * 25 * 0.95
reliability = max(0, 100 - year25)

# --- Risk Lookup ---
def get_failures(material, test_keys):
    rows = []
    for t in test_keys:
        match = risk_df[
            (risk_df["Material"].str.contains(material, case=False)) &
            (risk_df["Stress"].str.contains(t.split()[0], case=False))
        ]
        if not match.empty:
            match = match.copy()
            match["Component"] = ""
            rows.append(match)
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# --- Run Simulation ---
if st.sidebar.button("▶️ Run Simulation"):

    st.subheader(f"📍 Environmental Conditions – {city}")
    st.write(f"**Temperature:** {avg_temp:.1f} °C | **Irradiance:** {avg_irr:.1f} W/m² | **UV Index (proxy):** {uv_index:.2f}")

    st.subheader("📋 Selected Bill of Materials")
    bom_table = pd.DataFrame([
        {"Component": k, "Material": v["Type"], "Supplier": v["Supplier"],
         "Region": v["Region"], "Certifications": v["Certifications"]}
        for k, v in selections.items()
    ])
    st.dataframe(bom_table)

    st.subheader("📉 Degradation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Arrhenius Factor", f"{accel:.2f}")
    col2.metric("Year-1 Degradation", f"{year1:.2f}%")
    col3.metric("25-Year Loss", f"{year25:.2f}%")
    col4.metric("Reliability Score", f"{reliability:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    if selected_tests:
        risks = []
        for comp, row in selections.items():
            material = row["Type"]
            failure_df = get_failures(material, selected_tests.keys())
            if not failure_df.empty:
                failure_df["Component"] = comp
                risks.append(failure_df)
        if risks:
            final_risks = pd.concat(risks)
            st.dataframe(final_risks[["Component", "Material", "Stress", "Failure Mode", "Risk Score"]])
        else:
            st.success("✅ No major risks found.")
    else:
        st.info("ℹ️ Select a test profile to analyze failure risk.")
