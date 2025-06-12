import streamlit as st
import pandas as pd
import numpy as np
import requests
import matplotlib.pyplot as plt

st.set_page_config("PVDevSim Pro", layout="wide")
st.title("☀️ PVDevSim – Advanced PV Module Reliability Simulator")

# Load required CSVs
try:
    bom_df = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("enhanced_failure_risk_matrix.csv")
    weibull_df = pd.read_csv("weibull_parameters_by_supplier.csv")
except Exception as e:
    st.error(f"❌ Missing required file: {e}")
    st.stop()

# City selection
city_coords = {
    "Phoenix, USA": (33.45, -112.07),
    "Chennai, India": (13.08, 80.27),
    "Munich, Germany": (48.14, 11.58),
    "Dubai, UAE": (25.20, 55.27),
    "São Paulo, Brazil": (-23.55, -46.63)
}
city = st.sidebar.selectbox("🌍 Location", list(city_coords.keys()))
lat, lon = city_coords[city]

@st.cache_data
def get_weather(lat, lon):
    url = f"https://re.jrc.ec.europa.eu/api/tmy?lat={lat}&lon={lon}&outputformat=json"
    r = requests.get(url)
    if r.status_code != 200: return None
    try:
        df = pd.DataFrame(r.json()["outputs"]["tmy_hourly"])
        df["time"] = pd.date_range("2023-01-01", periods=len(df), freq="H")
        return df
    except: return None

weather_df = get_weather(lat, lon)
if weather_df is None:
    st.error("⚠️ Weather fetch failed")
    st.stop()

avg_temp = weather_df["T2m"].mean()
avg_rh = weather_df["RH"].mean()
avg_irr = weather_df["G(h)"].mean()
uv_index = avg_irr / 50

# Stress Profiles
test_profiles = {
    "None": {},
    "IEC Basic": {"UV": 0.3, "DH2000": 1.0, "TC200": 0.5},
    "PVEL Scorecard": {"UV": 0.5, "DH2000": 1.4, "PID": 1.0, "HF": 0.6},
    "RETC MQI": {"UV": 0.4, "HF": 0.8, "Dynamic Load": 0.6, "PID": 0.8}
}
profile = st.sidebar.selectbox("🧪 Stress Profile", list(test_profiles.keys()))
selected_tests = test_profiles.get(profile, {})

# BOM selector
def select_bom(label):
    st.sidebar.header(f"🔧 {label}")
    selections = {}
    for comp in bom_df["Component"].unique():
        types = bom_df[bom_df["Component"] == comp]["Type"].unique()
        selected = st.sidebar.selectbox(f"{comp} – {label}", types, key=f"{label}-{comp}")
        row = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == selected)].iloc[0]
        selections[comp] = row
    return selections

bom1 = select_bom("BOM 1")
bom2 = select_bom("BOM 2")

# Degradation modeling
def arrhenius(temp, Ea=0.7):
    k = 8.617e-5
    T = temp + 273.15
    return np.exp((Ea / k) * (1 / 298 - 1 / T))

def weibull_survival(years, eta, beta):
    return np.exp(-(years / eta) ** beta)

def simulate_bom(bom, label):
    front_encap = bom["Encapsulant - Front"]["Type"]
    cell = bom["Cell"]["Type"]
    mat_row = weibull_df[weibull_df["Material"] == front_encap]
    cell_row = weibull_df[weibull_df["Material"] == cell]

    years = np.arange(1, 26)

    if mat_row.empty or cell_row.empty:
        st.warning(f"⚠️ Weibull parameters not found for {label} – {front_encap} or {cell}")
        return pd.DataFrame({"Year": years, f"{label} Reliability": [np.nan]*25})

    mat = mat_row.iloc[0]
    cell = cell_row.iloc[0]

    eta_m = mat["Base_Lifetime"] / arrhenius(avg_temp, mat["Ea"])
    eta_c = cell["Base_Lifetime"] / arrhenius(avg_temp, cell["Ea"])

    surv_m = weibull_survival(years, eta_m, mat["Beta"])
    surv_c = weibull_survival(years, eta_c, cell["Beta"])

    rh_factor = 1 + 0.01 * (avg_rh - 50)
    uv_factor = 1 + 0.02 * (uv_index - 5)
    stress_factor = 1 + 0.05 * sum(selected_tests.values())

    combined = (surv_m + surv_c) / 2 / (rh_factor * uv_factor * stress_factor)
    return pd.DataFrame({"Year": years, f"{label} Reliability": combined * 100})

# Risk Matrix
def get_failures(material, test_keys):
    rows = []
    for t in test_keys:
        match = risk_df[(risk_df["Material"].str.contains(material, case=False)) &
                        (risk_df["Stress"].str.contains(t.split()[0], case=False))]
        if not match.empty:
            match["Component"] = ""
            rows.append(match)
    return pd.concat(rows) if rows else pd.DataFrame(columns=risk_df.columns)

# Run simulation
if st.sidebar.button("▶️ Simulate"):

    st.subheader(f"📍 {city} – Site Conditions")
    st.write(f"**Temp:** {avg_temp:.1f} °C | **RH:** {avg_rh:.1f}% | **Irradiance:** {avg_irr:.1f} W/m² | **UV Index:** {uv_index:.2f}")

    df1 = simulate_bom(bom1, "BOM 1")
    df2 = simulate_bom(bom2, "BOM 2")

    if not df1.empty and not df2.empty:
        result = pd.merge(df1, df2, on="Year")
        st.subheader("📉 Reliability Comparison (25 years)")
        st.line_chart(result.set_index("Year"))
        st.dataframe(result)

    st.subheader("🚨 Failure Risk Matrix")
    if selected_tests:
        risks = []
        for comp, row in bom1.items():
            fails = get_failures(row["Type"], selected_tests.keys())
            if not fails.empty:
                fails["Component"] = comp
                risks.append(fails)
        if risks:
            df = pd.concat(risks)
            st.dataframe(df[["Component", "Material", "Stress", "Failure Mode", "Risk Score", "Field Insight"]])
        else:
            st.success("✅ No major risks found.")
    else:
        st.info("ℹ️ Select a test profile to view failure analysis.")
