# Streamlit App: PVsyst-style Solar Dashboard with Full Features and Safe Data Fallback

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io
import requests
import datetime
from pvlib import location, irradiance, temperature, iotools
from streamlit_folium import st_folium
import folium
from fpdf import FPDF
import base64

# ----- Streamlit App Configuration -----
st.set_page_config("☀️ PVsyst Solar Report", layout="wide")
st.title("🔆 PVsyst-style Solar Simulation Dashboard")
st.markdown("Simulate solar output, performance, losses, and ROI.")

# ----- Sidebar Configuration -----
st.sidebar.header("📍 Location & System Setup")
mode = st.sidebar.radio("Location Input", ["Auto via IP", "Map Selection"])
if mode == "Auto via IP":
    try:
        ip_info = requests.get("https://ipinfo.io").json()
        lat, lon = map(float, ip_info["loc"].split(","))
        st.sidebar.success(f"Detected: {ip_info['city']} ({lat:.2f}, {lon:.2f})")
    except:
        lat, lon = 40.7128, -74.0060
        st.sidebar.warning("Failed to detect. Defaulting to NYC.")
else:
    m = folium.Map(location=[20, 0], zoom_start=2)
    map_data = st_folium(m, height=300, returned_objects=["last_clicked"])
    if map_data and map_data["last_clicked"]:
        lat = map_data["last_clicked"]["lat"]
        lon = map_data["last_clicked"]["lng"]
        st.sidebar.success(f"Selected: ({lat:.2f}, {lon:.2f})")
    else:
        lat, lon = 20.0, 0.0

# Module & Inverter Selection
modules = {
    "Qcells 400W": 400,
    "Canadian Solar 445W": 445,
    "LONGi 500W": 500,
    "Trina 670W": 670,
    "REC 410W": 410
}
module = st.sidebar.selectbox("Module", list(modules.keys()))
mod_power = modules[module]
inverter = st.sidebar.selectbox("Inverter", ["Fronius 10kW", "SMA 7.7kW", "Huawei 10kW"])

tilt = st.sidebar.slider("Tilt Angle (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
series = st.sidebar.slider("Modules in Series", 5, 30, 15)
parallel = st.sidebar.slider("Strings in Parallel", 1, 10, 2)

st.sidebar.header("🔧 Losses")
soiling = st.sidebar.slider("Soiling %", 0, 10, 2)
shading = st.sidebar.slider("Shading %", 0, 20, 5)
temp_loss = st.sidebar.slider("Temperature %", 0, 10, 2)
mismatch = st.sidebar.slider("Mismatch %", 0, 5, 1)
wiring = st.sidebar.slider("Wiring %", 0, 5, 1)
inv_eff = st.sidebar.slider("Inverter Efficiency %", 90, 99, 97)

st.sidebar.header("💰 Financial")
cost_watt = st.sidebar.number_input("System Cost ($/W)", 0.5, 3.0, 1.2)
kwh_rate = st.sidebar.number_input("Electricity Rate ($/kWh)", 0.05, 0.5, 0.15)

# ----- Data Collection -----
st.subheader("☀️ Weather and Solar Simulation")
tmy, _ = iotools.get_pvgis_tmy(lat, lon)
site = location.Location(lat, lon)
solpos = site.get_solarposition(tmy.index)

dni = tmy.get("DNI", tmy.get("GHI", pd.Series([0]*len(tmy), index=tmy.index)))
dhi = tmy.get("DHI", tmy.get("GHI", pd.Series([0]*len(tmy), index=tmy.index)))
ghi = tmy.get("GHI", pd.Series([0]*len(tmy), index=tmy.index))

poa = irradiance.get_total_irradiance(
    tilt, azimuth, dni, ghi, dhi,
    solar_zenith=solpos["zenith"],
    solar_azimuth=solpos["azimuth"]
)
temp_cell = temperature.sapm_cell(poa["poa_global"], tmy["TempAir"], 2)

# ----- Simulation -----
system_kw = mod_power * series * parallel / 1000
gross = poa["poa_global"] / 1000 * system_kw
loss_factor = (soiling + shading + temp_loss + mismatch + wiring) / 100
net = gross * (1 - loss_factor) * (inv_eff / 100)
monthly_energy = net.resample("M").sum()
annual_kwh = monthly_energy.sum()
system_cost = cost_watt * system_kw * 1000
savings = annual_kwh * kwh_rate
payback = system_cost / savings if savings else np.inf

# ----- Output Summary -----
st.subheader("📊 System Performance Summary")
st.metric("System Size (kW)", f"{system_kw:.2f}")
st.metric("Annual Output (kWh)", f"{annual_kwh:.0f}")
st.metric("Payback Period (years)", f"{payback:.1f}" if np.isfinite(payback) else "N/A")

with st.expander("📆 Monthly Energy Output"):
    fig, ax = plt.subplots()
    monthly_energy.index = monthly_energy.index.strftime("%b")
    ax.bar(monthly_energy.index, monthly_energy.values, color="green")
    ax.set_ylabel("kWh")
    st.pyplot(fig)

with st.expander("📈 I-V and P-V Curve"):
    v = np.linspace(0, 40, 100)
    i = 13 * (1 - (v / 40) ** 1.4)
    p = v * i
    fig2, ax2 = plt.subplots()
    ax2.plot(v, i, label="I-V", color="blue")
    ax2b = ax2.twinx()
    ax2b.plot(v, p, '--', color="orange", label="P-V")
    ax2.set_xlabel("Voltage (V)")
    ax2.set_ylabel("Current (A)", color="blue")
    ax2b.set_ylabel("Power (W)", color="orange")
    st.pyplot(fig2)

with st.expander("🌞 POA Irradiance and Cell Temperature"):
    fig3, ax3 = plt.subplots()
    poa["poa_global"].plot(ax=ax3, color="red", label="POA (W/m²)")
    ax3b = ax3.twinx()
    temp_cell.plot(ax=ax3b, color="blue", label="Temp")
    ax3.set_ylabel("POA (W/m²)", color="red")
    ax3b.set_ylabel("Cell Temp (°C)", color="blue")
    st.pyplot(fig3)

# ----- PDF Export -----
with st.expander("📄 Export PDF Report"):
    if st.button("📤 Generate PDF Report"):
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(190, 10, "Solar System Performance Report", ln=True, align="C")

        pdf.set_font("Arial", size=12)
        pdf.ln(10)
        pdf.cell(190, 10, f"System Size: {system_kw:.2f} kW", ln=True)
        pdf.cell(190, 10, f"Annual Output: {annual_kwh:.0f} kWh", ln=True)
        pdf.cell(190, 10, f"System Cost: ${system_cost:,.0f}", ln=True)
        pdf.cell(190, 10, f"Annual Savings: ${savings:,.0f}", ln=True)
        pdf.cell(190, 10, f"Estimated Payback: {payback:.1f} years", ln=True)

        pdf.ln(10)
        pdf.cell(190, 10, "Loss Breakdown:", ln=True)
        pdf.cell(190, 10, f"Soiling: {soiling}%  Shading: {shading}%  Temp: {temp_loss}%", ln=True)
        pdf.cell(190, 10, f"Mismatch: {mismatch}%  Wiring: {wiring}%  Inverter Eff: {inv_eff}%", ln=True)

        pdf_output = io.BytesIO()
        pdf.output(pdf_output)
        st.download_button("📥 Download PDF", pdf_output.getvalue(), file_name="solar_report.pdf")

# ----- Excel Export -----
with st.expander("📥 Export Excel Report"):
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        monthly_energy.to_frame("Monthly kWh").to_excel(writer, sheet_name="Monthly Output")
        pd.DataFrame({
            "System kW": [system_kw],
            "Annual Energy": [annual_kwh],
            "System Cost ($)": [system_cost],
            "Annual Savings ($)": [savings],
            "Payback (Years)": [payback]
        }).to_excel(writer, sheet_name="Summary", index=False)
        poa.to_excel(writer, sheet_name="POA Data")
        temp_cell.to_frame("Cell Temp").to_excel(writer, sheet_name="Cell Temperature")
    st.download_button("⬇️ Download Excel Report", buffer.getvalue(), file_name="pvsyst_sim_report.xlsx")
