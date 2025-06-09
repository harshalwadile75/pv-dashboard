import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from streamlit_folium import st_folium
import folium
from pvlib import location, irradiance, temperature, iotools

st.set_page_config(page_title="🔆 PVsyst-Style Solar Dashboard", layout="wide")
st.title("🔆 Advanced Solar Simulation Dashboard")

# Sidebar - Location
st.sidebar.header("📍 Select Location")
mode = st.sidebar.radio("Location Input", ["Auto via IP", "Pick on Map"])

if mode == "Auto via IP":
    try:
        ip_info = requests.get("https://ipinfo.io").json()
        loc = ip_info["loc"].split(",")
        lat, lon = float(loc[0]), float(loc[1])
        st.sidebar.success(f"Auto-detected: {ip_info['city']} ({lat}, {lon})")
    except:
        st.sidebar.error("IP detection failed. Defaulting to NYC.")
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
st.sidebar.header("🔋 PV Module")
module_options = {
    "Qcells Q.PEAK DUO ML-G10+ 400W": 400,
    "Canadian Solar BiHiKu 445W": 445,
    "JA Solar DeepBlue 3.0 470W": 470,
    "LONGi Hi-MO6 500W": 500,
    "Trina Vertex 670W": 670,
    "REC Alpha Pure 410W": 410,
    "Jinko Tiger Neo 480W": 480
}
module = st.sidebar.selectbox("Choose Module", list(module_options.keys()))
module_watt = module_options[module]

# Inverter Selection
inverters = [
    "Fronius Symo 10kW",
    "SMA Sunny Boy 7.7-US",
    "Enphase IQ8+",
    "Huawei SUN2000-10KTL-M1",
    "SolarEdge SE10000H"
]
inverter = st.sidebar.selectbox("Choose Inverter", inverters)

# System Configuration
st.sidebar.header("⚙️ System Setup")
tilt = st.sidebar.slider("Tilt (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
series = st.sidebar.slider("Modules in Series", 5, 30, 15)
parallel = st.sidebar.slider("Strings in Parallel", 1, 10, 2)

# Losses
st.sidebar.header("🔧 Loss Factors")
soiling = st.sidebar.slider("Soiling Loss %", 0, 10, 2)
shading = st.sidebar.slider("Shading Loss %", 0, 15, 3)
temp_loss = st.sidebar.slider("Temp Loss %", 0, 10, 2)
mismatch = st.sidebar.slider("Mismatch %", 0, 5, 1)
wiring = st.sidebar.slider("Wiring %", 0, 5, 1)
inverter_eff = st.sidebar.slider("Inverter Efficiency %", 90, 99, 97)

# Cost Inputs
st.sidebar.header("💰 Financial")
cost_watt = st.sidebar.number_input("Cost per Watt ($)", 0.5, 3.0, 1.0)
price_kwh = st.sidebar.number_input("Electricity Price ($/kWh)", 0.05, 0.5, 0.15)

# Get TMY Weather Data
st.subheader("☀️ Weather Data & Irradiance Simulation")
tmy, meta = iotools.get_pvgis_tmy(lat, lon)
site = location.Location(lat, lon, tz="Etc/GMT+5")
solpos = site.get_solarposition(tmy.index)

# Show available columns for debugging
st.write("📋 TMY Columns Found:", list(tmy.columns))

# Safe fallback for missing DNI/DHI
dni = tmy["DNI"] if "DNI" in tmy.columns else (tmy["GHI"] if "GHI" in tmy.columns else pd.Series([0]*len(tmy), index=tmy.index))
dhi = tmy["DHI"] if "DHI" in tmy.columns else (tmy["GHI"] if "GHI" in tmy.columns else pd.Series([0]*len(tmy), index=tmy.index))

poa = irradiance.get_total_irradiance(
    surface_tilt=tilt,
    surface_azimuth=azimuth,
    dni=dni,
    ghi=tmy["GHI"] if "GHI" in tmy.columns else pd.Series([0]*len(tmy), index=tmy.index),
    dhi=dhi,
    solar_zenith=solpos["zenith"],
    solar_azimuth=solpos["azimuth"]
)

temps = temperature.sapm_cell(poa["poa_global"], tmy["TempAir"], 2)

# Energy Simulation
system_kw = module_watt * series * parallel / 1000
gross_power = poa["poa_global"] / 1000 * system_kw
total_losses = (soiling + shading + temp_loss + mismatch + wiring) / 100
net_power = gross_power * (1 - total_losses) * (inverter_eff / 100)
monthly_energy = net_power.resample("M").sum()
annual_energy = monthly_energy.sum()

# Cost & ROI
cost = system_kw * 1000 * cost_watt
savings = annual_energy * price_kwh
payback = cost / savings if savings > 0 else np.nan

# Results
st.subheader("📊 System Summary")
col1, col2, col3 = st.columns(3)
col1.metric("System Size (kW)", f"{system_kw:.2f}")
col2.metric("Annual Output (kWh)", f"{annual_energy:.0f}")
col3.metric("Payback (Years)", f"{payback:.1f}" if not np.isnan(payback) else "N/A")

# Monthly Bar Chart
st.subheader("📆 Monthly Energy Output")
fig, ax = plt.subplots()
monthly_energy.index = monthly_energy.index.strftime("%b")
ax.bar(monthly_energy.index, monthly_energy.values, color="green")
ax.set_ylabel("kWh")
st.pyplot(fig)

# IV & PV Curves
st.subheader("📉 I-V & P-V Curve")
voc = 40
isc = 13
v = np.linspace(0, voc, 100)
i = isc * (1 - (v / voc) ** 1.4)
p = v * i
fig2, ax1 = plt.subplots()
ax1.plot(v, i, label="I-V", color="blue")
ax2 = ax1.twinx()
ax2.plot(v, p, '--', label="P-V", color="orange")
ax1.set_xlabel("Voltage (V)")
ax1.set_ylabel("Current (A)", color="blue")
ax2.set_ylabel("Power (W)", color="orange")
st.pyplot(fig2)

# Export to Excel
st.subheader("📤 Export to Excel")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    monthly_energy.to_frame("Monthly kWh").to_excel(writer, sheet_name="Energy")
    pd.DataFrame({
        "System Size (kW)": [system_kw],
        "Annual Energy (kWh)": [annual_energy],
        "System Cost ($)": [cost],
        "Payback (Years)": [payback]
    }).to_excel(writer, sheet_name="Summary", index=False)
st.download_button("📥 Download Excel Report", buffer.getvalue(), file_name="solar_summary.xlsx")
