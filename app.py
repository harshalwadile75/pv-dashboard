import streamlit as st
import pandas as pd
import requests
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

st.set_page_config("Simple PV Simulator", layout="wide")
st.title("🔆 PVsyst-Style PV Simulation App")

# --- Default Values ---
DEFAULT_LAT = 34.05
DEFAULT_LON = -118.25

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("System Inputs")
    lat = st.number_input("Latitude (-90 to 90)", min_value=-90.0, max_value=90.0, value=DEFAULT_LAT)
    lon = st.number_input("Longitude (-180 to 180)", min_value=-180.0, max_value=180.0, value=DEFAULT_LON)
    system_kw = st.number_input("System Size (kW)", min_value=0.1, value=5.0)
    tilt = st.slider("Tilt Angle (°)", 0, 60, 25)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)
    cost_per_watt = st.number_input("System Cost ($/W)", min_value=0.5, value=1.2)
    rate = st.number_input("Electricity Rate ($/kWh)", min_value=0.05, value=0.12)
    run_button = st.button("Run Simulation")

# --- Weather Function ---
def get_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}"
        "&hourly=global_horizontal_irradiance,temperature_2m&timezone=UTC"
    )
    try:
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

    except Exception as e:
        st.error(f"Error fetching weather data: {e}")
        return pd.DataFrame()

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

# --- Main Run ---
if run_button:
    st.subheader("☀️ Weather Data")
    weather = get_weather(lat, lon)
    if weather.empty:
        st.stop()
    st.write(weather.head())

    st.subheader("🔋 Simulated Monthly Energy Output")
    energy_df = simulate(weather, system_kw, tilt, azimuth)
    st.bar_chart(energy_df)

    st.subheader("📈 Summary")
    annual_kwh = energy_df['Energy (kWh)'].sum()
    cost = system_kw * 1000 * cost_per_watt
    savings = annual_kwh * rate
    payback = cost / savings if savings > 0 else None

    col1, col2, col3 = st.columns(3)
    col1.metric("Annual Output", f"{annual_kwh:.1f} kWh")
    col2.metric("Estimated Savings", f"${savings:.2f}")
    col3.metric("Payback Period", f"{payback:.1f} yrs" if payback else "N/A")
