import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from streamlit_folium import st_folium
import folium
from pvlib import location, irradiance, temperature, iotools

st.set_page_config(page_title="☀️ Full Solar Simulation Dashboard", layout="wide")
st.title("☀️ Solar Simulation, Cost, ROI, and Curve Dashboard")

# Sidebar - Location
st.sidebar.header("📍 Location Input")
mode = st.sidebar.radio("Location Mode", ["Auto via IP", "Map Picker"])

if mode == "Auto via IP":
    try:
        ip_info = requests.get("https://ipinfo.io").json()
        loc = ip_info["loc"].split(",")
        lat, lon = float(loc[0]), float(loc[1])
        st.sidebar.success(f"Detected: {ip_info['city']} ({lat}, {lon})")
    except:
        st.sidebar.error("Auto-detect failed. Defaulting to NYC.")
        lat, lon = 40.7128, -74.0060
else:
    m = folium.Map(location=[20, 0], zoom_start=2)
    map_data = st_folium(m, height=350, returned_objects=["last_clicked"])
    if map_data and map_data["last_clicked"]:
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.sidebar.success(f"Selected: ({lat:.2f}, {lon:.2f})")
    else:
        lat, lon = 20.0, 0.0

# Module Selection
st.sidebar.header("📦 PV Module")
module_options = {
    "Qcells Q.PEAK DUO BLK ML-G10+ 400W": 400,
    "Qcells Q.TRON BLK M-G2+ 430W": 430,
    "Canadian Solar HiKu6 420W": 420,
    "Canadian Solar BiHiKu 445W": 445,
    "JA Solar JAM72S30 455W": 455,
    "JA Solar DeepBlue 3.0 470W": 470,
    "LONGi Hi-MO5 450W": 450,
    "LONGi Hi-MO6 500W": 500,
    "Trina Vertex S 425W": 425,
    "Trina Vertex 670W": 670,
    "REC Alpha Pure 410W": 410,
    "Jinko Tiger Neo 480W": 480,
    "First Solar Series 6 Thin Film 460W": 460
}
module_name = st.sidebar.selectbox("Module", list(module_options.keys()))
module_power = module_options[module_name]

# Inverter Selection
inverter_list = [
    "Fronius Symo 10kW",
    "Huawei SUN2000-10KTL-M1",
    "SMA Sunny Boy 7.7-US",
    "Enphase IQ8+ Micro",
    "Sungrow SG10RT",
    "SolarEdge SE10000H",
    "Growatt MID 11KTL3-X"
]
inverter = st.sidebar.selectbox("Inverter", inverter_list)

# System Configuration
st.sidebar.header("⚙️ System Configuration")
tilt = st.sidebar.slider("Tilt (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
modules_series = st.sidebar.slider("Modules in Series", 5, 30, 15)
modules_parallel = st.sidebar.slider("Parallel Strings", 1, 10, 2)

# Losses
st.sidebar.header("🔧 Losses")
soiling = st.sidebar.slider("Soiling Loss (%)", 0, 10, 2)
shading = st.sidebar.slider("Shading Loss (%)", 0, 15, 3)
temp_loss = st.sidebar.slider("Temperature Loss (%)", 0, 10, 2)
mismatch = st.sidebar.slider("Mismatch Loss (%)", 0, 5, 1)
wiring = st.sidebar.slider("Wiring Loss (%)", 0, 5, 1)
inverter_eff = st.sidebar.slider("Inverter Efficiency (%)", 90, 99, 97)

# Cost Inputs
st.sidebar.header("💰 Cost & ROI")
cost_per_watt = st.sidebar.number_input("System Cost per Watt ($)", 0.5, 3.0, 1.0)
price_per_kwh = st.sidebar.number_input("Electricity Price ($/kWh)", 0.05, 0.5, 0.15)

# Get Weather Data
st.subheader("☀️ Weather and Irradiance")
tmy, meta = iotools.get_pvgis_tmy(lat, lon)
site = location.Location(lat, lon, tz="Etc/GMT+5", altitude=meta.get("elevation", 10))
solpos = site.get_solarposition(tmy.index)
poa = irradiance.get_total_irradiance(
    surface_tilt=tilt, surface_azimuth=azimuth,
    dni=tmy["DNI"], ghi=tmy["GHI"], dhi=tmy["DHI"],
    solar_zenith=solpos["zenith"], solar_azimuth=solpos["azimuth"]
)
temps = temperature.sapm_cell(poa["poa_global"], tmy["TempAir"], 2)

# Energy Simulation
system_kw = module_power * modules_series * modules_parallel / 1000
gross_power = poa["poa_global"] / 1000 * system_kw
total_losses = (soiling + shading + temp_loss + mismatch + wiring) / 100
net_power = gross_power * (1 - total_losses) * (inverter_eff / 100)
monthly_energy = net_power.resample("M").sum()
annual_energy = monthly_energy.sum()

# Cost Calculation
system_cost = system_kw * 1000 * cost_per_watt
annual_savings = annual_energy * price_per_kwh
payback_years = system_cost / annual_savings

# Results
st.subheader("📊 System Summary")
col1, col2, col3 = st.columns(3)
col1.metric("System Size", f"{system_kw:.2f} kW")
col2.metric("Annual Output", f"{annual_energy:.0f} kWh")
col3.metric("Payback", f"{payback_years:.1f} years")

# Monthly Energy Plot
st.subheader("📆 Monthly Energy Output")
fig, ax = plt.subplots()
monthly_energy.index = monthly_energy.index.strftime("%b")
ax.bar(monthly_energy.index, monthly_energy.values, color='green')
ax.set_ylabel("kWh")
st.pyplot(fig)

# IV & PV Curve
st.subheader("📉 I-V & P-V Curve")
voc = 40
isc = 13
v = np.linspace(0, voc, 100)
i = isc * (1 - (v / voc)**1.4)
p = v * i
fig2, ax1 = plt.subplots()
ax1.plot(v, i, label="I-V", color="blue")
ax2 = ax1.twinx()
ax2.plot(v, p, '--', label="P-V", color="orange")
ax1.set_xlabel("Voltage (V)")
ax1.set_ylabel("Current (A)", color='blue')
ax2.set_ylabel("Power (W)", color='orange')
st.pyplot(fig2)

# Export to Excel
st.subheader("📤 Export Report")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
    monthly_energy.to_frame(name="Monthly kWh").to_excel(writer, sheet_name="Energy")
    pd.DataFrame({
        "System Size (kW)": [system_kw],
        "Annual Energy (kWh)": [annual_energy],
        "System Cost ($)": [system_cost],
        "Payback (Years)": [payback_years]
    }).to_excel(writer, sheet_name="Summary", index=False)
st.download_button("📥 Download Excel", buffer.getvalue(), file_name="solar_summary.xlsx")
