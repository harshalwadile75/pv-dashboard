import streamlit as st
import pandas as pd
import requests
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

st.set_page_config("PV System Simulator", layout="wide")
st.title("🔆 PVsyst-Like Solar Simulation App")

# --- Cities with coordinates ---
cities = [
    {"city": "Los Angeles, USA", "lat": 34.05, "lon": -118.25},
    {"city": "New York, USA", "lat": 40.71, "lon": -74.01},
    {"city": "London, UK", "lat": 51.51, "lon": -0.13},
    {"city": "Tokyo, Japan", "lat": 35.68, "lon": 139.76},
    {"city": "Delhi, India", "lat": 28.61, "lon": 77.20},
    {"city": "Berlin, Germany", "lat": 52.52, "lon": 13.41},
    {"city": "Sydney, Australia", "lat": -33.87, "lon": 151.21},
    {"city": "São Paulo, Brazil", "lat": -23.55, "lon": -46.63},
    {"city": "Cairo, Egypt", "lat": 30.04, "lon": 31.24},
    {"city": "Cape Town, South Africa", "lat": -33.92, "lon": 18.42}
]

modules = [
    {"brand": "Qcells", "model": "Q.PEAK DUO ML-G10+", "power": 410, "efficiency": 20.9},
    {"brand": "Canadian Solar", "model": "HiKu6", "power": 450, "efficiency": 21.3},
    {"brand": "LONGi", "model": "Hi-MO 5m", "power": 500, "efficiency": 21.0}
]

inverters = [
    {"brand": "SMA", "model": "Sunny Boy 5.0", "rated_power": 5000, "efficiency": 97.5},
    {"brand": "Huawei", "model": "SUN2000-6KTL", "rated_power": 6000, "efficiency": 98.6},
    {"brand": "Fronius", "model": "Primo 5.0", "rated_power": 5000, "efficiency": 97.8}
]

module_models = [f"{m['brand']} - {m['model']} ({m['power']}W)" for m in modules]
inverter_models = [f"{i['brand']} - {i['model']} ({i['rated_power']}W)" for i in inverters]
city_names = [c['city'] for c in cities]

# --- Sidebar Inputs ---
with st.sidebar:
    st.header("📍 Location & Setup")
    selected_city = st.selectbox("Select City", city_names)
    city_data = next(c for c in cities if c['city'] == selected_city)
    lat, lon = city_data['lat'], city_data['lon']

    tilt = st.slider("Tilt Angle (°)", 0, 60, 25)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)

    st.header("🔌 Components")
    selected_module = st.selectbox("PV Module", module_models)
    selected_inverter = st.selectbox("Inverter", inverter_models)

    st.header("💰 Financials")
    cost_per_watt = st.number_input("System Cost ($/W)", 0.5, 5.0, 1.2)
    rate = st.number_input("Electricity Rate ($/kWh)", 0.05, 0.50, 0.12)
    simulate = st.button("Run Simulation")

# --- Weather Fetch Function using Tomorrow.io ---
def get_weather(lat, lon):
    api_key = "YOUR_TOMORROW_IO_API_KEY"  # Replace with your actual Tomorrow.io API key
    url = f"https://api.tomorrow.io/v4/weather/forecast?location={lat},{lon}&fields=solarGHI,temperature&timesteps=1h&apikey={api_key}"

    try:
        r = requests.get(url)
        if r.status_code != 200:
            st.error(f"Weather fetch failed: {r.status_code}")
            return pd.DataFrame()

        data = r.json()
        timeline = data.get("timelines", {}).get("hourly", [])
        if not timeline:
            st.error("No hourly weather data available.")
            return pd.DataFrame()

        records = timeline[0]['intervals']
        times = [pd.to_datetime(r['startTime']) for r in records]
        ghi = [r['values'].get('solarGHI', 0) for r in records]
        temp = [r['values'].get('temperature', 20) for r in records]

        df = pd.DataFrame({'ghi': ghi, 'temp_air': temp}, index=times)
        return df.resample('M').mean()

    except Exception as e:
        st.error(f"Error fetching or parsing weather: {e}")
        return pd.DataFrame()

# --- Main Simulation ---
if simulate:
    mod = modules[module_models.index(selected_module)]
    inv = inverters[inverter_models.index(selected_inverter)]

    st.subheader(f"☀️ Weather Data for {selected_city}")
    weather = get_weather(lat, lon)
    if weather.empty:
        st.stop()
    st.write(weather.head())

    st.subheader("🔋 Energy Simulation")
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

    st.subheader("📈 System Insights")
    annual_kwh = df["Energy (kWh)"].sum()
    system_kw = mod['power'] / 1000
    cost = system_kw * 1000 * cost_per_watt
    savings = annual_kwh * rate
    payback = cost / savings if savings > 0 else None
    pr = annual_kwh / (system_kw * 365 * 5) * 100  # ~5 hours/day average

    col1, col2, col3 = st.columns(3)
    col1.metric("Annual Output", f"{annual_kwh:.1f} kWh")
    col2.metric("Estimated Savings", f"${savings:.2f}")
    col3.metric("Payback Period", f"{payback:.1f} yrs" if payback else "N/A")
    st.metric("Performance Ratio (est)", f"{pr:.1f}%")
