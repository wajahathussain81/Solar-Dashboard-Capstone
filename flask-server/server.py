import os
import time
import calendar
from datetime import datetime
import pandas as pd
import sqlalchemy
from flask import Flask, jsonify, request
from API.Enphase.solar_data import update_or_initialize_site_db_setup
from API.Enphase.api_setup import reset_api_count
from Database.Prod_DB.setup_update_read_db import initial_db_setup_daily, update_prod_db, download_DB_data_daily
from Database.Site_Details_DB.setup_update_read import read_site_db
from Database.Prod_DB_15_min.setup_update_read import initial_db_setup_15min, download_DB_data_15min, \
    update_15min_prod_db
from apscheduler.schedulers.background import BackgroundScheduler
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


# Scheduling Function
def update_15min_database():
    print('Updating 15 minute database...')
    prod_15min_engine = sqlalchemy.create_engine('sqlite:///Prod_15min_DB.db')
    update_15min_prod_db(prod_15min_engine)
    prod_15min_engine.dispose()


def daily_update_database():
    print('Updating daily databases...')
    prod_engine = sqlalchemy.create_engine('sqlite:///Prod_DB.db')
    sites_engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    # setting up site data
    update_or_initialize_site_db_setup(sites_engine)
    time.sleep(90)  # Waiting 90s so as not to overload the Enphase API
    # Setting up daily production data
    update_prod_db(prod_engine, sites_engine)
    # Setting up Metrics tab data / aggregated data
    put_aggregated_production_on_DB(sites_engine)
    # Setting up Alerts tab
    put_zeroProductionDaily_sites_on_DB(sites_engine)
    prod_engine.dispose()
    sites_engine.dispose()


def initial_database_setup():
    print('Setting up initial database...')
    prod_engine = sqlalchemy.create_engine('sqlite:///Prod_DB.db')
    sites_engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    prod_15min_engine = sqlalchemy.create_engine('sqlite:///Prod_15min_DB.db')
    # site detials db
    update_or_initialize_site_db_setup(sites_engine)
    # daily production db
    time.sleep(90)  # Waiting 90s so as not to overload the Enphase API
    initial_db_setup_daily(prod_engine, sites_engine)
    # 15 min production db
    initial_db_setup_15min(prod_15min_engine)
    # Setting up Metrics tab data / aggregated data
    put_aggregated_production_on_DB(sites_engine)
    # Setting up Alerts tab
    put_zeroProductionDaily_sites_on_DB(sites_engine)
    prod_engine.dispose()
    prod_15min_engine.dispose()
    sites_engine.dispose()


def get_site_details_data():
    engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    data_df = read_site_db(engine)
    engine.dispose()
    return data_df


def inverter_corresponding_sites(Enphase=True):
    manufactured_site_list = []
    manufactured_df_dict = get_site_details_data()
    for manufacturer, df in manufactured_df_dict.items():
        if not Enphase and manufacturer == 'Enphase':
            continue
        manufacturer_dict = dict()
        manufacturer_dict['manufacturer_name'] = manufacturer
        try:
            manufacturer_dict['sites'] = df['site name'].to_list()
        except KeyError:
            manufacturer_dict['sites'] = df['public_name'].to_list()
        manufactured_site_list.append(manufacturer_dict)
    return manufactured_site_list


def get_prod_data_daily(timeframe='daily'):
    engine = sqlalchemy.create_engine('sqlite:///Prod_DB.db')
    data_df = download_DB_data_daily(engine, interval=timeframe)
    engine.dispose()
    return data_df


def get_prod_data_15min(timeframe='15T'):
    engine = sqlalchemy.create_engine('sqlite:///Prod_15min_DB.db')
    data_df = download_DB_data_15min(engine, interval=timeframe)
    engine.dispose()
    return data_df


@app.route("/api/site_filter/daily")
def get_site_name_all():
    data = inverter_corresponding_sites(Enphase=True)
    return jsonify(data)


@app.route("/api/site_filter/fifteen")
def get_site_name_fronius_solaredge():
    data = inverter_corresponding_sites(Enphase=False)
    return jsonify(data)


def put_aggregated_production_on_DB(sites_engine):
    print('Updating Metrics/Aggregated production data')
    # Get last month's date range
    last_month = {'start_date': (datetime.today() - pd.DateOffset(months=1)).to_pydatetime().replace(day=1)}
    last_month['end_date'] = datetime(last_month['start_date'].year, last_month['start_date'].month,
                                      calendar.monthrange(last_month['start_date'].year,
                                                          last_month['start_date'].month)[1]).strftime('%Y-%m-%d')
    last_month['start_date'] = last_month['start_date'].strftime('%Y-%m-%d')

    last_7_days = {
        'start_date': (datetime.today() - pd.DateOffset(days=7)).to_pydatetime().strftime('%Y-%m-%d'),
        'end_date': datetime.today().strftime('%Y-%m-%d')
    }

    # get the last three months from today date range
    three_month = {
        'start_date': (datetime.today() - pd.DateOffset(months=3)).to_pydatetime().strftime('%Y-%m-%d'),
        'end_date': datetime.today().strftime('%Y-%m-%d')
    }

    # get the last 6 months from today's date range
    six_month = {
        'start_date': (datetime.today() - pd.DateOffset(months=6)).to_pydatetime().strftime('%Y-%m-%d'),
        'end_date': datetime.today().strftime('%Y-%m-%d')
    }

    # get last year's date range
    last_year = {
        'start_date': datetime(datetime.today().year - 1, 1, 1).strftime('%Y-%m-%d'),
        'end_date': datetime(datetime.today().year - 1, 12,
                             calendar.monthrange(datetime.today().year - 1, 12)[1]).strftime('%Y-%m-%d')
    }

    month_to_date = {
        'start_date': datetime.today().replace(day=1).strftime('%Y-%m-%d'),
        'end_date': datetime.today().strftime('%Y-%m-%d')
    }

    # get date range from start of this year to today (year to date)
    ytd = {
        'start_date': datetime.today().replace(month=1, day=1).strftime('%Y-%m-%d'),
        'end_date': datetime.today().strftime('%Y-%m-%d')
    }
    date_ranges = {
        'last_7_days': last_7_days,
        'month_to_date': month_to_date,
        'last_month': last_month,
        'three_month': three_month,
        'six_month': six_month,
        'last_year': last_year,
        'ytd': ytd
    }

    data_json = get_prod_data_daily()
    sites_list = list(data_json.keys())

    df_dict_sites = {}
    for site in sites_list:
        value = pd.DataFrame.from_records(data_json[site])
        if 'index' in value.columns:
            value.drop(columns='index', inplace=True)
        df_dict_sites[site] = value

    aggregated_data = []
    for site in sites_list:
        site_data = {}
        site_df = df_dict_sites[site]
        site_daterange_list = []
        for key, date_dict in date_ranges.items():
            date_filtered_df = site_df[
                (site_df['Date'] >= date_dict['start_date']) & (site_df['Date'] <= date_dict['end_date'])]
            daterange_sum_dict = {key: date_filtered_df['Production (kWh)'].sum()}
            site_daterange_list.append(daterange_sum_dict)
        site_data['site'] = site
        site_data['date_range'] = site_daterange_list
        aggregated_data.append(site_data)

    aggregated_df = pd.DataFrame(aggregated_data)

    all_rows_df = pd.DataFrame()
    for index, row in aggregated_df.iterrows():
        site = row['site']
        row = row['date_range']

        combined_dict = {}
        for d in row:
            combined_dict.update(d)

        row_df = pd.DataFrame(combined_dict, index=[site])
        all_rows_df = pd.concat([all_rows_df, row_df], axis=0)

    aggregated_df = aggregated_df.drop(columns='date_range').join(all_rows_df, on='site')

    site_details_data = get_site_details_data()
    enphase_df = site_details_data['Enphase'].filter(items=['name', 'size_w'], axis=1).rename(columns={'name': 'site'})
    enphase_df['size_kw'] = enphase_df['size_w'] / 1000
    enphase_df.drop(columns=['size_w'], inplace=True)
    solaredge_df = site_details_data['SolarEdge'].filter(items=['site name', 'Peak Power'], axis=1).rename(
        columns={'site name': 'site', 'Peak Power': 'size_kw'})
    fronius_df = site_details_data['Fronius'].filter(items=['site name', 'Peak Power'], axis=1).rename(
        columns={'site name': 'site', 'Peak Power': 'size_kw'})
    total_size_df = pd.concat([enphase_df, solaredge_df, fronius_df], axis=0, ignore_index=True)

    aggregated_df = aggregated_df.join(total_size_df.set_index('site'), on='site')
    aggregated_df['Last_Year_Prod_Over_Site_Size_KW'] = aggregated_df['last_year'] / aggregated_df['size_kw']

    numerical_cols = aggregated_df.select_dtypes(include='number')
    # numerical_cols = [col for col in numerical_cols if col != 'size_kw']
    for col in numerical_cols:
        aggregated_df[col] = aggregated_df[col].apply(lambda x: format(round(x, 2), ','))

    aggregated_df.to_sql('Metrics', sites_engine, if_exists='replace')
    print('Finished Updating Metrics on DB')
    return


@app.route("/api/aggregated-production", methods=['GET'])
def get_aggregated_production():
    engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    table_name = 'Metrics'
    query = f"SELECT * FROM '{table_name}'"
    df = pd.read_sql(query, engine)
    engine.dispose()
    df = df.drop(columns='index')
    unit_per_daterange = {
        'last_7_days': 'kWh',
        'month_to_date': 'kWh',
        'last_month': 'kWh',
        'three_month': 'kWh',
        'six_month': 'kWh',
        'last_year': 'kWh',
        'ytd': 'kWh',
        'size_kw': 'kW',
        'Last_Year_Prod_Over_Site_Size_KW': 'kWh/kW'
    }
    metric_cols_list = df.columns.drop('site').tolist()
    aggregated_data = []
    for idx, row in df.iterrows():
        site_dict = {'site': row['site'], 'date_range': []}
        for time_frame in metric_cols_list:
            site_dict['date_range'].append({time_frame: row[time_frame] + ' ' + unit_per_daterange[time_frame]})
        aggregated_data.append(site_dict)

    return jsonify(aggregated_data)


def put_zeroProductionDaily_sites_on_DB(sites_engine):
    print('Updating Alerts data')
    data_json = get_prod_data_daily()
    sites_list = list(data_json.keys())

    df_dict_sites = {}
    for site in sites_list:
        value = pd.DataFrame.from_records(data_json[site])
        if 'index' in value.columns:
            value.drop(columns='index', inplace=True)
        df_dict_sites[site] = value

    site_zeroDays = {}
    for site, df in df_dict_sites.items():
        zero_mask = df['Production (kWh)'] == 0
        reversed_zero_mask = zero_mask[::-1]
        consecutive_zeros = 0
        for value in reversed_zero_mask:
            if value is True:
                consecutive_zeros += 1
            else:
                break
        site_zeroDays[site] = consecutive_zeros

    ZeroDayDf = pd.DataFrame(site_zeroDays, index=['ZeroDayCount'])
    ZeroDayDf.to_sql('Alerts', sites_engine, if_exists='replace')
    print('Finished Updating Alerts on DB')
    return


@app.route("/alerts", methods=['GET'])
def get_zeroProductionDaily_sites():
    engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    table_name = 'Alerts'
    query = f"SELECT * FROM '{table_name}'"
    df = pd.read_sql(query, engine)
    engine.dispose()
    site_zeroDays = {}
    for site in [col for col in df.columns if col != 'index']:
        site_zeroDays[site] = df[site].item()

    return jsonify(site_zeroDays)


@app.route('/api/data', methods=['POST'])
def handle_daily_data():
    selection = request.json.get('selection')

    if selection == 'daily':
        data_df = get_prod_data_daily(timeframe='daily')
    elif selection == 'monthly':
        data_df = get_prod_data_daily(timeframe='monthly')
    elif selection == 'yearly':
        data_df = get_prod_data_daily(timeframe='yearly')
    else:
        raise KeyError('Only accepted values are: daily, monthly, yearly')
    return jsonify(data_df)


@app.route('/api/15min/data', methods=['POST'])
def handle_15min_data():
    selection = request.json.get('selection')

    if selection == '15T':
        data_df = get_prod_data_15min(timeframe='15T')
    elif selection == 'H':
        data_df = get_prod_data_15min(timeframe='H')
    elif selection == '12H':
        data_df = get_prod_data_15min(timeframe='12H')
    else:
        raise KeyError('Only accepted values are: 15T, H, 12H')
    return jsonify(data_df)


if __name__ == '__main__':
    if not os.path.exists('Prod_DB.db') or not os.path.exists('Site_Details_DB.db') or not os.path.exists(
            'Prod_15min_DB.db'):
        if os.path.exists('Prod_DB.db'):
            os.remove('Prod_DB.db')
        if os.path.exists('Site_Details_DB.db'):
            os.remove('Site_Details_DB.db')
        if os.path.exists('Prod_15min_DB.db'):
            os.remove('Prod_15min_DB.db')

        initial_database_setup()

    scheduler = BackgroundScheduler()
    scheduler.add_job(daily_update_database, 'cron', hour='13',
                      minute=0)  # Update database every day at 7am calgary time
    # 11am on the server corresponds to 5am calgary time
    scheduler.add_job(reset_api_count, 'cron', day='3', hour=0, minute=0)  # Update Enphase api 3rd day of each month
    scheduler.add_job(update_15min_database, 'cron', minute='5,20,35,50', hour='*')
    scheduler.start()

    app.run(debug=True, use_reloader=False)  # This file will be the allways active file on pythonanywhere
    # for tutorial watch: https://www.youtube.com/watch?v=z7dYIKm4np8
    # follow it almost exactly except instead of "app" use "server" in WSGI file
    # Also upgrade to the 5 dollar paid tier and set this file as always running to update databases
