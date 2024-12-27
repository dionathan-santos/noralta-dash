import pandas as pd
from pymongo import MongoClient

# Step 1: Load Excel File
file_path = '01 Jan Activity Countin.xlsx'  # Update this with your file path
data = pd.read_excel(file_path)

# Step 2: Connect to MongoDB
mongodb_uri = "mongodb+srv://dionathan:Sad##13021991@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongodb_uri)

# Replace these with your database and collection names
db = client["real_estate"]  # Your database name
collection = db["listings"]  # Your collection name

# Step 3: Convert DataFrame to JSON and Insert into MongoDB
data.reset_index(inplace=True)  # Ensure the data has a clean index
records = data.to_dict('records')  # Convert to a list of dictionaries
collection.insert_many(records)  # Insert into MongoDB

print("Data successfully uploaded to MongoDB!")
