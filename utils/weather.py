from pvlib.location import Location

def get_tmy_data(lat, lon):
    loc = Location(lat, lon, 'UTC')
    tmy_data, meta = loc.get_clearsky().resample('M').mean(), {'latitude': lat, 'longitude': lon}
    return tmy_data
