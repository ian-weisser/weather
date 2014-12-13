#!/usr/bin/python3

"""
Example Application
Given a location, use the weather database to determine the best observation
station, forecast zone, and radar location.

How to use this application:
1) Create a temporary working directory: /tmp/working
2) Set it as the current working directory: cd /tmp/working
3) Make sure this file is in that directory: mv /someplace/me.py /tmp/working/
4) Download the metar, radar, and zone files to that directory:
    wget https://raw.githubusercontent.com/ian-weisser/data/master/metar.csv
    wget https://raw.githubusercontent.com/ian-weisser/data/master/radar.csv
    wget https://raw.githubusercontent.com/ian-weisser/data/master/zone.csv
5) Run the script: python3 me.py

"""
import csv
import os
import math


LATITUDE  = 43.01
LONGITUDE = -87.99

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
    os.getcwd()
    with open(working + '/radar.csv', 'r') as csvfile:
        radars = csv.DictReader(csvfile)
        output['Radar'] = best(radars)

    with open(working + '/metar.csv', 'r') as csvfile:
        metars = csv.DictReader(csvfile)
        output['Observation'] = best(metars)

    with open(working + '/zone.csv', 'r') as csvfile:
        zones = csv.DictReader(csvfile)
        output['Zone'] = best(zones)

    print(output)

if __name__ == "__main__":
    run()