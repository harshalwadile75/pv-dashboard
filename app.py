import streamlit as st
from utils.weather import get_tmy_data
from utils.simulation import run_simulation
from utils.financials import estimate_financials
from utils.export import export_pdf
from config import LOCATION_DEFAULT

st.set_page_config("PV Simulation Dashboard", layout="wide")

st.title("🔆 PVsyst-Style Solar Dashboard")

with st.sidebar:
    st.header("📍 Location")
    lat = st.number_input("Latitude", value=LOCATION_DEFAULT['latitude'])
    lon = st.number_input("Longitude", value=LOCATION_DEFAULT['longitude'])
    tmy_data = get_tmy_data(lat, lon)

    st.header("⚙️ System Setup")
    module_power = st.selectbox("Module Power (W)", [400, 450, 500])
    tilt = st.slider("Tilt (°)", 0, 60, 30)
    azimuth = st.slider("Azimuth (°)", 0, 360, 180)

    st.header("💸 Financials")
    cost_watt = st.number_input("System Cost ($/W)", 0.5, 5.0, 1.2)
    electricity_rate = st.number_input("Rate ($/kWh)", 0.05, 0.50, 0.12)

st.subheader("☀️ Monthly Solar Simulation")
energy_df, iv_curve = run_simulation(tmy_data, module_power, tilt, azimuth)
st.line_chart(energy_df)

st.subheader("📈 Performance Metrics")
col1, col2 = st.columns(2)
with col1:
    st.metric("Annual Energy (kWh)", round(energy_df['Energy (kWh)'].sum(), 2))
with col2:
    st.metric("Capacity Factor (%)", round((energy_df['Energy (kWh)'].sum() / (module_power*365/1000))*100, 2))

st.subheader("💰 ROI and Cost")
roi_df = estimate_financials(energy_df, cost_watt, electricity_rate, module_power)
st.dataframe(roi_df)

st.subheader("📤 Export Report")
if st.button("Export to PDF"):
    pdf_file = export_pdf(lat, lon, energy_df, roi_df)
    st.success("PDF Exported Successfully")
    st.download_button("Download PDF", data=pdf_file, file_name="solar_report.pdf")
