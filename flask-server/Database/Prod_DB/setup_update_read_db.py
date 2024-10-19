import pandas as pd
import sqlalchemy
from sqlalchemy import inspect
from API.Enphase.solar_data import recursive_production_for_site
from API.SolarEdge.solar_data import get_aggr_data_day
from API.Fronius.solar_data import fronius_daily_data


def initial_db_setup_daily(prod_engine, sites_engine):
    print("Database engine does not exist. Creating...")

    print('Enphase Daily Data')
    sites_data = recursive_production_for_site(sites_engine)
    sites = list(sites_data.keys())

    for site in sites:
        df = sites_data[site]
        df = df[~df.index.duplicated()]  # date is index
        df.to_sql(site, prod_engine)

    print('Solaredge Daily Data')
    sites_data = get_aggr_data_day(fetch_everything=True)
    sites = list(sites_data.keys())

    for site in sites:
        df = sites_data[site]
        df = df[~df.index.duplicated()]
        df.to_sql(site, prod_engine)

    print('Fronius Daily Data')
    sites_data = fronius_daily_data(fetch_everything=True)
    sites = list(sites_data.keys())
    for site in sites:
        df = sites_data[site]
        df = df[~df.index.duplicated()]
        df.to_sql(site, prod_engine)

    print("Daily Database setup complete.")
    print()

    return


def update_prod_db(prod_engine, sites_engine):
    # Update Enphase Data
    sites_data = recursive_production_for_site(sites_engine)
    sites = list(sites_data.keys())
    insp = inspect(prod_engine)
    for site in sites:
        if insp.has_table(site):
            df = sites_data[site]
            max_date_query = f"select max(Date) from '{site}'"
            max_date = pd.read_sql(max_date_query, prod_engine).iloc[0, 0]
            append_df = df[df.index > max_date]
            print(f"Just appended {len(append_df)} new rows to {site} table")
            append_df.to_sql(site, prod_engine, if_exists='append')
        else:
            df = sites_data[site]
            print(f"Created new site, appended {len(df)} new rows to {site} table")
            df.to_sql(site, prod_engine, if_exists='append')

    # Update Solaredge Data
    sites_data = get_aggr_data_day(fetch_everything=False)
    sites = list(sites_data.keys())
    for site in sites:
        if insp.has_table(site):
            df = sites_data[site]
            max_date_query = f"select max(Date) from '{site}'"
            max_date = pd.read_sql(max_date_query, prod_engine).iloc[0, 0]
            append_df = df[df.index > max_date]
            print(f"Just appended {len(append_df)} new rows to {site} table")
            append_df.to_sql(site, prod_engine, if_exists='append')
        else:
            df = sites_data[site]
            print(f"Created new site, appended {len(df)} new rows to {site} table")
            df.to_sql(site, prod_engine, if_exists='append')

    # Update Fronius Data
    sites_data = fronius_daily_data(fetch_everything=False)
    sites = list(sites_data.keys())
    for site in sites:
        if insp.has_table(site):
            df = sites_data[site]
            max_date_query = f"select max(Date) from '{site}'"
            max_date = pd.read_sql(max_date_query, prod_engine).iloc[0, 0]
            append_df = df[df.index > max_date]
            print(f"Just appended {len(append_df)} new rows to {site} table")
            append_df.to_sql(site, prod_engine, if_exists='append')
        else:
            df = sites_data[site]
            print(f"Created new site, appended {len(df)} new rows to {site} table")
            df.to_sql(site, prod_engine, if_exists='append')

    print("Database update complete.")
    return


def download_DB_data_daily(engine, interval='yearly'):
    data = get_Production_Data_From_DB(engine)

    combined_df = pd.DataFrame()
    for key, value in data.items():
        value = value.sort_values(by='Date')
        value = value.dropna()
        value['Date'] = pd.to_datetime(value['Date'])

        if interval == 'daily':
            pass
        elif interval == 'monthly':
            value.set_index('Date', inplace=True)
            value = value.resample('M').sum()
        elif interval == 'yearly':
            value.set_index('Date', inplace=True)
            value = value.resample('Y').sum()
        else:
            raise KeyError('Only accepts daily, monthly, or yearly')

        value = value.reset_index()
        value['Date'] = value['Date'].dt.strftime('%Y-%m-%d')
        data[key] = value.to_dict(orient='records')
        combined_df = pd.concat([combined_df, value], axis=0, ignore_index=True)

    if 'index' in combined_df.columns:
        combined_df.drop(columns=['index'], inplace=True)

    combined_df = combined_df.groupby('Date').sum()
    combined_df = combined_df.reset_index()
    combined_df = combined_df.sort_values(by='Date')
    combined_df = combined_df.dropna()
    data['combined'] = combined_df.to_dict(orient='records')

    return data


def read_db(engine, table_name):
    query = f"SELECT DISTINCT * FROM '{table_name}' ORDER BY Date DESC"
    df = pd.read_sql(query, engine)
    return df


def get_Production_Data_From_DB(engine):
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    df = pd.read_sql(query, engine)
    sites = df['name'].tolist()

    prod_data = {}
    for site in sites:
        df_temp = read_db(engine, site)
        prod_data[site] = df_temp

    return prod_data


if __name__ == "__main__":
    engine = sqlalchemy.create_engine('sqlite:///Prod_DB.db')
    # initial_db_setup(prod_engine=engine, sites_engine=None)
    # update_prod_db(engine, sites_engine=None)

    stock_data = download_DB_data_daily(engine, interval='monthly')
    print(stock_data)
    engine.dispose()
