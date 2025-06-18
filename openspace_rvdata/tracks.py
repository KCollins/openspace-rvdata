import os
import pandas as pd
from datetime import datetime as dt
import openspace_rvdata.geocsv2geojson as g2g

# Function to format each row into the desired text block
def format_row_to_text(row):
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
    df = pd.read_csv(fname, comment = '#')
    df['datetime'] = pd.to_datetime(df['iso_time'])
    df.index = df['datetime']
    df = df.resample(resample_rate).first()
    df = df.reset_index(drop=True)
    print(df.head(3))
    # Define the "before" and "after" text

    # Let's start by getting metadata:
    mdf = g2g.get_comment_dataframe(fname)
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
    with open(output_filename, "w") as f:
        f.write(before_text) # Write the "before" text first
    
        # Iterate through each row of the DataFrame, format it, and write to the file
        for index, row in df.iterrows():
            if index<len(df):
                f.write(format_row_to_text(row) + ",\n") # Add a newline after each entry for readability
            else:
                f.write(format_row_to_text(row) + "\n") #skip comma on last entry
        f.write(after_text) # Write the "after" text
    
    print(f"Successfully generated '{output_filename}' with the formatted data.")

def get_cruise_asset(mdf: pd.DataFrame):
    """
    Generates and saves a Lua asset file for each cruise in the DataFrame.

    Each cruise Lua file is named 'tmp/{cruise_id}.asset' and contains dynamic
    information from the cruise's row in the DataFrame, including the
    definition of the shared ship model asset.

    Args:
        mdf (pd.DataFrame): The input DataFrame containing cruise metadata.
                            Expected columns (after stripping whitespace):
                            'cruise_id', 'cruise_name', 'cruise_doi',
                            'depart_date', 'arrival_date', 'vessel_shortname'.
                            'depart_date' and 'arrival_date' should be in 'YYYY-MM-DD' format.
    """

    # Ensure the 'tmp' directory exists
    output_directory = "tmp"
    os.makedirs(output_directory, exist_ok=True)
    print(f"Ensuring output directory '{output_directory}' exists.")

    # Clean up column names by stripping whitespace
    mdf.columns = mdf.columns.str.strip()

    # --- Iterate through each row (cruise) in the DataFrame to generate cruise assets ---
    for index, row in mdf.iterrows():
        try:
            cruise_id = row['cruise_id']
            cruise_name = row['cruise_name'] # Still useful for meta description
            cruise_doi = row['cruise_doi']
            vessel_shortname = row['vessel_shortname'] # Get the vessel name for this cruise
            
            # Safe identifier for referencing the ship model asset
            # This is used for the Identifier in the inlined shipModel asset.
            safe_vessel_id = vessel_shortname.replace(" ", "_").replace("/", "_").replace("\\", "_").replace(".", "_").replace("-", "_")
            
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
        Path = "/Ship Tracks" -- A new path for your custom asset
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
        Path = "/Ship Tracks"
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
        Path = "/Ship Tracks",
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
            with open(file_path, "w") as f:
                f.write(lua_content)
            print(f"Generated asset file: {file_path}")

        except KeyError as e:
            print(f"Skipping row due to missing column: {e}. Check DataFrame columns.")
            print(f"Row data: {row.to_dict()}")
        except Exception as e:
            print(f"An unexpected error occurred for cruise '{row.get('cruise_id', 'N/A')}': {e}")