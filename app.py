import streamlit as st
import pandas as pd
import numpy as np
import requests

# --- Page Setup ---
st.set_page_config("PVDevSim – Map-Driven Simulator", layout="wide")
st.title("📍 PVDevSim – Interactive Map-Based PV Simulation")

# --- Load Required CSVs ---
try:
    bom_df = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("failure_risk_matrix_v2.csv")
except Exception as e:
    st.error(f"❌ Error loading CSVs: {e}")
    st.stop()

# --- Step 1: Location Selection via Map ---
st.sidebar.header("🌎 Select Location")
default_lat, default_lon = 25.2048, 55.2708  # Default to Dubai
location = st.sidebar.map(center={"lat": default_lat, "lon": default_lon}, zoom=2)

if location is None or not location["selected_rows"]:
    lat, lon = default_lat, default_lon
    st.info("📍 Using default location: Dubai")
else:
    lat = location["selected_rows"][0]["lat"]
    lon = location["selected_rows"][0]["lon"]
    st.success(f"📍 Selected location: Lat {lat:.2f}, Lon {lon:.2f}")

# --- Step 2: Fetch TMY from PVGIS ---
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
        st.error(f"❌ PVGIS parsing failed: {e}")
        return None

weather_df = get_pvgis_tmy(lat, lon)
if weather_df is None or weather_df.empty:
    st.error("⚠️ Could not retrieve TMY weather data. Try a different location.")
    st.stop()

# --- Step 3: Extract Environment Stressors ---
avg_temp = weather_df["T2m"].mean()
avg_irr = weather_df["G(h)"].mean()
uv_index = avg_irr / 50  # UV proxy

# --- Step 4: Sidebar - BOM Selection ---
st.sidebar.header("🔧 Module BOM")
selections = {}

# Encapsulant Front & Rear
for encap in ["Encapsulant - Front", "Encapsulant - Rear"]:
    options = bom_df[bom_df["Component"] == encap]["Type"].unique()
    sel = st.sidebar.selectbox(encap, options, key=encap)
    row = bom_df[(bom_df["Component"] == encap) & (bom_df["Type"] == sel)].iloc[0]
    selections[encap] = row

# Other Components
for comp in bom_df["Component"].unique():
    if "Encapsulant" in comp:
        continue
    options = bom_df[bom_df["Component"] == comp]["Type"].unique()
    sel = st.sidebar.selectbox(comp, options, key=comp)
    row = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == sel)].iloc[0]
    selections[comp] = row

# --- Step 5: Test Profiles ---
st.sidebar.header("📋 Test Protocol")
test_profiles = {
    "None": {},
    "IEC Basic": {"UV": 0.3, "DH1000": 1.0, "TC200": 0.5},
    "PVEL Scorecard": {"UV": 0.5, "DH2000": 1.4, "PID": 1.0, "HF": 0.6, "LID": 0.4},
    "RETC MQI": {"UV": 0.4, "HF": 0.8, "Dynamic Load": 0.6, "PID": 0.8}
}
profile = st.sidebar.selectbox("Standard", list(test_profiles.keys()))
selected_tests = test_profiles.get(profile, {})
total_test_score = sum(selected_tests.values())

# --- Step 6: Degradation Model ---
def arrhenius(temp, Ea=0.7, Tref=298):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / Tref - 1 / T))

accel_factor = arrhenius(avg_temp)
base_deg = 0.5
deg_rate = base_deg * accel_factor + uv_index * 0.03 + total_test_score * 0.05
year1 = deg_rate
year25 = year1 * 25 * 0.95
reliability = max(0, 100 - year25)

# --- Step 7: Risk Matrix Lookup ---
def get_failures(material, test_keys):
    rows = []
    for t in test_keys:
        matched = risk_df[
            (risk_df["Material"].str.contains(material, case=False)) &
            (risk_df["Stress"].str.contains(t.split()[0], case=False))
        ]
        if not matched.empty:
            matched = matched.copy()
            matched["Component"] = ""
            rows.append(matched)
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# --- Step 8: Run Simulation ---
if st.sidebar.button("▶️ Simulate"):

    st.subheader(f"📍 Environmental Conditions at Selected Location")
    st.write(f"**Avg Temp:** {avg_temp:.1f} °C | **Irradiance:** {avg_irr:.1f} W/m² | **UV Index Proxy:** {uv_index:.2f}")

    st.subheader("📋 Bill of Materials")
    bom_table = pd.DataFrame([
        {"Component": k, "Material": v["Type"], "Supplier": v["Supplier"], "Region": v["Region"], "Certifications": v["Certifications"]}
        for k, v in selections.items()
    ])
    st.dataframe(bom_table)

    st.subheader("📉 Degradation Metrics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Arrhenius Factor", f"{accel_factor:.2f}")
    col2.metric("Year 1 Degradation", f"{year1:.2f}%")
    col3.metric("25-Year Loss", f"{year25:.2f}%")
    col4.metric("Reliability Score", f"{reliability:.1f}/100")

    st.subheader("🚨 Failure Risk Analysis")
    if selected_tests:
        risk_rows = []
        for comp, row in selections.items():
            mat = row["Type"]
            fail_df = get_failures(mat, selected_tests.keys())
            if not fail_df.empty:
                fail_df["Component"] = comp
                risk_rows.append(fail_df)
        if risk_rows:
            final_risk_df = pd.concat(risk_rows)
            st.dataframe(final_risk_df[["Component", "Material", "Stress", "Failure Mode", "Risk Score"]])
        else:
            st.success("✅ No significant risks found for the selected BOM and test conditions.")
    else:
        st.info("ℹ️ Select a test standard to enable failure matrix analysis.")
