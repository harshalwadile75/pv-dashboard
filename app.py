import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from streamlit_folium import st_folium
import folium
from pvlib import location, irradiance, temperature, iotools

st.set_page_config(page_title="🌎 Solar Dashboard with Auto-Location & Map", layout="wide")
st.title("🌞 Solar Dashboard with Auto Location & Map Picker")

# Step 1: Select Location Input Mode
st.sidebar.header("📍 Location Input")
mode = st.sidebar.radio("Choose Location Mode", ["IP Auto-Detect", "Map Picker"])

if mode == "IP Auto-Detect":
    st.sidebar.write("🌐 Detecting your location...")
    try:
        ip_info = requests.get("https://ipinfo.io").json()
        loc = ip_info["loc"].split(",")
        lat, lon = float(loc[0]), float(loc[1])
        st.sidebar.success(f"📍 Location: {ip_info['city']} ({lat}, {lon})")
    except:
        st.sidebar.error("Unable to detect location. Please use map instead.")
        lat, lon = 40.7128, -74.0060
else:
    st.sidebar.write("🗺️ Click on the map to select a location")
    map_center = [20, 0]
    m = folium.Map(location=map_center, zoom_start=2)
    map_data = st_folium(m, height=350, returned_objects=["last_clicked"])
    if map_data and map_data["last_clicked"]:
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.sidebar.success(f"📌 Selected: ({lat:.4f}, {lon:.4f})")
    else:
        lat, lon = 20.0, 0.0

# PV System Configuration
st.sidebar.header("⚙️ PV System")
tilt = st.sidebar.slider("Tilt (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
module_power = st.sidebar.selectbox("Module Power (W)", [400, 450])
modules_series = st.sidebar.slider("Modules in Series", 5, 30, 15)
modules_parallel = st.sidebar.slider("Parallel Strings", 1, 10, 2)

# Losses
st.sidebar.header("🔧 Losses")
soiling = st.sidebar.slider("Soiling Loss (%)", 0, 10, 2)
shading = st.sidebar.slider("Shading Loss (%)", 0, 15, 3)
temp_loss = st.sidebar.slider("Temp Loss (%)", 0, 10, 2)
mismatch = st.sidebar.slider("Mismatch Loss (%)", 0, 5, 1)
wiring = st.sidebar.slider("Wiring Loss (%)", 0, 5, 1)
inverter_eff = st.sidebar.slider("Inverter Efficiency (%)", 90, 99, 97)

# Load TMY Data
st.subheader("☀️ Loading TMY Weather Data...")
try:
    tmy, meta = iotools.get_pvgis_tmy(lat, lon)
    site = location.Location(lat, lon, tz="Etc/GMT+5", altitude=meta.get("elevation", 10))
    tmy.index.name = "Time"
    st.success(f"TMY data loaded for {meta['location']} at {lat:.2f}, {lon:.2f}")
except Exception as e:
    st.error(f"Failed to fetch TMY data: {e}")
    st.stop()

# Calculate Irradiance
solpos = site.get_solarposition(tmy.index)
poa = irradiance.get_total_irradiance(
    surface_tilt=tilt,
    surface_azimuth=azimuth,
    dni=tmy["DNI"],
    ghi=tmy["GHI"],
    dhi=tmy["DHI"],
    solar_zenith=solpos["zenith"],
    solar_azimuth=solpos["azimuth"]
)

temps = temperature.sapm_cell(poa["poa_global"], tmy["TempAir"], 2)
system_kw = module_power * modules_series * modules_parallel / 1000
gross_power = poa["poa_global"] / 1000 * system_kw
total_losses = (soiling + shading + temp_loss + mismatch + wiring) / 100
net_power = gross_power * (1 - total_losses) * (inverter_eff / 100)
monthly_energy = net_power.resample("M").sum()

# Display Summary
annual_energy = monthly_energy.sum()
st.subheader("📊 System Performance")
col1, col2 = st.columns(2)
col1.metric("System Size", f"{system_kw:.2f} kW")
col2.metric("Annual Energy", f"{annual_energy:.0f} kWh")

# Plot Monthly Energy
st.subheader("📆 Monthly Energy Production")
fig, ax = plt.subplots()
monthly_energy.index = monthly_energy.index.strftime("%b")
ax.bar(monthly_energy.index, monthly_energy.values, color="orange")
ax.set_ylabel("kWh")
st.pyplot(fig)
