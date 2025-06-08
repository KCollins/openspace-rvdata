import pandas as pd
import requests # This library is essential for making HTTP requests
from datetime import datetime as dt # Still useful if you need to manually construct datetimes

def get_r2r_url(cruise_id=None, doi=None, vessel_name=None):
    """
    Generates a URL for the rvdata.us R2R (Rolling Deck to Repository) API.
    This function does not encompass all the options offered by the API, but
    allows for lookup by cruise_id, DOI, or vessel name.

    Args:
        cruise_id (str, optional): The unique identifier for a cruise (e.g., "RR2402").
                                   If provided, it will construct a URL for that specific cruise.
        doi (str, optional): A Digital Object Identifier (DOI) associated with cruise data
                             (e.g., "10.7284/910464"). The function will extract the numerical
                             suffix for the URL.
        vessel_name (str, optional): The name of a vessel (e.g., "Revelle").

    Returns:
        str: The constructed R2R API URL.

    Raises:
        ValueError: If no arguments are given or an invalid combination of arguments is provided.
    """
    base_url = "https://service.rvdata.us/api/cruise/"

    if cruise_id:
        if doi or vessel_name:
            raise ValueError("Cannot specify 'cruise_id' with 'doi' or 'vessel_name'.")
        return f"{base_url}cruise_id/{cruise_id}"
    elif vessel_name:
        if doi:
            raise ValueError("Cannot specify 'vessel_name' with 'doi'.")
        return f"{base_url}vessel/{vessel_name}"
    elif doi:
        # Extract the numerical part of the DOI.
        # Assumes DOI format like "10.xxxx/YYYYY" where YYYYY is the part needed.
        try:
            doi_parts = doi.split('/')
            if len(doi_parts) < 2:
                raise ValueError("Invalid DOI format. Expected '10.xxxx/YYYYY'.")
            doi_suffix = doi_parts[-1]
            return f"{base_url}doi/{doi_suffix}"
        except Exception as e:
            raise ValueError(f"Error processing DOI '{doi}': {e}")
    else:
        raise ValueError("At least one argument (cruise_id, doi, or vessel_name) must be provided.")

def get_cruise_data(url):
    """
    Fetches cruise data from the rvdata.us API and parses it into a pandas DataFrame.

    Args:
        url (str): The URL for the cruise(s) of interest; e.g.,
        "https://service.rvdata.us/api/cruise/cruise_id/RR2402"
        "https://service.rvdata.us/api/cruise/doi/910464"
        "https://service.rvdata.us/api/cruise/vessel/Revelle"

    Returns:
        pandas.DataFrame: A DataFrame containing the cruise data, or an empty
                          DataFrame if data fetching fails or is empty.
    """

    try:
        response = requests.get(url)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json() # Parse the JSON response into a Python dictionary

        # Check if the status is OK and data exists
        if data.get("status") == 200 and data.get("data"):
            # The actual records are in the 'data' key, which is a list of dictionaries
            df = pd.json_normalize(data['data'])

            # --- Post-processing (as in the previous example) ---
            # Parse the 'keyword' column into a list
            if 'keyword' in df.columns:
                df['keyword_list'] = df['keyword'].apply(
                    lambda x: [item.strip() for item in x.split(',') if item.strip()] if pd.notna(x) else []
                )
                df = df.drop(columns=['keyword'])

            # Convert date columns to datetime objects
            date_columns = ['depart_date', 'arrive_date', 'release_date', 'release_date_sent', 'release_sent']
            for col in date_columns:
                if col in df.columns:
                    df[col] = pd.to_datetime(df[col], errors='coerce') # 'coerce' will turn unparseable dates into NaT

            # Convert specific numeric columns (like lat/lon min/max) that might be strings
            numeric_cols = ['longitude_min', 'longitude_max', 'latitude_min', 'latitude_max']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            return df
        else:
            print(f"API returned status: {data.get('status')}, message: {data.get('status_message', 'No message')}")
            return pd.DataFrame() # Return an empty DataFrame if no valid data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
        return pd.DataFrame()
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occurred: {e}")
        return pd.DataFrame()
    except requests.exceptions.Timeout as e:
        print(f"Timeout error occurred: {e}")
        return pd.DataFrame()
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred: {e}")
        return pd.DataFrame()
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return pd.DataFrame()