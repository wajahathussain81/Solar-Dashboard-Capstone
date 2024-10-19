import time

import numpy as np
import requests
import pandas as pd
import pathlib
import json
from API.Enphase.api_setup import Generate_New_Access_Token_From_Refresh_Token, get_params
from Database.Site_Details_DB.setup_update_read import read_site_db
from API.Fronius.solar_data import import_config_json as import_config_json_fr, get_site_details as get_site_details_fr
from API.SolarEdge.solar_data import import_config_json as import_config_json_sol, \
    get_site_details as get_site_details_sol


def list_all_sites():
    params, json_path, json_file = get_params()

    # Extract required parameters
    oauth_access_token = params.get('access_token')
    api_key = params.get('api_key')
    endpoint = params.get('api_endpoint')

    headers = {
        'Authorization': f'Bearer {oauth_access_token}',
        'key': api_key,
        'Accept': 'application/json',
    }

    parameters = {
        'page': 1,
        'size': 100,
        'sort_by': 'id',
    }
    response = requests.get(endpoint, headers=headers, params=parameters)

    params['API_Count'] += 1

    if response.status_code == 200:
        systems_data = response.json()
        systems_df = pd.DataFrame(systems_data['systems'])
        params['Operational'] = True
        params['Consecutive_Failures'] = 0
    else:
        print(f"Error Fetching all systems: {response.status_code} - {response.text}")
        if response.status_code != 401 and response.status_code != 429:  # 401: not authorized, 429: too many requests
            params['Operational'] = False
        params['Consecutive_Failures'] = params['Consecutive_Failures'] + 1
        systems_df = None

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)

    return systems_df


def recursive_list_all_sites():
    a = list_all_sites()
    if a is not None:
        return a
    else:
        print('An error occurred. Waiting for 90s, regenerating access and refresh tokens and trying again')
        time.sleep(90)  # Sleep for 90 seconds
        Generate_New_Access_Token_From_Refresh_Token()
        return recursive_list_all_sites()


def production_for_site(engine=None):
    params, json_path, json_file = get_params()

    # Extract required parameters
    oauth_access_token = params.get('access_token')
    api_key = params.get('api_key')
    api_endpoint = params.get('api_endpoint')

    if engine is None:
        all_enphase_systems = recursive_list_all_sites()
        print('Using API to get site data')
    else:
        all_enphase_systems = read_site_db(engine)
        all_enphase_systems = all_enphase_systems['Enphase']
        print('Using database to get site data')

    system_id_list = all_enphase_systems['system_id'].tolist()

    system_prod_data = {}
    for system_id in system_id_list:
        data_endpoint = api_endpoint + f'/{system_id}/energy_lifetime'

        # Set up headers with OAuth 2.0 access token and API key
        headers = {
            'Authorization': f'Bearer {oauth_access_token}',
            'key': api_key,
            'Accept': 'application/json',
        }

        # Make the GET request
        response = requests.get(data_endpoint, headers=headers)
        params['API_Count'] += 1

        if response.status_code == 200:
            params['Operational'] = True
            params['Consecutive_Failures'] = 0
            production_meter_readings_data = response.json()

            start_date = production_meter_readings_data['start_date']
            daily_production_data = production_meter_readings_data['production']
            daily_production_data = np.array(daily_production_data) / 1000  # converting from Wh to kWh

            date_rng = pd.date_range(start=start_date, periods=len(daily_production_data), freq='D')

            df = pd.DataFrame({'Date': date_rng, 'Production (kWh)': daily_production_data})

            if df is not None and system_prod_data is not None:
                system_prod_data[system_id] = df.set_index('Date')

        else:
            print(f"Error: {response.status_code} - {response.text}")
            if response.status_code != 401 and response.status_code != 429:  # 401: not authorized, 429: too many requests
                params['Operational'] = False
            params['Consecutive_Failures'] = params['Consecutive_Failures'] + 1
            system_prod_data = None

    system_prod_data_site_names = {}
    if system_prod_data is not None:
        id_name_map = all_enphase_systems.filter(items=['system_id', 'name']).set_index('name').to_dict()[
            'system_id']

        for name in id_name_map.keys():
            system_prod_data_site_names[name] = system_prod_data.pop(id_name_map[name])

        system_prod_data = system_prod_data_site_names

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)

    return system_prod_data


def recursive_production_for_site(engine=None):
    a = production_for_site(engine=engine)
    if a is not None:
        return a
    else:
        print('Waiting for 90s, regenerating access and refresh tokens and trying again')
        time.sleep(90)  # Sleep for 90 seconds
        Generate_New_Access_Token_From_Refresh_Token()
        return recursive_production_for_site(engine=engine)


def production_for_site_15_min():
    """This function will not be used, no point in going further"""
    # Load parameters from JSON file
    params, json_path, json_file = get_params()

    oauth_access_token = params.get('access_token')
    api_key = params.get('api_key')
    api_endpoint = params.get('api_endpoint')

    # Retrieve list of all Enphase systems
    all_enphase_systems = list_all_sites()
    system_id_list = all_enphase_systems['system_id'].tolist()

    system_prod_data = {}
    for system_id in system_id_list:
        # Endpoint for 15-minute production data
        data_endpoint = f"{api_endpoint}/{system_id}/telemetry/production_meter?granularity=15mins"

        # Set up headers with OAuth 2.0 access token and API key
        headers = {
            'Authorization': f'Bearer {oauth_access_token}',
            'key': api_key,
            'Accept': 'application/json',
        }

        # Make the GET request
        response = requests.get(data_endpoint, headers=headers)
        params['API_Count'] += 1

        if response.status_code == 200:
            params['Operational'] = True
            params['Consecutive_Failures'] = 0
            production_data = response.json()

            # Extract production data
            timestamps = [entry['at'] for entry in production_data['production']]
            production_values = [entry['production'] for entry in production_data['production']]

            # Construct DataFrame for 15-minute production data
            df = pd.DataFrame({'Timestamp': timestamps, 'Production (Wh)': production_values})
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], unit='s')  # Convert Unix timestamp to datetime
            df.set_index('Timestamp', inplace=True)

            system_prod_data[system_id] = df

        else:
            if response.status_code != 401 and response.status_code != 429:  # 401: not authorized, 429: too many requests
                params['Operational'] = False
            params['Consecutive_Failures'] = params['Consecutive_Failures'] + 1
            system_prod_data = None

    if system_prod_data is not None:
        id_name_map = all_enphase_systems.filter(items=['system_id', 'name']).set_index('name').to_dict()[
            'system_id']

        for name in id_name_map.keys():
            system_prod_data[name] = system_prod_data.pop(id_name_map[name])

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)

    return system_prod_data


def recursive_15m_production_for_site():
    """This function will not be used, no point in going further"""
    aa = production_for_site_15_min()
    if aa is not None:
        return aa
    else:
        time.sleep(90)  # Sleep for 90 seconds
        print('Waiting for 90s, regenerating access and refresh tokens and trying again')
        Generate_New_Access_Token_From_Refresh_Token()
        return recursive_15m_production_for_site()


def SiteSize_Enphase(sites_engine=None, all_enphase_systems=None):
    if all_enphase_systems is None:
        if sites_engine is None:
            all_enphase_systems = recursive_list_all_sites()
            time.sleep(90)  # wait to not overload the Enphase API
            print('Using API to get site data')
        else:
            all_enphase_systems = read_site_db(sites_engine)
            all_enphase_systems = all_enphase_systems['Enphase']
            print('Using database to get site data')
    else:
        print('Using function parameter to get site data')

    params, json_path, json_file = get_params()

    # Extract required parameters
    oauth_access_token = params.get('access_token')
    api_key = params.get('api_key')
    endpoint = params.get('api_endpoint')

    headers = {
        'Authorization': f'Bearer {oauth_access_token}',
        'key': api_key,
        'Accept': 'application/json',
    }

    parameters = {
        'page': 1,
        'size': 100,
        'sort_by': 'id',
    }

    systems_df = []  # the naming is intentional even though it is an array
    for system_id in all_enphase_systems['system_id']:
        endpoint_site = endpoint + f"/{system_id}/summary"
        response = requests.get(endpoint_site, headers=headers, params=parameters)
        params['API_Count'] += 1
        if response.status_code == 200:
            systems_data = response.json()
            systems_data = pd.DataFrame(systems_data, index=[system_id])
            systems_df.append(systems_data)
            params['Operational'] = True
            params['Consecutive_Failures'] = 0
        else:
            print(f"Error Fetching all systems: {response.status_code} - {response.text}")
            if response.status_code != 401 and response.status_code != 429:  # 401: not authorized, 429: too many requests
                params['Operational'] = False
            params['Consecutive_Failures'] = params['Consecutive_Failures'] + 1
            systems_df = None

    if systems_df is not None:
        systems_df = pd.concat(systems_df)

    with open(json_path, 'w') as json_file:
        json.dump(params, json_file, indent=4)

    return systems_df


def recursive_SiteSize_Enphase(all_enphase_systems=None):
    aa = SiteSize_Enphase(all_enphase_systems=all_enphase_systems)
    if aa is not None:
        return aa
    else:
        time.sleep(90)  # Sleep for 90 seconds
        print('Waiting for 90s, regenerating access and refresh tokens and trying again')
        Generate_New_Access_Token_From_Refresh_Token()
        return recursive_SiteSize_Enphase(all_enphase_systems=all_enphase_systems)


def update_or_initialize_site_db_setup(engine):
    print("Creating or Updating Database...")

    print('Enphase Site Details')
    json_file = f'enphase_status_mapping.json'
    json_path = pathlib.Path(__file__).parents[0] / pathlib.Path(json_file)
    with open(json_path, 'r') as json_file:
        enphase_status_mapping = json.load(json_file)
    sites_data = recursive_list_all_sites()
    sites_data.drop(columns=['address', 'other_references', 'energy_lifetime', 'energy_today', 'system_size'],
                    inplace=True)
    Site_Size = recursive_SiteSize_Enphase(all_enphase_systems=sites_data)
    sites_data = sites_data.join(Site_Size['size_w'], on='system_id')
    sites_data['status'] = sites_data['status'].map(enphase_status_mapping)
    sites_data.set_index('system_id', inplace=True)
    sites_data.to_sql('Enphase_SD', engine, if_exists='replace')

    print('Solaredge Site Details')
    api_endpoint, api_key = import_config_json_sol()
    site_ids, site_details = get_site_details_sol(api_key, api_endpoint, export_siteids=True)
    site_df = pd.DataFrame(site_details).T.set_index('site name', drop=True)
    address_df = site_df['Location'].apply(pd.Series)
    site_df.drop(columns=['Location'], inplace=True)
    site_df.join(address_df)
    site_df.to_sql('Solaredge_SD', engine, if_exists='replace')

    print('Fronius Site Details')
    api_endpoint, api_key = import_config_json_fr()
    site_details = get_site_details_fr(api_key, api_endpoint)
    site_df = pd.DataFrame(site_details).T.set_index('site name', drop=True)
    address_df = site_df['Location'].apply(pd.Series)
    site_df.drop(columns=['Location', 'Devices'], inplace=True)
    site_df.join(address_df)
    site_df.to_sql('Fronius_SD', engine, if_exists='replace')

    print("Site Details Database setup complete.")
    print()

    return


if __name__ == "__main__":
    # a = list_all_sites()
    # print(a)
    # a = recursive_list_all_sites()
    # print(a)
    a = recursive_production_for_site()
    print(a)
