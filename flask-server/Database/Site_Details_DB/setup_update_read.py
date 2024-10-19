import pandas as pd
import sqlalchemy


def read_db(engine, table_name):
    query = f"SELECT * FROM '{table_name}'"
    df = pd.read_sql(query, engine)
    return df


def read_site_db(engine):
    site_detials_dict = {}

    Enphase = read_db(engine, 'Enphase_SD')
    site_detials_dict['Enphase'] = Enphase

    Solaredge = read_db(engine, 'Solaredge_SD')
    site_detials_dict['SolarEdge'] = Solaredge

    Fronius = read_db(engine, 'Fronius_SD')
    site_detials_dict['Fronius'] = Fronius

    return site_detials_dict


if __name__ == "__main__":
    # run this code from server.py for the actual effects
    engine = sqlalchemy.create_engine('sqlite:///Site_Details_DB.db')
    # can not import due to circular imports
    # update_or_initialize_site_db_setup(engine)
    a = read_site_db(engine)
    print(a)
    engine.dispose()
