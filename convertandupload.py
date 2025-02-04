import pandas as pd
from pymongo import MongoClient, errors
import time

# Step 1: Load Excel File
file_path = 'combined_data (2).csv'  # Update this with your file path
data = pd.read_csv(file_path)

# Step 2: Connect to MongoDB
mongodb_uri = "mongodb+srv://dionathan:19910213200287@cluster1.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1"

# Retry logic for connecting to MongoDB
for _ in range(5):  # Retry up to 5 times
    try:
        client = MongoClient(
            mongodb_uri,
            serverSelectionTimeoutMS=30000,  # 30 seconds
            socketTimeoutMS=30000            # 30 seconds
        )
        client.admin.command('ping')  # Test connection
        print("Connection successful!")
        break
    except errors.ServerSelectionTimeoutError as e:
        print("Connection failed, retrying...")
        time.sleep(5)  # Wait before retrying
else:
    print("Failed to connect to MongoDB after multiple retries.")
    exit()

# Replace these with your database and collection names
db = client["real_estate"]  # Your database name
collection = db["listings"]  # Your collection name

# Step 3: Prepare Data for Upload
data.reset_index(inplace=True)  # Ensure the data has a clean index
records = data.to_dict('records')  # Convert to a list of dictionaries

# Sanitize keys in the records to ensure compatibility with MongoDB
def sanitize_keys(record):
    """Replace any dots in the keys with underscores."""
    return {key.replace('.', '_'): value for key, value in record.items()}

records = [sanitize_keys(record) for record in records]

# Step 4: Insert Data in Batches
batch_size = 500  # Adjust batch size as needed
for i in range(0, len(records), batch_size):
    batch = records[i:i + batch_size]
    retries = 3
    while retries > 0:
        try:
            collection.insert_many(batch)
            print(f"Batch {i // batch_size + 1} inserted successfully.")
            break
        except errors.BulkWriteError as bwe:
            print(f"Batch {i // batch_size + 1} failed: {bwe.details}")
            break  # Skip this batch if it's a permanent issue
        except errors.AutoReconnect as e:
            retries -= 1
            print(f"Retrying batch {i // batch_size + 1} due to {e}. Retries left: {retries}")
            time.sleep(5)
    else:
        print(f"Failed to insert batch {i // batch_size + 1} after multiple retries.")

print("Data upload process completed.")
