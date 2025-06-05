
import pandas as pd
import json
import io

def convert_geocsv_to_geojson(csv_file_path, output_geojson_path):
    """
    Converts a GeoCSV file into a GeoJSON LineString feature collection.

    Args:
        csv_file_path (str): The path to the input GeoCSV file.
        output_geojson_path (str): The path where the output GeoJSON file will be saved.
    """
    # Use io.StringIO to simulate a file for pandas to read after skipping comments
    with open(csv_file_path, 'r') as f:
        # Read lines, filtering out those starting with '#'
        lines = [line for line in f if not line.strip().startswith('#')]

    # Join the filtered lines back into a string and read with pandas
    # This ensures pandas reads only the data rows
    data_csv = io.StringIO("".join(lines))

    # Read the data into a pandas DataFrame
    # The header is automatically inferred from the first uncommented line
    df = pd.read_csv(data_csv)

    # Prepare the list of coordinates (longitude, latitude) for the LineString
    coordinates = []
    for index, row in df.iterrows():
        coordinates.append([row['ship_longitude'], row['ship_latitude']])

    # Prepare properties for the GeoJSON Feature
    # You can include any relevant metadata from the CSV or original GeoCSV header
    # For a LineString, properties usually apply to the entire line.
    # If you want properties for each point, you'd create a MultiPoint or a FeatureCollection of Points.
    # For a trackline, often properties are summary or apply to the whole line.
    # For this example, we'll store all data for each point in the properties of the LineString itself.
    # This is a common way to carry along all data when representing a line.
    # A more idiomatic GeoJSON approach might be to have a FeatureCollection of Points
    # if you need properties specific to each point. But for a continuous line,
    # embedding properties this way or just including common metadata is standard.

    # Let's create a list of properties for each point if we were to make a FeatureCollection of Points.
    # Since we are making a LineString, we can put the full DataFrame as a property (as JSON string)
    # or just selected metadata. For simplicity, let's include the full data for each point
    # as an attribute of the LineString, or just key metadata.

    # For a simple LineString, typically properties describe the line itself.
    # If you need per-point properties, a FeatureCollection of Points is better.
    # However, for a track, often the entire DataFrame's data is useful context.

    # Let's create a GeoJSON Feature representing the entire track as a LineString.
    # We'll embed the original DataFrame rows as a list of dictionaries in the properties
    # if you need to retain all original data per point.

    # Define standard properties based on the GeoCSV header for the LineString
    # These would typically be extracted programmatically if the header was dynamic.
    properties = {
        "title": "Processed Trackline Navigation Data: One Minute Resolution",
        "description": "Ship track data converted from GeoCSV.",
        "cruise_id": "RR2402",
        "source_dataset": "doi:10.7284/160211",
        "attribution": "Rolling Deck to Repository (R2R) Program; http://www.rvdata.us/",
        # Convert DataFrame to a list of dicts for properties, if needed for individual points
        # Be cautious: this can make the GeoJSON file very large if your DataFrame is big.
        # "track_points_data": df.to_dict(orient='records')
    }

    # The main GeoJSON structure
    geojson_data = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                },
                "properties": properties # Attach the common properties to the LineString feature
            }
        ]
    }

    # Save the GeoJSON data to a file
    with open(output_geojson_path, 'w') as f:
        json.dump(geojson_data, f, indent=2)

    print(f"GeoJSON file saved successfully to {output_geojson_path}")

# --- Example Usage ---
# Create a dummy CSV file for demonstration
# csv_content = """#dataset: GeoCSV 2.0
# #title: Processed Trackline Navigation Data: One Minute Resolution
# #field_unit: ISO_8601,degree_east,degree_north,meter/second,degree
# #field_type: datetime,float,float,float,float
# #field_standard_name: iso_time,ship_longitude,ship_latitude,speed_made_good,course_made_good
# #field_long_name: date and time,longitude of vessel,latitude of vessel,course made good,speed made good
# #standard_name_cv: http://www.rvdata.us/voc/fieldname
# #ellipsoid: WGS-84 (EPSG:4326)
# #delimiter: ,
# #field_missing: NAN
# #attribution: Rolling Deck to Repository (R2R) Program; http://www.rvdata.us/
# #source_repository: doi:10.17616/R39C8D
# #source_event: doi:10.7284/910464
# #source_dataset: doi:10.7284/160211
# #cruise_id: RR2402
# #creation_date: 2024-09-26T20:19:27Z
# iso_time,ship_longitude,ship_latitude,speed_made_good,course_made_good
# 2024-02-16T23:59:59.00Z,-117.236072,32.706520,0.00,40.213
# 2024-02-17T00:01:00.00Z,-117.236062,32.706543,0.15,180.000
# 2024-02-17T00:02:00.00Z,-117.236048,32.706520,0.00,239.400
# 2024-02-17T00:03:00.00Z,-117.236063,32.706518,0.22,180.000
# 2024-02-17T00:04:00.00Z,-117.236078,32.706533,0.00,0.000
# 2024-02-17T00:05:00.00Z,-117.236043,32.706518,0.44,90.000
# 2024-02-17T00:06:00.00Z,-117.236075,32.706540,0.29,319.787
# 2024-02-17T00:07:00.00Z,-117.236067,32.706550,0.22,59.400
# 2024-02-17T00:08:00.00Z,-117.236083,32.706563,0.35,0.000
# """
# with open("RR2402_control.geoCSV", "w") as f:
#     f.write(csv_content)

# Define input and output file paths
input_csv = "RR2402_1min.geoCSV"
output_geojson = "RR2402_track.geojson"

# Run the conversion
convert_geocsv_to_geojson(input_csv, output_geojson)
