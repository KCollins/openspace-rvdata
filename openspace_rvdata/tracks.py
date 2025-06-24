"""This module supports the generation of geoJSONs and OpenSpace asset files from geoCSVs."""

import io
import json
import os
import pandas as pd

def get_comment_dataframe(fname):
    """
    Reads a CSV file, extracts lines starting with '#', and returns them as a pandas DataFrame.

    Parameters
    ----------
    fname : str
        The path to the CSV file.

    Returns
    -------
    pandas.DataFrame
        A DataFrame where the index represents the extracted keys from comment lines
        (e.g., 'dataset', 'title'), and the 'Value' column contains their
        corresponding values. Returns an empty DataFrame if the file is not found
        or no comment lines are present.
        
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

    # Convert the dictionary to a pandas DataFrame
    # The dictionary keys become the DataFrame's index, and values go into the 'Value' column
    df_comments = pd.DataFrame.from_dict(comment_data, orient='index', columns=['Value'])
    return df_comments

def convert_geocsv_to_geojson(csv_file_path, output_geojson_path):
    """
    Converts a GeoCSV file into a GeoJSON LineString feature collection.

    Parameters
    ----------
    csv_file_path : str
        The path to the input GeoCSV file.
    output_geojson_path : str
        The path where the output GeoJSON file will be saved.

    Examples
    --------
    >>> import openspace_rvdata.tracks as trk
    >>> csv_path = "tmp/RR2402_1min.geoCSV"
    >>> geojson_path = "tmp/RR2402_1min.geoJSON"
    >>> trk.convert_geocsv_to_geojson(csv_path, geojson_path)

    """
    # pull metadata from CSV file
    metadata_df = get_comment_dataframe(csv_file_path)

    # Use io.StringIO to simulate a file for pandas to read after skipping comments
    with open(csv_file_path, 'r', encoding='utf-8') as f:
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
    for _, row in df.iterrows():
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
    with open(output_geojson_path, 'w', encoding='utf-8') as f:
        json.dump(geojson_data, f, indent=2)

    print(f"GeoJSON file saved successfully to {output_geojson_path}")

# Function to format each row into the desired text block
def format_row_to_text(row):
    """
    Generates an OpenSpace keyframe asset file from a GeoCSV file.

    This function reads a GeoCSV file, extracts and resamples navigation data,
    and embeds it into a Lua-based OpenSpace asset file format. It also
    incorporates cruise metadata extracted from the GeoCSV comments. The
    resulting asset file is saved to a local 'tmp' directory.

    Parameters
    ----------
    fname : str
        The path to the input GeoCSV file containing navigation data.
    resample_rate : str, default "60min"
        The desired sampling rate for the output keyframes. This string should be
        compatible with pandas' `resample` method (e.g., "1min", "30s", "1H").

    Raises
    ------
    FileNotFoundError
        If the specified `fname` does not exist.
    KeyError
        If required metadata keys ('cruise_id', 'source_dataset', 'title') are not
        found in the GeoCSV comments via `get_comment_dataframe`, or if essential
        columns like 'iso_time', 'ship_longitude', or 'ship_latitude' are missing
        from the GeoCSV data.
    ValueError
        If the 'iso_time' column cannot be parsed into datetime objects or
        if `resample_rate` is not a valid pandas frequency string.
    IOError
        If there is an issue writing the output keyframe asset file.
    """

    # Extract the timestamp, removing the ".00Z" part
    iso_time_formatted = f'["{row["iso_time"].split(".")[0]}"]'

    # Construct the formatted string
    formatted_string = f"""  {iso_time_formatted} = {{
    Type = "GlobeTranslation",
    Globe = "Earth",
    Longitude = {row["ship_longitude"]},
    Latitude = {row["ship_latitude"]},
    Altitude = 0,
    SpeedMadeGood = {row["speed_made_good"]},
    CourseMadeGood = {row["course_made_good"]},
    UseHeightmap = false
  }}"""
    return formatted_string

def get_cruise_keyframes(fname, resample_rate="60min"):
    """
    Generates a keyframe asset from geoCSV; saves to local /tmp directory.
    """
    df = pd.read_csv(fname, comment = '#')
    df['datetime'] = pd.to_datetime(df['iso_time'])
    df.index = df['datetime']
    df = df.resample(resample_rate).first()
    df = df.reset_index(drop=True)
    print(df.head(3))
    # Define the "before" and "after" text

    # Let's start by getting metadata:
    mdf = get_comment_dataframe(fname)
    cruise_id = mdf.loc["cruise_id", "Value"]
    cruise_doi = mdf.loc["source_dataset", "Value"].strip("doi:")
    cruise_title = mdf.loc["title", "Value"]
    before_text = """local keyframes = {
    """
    after_text = f"""}}
    
    asset.export("keyframes", keyframes)
    
    asset.meta = {{
      Name = "Ship Track Position: {cruise_id}",
      Description = [[This asset provides position information for the ship track for the cruise {cruise_id}: {cruise_title}]],
      Author = "OpenSpace Team",
      URL = "http://doi.org/{cruise_doi}",
      License = "MIT license"
    }}
    """
    # Specify the output file name
    os.makedirs("tmp", exist_ok=True)
    output_filename = "tmp/" + cruise_id+"_keyframes.asset"

    # Open the file in write mode and write the content
    with open(output_filename, "w", encoding = "utf-8") as f:
        f.write(before_text) # Write the "before" text first
        # Iterate through each row of the DataFrame, format it, and write to the file
        for index, row in df.iterrows():
            if index<len(df):
                f.write(format_row_to_text(row) + ",\n") # Add a newline after each entry for readability
            else:
                f.write(format_row_to_text(row) + "\n") #skip comma on last entry
        f.write(after_text) # Write the "after" text

    print(f"Successfully generated '{output_filename}' with the formatted data.")

# Function to generate assets based on cruise metadata
def get_cruise_asset(mdf: pd.DataFrame):
    """
    Generates and saves a Lua asset file for each cruise in the DataFrame.

    Each cruise's Lua asset file is named 'tmp/{cruise_id}.asset'. These files
    contain dynamic information derived from the corresponding cruise's row in
    the input DataFrame, including the definition of a shared ship model asset
    for visualization in OpenSpace.

    Parameters
    ----------
    mdf : pandas.DataFrame
        The input DataFrame containing cruise metadata.

        Expected columns include (after stripping whitespace):
        'cruise_id' : Unique identifier for the cruise (e.g., "RR2402").
        'cruise_name' : Full name of the cruise.
        'cruise_doi' : Digital Object Identifier for the cruise data.
        'depart_date' : Start date of the cruise in 'YYYY-MM-DD' format.
        'arrival_date' : End date of the cruise in 'YYYY-MM-DD' format.
        'vessel_shortname' : Short name of the vessel (e.g., "Revelle").
        
    """
    # Ensure the 'tmp' directory exists
    output_directory = "tmp"
    os.makedirs(output_directory, exist_ok=True)
    print(f"Ensuring output directory '{output_directory}' exists.")

    # Clean up column names by stripping whitespace
    mdf.columns = mdf.columns.str.strip()

    # --- Iterate through each row (cruise) in the DataFrame to generate cruise assets ---
    for _, row in mdf.iterrows():
        try:
            cruise_id = row['cruise_id']
            cruise_name = row['cruise_name'] # Still useful for meta description
            cruise_doi = row['cruise_doi']
            vessel_shortname = row['vessel_shortname'] # Get the vessel name for this cruise

            # Safe identifier for referencing the ship model asset
            # This is used for the Identifier in the inlined shipModel asset.
            safe_vessel_id = vessel_shortname.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_") # pylint: disable=C0301

            # Convert dates to ISO 8601 format required by OpenSpace Lua assets
            depart_date_str = pd.to_datetime(row['depart_date']).strftime("%Y-%m-%dT%H:%M:%S.00Z")
            arrive_date_str = pd.to_datetime(row['arrive_date']).strftime("%Y-%m-%dT%H:%M:%S.00Z")

            # --- Construct the Lua asset content using an f-string ---
            # The ship model definition is now inlined directly into each cruise asset file.
            lua_content = f"""local sun = asset.require("scene/solarsystem/sun/transforms")
local earthTransforms = asset.require("scene/solarsystem/planets/earth/earth")

-- Define the ship model resource (inlined for each cruise asset)
local shipModel = asset.resource({{
    Name = "{cruise_id} Model",
    Type = "UrlSynchronization",
    Identifier = "{safe_vessel_id}_3d_model", -- Unique identifier for the resource
    Url = "https://github.com/CreativeTools/3DBenchy/raw/master/Single-part/3DBenchy.stl", -- Hardcoded URL for the 3D model
    Version = 1
}})

-- The keyframes for the ship's trajectory
local shipKeyframes = asset.require("./{cruise_id}_keyframes.asset") -- Assumes {cruise_id}_keyframes.asset defines 'keyframes'

-- Define the ship's position based on the keyframes
local shipPosition = {{
    Identifier = "ShipPosition_{cruise_id}",
    Parent = earthTransforms.Earth.Identifier, -- Parent the asset to Earth
    TimeFrame = {{
        Type = "TimeFrameInterval",
        Start = "{depart_date_str}",
        End = "{arrive_date_str}"
    }},
    Transform = {{
        Translation = {{
            Type = "TimelineTranslation",
            Keyframes = shipKeyframes.keyframes
        }}
    }},
    GUI = {{
        Name = "{cruise_id} Position",
        Path = "/Ship Tracks/{vessel_shortname}/{cruise_id}" -- A new path for your custom asset
    }}
}}

-- Define the ship model to be rendered
local shipRenderable = {{
    Identifier = "ShipModel_{cruise_id}",
    Parent = shipPosition.Identifier,
    TimeFrame = {{
        Type = "TimeFrameInterval",
        Start = "{depart_date_str}",
        End = "{arrive_date_str}"
    }},
    Transform = {{
        Scale = {{
            Type = "StaticScale",
            Scale = 1000.0 -- You might need to adjust this scale based on your model's size and desired visibility
        }}
    }},
    Renderable = {{
        Type = "RenderableModel",
        GeometryFile = shipModel .. "3DBenchy.stl", -- Reference the synchronized STL model as required by your example
        LightSources = {{
            sun.LightSource,
            {{
                Identifier = "Camera",
                Type = "CameraLightSource",
                Intensity = 0.5
            }}
        }}
    }},
    GUI = {{
        Name = "{vessel_shortname} Model",
        Path = "/Ship Tracks/{vessel_shortname}/{cruise_id}"
    }}
}}

-- Define the trail for the ship's trajectory
local shipTrail = {{
    Identifier = "ShipTrail_{cruise_id}",
    Parent = earthTransforms.Earth.Identifier, -- Parent the trail to Earth
    Renderable = {{
        Type = "RenderableTrailTrajectory",
        Enabled = true, -- Set to true to show the trail by default
        Translation = {{
            Type = "TimelineTranslation",
            Keyframes = shipKeyframes.keyframes
        }},
        Color = {{ 1.0, 0.5, 0.0 }}, -- An orange trail for visibility (RGB values 0-1)
        StartTime = "{depart_date_str}",
        EndTime = "{arrive_date_str}",
        SampleInterval = 60, -- Sample every 60 seconds
        EnableFade = true -- Enable fade for the trail
    }},
    GUI = {{
        Name = "{cruise_id} Trail",
        Path = "/Ship Tracks/{vessel_shortname}/{cruise_id}",
        Focusable = false
    }}
}}

asset.onInitialize(function()
    openspace.addSceneGraphNode(shipPosition)
    openspace.addSceneGraphNode(shipRenderable)
    openspace.addSceneGraphNode(shipTrail)
end)

asset.onDeinitialize(function()
    openspace.removeSceneGraphNode(shipTrail)
    openspace.removeSceneGraphNode(shipRenderable)
    openspace.removeSceneGraphNode(shipPosition)
end)

asset.export(shipPosition)
asset.export(shipRenderable)
asset.export(shipTrail)

asset.meta = {{
    Name = "Ship Track Position: {cruise_id}",
    Description = [[This asset provides position information for the ship track for the cruise {cruise_id} ({vessel_shortname}): {cruise_name}.]],
    Author = "OpenSpace Team",
    URL = "http://doi.org/{cruise_doi}",
    License = "MIT license"
}}
"""
            # --- Save the content to a file ---
            file_path = os.path.join(output_directory, f"{cruise_id}.asset")
            with open(file_path, "w", encoding = "utf-8") as f:
                f.write(lua_content)
            print(f"Generated asset file: {file_path}")

        except KeyError as e:
            print(f"Skipping row due to missing column: {e}. Check DataFrame columns.")
            print(f"Row data: {row.to_dict()}")
