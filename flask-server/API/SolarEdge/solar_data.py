import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import os
import concurrent.futures
import time


def import_config_json():
    configfile_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "config.json")
    with open(configfile_path) as json_file:
        config_data = json.load(json_file)

    return config_data['api_endpoints'], config_data['api_key']


def get_monthly_daterange(start_date):
    startdate_year = start_date.year
    startdate_month = start_date.month

    date_range = {'startdates': [], 'enddates': []}

    for year in range(startdate_year, datetime.today().year + 1):
        end_month = 12 if year < datetime.today().year else datetime.today().month

        for month in range(startdate_month if year == startdate_year else 1, end_month + 1):
            start_of_month = datetime(year, month, 1).strftime('%Y-%m-%d')
            end_of_month = (datetime(year, month, 1) + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            end_of_month = end_of_month.strftime('%Y-%m-%d')

            date_range['startdates'].append(start_of_month)
            date_range['enddates'].append(end_of_month)

    return date_range


def get_yearly_daterange(start_date):
    startdate_year = datetime.strptime(start_date, '%Y-%m-%d').year
    end_date = datetime(startdate_year, 12, 31).strftime('%Y-%m-%d')
    date_range = {'startdates': [start_date], 'enddates': [end_date]}
    for year in range(startdate_year + 1, datetime.today().year + 1):
        start_of_year = datetime(year, 1, 1).strftime('%Y-%m-%d')
        if year == datetime.today().year:
            end_of_year = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            end_of_year = datetime(year, 12, 31).strftime('%Y-%m-%d')

        date_range['startdates'].append(start_of_year)
        date_range['enddates'].append(end_of_year)

    return date_range


def get_site_details(api_key, api_endpoint, export_siteids=False):
    payload = {
        "searchText": "Calgary",
        "api_key": api_key
    }
    response = requests.get(api_endpoint['site_list'], params=payload).json()
    site_details = dict()
    for site in response["sites"]["site"]:
        if site['accountId'] == 62361 and 'CoC' in site['name']:
            site_details[site['id']] = dict()
            site_details[site['id']]['site name'] = site['name']
            site_details[site['id']]['status'] = site['status']
            site_details[site['id']]['Peak Power'] = site['peakPower']
            location_values = ('country', 'state', 'city', 'address', 'zip')
            site_details[site['id']]['Location'] = {x: site['location'][x] for x in location_values}
    payload = {
        "api_key": api_key
    }
    site_ids = ",".join(str(site_id) for site_id in site_details.keys())
    response = requests.get(api_endpoint['site_date_range'].replace('{site}', site_ids), params=payload).json()

    for site in response['datePeriodList']['siteEnergyList']:
        site_details[site['siteId']]['start_date'] = site['dataPeriod']['startDate']

    if export_siteids:
        return site_ids, site_details
    else:
        return site_details


def fetch_aggr_data_day(site, api_key, api_endpoint, startdate, enddate):
    payload = {
        'api_key': api_key,
        'startDate': startdate,
        'endDate': enddate,
        'timeUnit': 'DAY'
    }
    response = requests.get(api_endpoint['site_aggr_data'].replace('{site}', str(site)), params=payload)
    return site, response.json()['energy']['values']


def fetch_aggr_data_15min(site, api_key, api_endpoint, startdate, enddate):
    payload = {
        'api_key': api_key,
        'startDate': startdate,
        'endDate': enddate,
        'timeUnit': 'QUARTER_OF_AN_HOUR'
    }
    response = requests.get(api_endpoint['site_aggr_data'].replace('{site}', str(site)), params=payload)
    return site, response.json()['energy']['values']

# Do we need parallelization? I know why we are using it but it seems unstable only because we are relying on an external api
# def get_aggr_data(api_key, api_endpoint, site_details):
#     aggr_data = dict()
#     site_daily_data = dict()
#
#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         futures = []
#         for site, site_detail in site_details.items():
#             date_range = get_yearly_daterange(site_detail['start_date'])
#             aggr_data[site] = []
#             for startdate, enddate in zip(date_range['startdates'], date_range['enddates']):
#                 futures.append(executor.submit(fetch_aggr_data_15min, site, api_key, api_endpoint, startdate, enddate))
#                 time.sleep(0.1)
#
#         for future in concurrent.futures.as_completed(futures):
#             site, data = future.result()
#             aggr_data[site].extend(data)
#
#             site_df = (
#                 pd.DataFrame(aggr_data[site])
#                 .dropna()
#                 .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
#                 .set_index('Date')
#             )
#             site_daily_data[site_details[site]['site name']] = site_df
#
#     return site_daily_data


def get_aggr_data_day(fetch_everything=True):
    api_endpoint, api_key = import_config_json()
    site_details = get_site_details(api_key, api_endpoint, export_siteids=False)
    aggr_data = dict()
    site_daily_data = dict()

    for site, site_detail in site_details.items():
        date_range = get_yearly_daterange(site_detail['start_date'])
        aggr_data[site] = []
        if fetch_everything is True:
            for startdate, enddate in zip(date_range['startdates'], date_range['enddates']):
                site, data = fetch_aggr_data_day(site, api_key, api_endpoint, startdate, enddate)
                aggr_data[site].extend(data)

                site_df = (
                    pd.DataFrame(aggr_data[site])
                    .dropna()
                    .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
                    .set_index('Date')
                )
                site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
                site_df.drop(columns=['Production (Wh)'], inplace=True)
                site_daily_data[site_details[site]['site name']] = site_df

        else:
            today_date = datetime.today()
            days_cushion = 5

            enddate = today_date + timedelta(days=days_cushion)
            enddate = enddate.strftime('%Y-%m-%d')

            startdate = today_date - timedelta(days=days_cushion)
            startdate = startdate.strftime('%Y-%m-%d')

            site, data = fetch_aggr_data_day(site, api_key, api_endpoint, startdate, enddate)
            aggr_data[site].extend(data)

            site_df = (
                pd.DataFrame(aggr_data[site])
                .dropna()
                .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
                .set_index('Date')
            )
            site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
            site_df.drop(columns=['Production (Wh)'], inplace=True)
            site_daily_data[site_details[site]['site name']] = site_df

    for key, value in site_daily_data.items():
        value.index = pd.to_datetime(value.index)
        site_daily_data[key] = value[value.index < pd.Timestamp.today().normalize()]

    return site_daily_data


def get_aggr_data_15min(fetch_everything=True):
    api_endpoint, api_key = import_config_json()
    site_details = get_site_details(api_key, api_endpoint, export_siteids=False)
    aggr_data = dict()
    site_daily_data = dict()
    current_date = datetime.now()
    two_months_ago = current_date - timedelta(days=60)

    for site, site_detail in site_details.items():
        date_range = get_monthly_daterange(two_months_ago)
        aggr_data[site] = []
        if fetch_everything is True:
            for startdate, enddate in zip(date_range['startdates'], date_range['enddates']):
                site, data = fetch_aggr_data_15min(site, api_key, api_endpoint, startdate, enddate)
                aggr_data[site].extend(data)

                site_df = (
                    pd.DataFrame(aggr_data[site])
                    .dropna()
                    .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
                    .set_index('Date')
                )
                site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
                site_df.drop(columns=['Production (Wh)'], inplace=True)
                site_df = site_df.head(len(site_df) - 1)
                site_daily_data[site_details[site]['site name']] = site_df

        else:
            today_date = datetime.today()
            days_cushion = 2

            enddate = today_date + timedelta(days=days_cushion)
            enddate = enddate.strftime('%Y-%m-%d')

            startdate = today_date - timedelta(days=days_cushion)
            startdate = startdate.strftime('%Y-%m-%d')

            site, data = fetch_aggr_data_15min(site, api_key, api_endpoint, startdate, enddate)
            aggr_data[site].extend(data)

            site_df = (
                pd.DataFrame(aggr_data[site])
                .dropna()
                .rename(columns={'date': 'Date', 'value': 'Production (Wh)'})
                .set_index('Date')
            )
            site_df['Production (kWh)'] = site_df['Production (Wh)'] / 1000
            site_df.drop(columns=['Production (Wh)'], inplace=True)
            site_df = site_df.head(len(site_df) - 1)
            site_daily_data[site_details[site]['site name']] = site_df

    return site_daily_data


if __name__ == '__main__':
    start = time.time()
    prod_dict = get_aggr_data_15min(fetch_everything=False)
    print(f'{round(time.time() - start, 2)} seconds to run')
    print(prod_dict)
