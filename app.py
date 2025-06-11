import streamlit as st
import pandas as pd
import requests
import json
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

st.set_page_config("PV System Simulator", layout="wide")
st.title("🔆 PVsyst-Like Solar Simulation App")

# --- Load Modules and Inverters ---
with open("data/modules.json", "r") as f:
    modules = json.load(f)

with open("data/inverters.json", "r") as f:
    inverters = json.load(f)

module_models = [f"{m['brand']} - {m['model']} ({m['power']}W)" for m in modules]
inverter_models = [f"{i['brand']} - {i['model']} ({i['rated_power']}W)" for i in inverters]

# --- Inputs ---
with st.sidebar:
    st.header("Location & Setup")
    lat = st.number_input("Latitude", -90.0, 90.0, 34.05)
    lon = st.number_input("Longitude", -180.0, 180.0, -118.25)
    tilt = st.slider("Tilt Angle (°)", 0, 60, 25)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)

    st.header("Components")
    selected_module = st.selectbox("PV Module", module_models)
    selected_inverter = st.selectbox("Inverter", inverter_models)

    st.header("Financials")
    cost_per_watt = st.number_input("System Cost ($/W)", 0.5, 5.0, 1.2)
    rate = st.number_input("Electricity Rate ($/kWh)", 0.05, 0.50, 0.12)
    simulate = st.button("Simulate")

# --- Utility Functions ---
def get_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=global_horizontal_irradiance,temperature_2m&timezone=UTC"
    )
    try:
        r = requests.get(url)
        if r.status_code != 200:
            st.error(f"Weather fetch failed: {r.status_code}")
            return pd.DataFrame()

        data = r.json()
        time = pd.to_datetime(data['hourly']['time'])
        ghi = data['hourly']['global_horizontal_irradiance']
        temp = data['hourly']['temperature_2m']
        df = pd.DataFrame({'ghi': ghi, 'temp_air': temp}, index=time)
        return df.resample('M').mean()
    except Exception as e:
        st.error(f"Error fetching weather: {e}")
        return pd.DataFrame()

# --- Simulation ---
if simulate:
    mod = modules[module_models.index(selected_module)]
    inv = inverters[inverter_models.index(selected_inverter)]

    st.subheader("☀️ Fetching Weather...")
    weather = get_weather(lat, lon)
    if weather.empty:
        st.stop()
    st.write(weather.head())

    st.subheader("🔋 Simulating Energy Output...")
    location = Location(lat, lon, 'UTC')
    system = PVSystem(
        surface_tilt=tilt,
        surface_azimuth=azimuth,
        module_parameters={'pdc0': mod['power']},
        inverter_parameters={'pdc': inv['rated_power']}
    )
    mc = ModelChain(system, location)
    mc.weather = weather.rename(columns={'ghi': 'poa_global', 'temp_air': 'temp_air'})
    mc.run_model_from_poa_irradiance(mc.weather['poa_global'], mc.weather['temp_air'])
    energy = mc.ac.resample('M').sum() / 1000

    df = pd.DataFrame({
        "Month": energy.index.month_name(),
        "Energy (kWh)": energy.values
    }).set_index("Month")

    st.subheader("📊 Monthly Energy Output")
    st.bar_chart(df)
    st.dataframe(df)

    st.subheader("📈 Performance Summary")
    annual_kwh = df["Energy (kWh)"].sum()
    system_kw = mod['power'] / 1000
    cost = system_kw * 1000 * cost_per_watt
    savings = annual_kwh * rate
    payback = cost / savings if savings > 0 else None
    pr = annual_kwh / (system_kw * 365 * 5) * 100  # rough est

    col1, col2, col3 = st.columns(3)
    col1.metric("Annual Output", f"{annual_kwh:.1f} kWh")
    col2.metric("Estimated Savings", f"${savings:.2f}")
    col3.metric("Payback Period", f"{payback:.1f} yrs" if payback else "N/A")
    st.metric("Performance Ratio (est)", f"{pr:.1f}%")
