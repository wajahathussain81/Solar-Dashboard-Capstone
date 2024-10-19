import time
import requests
import pandas as pd
import os
import json
from datetime import datetime, timedelta
import concurrent.futures
from collections import defaultdict
from math import ceil
from calendar import monthrange


def import_config_json():
    configfile_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
    with open(configfile_path) as json_file:
        config_data = json.load(json_file)

    return config_data['api_endpoints'], config_data['api_key']


def round_time(log_time):
    rounded_minute = int(ceil(log_time.minute / 15.0)) * 15

    if rounded_minute >= 60:
        rounded_minute = 0  # Reset to 0 if it exceeds 59
        if log_time.hour == 23:
            # Increment day and reset hour to 0
            next_day = log_time.day + 1
            _, last_day_of_month = monthrange(log_time.year, log_time.month)
            if next_day > last_day_of_month:
                next_month = log_time.month + 1
                if next_month > 12:
                    next_month = 1
                    next_year = log_time.year + 1
                else:
                    next_year = log_time.year
                log_time = log_time.replace(year=next_year, month=next_month, day=1, hour=0)
            else:
                log_time = log_time.replace(day=next_day, hour=0)
        else:
            log_time = log_time.replace(hour=log_time.hour + 1)

    rounded_time = datetime(log_time.year, log_time.month, log_time.day, log_time.hour, rounded_minute).strftime('%Y-%m-%dT%H:%M:%SZ')
    return rounded_time


def calc_start_date(site, api_endpoint, api_key, temp_startdate):
    payload = {
        'from': temp_startdate.split('T')[0],
        'to': datetime.today().strftime('%Y-%m-%d'),
        'channel': 'EnergyOutput',
        'limit': 1
    }
    response = requests.get(api_endpoint['aggr_data'].replace('{site}', site), params=payload,
                            headers=api_key).json()
    return response['data'][0]['logDateTime']


def get_site_details(api_key, api_endpoints):
    response = requests.get(api_endpoints['site_details'], headers=api_key).json()
    site_details = dict()
    for site in response['pvSystems']:
        site_details[site['pvSystemId']] = dict()
        site_details[site['pvSystemId']]['site name'] = site['name']
        site_details[site['pvSystemId']]['Peak Power'] = site['peakPower']/1000
        site_details[site['pvSystemId']]['startdate'] = calc_start_date(
            site['pvSystemId'],
            api_endpoints,
            api_key,
            site['installationDate']
        )

        location_values = ('country', 'state', 'city', 'street', 'zipCode')
        site_details[site['pvSystemId']]['Location'] = {x: site['address'][x] for x in location_values}

        payload = {
            'limit': 1000,
            'type': 'inverter'
        }
        response = requests.get(api_endpoints["site_devices"].replace("{site}", site['pvSystemId']), headers=api_key, params=payload).json()
        site_details[site['pvSystemId']]["Devices"] = dict()
        for device in response['devices']:
            site_details[site['pvSystemId']]["Devices"][device['deviceId']] = dict()
            site_details[site['pvSystemId']]["Devices"][device['deviceId']]['Device Type'] = device['deviceType']
            site_details[site['pvSystemId']]["Devices"][device['deviceId']]['Device Name'] = device['deviceName']
            site_details[site['pvSystemId']]["Devices"][device['deviceId']]['activationdate'] = device['activationDate']
            if device['isActive'] is True:
                site_details[site['pvSystemId']]["Devices"][device['deviceId']]['Device Status'] = 'Active'
            else:
                site_details[site['pvSystemId']]["Devices"][device['deviceId']]['Device Status'] = 'Inactive'

    return site_details


def fetch_hist_data(site, api_key, api_endpoint, start_date):
    end_date = (datetime.utcnow() - timedelta(hours=6))
    delta = timedelta(days=1)
    interval_start_date = datetime.strptime(start_date, '%Y-%m-%d')
    interval_date = interval_start_date + delta
    compiled_data = []

    while interval_date < end_date:
        payload = {
            'from': interval_start_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'to': interval_date.strftime('%Y-%m-%dT%H:%M:%S'),
            'channel': 'EnergyProductionTotal',
            'limit': 1000,
            'timezone': 'local'
        }
        response = requests.get(api_endpoint['hist_data'].replace('{site}', site), params=payload, headers=api_key)

        # Check if API call is successful
        if response.status_code != 200:
            print(
                f"Failed to fetch data for {interval_start_date.strftime('%Y-%m-%d')}. Status Code: {response.status_code}")
            continue

        try:
            data = response.json()['data']
        except ValueError:
            print("Failed to decode JSON response")
            continue

        data_aggr = defaultdict(float)

        if not data:
            datetime_range = pd.date_range(interval_start_date, interval_date, freq='15min').strftime(
                '%Y-%m-%dT%H:%M:%SZ')
            for date_time in datetime_range:
                data_aggr[date_time] = 0
        else:
            for entry in data:
                log_time = datetime.strptime(entry['logDateTime'], '%Y-%m-%dT%H:%M:%S%z')
                rounded_time = round_time(log_time)
                data_aggr[rounded_time] += entry['channels'][0]['value']

        for date, data in data_aggr.items():
            compiled_data.append({'date': date, 'value': data})

        interval_start_date = interval_date
        interval_date += delta
        diff_end_interval = end_date - interval_start_date
        if diff_end_interval.days < 1 and diff_end_interval.seconds > 3600:
            interval_date = end_date.replace(minute=0, second=0)

    return site, compiled_data


def get_aggr_15min_data(api_key, api_endpoints, site_details, fetch_everything):
    hist_data = dict()
    site_hist_data = dict()
    two_months_ago = (datetime.utcnow() - timedelta(days=60, hours=6)).strftime('%Y-%m-%d')
    start_date_update = (datetime.utcnow() - timedelta(days=2, hours=6)).strftime('%Y-%m-%d')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for site, site_detail in site_details.items():
            if fetch_everything:
                futures.append(executor.submit(fetch_hist_data, site, api_key, api_endpoints, two_months_ago))
            else:
                futures.append(executor.submit(fetch_hist_data, site, api_key, api_endpoints, start_date_update))

        for future in concurrent.futures.as_completed(futures):
            site, data = future.result()
            hist_data[site] = data
            site_df = (
                pd.DataFrame(hist_data[site])
                .dropna()
                .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
            )
            site_df['Date'] = pd.to_datetime(site_df['Date']).dt.strftime("%Y-%m-%d %H:%M:%S")
            site_df.set_index('Date', inplace=True)
            site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
            site_df.drop(columns=['Production (Wh)'], inplace=True)
            site_hist_data[site_details[site]['site name']] = site_df
    return site_hist_data


def fetch_aggr_data(site, api_key, api_endpoint, start_date):
    start_date = start_date.split('T')[0]
    end_date = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
    compiled_data = []
    while True:
        payload = {
            'from': start_date,
            'to': end_date,
            'channel': 'EnergyOutput',
            'limit': 1000
        }
        response = requests.get(api_endpoint['aggr_data'].replace('{site}', site), params=payload,
                                headers=api_key).json()

        if response['links']['totalItemsCount'] == 0:
            date_range = pd.date_range(start_date, end_date, freq='D')
            for date_day in date_range:
                data_org = {'date': date_day.strftime('%Y-%m-%d'), 'value': 0}
                compiled_data.append(data_org)
            break

        for data in response['data']:
            data_org = {'date': data['logDateTime'], 'value': data['channels'][0]['value']}
            compiled_data.append(data_org)

        # print(compiled_data)

        if compiled_data[-1]['date'] == end_date:
            break
        else:
            start_date = (datetime.strptime(compiled_data[-1]['date'], '%Y-%m-%d') + timedelta(days=1)).strftime('%Y-%m-%d')

    return site, compiled_data


def get_aggr_daily_data(api_key, api_endpoints, site_details, fetch_everything):
    aggr_data = dict()
    site_daily_data = dict()
    start_date_update = (datetime.utcnow() - timedelta(days=2, hours=6)).strftime('%Y-%m-%d')

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []

        for site, site_detail in site_details.items():
            if fetch_everything:
                futures.append(executor.submit(fetch_aggr_data, site, api_key, api_endpoints, site_detail['startdate']))
            else:
                futures.append(executor.submit(fetch_aggr_data, site, api_key, api_endpoints, start_date_update))

        for future in concurrent.futures.as_completed(futures):
            site, data = future.result()
            aggr_data[site] = data
            site_df = (
                pd.DataFrame(aggr_data[site])
                .dropna()
                .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
                .set_index('Date')
            )
            site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
            site_df.drop(columns=['Production (Wh)'], inplace=True)
            site_daily_data[site_details[site]['site name']] = site_df
    return site_daily_data


def fronius_daily_data(fetch_everything=True):
    api_endpoint, api_key = import_config_json()
    site_details = get_site_details(api_key, api_endpoint)
    aggr_data = get_aggr_daily_data(api_key, api_endpoint, site_details, fetch_everything)
    return aggr_data


def fronius_15min_data(fetch_everything=True):
    api_endpoint, api_key = import_config_json()
    site_details = get_site_details(api_key, api_endpoint)
    hist_data = get_aggr_15min_data(api_key, api_endpoint, site_details, fetch_everything)
    return hist_data


if __name__ == '__main__':
    start = time.perf_counter()
    prod_data = fronius_15min_data(fetch_everything=False)
    print(f'{time.perf_counter() - start:.4f}')
    print(prod_data['Haskayne Legacy Park'].to_dict())
    final_data = 0
    prod_data_dict = prod_data['Haskayne Legacy Park'].to_dict()
    print()
    for date, data in prod_data_dict['Production (kWh)'].items():
        if '2024-03-26' in date:
            final_data += data
    print(final_data)