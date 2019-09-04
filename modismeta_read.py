"""
  a301.scripts.modismeta_read 
  ___________________________

  parses a Modis Level1b CoreMetata.0 string and extracts
  a dictionary. 

  to run from the command line::

    modisheader  level1b_file.hdf

  to run from a python script::

    from a301.scripts.modismeta_read import parseMeta
    out=parseMeta(level1b_file)
"""
from __future__ import print_function
import pprint
import types
import pdb
import numpy as np
import argparse
from pathlib import Path
from pyhdf.SD import SD, SDC
import sys
import pprint


def read_mda(attribute):
    lines = attribute.split('\n')
    mda = {}
    current_dict = mda
    path = []
    for line in lines:
        if not line:
            continue
        if line.strip() == 'END':
            break
        try:
            key, val = line.split('=')
        except ValueError:
            continue
        key = key.strip()
        val = val.strip()
        try:
            val = eval(val)
        except (NameError,SyntaxError,ValueError) as e:
            pass
        if key in ['GROUP', 'OBJECT']:
            new_dict = {}
            path.append(val)
            current_dict[val] = new_dict
            current_dict = new_dict
        elif key in ['END_GROUP', 'END_OBJECT']:
            if val != path[-1]:
                raise SyntaxError
            path = path[:-1]
            current_dict = mda
            for item in path:
                current_dict = current_dict[item]
        elif key in ['CLASS', 'NUM_VAL']:
            pass
        else:
            current_dict[key] = val
    return mda
    
    
class metaParse:
    def __init__(self,metaDat):
        import re
        self.metaDat=str(metaDat).rstrip(' \t\r\n\0')
        self.meta_dict = read_mda(self.metaDat)
        the_dict=self.meta_dict['INVENTORYMETADATA']
        product=the_dict['COLLECTIONDESCRIPTIONCLASS']['SHORTNAME']['VALUE']
        L2 = product.find('L2') > -1
        if L2:
            rectangle=the_dict[ 'SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']['BOUNDINGRECTANGLE']
            left_lon=rectangle['WESTBOUNDINGCOORDINATE']['VALUE']
            right_lon=rectangle['EASTBOUNDINGCOORDINATE']['VALUE']
            top_lat=rectangle['NORTHBOUNDINGCOORDINATE']['VALUE']
            bot_lat=rectangle['SOUTHBOUNDINGCOORDINATE']['VALUE']
            theLongs=[right_lon,left_lon,left_lon,right_lon]
            theLats=[bot_lat,bot_lat,top_lat,top_lat]  #ccw from lower right
        else:
            #pdb.set_trace()
            theLongs=self.meta_dict['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']\
                      ['HORIZONTALSPATIALDOMAINCONTAINER']['GPOLYGON']['GPOLYGONCONTAINER']\
                      ['GRINGPOINT']['GRINGPOINTLONGITUDE']['VALUE']
            theLats=self.meta_dict['INVENTORYMETADATA']['SPATIALDOMAINCONTAINER']['HORIZONTALSPATIALDOMAINCONTAINER']\
                     ['GPOLYGON']['GPOLYGONCONTAINER']['GRINGPOINT']['GRINGPOINTLATITUDE']['VALUE']
        lon_list,lat_list = np.array(theLongs),np.array(theLats)
        min_lat,max_lat=np.min(lat_list),np.max(lat_list)
        min_lon,max_lon=np.min(lon_list),np.max(lon_list)
        lon_0 = (max_lon + min_lon)/2.
        lat_0 = (max_lat + min_lat)/2.
        lon_list, lat_list=list(lon_list),list(lat_list)
        corner_dict = dict(lon_list=lon_list,lat_list=lat_list,
                           min_lat=min_lat,max_lat=max_lat,min_lon=min_lon,
                           max_lon=max_lon,lon_0=lon_0,lat_0=lat_0)
        self.value1=corner_dict
        self.value2=self.meta_dict['INVENTORYMETADATA']['ORBITCALCULATEDSPATIALDOMAIN']['ORBITCALCULATEDSPATIALDOMAINCONTAINER']
        self.value3=self.meta_dict['INVENTORYMETADATA']['ECSDATAGRANULE']
        self.value4=self.meta_dict['INVENTORYMETADATA']['RANGEDATETIME']
        self.value5=self.meta_dict['INVENTORYMETADATA']['COLLECTIONDESCRIPTIONCLASS']
        self.value6=self.meta_dict['INVENTORYMETADATA']['ASSOCIATEDPLATFORMINSTRUMENTSENSOR']\
                                         ['ASSOCIATEDPLATFORMINSTRUMENTSENSORCONTAINER']

def parseMeta(filename):
    """
    Read useful information from a CoreMetata.0 attribute

    Parameters
    ----------

    filename: str or Path object
       name of an hdf4 modis level1b file

    Returns
    -------
    
    outDict: dict
        key, value:

    lat_list: np.array
        4 corner latitudes
    lon_list: np.array
        4 corner longitudes
    max_lat: float
        largest corner latitude
    min_lat: float
        smallest corner latitude
    max_lon: float
        largest corner longitude
    min_lon: float
        smallest corner longitude
    daynight: str
        'Day' or 'Night'
    starttime: str
        swath start time in UCT
    stoptime: str
        swath stop time in UCT
    startdate: str
        swath start datein UCT
    orbit: str
        orbit number
    equatordate: str
        equator crossing date in UCT
    equatortime: str
        equator crossing time in UCT
    nasaProductionDate: str
        date file was produced, in UCT
    """
    filename=str(filename)
    the_file = SD(filename, SDC.READ)
    metaDat=the_file.attributes()['CoreMetadata.0']
    parseIt=metaParse(metaDat)
    outDict={}
    outDict['orbit']=parseIt.value2['ORBITNUMBER']['VALUE']
    outDict['daynight']=parseIt.value3['DAYNIGHTFLAG']['VALUE']
    outDict['filename']=parseIt.value3['LOCALGRANULEID']['VALUE']
    outDict['stopdate']=parseIt.value4['RANGEENDINGDATE']['VALUE']
    outDict['startdate']=parseIt.value4['RANGEBEGINNINGDATE']['VALUE']
    outDict['starttime']=parseIt.value4['RANGEBEGINNINGTIME']['VALUE']
    outDict['stoptime']=parseIt.value4['RANGEENDINGTIME']['VALUE']
    outDict['equatortime']=parseIt.value2['EQUATORCROSSINGTIME']['VALUE']
    outDict['equatordate']=parseIt.value2['EQUATORCROSSINGDATE']['VALUE']
    outDict['nasaProductionDate']=parseIt.value3['PRODUCTIONDATETIME']['VALUE']
    outDict['type'] = parseIt.value5
    outDict['sensor'] = parseIt.value6
    outDict.update(parseIt.value1)
    return outDict

def make_parser():
    """
    set up the command line arguments needed to call the program
    """
    linebreaks = argparse.RawTextHelpFormatter
    parser = argparse.ArgumentParser(
        formatter_class=linebreaks, description=__doc__.lstrip())
    parser.add_argument('level1b_file', type=str, help='name of level1b hdf4 file')
    return parser

def main(args=None):
    """
    args: optional -- if missing then args will be taken from command line
          or pass [level1b_file] -- list with name of level1b_file to open
    """
    parser = make_parser()
    parsed_args = parser.parse_args(args)
    filename = str(Path(parsed_args.level1b_file).resolve())
    out=parseMeta(filename)
    print(f'header for {filename}')
    pprint.pprint(out)

if __name__=='__main__':
    sys.exit(main())

