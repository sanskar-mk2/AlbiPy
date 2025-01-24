from AlbiPy import sniffing_thread
import pandas as pd
import time
from mysql.connector import Error
import mysql.connector
import json

HEADERS = [
    "UnitPriceSilver",
    "TotalPriceSilver", 
    "Amount",
    "Tier",
    "AuctionType",
    "ItemTypeId",
    "ItemGroupTypeId",
    "EnchantmentLevel", 
    "QualityLevel",
    "Location",
]

def load_config():
    with open('config.json') as f:
        return json.load(f)

def create_db_connection(config):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=config['db_host'],
            user=config['db_user'],
            passwd=config['db_password'],
            database=config['db_name']
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")
    return connection

def read_query(connection, query):
    try:
        cursor = connection.cursor()
        result = None
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        return result
    except Error as err:
        print(f"Error: '{err}'")

def execute_query(connection, query):
    try:
        cursor = connection.cursor()
        cursor.execute(query)
        connection.commit()
        cursor.close()
        print("Query successful")
    except Error as err:
        print(f"Error: '{err}'")

def setup_database(connection):
    create_table = """
    CREATE TABLE IF NOT EXISTS albion_table (
        UnitPriceSilver INT,
        TotalPriceSilver INT,
        Amount INT,
        Tier INT,
        AuctionType VARCHAR(255),
        ItemTypeId VARCHAR(255),
        ItemGroupTypeId VARCHAR(255),
        EnchantmentLevel INT,
        QualityLevel INT,
        Location VARCHAR(255),
        Utc FLOAT
    )
    """
    execute_query(connection, create_table)

def process_market_data(orders):
    data = []
    for order in orders:
        data.append([
            order.UnitPriceSilver,
            order.TotalPriceSilver,
            order.Amount,
            order.Tier,
            order.AuctionType,
            order.ItemTypeId,
            order.ItemGroupTypeId,
            order.EnchantmentLevel,
            order.QualityLevel,
            order.Location,
        ])
    
    df = pd.DataFrame(data, columns=HEADERS)
    requests = df[df["AuctionType"] == "request"]
    offers = df[df["AuctionType"] == "offer"]
    
    max_request = requests.groupby(["AuctionType", "ItemTypeId"])["UnitPriceSilver"].max().reset_index()
    min_offer = offers.groupby(["AuctionType", "ItemTypeId"])["UnitPriceSilver"].min().reset_index()
    
    df_found = pd.DataFrame(columns=HEADERS)
    
    # Process requests
    for i in range(len(max_request)):
        max_req = max_request.iloc[i]
        max_req_df = requests[
            (requests["ItemTypeId"] == max_req["ItemTypeId"]) &
            (requests["UnitPriceSilver"] == max_req["UnitPriceSilver"])
        ]
        if len(max_req_df) > 0:
            df_found.loc[(len(df_found))] = max_req_df.iloc[0]

    # Process offers
    for i in range(len(min_offer)):
        min_off = min_offer.iloc[i]
        min_off_df = offers[
            (offers["ItemTypeId"] == min_off["ItemTypeId"]) &
            (offers["UnitPriceSilver"] == min_off["UnitPriceSilver"])
        ]
        if len(min_off_df) > 0:
            df_found.loc[(len(df_found))] = min_off_df.iloc[0]
            
    return df_found[df_found["Location"] != "Unknown"]

def update_database(connection, df_found):
    for i in range(len(df_found)):
        row = df_found.iloc[i]
        location = row["Location"]
        auction_type = row["AuctionType"]
        item_type_id = row["ItemTypeId"]
        
        query = f"""
        SELECT * FROM albion_table 
        WHERE Location = '{location}' 
        AND AuctionType = '{auction_type}' 
        AND ItemTypeId = '{item_type_id}';
        """
        
        result = read_query(connection, query)
        current_time = time.time()
        
        if len(result) > 0:
            query = f"""
            UPDATE albion_table 
            SET UnitPriceSilver = {row.UnitPriceSilver},
                TotalPriceSilver = {row.TotalPriceSilver},
                Amount = {row.Amount},
                Tier = {row.Tier},
                EnchantmentLevel = {row.EnchantmentLevel},
                QualityLevel = {row.QualityLevel},
                Utc = '{current_time}'
            WHERE Location = '{location}'
            AND AuctionType = '{auction_type}'
            AND ItemTypeId = '{item_type_id}';
            """
        else:
            query = f"""
            INSERT INTO albion_table 
            (UnitPriceSilver, TotalPriceSilver, Amount, Tier, AuctionType,
             ItemTypeId, ItemGroupTypeId, EnchantmentLevel, QualityLevel,
             Location, Utc)
            VALUES
            ({row.UnitPriceSilver}, {row.TotalPriceSilver}, {row.Amount},
             {row.Tier}, '{row.AuctionType}', '{row.ItemTypeId}',
             '{row.ItemGroupTypeId}', {row.EnchantmentLevel},
             {row.QualityLevel}, '{row.Location}', '{current_time}');
            """
        execute_query(connection, query)

if __name__ == "__main__":
    config = load_config()
    connection = create_db_connection(config)
    setup_database(connection)
    
    print("Starting sniffing thread...")
    thread = sniffing_thread()
    thread.start()

    try:
        while True:
            time.sleep(5)
            orders = thread.get_data()
            df_found = process_market_data(orders)
            print(df_found)
            update_database(connection, df_found)

    except KeyboardInterrupt:
        pass

    thread.stop()
    print("\nThread stopped!")
