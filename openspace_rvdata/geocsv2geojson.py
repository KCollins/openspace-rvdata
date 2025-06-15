
import pandas as pd
import json
import io

def get_comment_dataframe(fname):
    """
    Reads a CSV file, extracts lines starting with '#', and returns them as a pandas DataFrame.

    Args:
        fname (str): The path to the CSV file.

    Returns:
        pandas.DataFrame: A DataFrame where the index represents the extracted
                          keys from comment lines (e.g., 'dataset', 'title'),
                          and the 'Value' column contains their corresponding values.
                          Returns an empty DataFrame if the file is not found or no
                          comment lines are present.
    """
    comment_data = {}
    try:
        with open(fname, 'r', encoding='utf-8') as f:
            for line in f:
                # Check if the line starts with '#' after stripping leading/trailing whitespace
                if line.strip().startswith('#'):
                    # Remove the '#' and any leading/trailing whitespace from the start of the line
                    processed_line = line.strip().lstrip('#').strip()
                    if ':' in processed_line:
                        # Split by the first colon to separate key and value
                        key, value = processed_line.split(':', 1)
                        comment_data[key.strip()] = value.strip()
                    else:
                        # If a line doesn't have a key:value format, store it with a generic key
                        # This handles cases like a standalone comment line without a colon
                        comment_data[f"unparsed_line_{len(comment_data)}"] = processed_line
    except FileNotFoundError:
        print(f"Error: The file '{fname}' was not found.")
        return pd.DataFrame(columns=['Value']) # Return an empty DataFrame on error
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        return pd.DataFrame(columns=['Value']) # Return an empty DataFrame on error

    # Convert the dictionary to a pandas DataFrame
    # The dictionary keys become the DataFrame's index, and values go into the 'Value' column
    df_comments = pd.DataFrame.from_dict(comment_data, orient='index', columns=['Value'])
    return df_comments

def convert_geocsv_to_geojson(csv_file_path, output_geojson_path):
    """
    Converts a GeoCSV file into a GeoJSON LineString feature collection.

    Args:
        csv_file_path (str): The path to the input GeoCSV file.
        output_geojson_path (str): The path where the output GeoJSON file will be saved.
    """
    # pull metadata from CSV file
    metadata_df = get_comment_dataframe(csv_file_path)
    
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
        "title": metadata_df.loc['cruise_id', 'Value'],
        "description": "Ship track data converted from GeoCSV.",
        "cruise_id": metadata_df.loc['cruise_id', 'Value'],
        "source_dataset": metadata_df.loc['source_event', 'Value'],
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


