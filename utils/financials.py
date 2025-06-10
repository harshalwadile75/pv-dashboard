import pandas as pd

def estimate_financials(energy_df, cost_watt, rate, module_power):
    annual_energy = energy_df['Energy (kWh)'].sum()
    system_cost = module_power * cost_watt
    annual_savings = annual_energy * rate
    payback = system_cost / annual_savings

    df = pd.DataFrame({
        "System Cost ($)": [system_cost],
        "Annual Energy (kWh)": [annual_energy],
        "Annual Savings ($)": [annual_savings],
        "Payback Period (yrs)": [round(payback, 2)]
    })

    return df
