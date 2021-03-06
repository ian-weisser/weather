#!/usr/bin/python3

"""
Scrape publicly-accessible records of the US National Weather Service
Build a database for the locations of:
- METAR observation stations
- Radar Stations
- Forecast Zones

WHO SHOULD USE IT:

This script should NOT be run by each end user of the database - that would
abuse the NWS servers. Developers and packagers don't need to run this script;
instead they can simply mirror the updated database from:
    https://raw.githubusercontent.com/ian-weisser/data/master/metar.csv
    https://raw.githubusercontent.com/ian-weisser/data/master/radar.csv
    https://raw.githubusercontent.com/ian-weisser/data/master/zone.csv

This script _should_ be included in any GPL source packages for completeness,
for security audits, and for troubleshooting bugs discovered in the data.

CREDITS:

The data files are created from non-copyrightable US Government data.
All data is provided as-is, including misspellings, format problems, etc.,
from the NWS sources.

Thanks to the National Weather Service for making this information available.
And, of course, thanks to fellow taxpayers!

BUGS:

Please report bugs in the source data files to the National Weather Service
Please report bugs in this script to ian-weisser@ubuntu.com


AUTHORS, COPYRIGHT, AND LICENSE

Written by Ian Weisser. Copyright 2014 by Ian Weisser ian@korinthianviolins.com
This software is freely redistributable under the terms of the GPLv3 license.
"""

# Python Standard Library (Debian package libpython3.*-minimal)
import os

# Python Standard Library (Debian package libpython3.*-stdlib)
import csv
import datetime
#import dbm.gnu

# Other Python packages
import httplib2      # (Debian package python3-httplib2)




DIR    = os.path.expanduser('~') + '/uploads/data'
print(DIR)
CACHE  = '/tmp/weather'
SOURCE = { 'Radar' : 'http://www.ncdc.noaa.gov/homr/file/nexrad-stations.txt',
           'Metar' : {'Locations':'http://weather.noaa.gov/data/nsd_cccc.txt',
                      'Stations' :'http://weather.noaa.gov/pub/data/' +
                                  'observations/metar/stations/' },
           'Zones' : 'http://www.nws.noaa.gov/geodata/catalog/wsom/' +
                     'html/cntyzone.htm'
         }



class Radar(dict):
    """
    Download, process, and save radar station data
    - Download the radar station table
    - Parse the radar station table into a dict
    - Output the dict into a csv file
    - (optional) Output the dict into a dbm file
    """
    def __init__(self):
        """ Create the dict, download and unzip the data """
        super(Radar, self).__init__()
        self.content = ""
        self.status  = 0
        self.download_nws()

    def download_nws(self):
        """ Download from the NWS, and unzip the kml file """
        get                = httplib2.Http(CACHE)
        resp, content      = get.request(SOURCE['Radar'], "GET")
        self.status        = resp['status']
        self.content       = content.decode('utf-8')

    def parse_nws(self):
        """
        Parse the NWS radar station file
        First, parse the header to determine field widths and column name
        Then parse the body into a dict
        """
        stations = self.content.split('\r\n')[:-1]

        column_metadata = []
        line1 = stations[0]                  # COLUMN NAMES
        line2 = stations[1]                  # ------ -----
        for col in range(0, len(line1), 1):
            if col == 0:
                start = 0
            elif line2[col] == '-':
                continue
            else:  # line2[col] == ' '
                name = line1[start:col].strip()
                column_metadata.append((name, start, col)) # Append a tuple
                start = col                                # Reset start

        for one_radar_line in stations[2:]:   # Lines 0 and 1 are header
            if one_radar_line == '':          # Blank CR/LF at EOF
                continue
            one_radar = {}
            for field in column_metadata:
                col_name            = field[0]
                col_start           = field[1]
                col_end             = field[2]
                field_data          = one_radar_line[col_start:col_end].strip()
                one_radar[col_name] = field_data

            name                    = one_radar['ICAO']
            self[name]              = {}
            self[name]['Name']      = name
            if len(one_radar['ST']) > 0:
                self[name]['Location'] = (one_radar['NAME'] + ' ' +
                                         one_radar['ST'])
            else:
                self[name]['Location'] = (one_radar['NAME'] + ' ' +
                                         one_radar['COUNTRY'])
            self[name]['Latitude']  = one_radar['LAT']
            self[name]['Longitude'] = one_radar['LON']
            self[name]['Elevation'] = one_radar['ELEV']
            self[name]['URL']       = \
                'http://www.ncdc.noaa.gov/nexradinv/chooseday.jsp?id=' + name

            # URL can be generated, too. Merely add the name to the id:
            # http://www.ncdc.noaa.gov/nexradinv/chooseday.jsp?id=PAEC

    def csv(self):
        """ Output the dict as a CSV """
        with open(DIR + '/radar.csv', 'w') as csvfile:
            # Add URL field, if desired
            # Add Elevation field, if desired
            fieldnames = ['Name', 'Location',  'Latitude', 'Longitude' ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            rows = list(self.keys())
            rows.sort()
            for row in rows:
                writer.writerow(self[row])

    #def dbm(self):
    #    """ Output the dict as a DBM lookup table (faster than CSV) """
    #    dbf  = dbm.gnu.open(DIR + '/dbm/radar.dbm','n')
    #    rows = list(self.keys())
    #    rows.sort()
    #    for row in rows:
    #        # Add URL field, if desired
    #        # Add Elevation field, if desired
    #        dbf[row] = ','.join([str(self[row]['Location']),
    #                                str(self[row]['Latitude']),
    #                                str(self[row]['Longitude'])
    #                                #str(self[row]['Elevation']),
    #                                #str(self[row]['URL']),
    #                          ])
    #    dbf.close()




class Metar(dict):
    """
    Download, process, and save METAR observation station data
    - Download the station list
    - Parse the station list into a dict
    - Output the dict into a csv file
    - (optional) Output the dict into a dbm file
    """
    def __init__(self):
        """ Create the dict, download and unzip the data """
        super(Metar, self).__init__()
        self.stations  = []         # Simple list of downloadable stations
        self.list_of_stations()     # Populate the list. Data check
        self.status    = 0
        self.locations = ''
        self.download_nws()

    def list_of_stations(self):
        """
        Create a simple list of observation station codes
        not associated with any location. A data check.
        """
        get     = httplib2.Http(CACHE)
        content = get.request(SOURCE['Metar']['Stations'], "GET")[1]
        html    = content.decode('utf-8').split('\n')
        for line in html:
            if '<img src="/icons/text.gif" alt="[TXT]">' in line:
                self.stations.append(line.split('"')[5][0:4])

    def download_nws(self):
        """ Download worldwide METARs from the NWS """
        get             = httplib2.Http(CACHE)
        resp, content   = get.request(SOURCE['Metar']['Locations'], "GET")
        self.status     = resp['status']
        self.locations  = content.decode('utf-8')

    def parse(self):
        """
        Parse the NWS METAR file
        Fields are defined at http://weather.noaa.gov/tg/site.shtml
        """
        stations = self.locations.split('\n')[:-1]
        for station in stations:
            sta_line = station.split(';')
            icao = sta_line[0] 
            if icao.upper() not in self.stations:
                continue

            self[icao]                 = {}    
            self[icao]['Name']         = icao
            del sta_line[0]
                
            #self[icao]['Block_Num']    = sta_line[0].strip()
            del sta_line[0]

            #self[icao]['Station_Num']  = sta_line[0].strip()
            del sta_line[0]

            self[icao]['Location']     = sta_line[0].strip()
            del sta_line[0]

            if len(sta_line[0]) in [0, 2, 24]:
                #self[icao]['State']    = sta_line[0].strip()
                del sta_line[0]

            #self[icao]['Country']      = sta_line[0].strip()
            del sta_line[0]

            #self[icao]['WMO_Region']   = sta_line[0].strip()
            del sta_line[0]

            self[icao]['Latitude']     = dms_to_dec(sta_line[0].strip())
            del sta_line[0]

            self[icao]['Longitude']    = dms_to_dec(sta_line[0].strip())
            del sta_line[0]

            #self[icao]['Upper_Lat']     = station.split(';')[9].strip()
            #self[icao]['Upper_Lon']     = station.split(';')[10].strip()
            #self[icao]['Elevation']     = station.split(';')[11].strip()
            #self[icao]['Upper_Elev']    = station.split(';')[12].strip()
            #self[icao]['RSBN']          = station.split(';')[13].strip()


    def csv(self):
        """ Output the dict as a CSV """
        with open(DIR + '/metar.csv', 'w') as csvfile:
            # Add other fields, if desired
            fieldnames = ['Name', 'Location',  'Latitude', 'Longitude' ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            rows = list(self.keys())
            rows.sort()
            for row in rows:
                writer.writerow(self[row])

    #def dbm(self):
    #    """ Output the dict as a DBM lookup table (faster than CSV) """
    #    dbf = dbm.gnu.open(DIR + '/dbm/metar.dbm','n')
    #    rows = list(self.keys())
    #    rows.sort()
    #    for row in rows:
    #        # Add other fields, if desired
    #        dbf[row] = ','.join([str(self[row]['Location']),
    #                                str(self[row]['Latitude']),
    #                                str(self[row]['Longitude'])
    #                          ])
    #    dbf.close()



class Zones(dict):
    """
    Download, process, and save forecast zones
    - Download the zone list
    - Parse the zone list into a dict
    - Output the dict into a csv file
    - (optional) Output the dict into a dbm file
    """
    def __init__(self):
        """ Create the dict, download and unzip the data """
        super(Zones, self).__init__()
        self.status  = 0
        self.data_status   = 0
        self.data_url      = ''
        self.content       = ''
        self.download(SOURCE['Zones'])
        self.index_status = self.status
        self.status = 0

    def download(self, url):
        """
        Download the index web page to determine the zone file URL
        """
        get               = httplib2.Http(CACHE)
        resp, content     = get.request(url, "GET")
        self.status       = resp['status']
        self.content      = content.decode('utf-8')


    def parse_nws_index(self):
        """
        Locate the current zone file, listed on the index page
        Several may be listed - parse the html to determine the dates of each
        possible file.
        Figure out which file is the most recent (but not future)
        """
        possible_files = []
        lines = self.content.lower().split('tr>')
        for line in lines:
            if "download text file bp" in line:
                date_str = line.split('</td>')[0].split('<td>')[1].strip()
                date     = datetime.datetime.strptime(date_str, "%d %B %Y")
                url_stub = line.split('</td>')[1].split('"')[1].strip('.')
                url      = SOURCE['Zones'][0:-18] + url_stub[0:-3] + 'txt'
                possible_files.append({date:url})

        # Figure out which date is most recent in the past
        if len(possible_files) == 0:
            self.index_status = 0
        elif len(possible_files) == 1:
            possible = possible_files[0]
            self.data_url = list(possible.values())[0]
        else:
            today                  = datetime.datetime.today().timestamp()
            smallest_timedelta     = 10000000000
            smallest_timedelta_url = ''
            for possible in possible_files:
                date = list(possible.keys())[0].timestamp()
                if today - date < smallest_timedelta:
                    smallest_timedelta     = today - date
                    smallest_timedelta_url = list(possible.values())[0]
            self.data_url = smallest_timedelta_url


    def parse_nws_zones(self):
        """ Parse the zones fileinto a dict """
        lines = self.content.split('\r\n')[0:-1]
        for line in lines:
            zone          = line.split('|')[4]
            if len(zone) < 5:
                continue
            self[zone]    = {}
            #self[zone]['State_Code']    = line.split('|')[0]
            #self[zone]['Forecast_Zone'] = line.split('|')[1]
            #self[zone]['Warning_Area']  = line.split('|')[2]
            self[zone]['Zone_Name']     = line.split('|')[3]
            self[zone]['Zone']          = line.split('|')[4]
            self[zone]['County']        = line.split('|')[5]
            #self[zone]['Fips_Code']     = line.split('|')[6]
            #self[zone]['Time_Zone']     = line.split('|')[7]
            #self[zone]['Within_Cnty']   = line.split('|')[8]
            self[zone]['Latitude']      = line.split('|')[9]
            self[zone]['Longitude']     = line.split('|')[10]

    def csv(self):
        """ Output the dict as a CSV """
        with open(DIR + '/zone.csv', 'w') as csvfile:
            # Add other fields, if desired
            fieldnames = ['Zone', 'Zone_Name', 'County',
                          'Latitude', 'Longitude' ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames,
                                    extrasaction='ignore')
            writer.writeheader()
            rows = list(self.keys())
            rows.sort()
            for row in rows:
                writer.writerow(self[row])

    #def dbm(self):
    #    """ Output the dict as a DBM lookup table (faster than CSV) """
    #    dbf = dbm.gnu.open(DIR + '/dbm/zone.dbm','n')
    #    rows = list(self.keys())
    #    rows.sort()
    #    for row in rows:
    #        # Add other fields, if desired
    #        dbf[row] = ','.join([str(self[row]['Zone']),
    #                                str(self[row]['Zone_Name']),
    #                                str(self[row]['County']),
    #                                str(self[row]['Latitude']),
    #                                str(self[row]['Longitude'])
    #                          ])
    #    dbf.close()



def dms_to_dec(dms_string, spacer='-'):
    """Simple conversion from dd-mm-ssW to -dd.xxx"""
    dms = dms_string[:-1].split(spacer)

    # Degrees
    degrees = int(dms[0])

    # Minutes and Seconds
    if len(dms) > 1:
        minutes = float(dms[1])
        minsec = minutes / 60

    if len(dms) > 2:
        seconds = float(dms[2])
        minsec = minsec + (seconds / 3600)

    # Truncating
    minsec = str(minsec)[2:5]

    # Change S and W to negative
    if dms_string[-1:] in ['S', 'W']:
        sign = '-'
    else:
        sign = ''

    result = "{}{}.{}".format(sign, degrees, minsec)
    return result



def run():
    """
    Build the complete database. Overwrite any older database without checking
    """
    print("Starting run...")

    print("Checking US radar stations...")
    radar = Radar()
    if radar.status == '304' \
    and os.path.exists(DIR + '/radar.csv'):
        print("US radar information has not changed")
    elif radar.status in ['200', '304']:
        print("Updating US radar lookup table")
        radar.parse_nws()
        radar.csv()
    else:
        print("WARNING: Server status: {}".format(radar.status))


    print("Checking METAR observation stations...")
    metar = Metar()
    if  metar.status == '304' \
    and os.path.exists(DIR + '/metar.csv'):
        print("METAR information has not changed")
    elif metar.status in ['200', '304']:
        print("Updating METAR lookup table")
        metar.parse()
        metar.csv()
    else:
        print("WARNING: Server status: {}".format(metar.status))


    print("Checking Forcast/Alert Zone data...")
    zone = Zones()
    if zone.index_status == '304' \
    and os.path.exists(DIR + '/zone.csv'):
        print("Zone information has not changed")
    elif zone.index_status in ['200', '304']:
        zone.parse_nws_index()
        zone.download(zone.data_url)
        zone.data_status = zone.status
        zone.status = 0
        if zone.data_status == '304' \
        and os.path.exists(DIR + '/csv/zone.csv'):
            print("Zone information has not changed")
        elif zone.data_status in ['200', '304']:
            print("Updating Forecast/Alert Zone lookup table")
            zone.parse_nws_zones()
            zone.csv()
        else:
            print("WARNING: Server status: {}".format(zone.data_status))
    else:
        print("WARNING: Server status: {}".format(zone.index_status))

    print("End of run")


if __name__ == "__main__":
    run()
