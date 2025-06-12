
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


