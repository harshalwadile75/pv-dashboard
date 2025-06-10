import pandas as pd
from pvlib.location import Location

def get_tmy_data(lat, lon):
    loc = Location(lat, lon, 'UTC')
    
    # Use one year of hourly timestamps
    times = pd.date_range('2023-01-01', '2023-12-31 23:00', freq='H', tz='UTC')
    
    # Generate clear sky data for this year
    clearsky = loc.get_clearsky(times)
    
    # Return monthly averages
    tmy_data = clearsky.resample('M').mean()
    
    return tmy_data
