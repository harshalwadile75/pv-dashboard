import pandas as pd
from pvlib.pvsystem import PVSystem
from pvlib.modelchain import ModelChain
from pvlib.location import Location

def run_simulation(tmy_data, module_power, tilt, azimuth):
    location = Location(tmy_data.index[0].month, tmy_data.index[0].day)
    system = PVSystem(surface_tilt=tilt, surface_azimuth=azimuth, module_parameters={'pdc0': module_power})
    mc = ModelChain(system, location)
    mc.run_model(tmy_data)

    monthly_energy = mc.ac.resample('M').sum() / 1000
    df = pd.DataFrame({"Month": monthly_energy.index.month_name(), "Energy (kWh)": monthly_energy.values})
    df.set_index("Month", inplace=True)

    return df, mc.iv
