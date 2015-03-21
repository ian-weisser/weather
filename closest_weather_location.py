#!/usr/bin/python3

"""
Example Application
Given a location, use the weather database to determine the best observation
station, forecast zone, and radar location.

Download the waether location database each run. Use httplib2 for caching.

Script usage: python3 closest_weather_location.py
"""
# Python Standard Library (Debian package libpython3.*-minimal)
import io

# Python Standard Library (Debian package libpython3.*-stdlib)
import csv
import math

# Other Python packages
import httplib2      # (Debian package python3-httplib2)


LATITUDE  = 43.01
LONGITUDE = -87.99

def download(dl_type):
    """ Download data tables """
    cache    = '/tmp/weather'
    url      = 'https://raw.githubusercontent.com/ian-weisser/data/master/'
    if dl_type   == 'metar':
        source = url + 'metar.csv'
    elif dl_type == 'radar':
        source = url + 'radar.csv'
    elif dl_type == 'zone':
        source = url + 'zone.csv'
    else:
        return

    get           = httplib2.Http(cache)
    #resp, content = get.request(source, "GET")
    #status        = resp['status']
    content       = get.request(source, "GET")[1].decode('utf-8')
    csvfile       = io.StringIO(content)    # Stream content instead of saving
    table         = csv.DictReader(csvfile)

    return table


def precise_distance(a_lat, a_lon, b_lat, b_lon):
    """
    The Haversine formula is a generally accepted way of finding the
    great-circle distance between two sets of lat/lon coordinates.
    Originally published by R. W. Sinnott, "Virtues of the Haversine",
        Sky and Telescope 68 (2), 159 (1984)

    This function, with minor changes, was created by Wayne Dyck in 2009
    http://www.platoscave.net/blog/2009/oct/5/
         calculate-distance-latitude-longitude-python/

    Input: four lat/lon strings ("44.12345", "-88.12345") :
    Output is an integer of the distance in km.
    """
    radius = 6371 # km

    dlat = math.radians(b_lat - a_lat)
    dlon = math.radians(b_lon - a_lon)
    aaa = math.sin(dlat/2) * math.sin(dlat/2) + math.cos(math.radians(a_lat)) \
        * math.cos(math.radians(b_lat)) * math.sin(dlon/2) * math.sin(dlon/2)
    ccc = 2 * math.atan2(math.sqrt(aaa), math.sqrt(1-aaa))
    kilometers = radius * ccc

    return int(kilometers)


def rough_distance(degree_variance, test_latitude, test_longitude):
    """
    This is a simple filter based on looking for lat/lon within a
    certain range. If it passes this filter, then it's worth the CPU cycles
    to check precise distance.
    Input:
       The lat/lon range list: [35, 45, -80, -90]  35-45 N Lat, 80-90 W Lon
       The lat/lon of the test location:[44.12345, -88.12345]
    Output is a simple Boolean. True if the test location is within the range.
    """
    lat_a = LATITUDE + degree_variance
    lat_b = LATITUDE - degree_variance
    lon_a = LONGITUDE + degree_variance
    lon_b = LONGITUDE - degree_variance

    if lat_a < test_latitude < lat_b or lat_b < test_latitude < lat_a:
        pass
    else:
        return False

    if lon_a < test_longitude < lon_b or lon_b < test_longitude < lon_a:
        return True
    else:
        return False


def best(many_locations):
    """
    Iterate through the dict, looking for best candidates.
    """

    closest_dist = 100000
    closest_sta  = {}
    for loc in many_locations:
        if loc['Latitude'] == '' or loc['Longitude'] == '':
            continue
        lat = float(loc['Latitude'])
        lon = float(loc['Longitude'])

        # Pass all locations within 5 degrees.
        # It's a rough filter, but uses fewer CPU cycles.
        if not rough_distance(5, lat, lon):
            continue

        # Measure the distances of those closest hits.
        # This is more precise, but uses more CPU cycles.
        dist = precise_distance(LATITUDE, LONGITUDE, lat, lon )
        if  dist < closest_dist:
            closest_dist = dist
            closest_sta.update(loc)

    if len(closest_sta) == 0:
        return None
    else:
        return closest_sta


def run():
    """ Example application """
    output  = {}

    radars                = download('radar')
    metars                = download('metar')
    zones                 = download('zone')
    output['Radar']       = best(radars)
    output['Observation'] = best(metars)
    output['Zone']        = best(zones)

    print(output)

if __name__ == "__main__":
    run()
