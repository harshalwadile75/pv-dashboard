import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
from streamlit_folium import st_folium
import folium
from pvlib import location, irradiance, temperature, iotools

st.set_page_config("☀️ PVsyst-Style Solar Dashboard", layout="wide")
st.title("🔆 Advanced Solar Simulation Dashboard")

# --- LOCATION SELECTION ---
st.sidebar.header("📍 Select Location")
mode = st.sidebar.radio("Location Input", ["Auto via IP", "Pick on Map"])

if mode == "Auto via IP":
    try:
        ip_info = requests.get("https://ipinfo.io").json()
        lat, lon = map(float, ip_info["loc"].split(","))
        st.sidebar.success(f"Detected: {ip_info['city']} ({lat}, {lon})")
    except:
        lat, lon = 40.7128, -74.0060
        st.sidebar.warning("IP detection failed. Defaulting to NYC.")
else:
    m = folium.Map(location=[20, 0], zoom_start=2)
    loc_data = st_folium(m, height=350, returned_objects=["last_clicked"])
    if loc_data and loc_data["last_clicked"]:
        lat = loc_data["last_clicked"]["lat"]
        lon = loc_data["last_clicked"]["lng"]
        st.sidebar.success(f"Selected: ({lat:.2f}, {lon:.2f})")
    else:
        lat, lon = 20.0, 0.0

# --- MODULE & INVERTER SELECTION ---
st.sidebar.header("🔋 Select Equipment")
modules = {
    "Qcells 400W": 400,
    "Canadian Solar 445W": 445,
    "LONGi 500W": 500,
    "Trina 670W": 670,
    "REC 410W": 410
}
inverters = ["Fronius 10kW", "SMA 7.7kW", "Huawei 10kW", "Enphase IQ8+"]

module = st.sidebar.selectbox("PV Module", list(modules.keys()))
inverter = st.sidebar.selectbox("Inverter", inverters)
mod_power = modules[module]

# --- SYSTEM CONFIGURATION ---
st.sidebar.header("⚙️ Array Design")
tilt = st.sidebar.slider("Tilt Angle (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
series = st.sidebar.slider("Modules in Series", 5, 30, 15)
parallel = st.sidebar.slider("Strings in Parallel", 1, 10, 2)

# --- LOSSES ---
st.sidebar.header("🔧 Loss Factors (%)")
soiling = st.sidebar.slider("Soiling", 0, 10, 2)
shading = st.sidebar.slider("Shading", 0, 15, 3)
temp_loss = st.sidebar.slider("Temperature", 0, 10, 2)
mismatch = st.sidebar.slider("Mismatch", 0, 5, 1)
wiring = st.sidebar.slider("Wiring", 0, 5, 1)
inv_eff = st.sidebar.slider("Inverter Efficiency", 90, 99, 97)

# --- FINANCIALS ---
st.sidebar.header("💰 Financials")
cost_per_watt = st.sidebar.number_input("System Cost ($/W)", 0.5, 3.0, 1.0)
elec_price = st.sidebar.number_input("Electricity Rate ($/kWh)", 0.05, 0.5, 0.15)

# --- LOAD WEATHER DATA ---
st.subheader("☀️ Irradiance Simulation Using PVGIS")
tmy, _ = iotools.get_pvgis_tmy(lat, lon)
site = location.Location(lat, lon)
solpos = site.get_solarposition(tmy.index)

# Fallback for irradiance columns
dni = tmy["DNI"] if "DNI" in tmy.columns else tmy.get("GHI", pd.Series([0]*len(tmy), index=tmy.index))
dhi = tmy["DHI"] if "DHI" in tmy.columns else tmy.get("GHI", pd.Series([0]*len(tmy), index=tmy.index))
ghi = tmy["GHI"] if "GHI" in tmy.columns else pd.Series([0]*len(tmy), index=tmy.index)

# POA + Temperature
poa = irradiance.get_total_irradiance(
    tilt, azimuth, dni, ghi, dhi,
    solar_zenith=solpos["zenith"],
    solar_azimuth=solpos["azimuth"]
)
temps = temperature.sapm_cell(poa["poa_global"], tmy["TempAir"], 2)

# Energy Simulation
system_kw = mod_power * series * parallel / 1000
gross_power = poa["poa_global"] / 1000 * system_kw
total_loss = (soiling + shading + temp_loss + mismatch + wiring) / 100
net_power = gross_power * (1 - total_loss) * (inv_eff / 100)
monthly_energy = net_power.resample("M").sum()
annual_energy = monthly_energy.sum()

# Financials
system_cost = system_kw * 1000 * cost_per_watt
annual_savings = annual_energy * elec_price
payback = system_cost / annual_savings if annual_savings > 0 else float("inf")

# --- OUTPUTS ---
st.subheader("📊 System Summary")
col1, col2, col3 = st.columns(3)
col1.metric("System Size (kW)", f"{system_kw:.2f}")
col2.metric("Annual Output (kWh)", f"{annual_energy:.0f}")
col3.metric("Payback (Years)", f"{payback:.1f}")

with st.expander("⚙️ System Configuration Details"):
    st.write(f"**Modules:** {series} × {parallel} = {series*parallel}")
    st.write(f"**Total Power:** {module} × {series*parallel} = {system_kw*1000:.0f} W")

with st.expander("🔧 Loss Factors Summary"):
    st.write(f"Soiling: {soiling}%, Shading: {shading}%, Temp: {temp_loss}%, Mismatch: {mismatch}%, Wiring: {wiring}%, Inverter Efficiency: {inv_eff}%")

# --- PLOTS ---
st.subheader("📆 Monthly Energy Output")
fig1, ax1 = plt.subplots()
monthly_energy.index = monthly_energy.index.strftime("%b")
ax1.bar(monthly_energy.index, monthly_energy.values, color="orange")
ax1.set_ylabel("kWh")
st.pyplot(fig1)

st.subheader("📉 I-V and P-V Curve")
v = np.linspace(0, 40, 100)
i = 13 * (1 - (v / 40) ** 1.3)
p = v * i
fig2, ax2 = plt.subplots()
ax2.plot(v, i, label="I-V", color="blue")
ax2b = ax2.twinx()
ax2b.plot(v, p, '--', label="P-V", color="green")
ax2.set_xlabel("Voltage (V)")
ax2.set_ylabel("Current (A)", color="blue")
ax2b.set_ylabel("Power (W)", color="green")
st.pyplot(fig2)

with st.expander("📊 Weather Curves (POA & Cell Temp)"):
    fig3, ax3 = plt.subplots()
    poa["poa_global"].plot(ax=ax3, label="POA Irradiance (W/m²)", color="red")
    ax3.set_ylabel("POA (W/m²)", color="red")
    ax3b = ax3.twinx()
    temps.plot(ax=ax3b, label="Cell Temp (°C)", color="blue")
    ax3b.set_ylabel("Temp (°C)", color="blue")
    st.pyplot(fig3)

# --- EXCEL EXPORT ---
st.subheader("📥 Download Results")
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    monthly_energy.to_frame("Monthly kWh").to_excel(writer, sheet_name="Energy")
    pd.DataFrame({
        "System Size (kW)": [system_kw],
        "Annual Energy (kWh)": [annual_energy],
        "System Cost ($)": [system_cost],
        "Annual Savings ($)": [annual_savings],
        "Payback (Years)": [payback]
    }).to_excel(writer, sheet_name="Summary", index=False)
st.download_button("⬇️ Download Excel Report", buffer.getvalue(), "solar_summary.xlsx")
