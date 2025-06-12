import streamlit as st
import pandas as pd
import numpy as np

###############################################################################
# 1.  DATA LOAD
###############################################################################
try:
    bom_df  = pd.read_csv("full_material_bom_v3.csv")
    risk_df = pd.read_csv("failure_risk_matrix_v1.csv")
except FileNotFoundError as e:
    st.error(f"Missing file: {e}")
    st.stop()

###############################################################################
# 2.  SIDEBAR – MATERIAL PICKERS
###############################################################################
st.set_page_config("PVDevSim – Failure-Risk Edition", layout="wide")
st.title("🔬  PVDevSim — Module Simulator with Failure-Risk Analysis")

selections = {}

st.sidebar.header("🧪  Encapsulant Selection")
for side in ["Encapsulant - Front", "Encapsulant - Rear"]:
    opts = bom_df[bom_df["Component"] == side]["Type"].unique()
    sel  = st.sidebar.selectbox(side, opts, key=side)
    selections[side] = bom_df[(bom_df["Component"] == side) & (bom_df["Type"] == sel)].iloc[0]

st.sidebar.header("🧱  Other Components")
for comp in bom_df["Component"].unique():
    if "Encapsulant" in comp: 
        continue
    opts = bom_df[bom_df["Component"] == comp]["Type"].unique()
    sel  = st.sidebar.selectbox(comp, opts, key=comp)
    selections[comp] = bom_df[(bom_df["Component"] == comp) & (bom_df["Type"] == sel)].iloc[0]

###############################################################################
# 3.  STRESS & TEST INPUTS
###############################################################################
st.sidebar.header("🌡️  Degradation Params")
avg_temp   = st.sidebar.slider("Operating Temp (°C)", 25, 85, 45)
damp_heat  = st.sidebar.slider("Damp Heat (h)",        0, 5000, 2000)
uv_dose    = st.sidebar.slider("UV Dose (kWh/m²)",     0, 1000, 300)

st.sidebar.header("📋  Test Protocol")
profile = st.sidebar.selectbox("Standard", ["None","IEC Basic","PVEL Scorecard","RETC MQI"])
test_profiles = {
    "None": {},
    "IEC Basic":      {"TC200":0.5, "DH1000":1.0, "UV":0.3},
    "PVEL Scorecard": {"TC600":0.7, "DH2000":1.4, "PID":1.0, "UV":0.5, "LID":0.4, "HF":0.6},
    "RETC MQI":       {"TC200+DH2000+HF":2.5, "Dynamic Load":0.6, "PID":0.8, "UV":0.4}
}
selected_tests   = test_profiles.get(profile, {})
total_test_score = sum(selected_tests.values())

###############################################################################
# 4.  MATERIAL-BASED MULTIPLIERS (example)
###############################################################################
encap_mult = {"EVA":{"UV":1.2,"PID":1.3}, "POE":{"UV":0.7,"PID":0.5}, "EPE":{"UV":1.0,"PID":1.0}}
back_mult  = {"TPT":1.0,"PET":1.3,"Co-extruded":0.9}

def encap_factor(mat, mode): 
    for k,v in encap_mult.items():
        if k in mat: return v.get(mode,1.0)
    return 1.0
def backsheet_factor(mat): 
    for k in back_mult: 
        if k in mat: return back_mult[k]
    return 1.0

###############################################################################
# 5.  ARRHENIUS + DEGRADATION CALC
###############################################################################
def arrhenius(temp, Ea=0.7, Tref=298):
    k=8.617e-5;  T=temp+273.15
    return np.exp((Ea/k)*(1/Tref - 1/T))

accel  = arrhenius(avg_temp)
front  = selections["Encapsulant - Front"]["Type"]
rear   = selections["Encapsulant - Rear"]["Type"]
backsh = selections["Backsheet"]["Type"]

uv_fac  = (encap_factor(front,"UV")+encap_factor(rear,"UV"))/2
pid_fac = (encap_factor(front,"PID")+encap_factor(rear,"PID"))/2
dh_fac  = backsheet_factor(backsh)

base_deg = 0.5
deg_rate = base_deg*accel + damp_heat*0.0001*dh_fac + total_test_score*0.05*np.mean([uv_fac,pid_fac])

###############################################################################
# 6.  FAILURE-RISK LOOK-UP
###############################################################################
def lookup_failures(material, stresses):
    rows = []
    for stress in stresses:
        matches = risk_df[(risk_df["Material"].str.contains(material,case=False)) &
                          (risk_df["Stress"].str.contains(stress.split()[0],case=False))]
        rows.append(matches)
    if rows: return pd.concat(rows)
    return pd.DataFrame(columns=risk_df.columns)

###############################################################################
# 7.  RUN SIMULATION BUTTON
###############################################################################
if st.sidebar.button("▶️ Run Simulation"):

    # 7-A BOM Table
    st.subheader("📋 Bill of Materials")
    st.table(pd.DataFrame([{
        "Component":k,"Material":v["Type"],"Supplier":v["Supplier"],
        "Region":v["Region"],"Cert":v["Certifications"]} 
        for k,v in selections.items()
    ]))

    # 7-B Degradation Metrics
    year1 = deg_rate
    y25   = year1*25*0.95
    rel   = max(0,100-y25)

    st.subheader("📉 Degradation & Reliability")
    col1,col2,col3,col4 = st.columns(4)
    col1.metric("Arrhenius F",f"{accel:.2f}")
    col2.metric("Year-1 Deg",f"{year1:.2f}%")
    col3.metric("Loss @ 25 yr",f"{y25:.2f}%")
    col4.metric("Reliability",f"{rel:.1f}/100")

    # 7-C Failure-Risk Table
    st.subheader("🚨 Failure-Risk Analysis")
    if selected_tests:
        all_stresses = list(selected_tests.keys())
        risk_tables  = []
        for comp,row in selections.items():
            mat = row["Type"]
            tbl = lookup_failures(mat, all_stresses)
            if not tbl.empty:
                tbl.insert(0,"Component",comp)
                risk_tables.append(tbl)
        if risk_tables:
            risk_final = pd.concat(risk_tables,ignore_index=True)
            st.dataframe(risk_final)
        else:
            st.info("No risk data matched for selected materials/tests.")
    else:
        st.info("No test profile selected → risk analysis skipped.")
