import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(page_title="Advanced Solar Dashboard", layout="wide")
st.title("🔋 Advanced PV Module Simulation Dashboard")

# --- Feature Description Panel ---
with st.expander("ℹ️ Dashboard Functions and Future Upgrades"):
    st.markdown("""
    ### ✅ Current Dashboard Features
    | Feature | What It Does |
    |--------|---------------|
    | 🌞 Title | Shows "Solar Dashboard" as a heading |
    | 📝 Text Input | Lets you enter a location (like a city or coordinates) |
    | 🎚️ Tilt Slider | Choose the tilt angle (0° flat to 90° vertical) |
    | 🎚️ Azimuth Slider | Choose the azimuth angle (0–360°, which direction the panels face) |
    | 🖥️ Display Output | Shows your selected location, tilt, and azimuth below the sliders |

    ### 🔜 Upgrade Options (Coming Soon)
    | Upgrade | What It Adds |
    |--------|----------------|
    | ☀️ Solar Simulation | Use real irradiance data and show energy output |
    | 📉 PV Power Curves | Plot I-V and P-V curves of selected modules |
    | 📦 Module & Inverter Picker | Choose Qcells, Canadian Solar, etc. from dropdown |
    | 🔧 Losses & Conditions | Simulate shading, temperature effects, mismatch losses |
    | 📊 Monthly Energy Graphs | Simulate daily/monthly output across the year |
    | 💵 Cost & ROI Calculator | Calculate system cost, savings, payback |
    | 📄 Export to PDF/CSV | Download summary of your system design |
    """)

# --- Location & Orientation Inputs ---
st.subheader("📍 Site Configuration")
location = st.text_input("Enter location (city or coordinates)", value="New York")
st.write(f"📍 Location: {location}")

# --- Environmental Inputs ---
st.sidebar.header("🌤️ Environmental Conditions")
irradiance = st.sidebar.slider("Irradiance (W/m²)", 200, 1200, 1000)
temperature = st.sidebar.slider("Module Temperature (°C)", 15, 75, 25)

# --- System Configuration ---
st.sidebar.header("🔧 System Configuration")
tilt = st.sidebar.slider("Tilt angle (°)", 0, 90, 25)
azimuth = st.sidebar.slider("Azimuth (°)", 0, 360, 180)
modules_series = st.sidebar.slider("Modules in Series", 1, 30, 15)
modules_parallel = st.sidebar.slider("Strings in Parallel", 1, 10, 3)
st.write(f"🧭 Tilt: {tilt}°, Azimuth: {azimuth}°")

# --- Module Parameters (Example Module) ---
voc = 40.8  # Open Circuit Voltage (V)
isc = 13.5  # Short Circuit Current (A)
vmpp = 34.3 # Voltage at Max Power Point (V)
impp = 12.7 # Current at Max Power Point (A)
pmax = vmpp * impp  # Max Power (W)
temp_coeff = -0.003  # Power Temp Coefficient per °C

# --- Loss Factors ---
st.sidebar.header("⚡ Loss Factors")
soiling_loss = st.sidebar.slider("Soiling Loss (%)", 0, 10, 2) / 100
mismatch_loss = st.sidebar.slider("Mismatch Loss (%)", 0, 10, 1) / 100
temp_loss = st.sidebar.slider("Temperature Loss (%)", 0, 10, 3) / 100
total_loss_factor = 1 - (soiling_loss + mismatch_loss + temp_loss)

# --- Power Calculations ---
adjusted_pmax = pmax * (irradiance / 1000) * (1 + temp_coeff * (temperature - 25)) * total_loss_factor
total_dc_power = adjusted_pmax * modules_series * modules_parallel
total_voc = voc * modules_series
total_vmpp = vmpp * modules_series
total_isc = isc * modules_parallel
total_impp = impp * modules_parallel

# --- Output Summary ---
st.subheader("📊 System Output Summary")
col1, col2, col3 = st.columns(3)
col1.metric("Total Voc", f"{total_voc:.2f} V")
col1.metric("Total Vmpp", f"{total_vmpp:.2f} V")
col2.metric("Total Isc", f"{total_isc:.2f} A")
col2.metric("Total Impp", f"{total_impp:.2f} A")
col3.metric("DC Power Output", f"{total_dc_power/1000:.2f} kW")
col3.metric("Module Efficiency", "22.3 %")

# --- I-V and P-V Curves ---
st.subheader("🔍 I-V and P-V Curve")
v = np.linspace(0, voc, 100)
i = isc * (1 - (v / voc)**1.5)
p = v * i

fig, ax1 = plt.subplots()
ax1.plot(v, i, 'b-', label="I-V Curve")
ax1.set_xlabel("Voltage (V)")
ax1.set_ylabel("Current (A)", color='b')
ax2 = ax1.twinx()
ax2.plot(v, p, 'g--', label="P-V Curve")
ax2.set_ylabel("Power (W)", color='g')
st.pyplot(fig)

# --- Layout Visualization ---
st.subheader("📐 Module Layout (Series x Parallel)")
layout_fig, ax = plt.subplots()
for i in range(modules_parallel):
    for j in range(modules_series):
        ax.plot(j, -i, 'ks', markersize=12)
ax.set_xlim(-1, modules_series)
ax.set_ylim(-modules_parallel, 1)
ax.set_title("Module Strings")
ax.axis("off")
st.pyplot(layout_fig)
