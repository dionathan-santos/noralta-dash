import pandas as pd
import boto3
from decimal import Decimal
import numpy as np

# Load the updated CSV file (Modify this path if needed)
file_path = "Complete_Reformatted_Broker_Data_JAN25.csv"

def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility, replacing NaN and Infinity with None."""
    if isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):  # Replace NaN and Infinity
            return None
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    else:
        return obj

def prepare_dynamodb_data(file_path):
    """Prepare data for DynamoDB, ensuring no NaN or Infinity values."""
    # Read updated CSV file
    df = pd.read_csv(file_path)

    # ✅ Ensure 'Broker' column is treated as a string (matching DynamoDB partition key)
    if 'Broker' in df.columns:
        df['Broker'] = df['Broker'].astype(str)
    else:
        raise ValueError("The required 'Broker' column is missing from the dataset!")

    # ✅ Ensure 'fim' column exists and is a string
    if 'firm' in df.columns:
        df['firm'] = df['firm'].astype(str)  # Convert 'fim' to string to prevent type conflicts

    # ✅ Replace NaN and Infinity values in the entire DataFrame
    df.replace([np.inf, -np.inf, np.nan], None, inplace=True)

    # ✅ Drop any rows where 'Broker' is missing (ensuring valid primary keys)
    df = df.dropna(subset=['Broker'])

    print(f"\nOriginal number of records: {len(df)}")  # Should reflect total valid records
    print("\nSample records:")
    print(df.head())

    return df

def upload_data_to_dynamodb(data, table_name):
    """Upload data to DynamoDB using batch writer."""
    try:
        dynamodb = boto3.resource("dynamodb")
        table = dynamodb.Table(table_name)

        # Use batch_writer for efficient uploads
        with table.batch_writer() as batch:
            for _, row in data.iterrows():
                item = row.to_dict()
                item = convert_floats_to_decimal(item)  # Ensure valid numeric values
                batch.put_item(Item=item)

        print(f"\nSuccessfully uploaded {len(data)} records to '{table_name}'")
    except Exception as e:
        print(f"\nFailed to upload data to DynamoDB: {e}")

def main():
    table_name = "brokerage"

    try:
        # Prepare the data
        data = prepare_dynamodb_data(file_path)

        print("\nPreview of formatted data:")
        print(data.head())

        # Confirm with user before uploading
        confirmation = input(f"\nPrepared {len(data)} records for upload. Do you want to proceed? (yes/no): ")

        if confirmation.lower() == 'yes':
            upload_data_to_dynamodb(data, table_name)
        else:
            print("Upload cancelled by user.")

    except Exception as e:
        print(f"Error processing data: {e}")

if __name__ == "__main__":
    main()
