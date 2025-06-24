"""This module provides functions to pull data from the R2R repository."""

import os
import tarfile
import re # For regular expressions to find the correct geoCSV file
import json # Added for parsing nested JSON strings
import pandas as pd
import requests # This library is essential for making HTTP requests

def get_r2r_url(cruise_id=None, doi=None, vessel_name=None):
    """
    Generates a URL for the rvdata.us R2R (Rolling Deck to Repository) API.

    This function does not encompass all the options offered by the API, but
    allows for lookup by cruise_id, DOI, or vessel name.

    Parameters
    ----------
    cruise_id : str, optional
        The unique identifier for a cruise (e.g., "RR2402").
        If provided, it will construct a URL for that specific cruise.
    doi : str, optional
        A Digital Object Identifier (DOI) associated with cruise data
        (e.g., "10.7284/910464"). The function will extract the numerical
        suffix for the URL.
    vessel_name : str, optional
        The name of a vessel (e.g., "Revelle").

    Returns
    -------
    str
        The constructed R2R API URL.

    Raises
    ------
    ValueError
        If no arguments are given or an invalid combination of arguments is provided.

    Examples
    --------
    >>> import openspace_rvdata as r2r
    >>> url = r2r.get_r2r_url("RR2402")
    >>> print(url)
    https://www.rvdata.us/api/cruise/RR2402
    """
    base_url = "https://service.rvdata.us/api/cruise/"

    if cruise_id:
        if doi or vessel_name:
            raise ValueError("Cannot specify 'cruise_id' with 'doi' or 'vessel_name'.")
        return f"{base_url}cruise_id/{cruise_id}"
    if vessel_name:
        if doi:
            raise ValueError("Cannot specify 'vessel_name' with 'doi'.")
        return f"{base_url}vessel/{vessel_name}"
    if doi:
        # Extract the numerical part of the DOI.
        # Assumes DOI format like "10.xxxx/YYYYY" where YYYYY is the part needed.
        try:
            doi_parts = doi.split('/')
            if len(doi_parts) < 2:
                raise ValueError("Invalid DOI format. Expected '10.xxxx/YYYYY'.")
            doi_suffix = doi_parts[-1]
            return f"{base_url}doi/{doi_suffix}"
        except ValueError as e:
            raise ValueError(f"Error processing DOI '{doi}': {e}") from e

    raise ValueError("At least one argument (cruise_id, doi, or vessel_name) must be provided.")

def get_cruise_metadata(url):
    """
    Fetches cruise data from the rvdata.us API and parses it into a pandas DataFrame.

    Parameters
    ----------
    url : str
        The URL for the cruise(s) of interest; e.g.,
        "https://service.rvdata.us/api/cruise/cruise_id/RR2402"
        "https://service.rvdata.us/api/cruise/doi/910464"
        "https://service.rvdata.us/api/cruise/vessel/Revelle"

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the cruise data, or an empty
        DataFrame if data fetching fails or is empty.

    Examples
    --------
    >>> import openspace_rvdata as r2r
    >>> # Assuming you've generated a URL using get_r2r_url
    >>> url = r2r.get_r2r_url(cruise_id="RR2402")
    >>> mdf = r2r.get_cruise_metadata(url)
    >>> print(mdf.head()) # Or some other way to show expected output
    """
    try:
        response = requests.get(url, timeout = 60)
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
        # else:
        print(f"API returned status: {data.get('status')}, message: {data.get('status_message', 'No message')}")
        return pd.DataFrame() # Return an empty DataFrame if no valid data
    except requests.exceptions.HTTPError as e:
        print(f"HTTP error occurred: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error occurred: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Timeout error occurred: {e}")
    except requests.exceptions.RequestException as e:
        print(f"An unexpected request error occurred: {e}")
    except json.JSONDecodeError as e:
        print(f"Failed to decode JSON response: {e}")
    return pd.DataFrame()

def get_cruise_nav(cruise_id: str, sampling_rate: str = "60min") -> pd.DataFrame:
    """
    Fetches navigation data for a given cruise from the R2R repository (rvdata.org),
    processes it, and returns a resampled pandas DataFrame.

    Handles both .tar.gz archives and direct access to .geoCSV files within a
    /data subdirectory.

    Parameters
    ----------
    cruise_id : str
        The ID of the cruise (e.g., "RR2402").
    sampling_rate : str, default "60min"
        The desired sampling rate for the output DataFrame
        (e.g., "1min", "60min", "1H"). This string should be compatible
        with pandas' resample method.

    Returns
    -------
    pandas.DataFrame
        A DataFrame containing the navigation data, resampled
        to the specified rate. The DataFrame will have a DatetimeIndex.

    Raises
    ------
    requests.exceptions.RequestException
        If there's a problem with the network request.
    FileNotFoundError
        If the expected .geocsv file is not found after extraction/download.
    ValueError
        If the 'Navigation' product type is not found or if a suitable
        time column for resampling cannot be identified.

    Examples
    --------
    >>> import openspace_rvdata as r2r
    >>> gdf = r2r.get_cruise_nav(cruise_id="RR2402", sampling_rate="1min")
    >>> gdf.head()
"""
    # --- 1. Generate the initial URL ---
    base_api_url = "https://service.rvdata.us/api/fileset/cruise_id/"
    api_url = f"{base_api_url}{cruise_id}"
    print(f"Fetching metadata from: {api_url}")

    try:
        response = requests.get(api_url, timeout = 60)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        metadata = response.json()
        print(f"Successfully fetched metadata. Top-level keys: {metadata.keys()}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching metadata from {api_url}: {e}")
        raise

    # --- 2. Filter to product type "Navigation" and find "product_actual_url" ---
    navigation_entry_product_info = None
    all_product_types_found = set() # For debugging: collect all product_type_name values

    fileset_items = metadata.get('data', [])
    print(f"Found {len(fileset_items)} items in 'data'.")

    for i, item in enumerate(fileset_items):
        print(f"Processing item {i+1} from 'data' list...")
        product_info_str = item.get('product_info')
        if product_info_str and isinstance(product_info_str, str):
            try:
                product_details = json.loads(product_info_str)
                print(f"  Item {i+1} has 'product_info'. Parsed {len(product_details)} product details.")
                for detail in product_details:
                    product_type_name = detail.get('product_type_name')
                    if product_type_name:
                        all_product_types_found.add(product_type_name)
                        print(f"    Found product_type_name: '{product_type_name}'")
                    if product_type_name == 'Navigation':
                        navigation_entry_product_info = detail
                        print(f"  ---> Found 'Navigation' product type within item {i+1}!")
                        break
                if navigation_entry_product_info:
                    break
            except json.JSONDecodeError as e:
                print(f"Warning: Couldn't decode JSON from product_info. fileset_id: {item.get('fileset_id')}. {e}")
                continue
        else:
            print(f"  Item {i+1} lacks valid 'product_info' string (found: {product_info_str}).")


    if not navigation_entry_product_info:
        print(f"DEBUG: No 'Navigation' product type found within 'product_info' in API response for cruise {cruise_id}")
        if all_product_types_found:
            print(f"DEBUG: All product types found were: {sorted(list(all_product_types_found))}")
        else:
            print("DEBUG: No 'product_info' fields found or all failed to parse for any product_type_name.")
        raise ValueError(f"No 'Navigation' product type found within 'product_info' for cruise_id: {cruise_id}")

    product_actual_url = navigation_entry_product_info.get('product_actual_url')
    if not product_actual_url:
        raise ValueError(f"'product_actual_url' not found in Navigation product_info entry for cruise_id: {cruise_id}")

    print(f"Processing data from: {product_actual_url}")

    # --- 3. Set up temporary directory ---
    tmp_dir = os.path.join(os.getcwd(), "tmp")
    os.makedirs(tmp_dir, exist_ok=True) # Create /tmp subdirectory if it doesn't exist
    all_extracted_geocsv_files = [] # List to store paths of all extracted geoCSV files
    expected_geocsv_pattern = re.compile(r"\.geoCSV$", re.IGNORECASE)

    # --- 4. Handle download based on product_actual_url extension ---
    if product_actual_url.lower().endswith('.tar.gz'):
        print("Detected .tar.gz archive. Downloading and extracting...")
        archive_filename = os.path.join(tmp_dir, f"{cruise_id}_nav_data.tar.gz")

        try:
            archive_response = requests.get(product_actual_url, stream=True, timeout = 60)
            archive_response.raise_for_status()

            with open(archive_filename, 'wb') as f:
                for chunk in archive_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"Downloaded archive to: {archive_filename}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading archive from {product_actual_url}: {e}")
            raise

        # --- 5. Unzip the folder and bring .geoCSV files to /tmp ---
        try:
            with tarfile.open(archive_filename, "r:gz") as tar:
                members_to_extract = []
                for member in tar.getmembers():
                    if member.isfile() and expected_geocsv_pattern.search(member.name):
                        members_to_extract.append(member)

                if not members_to_extract:
                    raise FileNotFoundError("No .geoCSV file found in the archive.")

                print(f"Found {len(members_to_extract)} .geoCSV files in the archive. Extracting all to /tmp...")
                for member in members_to_extract:
                    target_path_in_tmp = os.path.join(tmp_dir, os.path.basename(member.name))
                    with open(target_path_in_tmp, 'wb') as outfile:
                        outfile.write(tar.extractfile(member).read())
                    all_extracted_geocsv_files.append(target_path_in_tmp)
                    print(f"  Extracted: {os.path.basename(member.name)}")

        except tarfile.ReadError as e:
            print(f"Error reading tar.gz file {archive_filename}: {e}")
            raise
        except FileNotFoundError:
            print("File not found.")
            raise
        finally:
            if os.path.exists(archive_filename):
                os.remove(archive_filename)
                print(f"Removed temporary archive: {archive_filename}")

    else:
        # If product_actual_url does not end in .tar.gz, check /data subdirectory
        print("URL does not end with .tar.gz. Attempting to check for /data subdirectory for .geoCSV files...")
        data_subdirectory_url = f"{product_actual_url}/data/"
        print(f"Checking for .geoCSV files in: {data_subdirectory_url}")

        # Common naming conventions for geoCSV files in such structures
        possible_geocsv_filenames = [
            f"{cruise_id}_1min.geoCSV",
            f"{cruise_id}.geoCSV", # General cruise ID file
            "navigation.geoCSV",
            "data.geoCSV",
            "metadata.geoCSV" # Sometimes generic names are used
        ]

        downloaded_any_geocsv = False
        for filename in possible_geocsv_filenames:
            file_url = f"{data_subdirectory_url}{filename}"
            print(f"Attempting to download: {file_url}")
            try:
                # Use stream=True for potentially large files, but for small geoCSV, it's fine.
                file_response = requests.get(file_url, stream=True, timeout = 60)
                file_response.raise_for_status() # Raise an exception for bad status codes

                target_path_in_tmp = os.path.join(tmp_dir, filename)
                with open(target_path_in_tmp, 'wb') as f:
                    for chunk in file_response.iter_content(chunk_size=8192):
                        f.write(chunk)
                all_extracted_geocsv_files.append(target_path_in_tmp)
                print(f"Successfully downloaded .geoCSV file: {filename}")
                downloaded_any_geocsv = True
            except requests.exceptions.RequestException as e:
                print(f"Could not download {filename} from {file_url}: {e}. Trying next possible file.")
                continue # Try the next filename

        if not downloaded_any_geocsv:
            raise FileNotFoundError(f"No .geoCSV file found in the /data subdirectory at {data_subdirectory_url} "
                                    f"using common naming conventions for cruise_id: {cruise_id}.")

    # --- 6. Read in the contents of the *selected* .geoCSV file as a pandas DataFrame ---
    selected_geocsv_to_read = None
    # Prioritize the "1min" file among the extracted/downloaded ones, if it exists
    for filepath in all_extracted_geocsv_files:
        if f"{cruise_id}_1min.geoCSV".lower() in os.path.basename(filepath).lower():
            selected_geocsv_to_read = filepath
            break
    # Fallback to the first found if "1min" not explicit, or if only one exists
    if not selected_geocsv_to_read and all_extracted_geocsv_files:
        selected_geocsv_to_read = all_extracted_geocsv_files[0]

    if not selected_geocsv_to_read or not os.path.exists(selected_geocsv_to_read):
        raise FileNotFoundError(f"No suitable .geoCSV file found or extracted/downloaded for cruise_id: {cruise_id}.")

    print(f"Reading data from selected .geoCSV file: {os.path.basename(selected_geocsv_to_read)}")
    try:
        df = pd.read_csv(selected_geocsv_to_read, comment='#')

        time_col = None
        possible_time_cols = ['ISO_8601_UTC', 'Time_UTC', 'datetime', 'Timestamp', 'time']
        for col in possible_time_cols:
            if col in df.columns:
                time_col = col
                break

        if time_col is None:
            # Fallback: Check if the first column can be parsed as datetime
            try:
                df['__temp_time_col'] = pd.to_datetime(df.iloc[:, 0], errors='coerce')
                if not df['__temp_time_col'].isnull().all():
                    time_col = df.columns[0]
                    df.rename(columns={time_col: 'time'}, inplace=True)
                    time_col = 'time'
                else:
                    df.drop(columns='__temp_time_col', inplace=True)
            except Exception: # pylint:disable=W0718
                pass # Ignore if first column isn't time-like

        if time_col is None:
            raise ValueError("Could not find a suitable time column for resampling in the .geoCSV file. "
                             "Please ensure a column like 'ISO_8601_UTC' or similar exists.")

        df[time_col] = pd.to_datetime(df[time_col])
        df.set_index(time_col, inplace=True)

    except pd.errors.EmptyDataError:
        print(f"The .geoCSV file at {selected_geocsv_to_read} is empty or only contains comments.")
        raise
    except Exception as e:
        print(f"Error reading or processing .geoCSV file {selected_geocsv_to_read}: {e}")
        raise
    # finally:
    #     # Clean up all temporary geoCSV files regardless of success or failure
    #     for fpath in all_extracted_geocsv_files:
    #         if os.path.exists(fpath):
    #             os.remove(fpath)
    #             print(f"Removed temporary .geoCSV file: {os.path.basename(fpath)}")


    # --- 7. Resample the DataFrame ---
    print(f"Resampling data to: {sampling_rate}")
    df_resampled = df.resample(sampling_rate).mean()

    return df_resampled
