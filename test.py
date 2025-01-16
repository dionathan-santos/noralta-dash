from pymongo import MongoClient

# MongoDB connection details
mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
database_name = "real_estate"
collection_name = "listings"  # Replace with your actual collection name

def test_mongo_connection():
    try:
        # Connect to MongoDB
        print("Connecting to MongoDB...")
        client = MongoClient(mongodb_uri, serverSelectionTimeoutMS=5000)
        print("Connection successful!")

        # Access the database
        db = client[database_name]
        print(f"Accessed database: {database_name}")

        # Access the collection
        collection = db[collection_name]
        print(f"Accessed collection: {collection_name}")

        # Fetch some documents
        print("Fetching documents...")
        documents = list(collection.find().limit(5))  # Fetch 5 documents
        for idx, doc in enumerate(documents, 1):
            print(f"Document {idx}: {doc}")

        # Close the connection
        client.close()
        print("Connection closed successfully!")

    except Exception as e:
        print(f"An error occurred: {e}")

# Run the test
if __name__ == "__main__":
    test_mongo_connection()
