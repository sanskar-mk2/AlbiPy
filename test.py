from AlbiPy import sniffing_thread

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
import pandas as pd
import time
from mysql.connector import Error
import mysql.connector

# LOCATIONS = {
#     "FOREST_GREEN_MARKETPLACE_PORTAL": "Lymhurst",
#     "#FOREST_GREEN_MARKETPLACE_CENTERCITY": "Lymhurst",
#     "#STEPPE_GREEN_MARKETPLACE_CENTERCITY": "Bridgewatch",
#     "%HIGHLAND_GREEN_MARKETPLACE_CENTERCITY": "Martlock",
#     '"SWAMP_GREEN_MARKETPLACE_CENTERCITY': "Thetford",
#     "%MOUNTAIN_GREEN_MARKETPLACE_CENTERCITY": "Fort Sterling",
#     "MISTS_GREEN_MARKETPLACE_SMALL": "Brecilien",
# }


def create_db_connection(host_name, user_name, user_password, db_name):
    connection = None
    try:
        connection = mysql.connector.connect(
            host=host_name, user=user_name, passwd=user_password, database=db_name
        )
        print("MySQL Database connection successful")
    except Error as err:
        print(f"Error: '{err}'")

    return connection


connection = create_db_connection("64.226.95.45", "sanskar", "pass", "albion")


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


if __name__ == "__main__":
    print("Starting sniffing thread...")
    thread = sniffing_thread()
    thread.start()

    try:
        while True:
            time.sleep(5)
            orders = thread.get_data()

            data = []

            for order in orders:
                data.append(
                    [
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
                    ]
                )

            df = pd.DataFrame(
                data,
                columns=HEADERS,
            )
            requests = df[df["AuctionType"] == "request"]
            offers = df[df["AuctionType"] == "offer"]
            max_request = requests.groupby(["AuctionType", "ItemTypeId"])[
                "UnitPriceSilver"
            ].max()
            min_offer = offers.groupby(["AuctionType", "ItemTypeId"])[
                "UnitPriceSilver"
            ].min()

            # get the max request and min offer for each item
            max_request = max_request.reset_index()
            min_offer = min_offer.reset_index()

            # compare_query = """
            #     SELECT * FROM albion_items;
            # """
            # compare_against = read_query(connection, compare_query)
            # # get machine_name column
            # machine_names = [row[0] for row in compare_against]

            # do it for both requests and offers, drop rows that don't have a match
            df_found = pd.DataFrame(columns=HEADERS)
            for i in range(len(max_request)):
                max_req = max_request.iloc[i]
                max_req_df = requests[
                    (requests["ItemTypeId"] == max_req["ItemTypeId"])
                    & (requests["UnitPriceSilver"] == max_req["UnitPriceSilver"])
                ]
                if len(max_req_df) > 0:
                    df_found.loc[(len(df_found))] = max_req_df.iloc[0]

            for i in range(len(min_offer)):
                min_off = min_offer.iloc[i]
                min_off_df = offers[
                    (offers["ItemTypeId"] == min_off["ItemTypeId"])
                    & (offers["UnitPriceSilver"] == min_off["UnitPriceSilver"])
                ]
                # print(min_off_df)
                if len(min_off_df) > 0:
                    df_found.loc[(len(df_found))] = min_off_df.iloc[0]

            print(df_found)

            # discard all rows with Location = "Unknown"
            df_found = df_found[df_found["Location"] != "Unknown"]
            query_database = """
            SELECT * FROM albion_table;
            """

            result = read_query(connection, query_database)

            # upsert based on location, auction type and itemtypeid
            for i in range(len(df_found)):
                row = df_found.iloc[i]
                location = row["Location"]
                auction_type = row["AuctionType"]
                item_type_id = row["ItemTypeId"]
                query = f"""
                SELECT * FROM albion_table WHERE Location = '{location}' AND AuctionType = '{auction_type}' AND ItemTypeId = '{item_type_id}';
                """

                result = read_query(connection, query)
                if len(result) > 0:
                    query = f"""
                    UPDATE albion_table SET UnitPriceSilver = {row.UnitPriceSilver}, TotalPriceSilver = {row.TotalPriceSilver}, Amount = {row.Amount}, Tier = {row.Tier}, EnchantmentLevel = {row.EnchantmentLevel}, QualityLevel = {row.QualityLevel}, Utc = '{time.time()}' WHERE Location = '{location}' AND AuctionType = '{auction_type}' AND ItemTypeId = '{item_type_id}';
                    """
                    execute_query(connection, query)
                else:
                    query = f"""
                    INSERT INTO albion_table (UnitPriceSilver, TotalPriceSilver, Amount, Tier, AuctionType, ItemTypeId, ItemGroupTypeId, EnchantmentLevel, QualityLevel, Location, Utc) VALUES ({row.UnitPriceSilver}, {row.TotalPriceSilver}, {row.Amount}, {row.Tier}, '{row.AuctionType}', '{row.ItemTypeId}', '{row.ItemGroupTypeId}', {row.EnchantmentLevel}, {row.QualityLevel}, '{row.Location}', '{time.time()}');
                    """
                    execute_query(connection, query)

    except KeyboardInterrupt:
        pass

    thread.stop()
    print("\nThread stopped!")
