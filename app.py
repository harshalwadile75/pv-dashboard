import streamlit as st
import pandas as pd
import requests
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

st.set_page_config("Simple PV Simulator", layout="wide")
st.title("🔆 PVsyst-Style PV Simulation App")

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("System Inputs")
    lat = float(st.number_input("Latitude", value=34.05))
    lon = float(st.number_input("Longitude", value=-118.25))
    system_kw = st.number_input("System Size (kW)", value=5.0)
    tilt = st.slider("Tilt Angle (°)", 0, 60, 25)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)
    cost_per_watt = st.number_input("System Cost ($/W)", 0.5, 5.0, 1.2)
    rate = st.number_input("Electricity Rate ($/kWh)", 0.05, 0.50, 0.12)

# --- Weather Function ---
def get_weather(lat, lon):
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        st.error("Invalid latitude or longitude values.")
        return pd.DataFrame()

    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=global_horizontal_irradiance,temperature_2m&timezone=UTC"
    )
    response = requests.get(url)

    if response.status_code != 200:
        st.error(f"Failed to fetch weather: {response.status_code}")
        return pd.DataFrame()

    data = response.json()
    if 'hourly' not in data:
        st.error("Incomplete weather data returned.")
        return pd.DataFrame()

    time = pd.to_datetime(data['hourly']['time'])
    ghi = data['hourly']['global_horizontal_irradiance']
    temp = data['hourly']['temperature_2m']
    df = pd.DataFrame({'ghi': ghi, 'temp_air': temp}, index=time)
    df.index.name = 'time'
    return df.resample('M').mean()

# --- Get Weather ---
st.subheader("☀️ Weather Data")
weather = get_weather(lat, lon)
if weather.empty:
    st.stop()
st.write(weather.head())

# --- Simulate Energy ---
def simulate(weather, system_kw, tilt, azimuth):
    location = Location(lat, lon, 'UTC')
    system = PVSystem(surface_tilt=tilt, surface_azimuth=azimuth,
                      module_parameters={'pdc0': system_kw * 1000})
    mc = ModelChain(system, location)
    mc.weather = weather.rename(columns={'ghi': 'poa_global', 'temp_air': 'temp_air'})
    mc.run_model_from_poa_irradiance(mc.weather['poa_global'], mc.weather['temp_air'])
    monthly_energy = mc.ac.resample('M').sum() / 1000
    df = pd.DataFrame({"Month": monthly_energy.index.month_name(), "Energy (kWh)": monthly_energy.values})
    df.set_index("Month", inplace=True)
    return df

energy_df = simulate(weather, system_kw, tilt, azimuth)

# --- Display Output ---
st.subheader("📊 Monthly Energy Output")
st.bar_chart(energy_df)

# --- Summary Metrics ---
st.subheader("📈 Summary")
annual_kwh = energy_df['Energy (kWh)'].sum()
cost = system_kw * 1000 * cost_per_watt
savings = annual_kwh * rate
payback = cost / savings if savings > 0 else None

col1, col2, col3 = st.columns(3)
col1.metric("Annual Output", f"{annual_kwh:.1f} kWh")
col2.metric("Estimated Savings", f"${savings:.2f}")
col3.metric("Payback Period", f"{payback:.1f} yrs" if payback else "N/A")
