import pandas as pd
import sqlalchemy
from API.SolarEdge.solar_data import get_aggr_data_15min
from API.Fronius.solar_data import fronius_15min_data


def initial_db_setup_15min(prod_engine):
    """We can only use Solaredge or Fronius for 15 minute data"""
    print("Database engine does not exist. Creating...")

    print('Solaredge 15min Data')
    sites_data = get_aggr_data_15min(fetch_everything=True)
    sites = list(sites_data.keys())

    for site in sites:
        df = sites_data[site]
        df = df[~df.index.duplicated()]
        df.to_sql(site, prod_engine)

    print('Fronius 15min Data')
    sites_data = fronius_15min_data(fetch_everything=True)
    sites = list(sites_data.keys())

    for site in sites:
        df = sites_data[site]
        df = df[~df.index.duplicated()]
        df.to_sql(site, prod_engine)

    print("Database setup complete.")

    return


def update_15min_prod_db(prod_engine):
    # Update Solaredge Data
    sites_data = get_aggr_data_15min(fetch_everything=False)
    sites = list(sites_data.keys())
    for site in sites:
        df = sites_data[site]
        max_date_query = f"select max(Date) from '{site}'"
        max_date = pd.read_sql(max_date_query, prod_engine).iloc[0, 0]
        append_df = df[df.index > max_date]
        # _query = f"select * from '{site}' order by Date DESC LIMIT {len(df)}"
        # sql_df = pd.read_sql(_query, prod_engine)
        # append_df = df[~df.index.isin(sql_df['Date'])]
        print(f"Just appended {len(append_df)} new rows to {site} table")
        append_df.to_sql(site, prod_engine, if_exists='append')

    # Update Fronius Data
    sites_data = fronius_15min_data(fetch_everything=False)
    sites = list(sites_data.keys())
    for site in sites:
        df = sites_data[site]
        max_date_query = f"select max(Date) from '{site}'"
        max_date = pd.read_sql(max_date_query, prod_engine).iloc[0, 0]
        append_df = df[df.index > max_date]
        # _query = f"select * from '{site}' order by Date DESC LIMIT {len(df)}"
        # sql_df = pd.read_sql(_query, prod_engine)
        # append_df = df[~df.index.isin(sql_df['Date'])]
        print(f"Just appended {len(append_df)} new rows to {site} table")
        append_df.to_sql(site, prod_engine, if_exists='append')

    print("Database update complete.")
    return


def download_DB_data_15min(engine, interval=None):
    data = get_Production_Data_From_DB(engine)

    for key, value in data.items():
        value = value.sort_values(by='Date')
        value = value.dropna()
        value['Date'] = pd.to_datetime(value['Date'])
        value.set_index('Date', inplace=True)

        if interval == '15T':
            pass
        elif interval == 'H':
            value = value.resample('H').sum()
        elif interval == '12H':
            value = value.resample('12H').sum()
        else:
            KeyError('Only accepts daily, monthly, or yearly')

        value = value.reset_index()
        value['Date'] = value['Date'].dt.strftime('%Y-%m-%d %H:%M:%S')
        data[key] = value.to_dict(orient='records')

    return data


def get_Production_Data_From_DB(engine):
    query = "SELECT name FROM sqlite_master WHERE type='table';"
    df = pd.read_sql(query, engine)
    sites = df['name'].tolist()

    prod_data = {}
    for site in sites:
        query_site = f"""SELECT DISTINCT * FROM "{site}" WHERE Date BETWEEN DATE(DATE('now'), '-7 days') AND DATE('now', '+1 day') ORDER BY Date DESC;"""
        df_temp = pd.read_sql(query_site, engine)
        prod_data[site] = df_temp

    return prod_data


if __name__ == "__main__":
    engine = sqlalchemy.create_engine('sqlite:///Prod_15min_DB.db')
    # initial_db_setup_15min(prod_engine=engine, sites_engine=None)
    # update_prod_db(engine, sites_engine=None)

    stock_data = download_DB_data_15min(engine, interval=None)
    print(stock_data)
    engine.dispose()
