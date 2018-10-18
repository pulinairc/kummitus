import requests

import xml.etree.ElementTree as ET

FMI_XML_NAMESPACES = {
    'wfs'   : 'http://www.opengis.net/wfs/2.0',
    'gml'   : 'http://www.opengis.net/gml/3.2',
    'BsWfs' : 'http://xml.fmi.fi/schema/wfs/2.0'
}

def get_fmi_url(api_key):
    """Get base URL for FMI service. Return None if api_key is missing."""
    if api_key:
        return 'http://data.fmi.fi/fmi-apikey/%s/wfs' % api_key

def getresponse(url, params):
    if(url and params):
        return requests.get(url, params=params)
    return None

def fmi_observations_weather_simple(api_key, params):
    """
    Get realtime information from finnish weather stations.

    From API documentation:
    
    Real time weather observations from weather stations. Default set contains
    wind speed, direction, gust, temperature, relative humidity, dew point,
    pressure reduced to sea level, one hour precipitation amount, visibility
    and cloud cover. By default, the data is returned from last 12 hour. At
    least one location parameter (geoid/place/fmisid/wmo/bbox) has to be given.
    The data is returned as a simple feature format.

    Possible query parameters:
    
    starttime       Parameter begin specifies the begin of time interval in
                    ISO-format (for example 2012-02-27T00:00:00Z).

    endtime         End of time interval in ISO-format
                    (for example 2012-02-27T00:00:00Z).

    timestep        The time step of data in minutes. Notice that timestep is
                    calculated from start of the ongoing hour or day.

    parameters      Comma separated list of meteorological parameters to
                    return.
    
    crs             Coordinate projection to use in results.  For example
                    EPSG::3067

    bbox            Bounding box of area for which to return data
                    (lon,lat,lon,lat). For example 21,61,22,62

    place           The location for which to provide data. Region can be given
                    after location name separated by comma (for example 
                    Kumpula,Kolari).
    
    fmisid          Identifier of the observation station.

    maxlocations    How many observation stations are fetched around queried
                    locations. Note that stations are only searched with 50
                    kilometers radius around the location.
    
    geoid           Geoid of the location for which to return data. (ID from
                    geonames.org)

    wmo             WMO code of the location for which to return data.

    Returned data:

    p_sea           Air pressure MSL        (hPa)
    r_1h            Precipitation amount    (mm)
    rh              Relative humidity       (%)
    ri_10min        Precipitation intensity (mm/h)
    snow_aws        Snow depth              (mm)
    t2m             Air temperature         (deg c)
    td              Dew-point temperature   (deg c)
    vis             Horizontal visibility   (m)
    wd_10min        Wind direction          (deg)
    wg_10min        Wind gust speed         (m/s) 
    ws_10min        Wind speed              (m/s)
    """
    url = get_fmi_url(api_key)
    response = getresponse(url, params)
    if response:
        results = {}
        root = ET.fromstring(response.text)
        ns = FMI_XML_NAMESPACES
        for elem in root.iterfind('.//BsWfs:BsWfsElement', ns):
            time = elem.find('.//BsWfs:Time', ns).text
            name = elem.find('.//BsWfs:ParameterName', ns).text
            value = elem.find('.//BsWfs:ParameterValue', ns).text

            measuretime = results.get(time)
            if measuretime:
                parameter = measuretime.get(name)
                if parameter:
                    print "ERROR: Duplicate value for parameter:", name  
                else:
                    measuretime[name] = value
            else:
                results[time] = { name : value }
        
        return results
    else:
        print 'ERROR: Could not get data from FMI API.'
