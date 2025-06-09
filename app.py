
import streamlit as st

st.set_page_config(page_title="🌞 Solar Dashboard", layout="centered")
st.title("🌞 Solar Dashboard")

st.write("Welcome! This dashboard simulates solar panel configuration.")

location = st.text_input("Enter location (city or coordinates)", value="New York")
tilt = st.slider("Tilt angle (degrees)", 0, 90, 25)
azimuth = st.slider("Azimuth (degrees)", 0, 360, 180)

st.write(f"📍 Location: {location}")
st.write(f"🧭 Tilt: {tilt}°, Azimuth: {azimuth}°")
