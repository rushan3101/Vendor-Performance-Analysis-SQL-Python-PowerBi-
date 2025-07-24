#Importing Libraries
import pandas as pd
import os
from sqlalchemy import create_engine
import time
import logging

#Configuring logging
logging.basicConfig(
    filename='logs/ingestions_db.log',
    level= logging.DEBUG,
    format = "%(asctime)s - %(levelname)s - %(message)s",
    filemode = "a"
)

#Creating Postgresql engine
engine = create_engine('sqlite:///inventory.db')

#Ingest dataframe to database function
def ingest_db(df:pd.DataFrame,table_name,engine):
    '''This function will ingest dataframe in database'''
    df.to_sql(name = table_name,con=engine,if_exists="replace",index=False)

#Loading raw data from csv and finally ingest it in database
def load_raw_data():
    '''This function will load the csv's as Dataframe and ingest it into Database'''
    start = time()
    for file in os.listdir('data'):
        if '.csv' in file :
            df = pd.read_csv(f'data/{file}')
            logging.info(f'Ingesting file {file} in db')
            ingest_db(df,file[:-4],engine)
    end = time()
    total_time = (end-start)/60
    logging.info("-----------INGESTION COMPLETE-----------")
    logging.info(f'Total time taken {total_time} minutes')

if __name__ == '__main__':
    load_raw_data()