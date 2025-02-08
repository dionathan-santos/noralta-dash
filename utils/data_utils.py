import pandas as pd
from pymongo import MongoClient

def get_mongodb_data(uri, database, collection):
    try:
        client = MongoClient(uri)
        db = client[database]
        collection = db[collection]
        data = list(collection.find())
        return pd.DataFrame(data)
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return pd.DataFrame()

def filter_data(data, start_date, end_date, area_city):
    data['Sold Date'] = pd.to_datetime(data['Sold Date'])
    filtered_data = data[(data['Sold Date'] >= pd.Timestamp(start_date)) & (data['Sold Date'] <= pd.Timestamp(end_date))]
    if area_city:
        filtered_data = filtered_data[filtered_data['Area/City'] == area_city]
    return filtered_data

def get_aws_credentials():
    try:
        return (
            st.secrets["aws"]["AWS_ACCESS_KEY_ID"],
            st.secrets["aws"]["AWS_SECRET_ACCESS_KEY"],
            st.secrets["aws"].get("AWS_REGION", "us-east-2")
        )
    except KeyError as e:
        available_keys = list(st.secrets.get("aws", {}).keys())
        raise Exception(
            f"Missing AWS credentials. Found keys under 'aws': {available_keys}"
        )
