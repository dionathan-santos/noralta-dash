import pandas as pd
from pymongo import MongoClient

def upload_data_to_mongodb(data, mongodb_uri, database_name, collection_name):
    """Uploads data to MongoDB collection."""
    try:
        # Connect to MongoDB
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        collection = db[collection_name]

        # Convert DataFrame to dictionary and insert into collection
        data_dict = data.to_dict("records")
        collection.insert_many(data_dict)
        print(f"Successfully uploaded {len(data_dict)} records to the '{collection_name}' collection.")
    except Exception as e:
        print(f"Failed to upload data to MongoDB: {e}")

def main():
    # MongoDB connection details
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"
    collection_name = "brokerage"

    # Read the CSV file from the same folder
    file_path = "Complete_Reformatted_Broker_Data.csv"
    try:
        # Read CSV file into DataFrame
        data = pd.read_csv(file_path)
        print("Preview of data to be uploaded:")
        print(data.head())

        # Validate data before uploading
        if not data.empty:
            upload_data_to_mongodb(data, mongodb_uri, database_name, collection_name)
        else:
            print("The file is empty. Please provide a valid CSV file.")
    except Exception as e:
        print(f"Error reading the file: {e}")

if __name__ == "__main__":
    main()
