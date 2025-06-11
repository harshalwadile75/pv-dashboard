import streamlit as st
import pandas as pd
import requests
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

st.set_page_config("Simple PV Analyzer", layout="wide")
st.title("🔆 Simple PV Analyzer (PVsyst-style)")

# --- User Inputs ---
with st.sidebar:
    st.header("System Configuration")
    lat = st.number_input("Latitude", value=34.05)
    lon = st.number_input("Longitude", value=-118.25)
    system_size_kw = st.number_input("System Size (kW)", value=5.0)
    tilt = st.slider("Tilt Angle (°)", 0, 60, 25)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)
    cost_per_watt = st.number_input("System Cost ($/W)", 0.5, 5.0, 1.2)
    rate = st.number_input("Electricity Rate ($/kWh)", 0.05, 0.50, 0.12)

# --- Get Live Weather Data ---
def get_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        "&hourly=global_horizontal_irradiance,temperature_2m&timezone=UTC"
    )
    r = requests.get(url)
    data = r.json()
    time = pd.to_datetime(data['hourly']['time'])
    ghi = data['hourly']['global_horizontal_irradiance']
    temp = data['hourly']['temperature_2m']
    df = pd.DataFrame({'ghi': ghi, 'temp_air': temp}, index=time)
    df.index.name = 'time'
    df = df.resample('M').mean()
    return df

st.subheader("📡 Fetching Weather Data...")
weather = get_weather(lat, lon)
st.write(weather.head())

# --- Simulate Performance ---
def simulate(weather, size_kw, tilt, azimuth):
    system = PVSystem(surface_tilt=tilt, surface_azimuth=azimuth,
                      module_parameters={'pdc0': size_kw * 1000})
    location = Location(lat, lon, 'UTC')
    mc = ModelChain(system, location)
    mc.weather = weather.rename(columns={'ghi': 'poa_global', 'temp_air': 'temp_air'})
    mc.run_model_from_poa_irradiance(mc.weather['poa_global'], mc.weather['temp_air'])
    monthly_energy = mc.ac.resample('M').sum() / 1000
    df = pd.DataFrame({"Month": monthly_energy.index.month_name(), "Energy (kWh)": monthly_energy.values})
    df.set_index("Month", inplace=True)
    return df, mc

energy_df, mc = simulate(weather, system_size_kw, tilt, azimuth)

st.subheader("📊 Monthly Energy Output")
st.bar_chart(energy_df)

# --- Summary Metrics ---
st.subheader("📈 Key Metrics")
annual_kwh = energy_df['Energy (kWh)'].sum()
cost = system_size_kw * 1000 * cost_per_watt
savings = annual_kwh * rate
payback = cost / savings if savings > 0 else None

col1, col2, col3 = st.columns(3)
col1.metric("Annual Output", f"{annual_kwh:.2f} kWh")
col2.metric("Estimated Savings", f"${savings:.2f}")
col3.metric("Payback Period", f"{payback:.1f} years" if payback else "N/A")

