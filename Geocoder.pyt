import arcpy
#import geopy
import os
import sys
#import urllib
import json

##----------------------------------------------------------------------
key = ""
##----------------------------------------------------------------------



if sys.version_info.major >= 3:
    from urllib.request import urlopen as urlopen
    from urllib.parse import urlencode

    def multiversionJson(url):
        return json.loads(urlopen(url).readall().decode('utf-8'))

else:
    from urllib import urlopen as urlopen
    from urllib import urlencode as urlencode

    def multiversionJson(url):
        return json.loads(urlopen(url).read())
    

class MetaData(object):
    """Represents metadata results from an attempted geocode
    """
    
    def __init__(self):
        self.confidence = ""
        self.matchCodes = ""
        self.hasMatch = False
        self.entityType = ""
        self.usageType = ""
        self.calculationMethod = ""
        
    def reset(self):
        self.confidence = ""
        self.matchCodes = ""
        self.hasMatch = False
        self.entityType = ""
        self.usageType = ""
        self.calculationMethod = ""
	
class DataPoint(object):
    """Represents data result from an attempted geocode
    """

    def __init__(self):
        self.formattedAddress = ""
        self.latitude = 0
        self.longitude = 0

    def load(self, data):
        point = data.get("point")
        self.latitude = point.get("coordinates")[0]
        self.longitude = point.get("coordinates")[1]
        self.formattedAddress = data.get("address")["formattedAddress"]

    def reset(self):
        self.formattedAddress = ""
        self.latitude = 0
        self.longitude = 0

    def coordinates(self):
        return [self.latitude, self.longitude]

    def address(self):
        return self.formattedAddress
	
class GeocodeResults(object):

    def __init__(self):
        self.dataResults = DataPoint()
        self.metaResults = MetaData()
        self.success = False
        self.ErrorReason = None
        self.url = ""

    def reset(self):
        self.dataResults.reset()
        self.metaResults.reset()
        self.success = False
        self.ErrorReason = None

    def coordinates(self):
        return self.dataResults.coordinates()

    def resolvedAddress(self):
        return self.dataResults.address()
    	
class Geocoder(object):
    """Encapsulates the actions for geocoding
    """

    def __init__(self, key):
        self.urlroot = "http://dev.virtualearth.net/REST/v1/Locations"
        self.key = key

    def geocode(self, query):
        
        params = {"query":query,
          "key": self.key,
          "maxResult" : 1
          }
        url = "?".join((self.urlroot, urlencode(params)))

        results = GeocodeResults()
        results.url = url
        try:
            resultSet = multiversionJson(url)
            #resultSet = json.loads(urlopen(url).read())
            #resultSet =json.loads(urlopen(url).readall().decode('utf-8'))
        except:
            results.ErrorReason = "Request Failed"
            return results
        resultRecords = resultSet['resourceSets'][0]['resources']
        if len(resultRecords) < 1:
            results.ErrorReason = "Location Not Found"
            return results

        results.dataResults.load(resultRecords[0])
        results.success = True
        return results	
	
	
class Toolbox(object):
    def __init__(self):
        self.label =  "Geocoding Toolbox"
        self.alias  = "Geocoder"

        # List of tool classes associated with this toolbox
        self.tools = [Geocode] 

class Geocode(object):
    def __init__(self):
        self.label       = "Geocode"
        self.description = "Geocodes input address to create a new  " + \
                           "featureclass from the resulting locations "

    def getParameterInfo(self):
        #Define parameter definitions

        # Input Table parameter
        in_table = arcpy.Parameter(
            displayName="Input Table",
            name="in_tables",
            datatype="GPTableView",
            parameterType="Required",
            direction="Input")
        
        # Address Field parameter
        address_field = arcpy.Parameter(
            displayName="Address Field",
            name="address_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        address_field.parameterDependencies = [in_table.name]

	# City Field parameter
        city_field = arcpy.Parameter(
            displayName="City Field",
            name="city_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        city_field.parameterDependencies = [in_table.name]

	# State Field parameter
        state_field = arcpy.Parameter(
            displayName="State Field",
            name="state_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        state_field.parameterDependencies = [in_table.name]

	# Zipcode Field parameter
        zipcode_field = arcpy.Parameter(
            displayName="Zipcode Field",
            name="zipcode_field",
            datatype="Field",
            parameterType="Optional",
            direction="Input")
        zipcode_field.parameterDependencies = [in_table.name]
        
        # Derived Output Features parameter
        out_features = arcpy.Parameter(
            displayName="Output Features",
            name="out_features",
            datatype="DEFeatureClass",
            parameterType="Required",
            direction="Output")
        
        out_features.parameterDependencies = [in_table.name]
        out_features.schema.clone = True

        parameters = [in_table, address_field, city_field, state_field, zipcode_field, out_features]
        
        return parameters
    def isLicensed(self): #optional
        return True
    def updateParameters(self, parameters): 
	#optional

        return

    def updateMessages(self, parameters): #optional
        return

    def execute(self, parameters, messages):
        inputTable  = parameters[0].valueAsText
        addressField   = parameters[1].valueAsText
        cityField = parameters[2].valueAsText
        stateField = parameters[3].valueAsText
        zipField = parameters[4].valueAsText
        output   = parameters[5].valueAsText

	#constants

        spatialReference = arcpy.SpatialReference(4326)

        memoryTable = arcpy.TableToTable_conversion(inputTable, "in_memory", "memoryTable")

        arcpy.AddField_management(memoryTable,
				  "Latitude",
				  "DOUBLE")
        arcpy.AddField_management(memoryTable,
				  "Longitude",
				  "DOUBLE")

        arcpy.AddField_management(memoryTable,
				  "GeoAddress",
				  "TEXT")

        addressGeocoder = Geocoder(key)
        cursorFields = ["Latitude", "Longitude", "GeoAddress"]
        additiveFields = [addressField, cityField, stateField, zipField]
        for field in additiveFields:
            if field:
                cursorFields.append(field)
        with arcpy.da.UpdateCursor(memoryTable, cursorFields) as TableRecords:
            for record in TableRecords:
                location = " ".join(record[3:])
                if location.strip() == "":
                    continue
                result = addressGeocoder.geocode(location)
                if result.success == False and result.ErrorReason == "Request Failed":
                    break
                coordinates = result.coordinates()
              
                record[0] = coordinates[0]
                record[1] = coordinates[1]
                record[2] = result.resolvedAddress()

                TableRecords.updateRow(record)                    

	# Process: Make XY Event Layer
        arcpy.MakeXYEventLayer_management(memoryTable, "Longitude", "Latitude", "XY_Event_Layer", spatialReference)

        if arcpy.Exists(output):
            arcpy.Delete_management(output)

	# Process: Copy Features
        arcpy.CopyFeatures_management("XY_Event_Layer", output, "", "0", "0", "0")
        arcpy.Delete_management("in_memory")

