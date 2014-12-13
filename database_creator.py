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
import io
import os

# Python Standard Library (Debian package libpython3.*-stdlib)
import csv
import datetime
#import dbm.gnu
import zipfile

# Other Python packages
import httplib2      # (Debian package python3-httplib2)




DIR    = os.path.expanduser('~') + '/uploads/data'
CACHE  = '/tmp/weather'
SOURCE = { 'Radar' : 'http://www.ncdc.noaa.gov/oa/radar/nexrad.kmz',
           'Metar' : 'http://weather.noaa.gov/data/nsd_cccc.txt',
           'Zones' :
               'http://www.nws.noaa.gov/geodata/catalog/wsom/html/cntyzone.htm'
         }



class Radar(dict):
    """
    Download, process, and save radar station data
    - Download the radar kml
    - Parse the radar kml into a dict
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
        zip_obj            = zipfile.ZipFile(io.BytesIO(content))
        self.content       = zip_obj.read('doc.kml').decode('utf-8')

    def parse_nws(self):
        """ Parse the NWS KML file with radar information """
        stations = self.content.split('<description>')[1:]
        for station in stations:
            sta  = station.split('</description>')[0].split('<BR>')
            name = sta[0][14:].strip()
            self[name]              = {}
            self[name]['Name']      = name
            self[name]['Location']  = sta[1][9:].strip()
            self[name]['Latitude']  = sta[2][9:].strip()
            self[name]['Longitude'] = sta[3][10:].strip()
            #self[name]['Elevation'] = sta[4][10:].strip()
            #self[name]['URL']       = sta[7].split('"')[1].strip()

            # URL can be generated, too. Merely add the name to the id:
            # http://www.ncdc.noaa.gov/nexradinv/chooseday.jsp?id=PAEC

    def csv(self):
        """ Output the dict as a CSV """
        with open(DIR + '/csv/radar.csv', 'w') as csvfile:
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
        self.content = ""
        self.status  = 0
        self.download_nws()

    def download_nws(self):
        """ Download worldwide METARs from the NWS """
        get           = httplib2.Http(CACHE)
        resp, content = get.request(SOURCE['Metar'], "GET")
        self.status   = resp['status']
        self.content  = content.decode('utf-8')

    def dms_to_dec(self, dms_string, spacer='-'):
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


    def parse(self):
        """
        Parse the NWS METAR file
        Fields are defined at http://weather.noaa.gov/tg/site.shtml
        """
        stations = self.content.split('\r\n')[:-1]
        for station in stations:
            icao                       = station.split(';')[0].strip()
            self[icao]                 = {}
            self[icao]['Name']         = icao
            #self[icao]['Block_Num']    = station.split(';')[1].strip()
            #self[icao]['Station_Num']  = station.split(';')[2].strip()
            self[icao]['Location']     = station.split(';')[3].strip()
            #self[icao]['State']        = station.split(';')[4].strip()
            #self[icao]['Country']      = station.split(';')[5].strip()
            #self[icao]['WMO_Region']   = station.split(';')[6].strip()
            self[icao]['Latitude']     = self.dms_to_dec(
                                           station.split(';')[7].strip())
            self[icao]['Longitude']    = self.dms_to_dec(
                                           station.split(';')[8].strip())
            #self[icao]['Upper_Lat']     = station.split(';')[9].strip()
            #self[icao]['Upper_Lon']     = station.split(';')[10].strip()
            #self[icao]['Elevation']     = station.split(';')[11].strip()
            #self[icao]['Upper_Elev']    = station.split(';')[12].strip()
            #self[icao]['RSBN']          = station.split(';')[13].strip()

    def csv(self):
        """ Output the dict as a CSV """
        with open(DIR + '/csv/metar.csv', 'w') as csvfile:
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
        self.index_status  = 0
        self.data_url      = ''
        self.content       = ''
        self.index_status   = self.download(SOURCE['Zones'])


    def download(self, url):
        """
        Download the index web page to determine the zone file URL
        """
        get           = httplib2.Http(CACHE)
        resp, content = get.request(url, "GET")
        self.content  = content.decode('utf-8')
        return resp['status']


    def parse_nws_index(self):
        """
        Locate the current zone file, listed on the index page
        Several may be listed - parse the html to determine the dates of each
        possible file. Figure out which file is the most recent (but not future)
        """

        # Find the appropriate table within the web page
        text    = self.content.split(
            'County-Public Forecast Zones Correlation file (CONUS/OCONUS)')[1]
        text    = text.split('</table>')[0]
        lines   = text.split('<tr>')[1:]

        # Parse the table into a dict of date:url possibles
        possible_files = {}
        for line in lines:
            date_txt = line.split('<td>')[1].split('</TD>')[0].strip()
            date     = datetime.datetime.strptime(date_txt, "%d %B %Y")
            url_stub = line.split('<TD>')[1].split('"')[1][2:]
            url      = SOURCE['Zones'][0:-18] + url_stub
            possible_files[date] = url

        # Figure out which date is most recent in the past
        today        = datetime.datetime.today()
        current_file = None
        for date in possible_files.keys():
            if date > today:
                continue
            elif current_file == None:
                current_file = date
                continue
            elif date > current_file:
                date = current_file

        # Return the corresponding URL
        self.data_url = possible_files[current_file]


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
        with open(DIR + '/csv/zone.csv', 'w') as csvfile:
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
        radar.dbm()

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
        metar.dbm()
    else:
        print("WARNING: Server status: {}".format(metar.status))


    print("Checking Forcast/Alert Zone data...")
    zone_followup = False
    zone = Zones()
    if zone.index_status == '304' \
    and os.path.exists(DIR + '/csv/zone.csv'):
        print("Zone information has not changed")
    elif zone.index_status in ['200', '304']:
        zone_followup = True
    else:
        print("WARNING: Server status: {}".format(zone.index_status))

    if zone_followup:
        zone.parse_nws_index()
        zone.data_status = zone.download(zone.data_url)
        if zone.data_status == '304' \
        and os.path.exists(DIR + '/csv/zone.csv'):
            print("Zone information has not changed")
        elif zone.data_status in ['200', '304']:
            print("Updating Forecast/Alert Zone lookup table")
            zone.parse_nws_zones()
            zone.csv()
            zone.dbm()
        else:
            print("WARNING: Server status: {}".format(zone.data_status))


    print("End of run")


if __name__ == "__main__":
    run()
