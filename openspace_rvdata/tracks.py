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
    os.makedirs("keyframes", exist_ok=True)
    output_filename = "keyframes/" + cruise_id+"_keyframes.asset"
    
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