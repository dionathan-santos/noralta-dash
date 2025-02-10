import boto3
import json
from decimal import Decimal

# Set AWS region
aws_region = "us-east-2"

# Initialize DynamoDB resource
dynamodb = boto3.resource("dynamodb", region_name=aws_region)

# Reference the 'brokerage' table
table = dynamodb.Table("brokerage")

# Function to scan and retrieve all items from the table
def fetch_brokerage_data():
    """Fetch all records from the 'brokerage' table and convert Decimals to float/int."""
    try:
        items = []
        last_evaluated_key = None

        while True:
            if last_evaluated_key:
                response = table.scan(ExclusiveStartKey=last_evaluated_key)
            else:
                response = table.scan()

            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")

            if not last_evaluated_key:
                break

        return items

    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

# Helper function to convert Decimal to int/float
def convert_decimals(obj):
    """Recursively converts Decimal objects to int or float."""
    if isinstance(obj, list):
        return [convert_decimals(i) for i in obj]
    elif isinstance(obj, dict):
        return {k: convert_decimals(v) for k, v in obj.items()}
    elif isinstance(obj, Decimal):
        return int(obj) if obj % 1 == 0 else float(obj)
    return obj

# Fetch and print the data
brokerage_data = fetch_brokerage_data()

if brokerage_data:
    converted_data = convert_decimals(brokerage_data)  # Convert Decimal values
    print(json.dumps(converted_data, indent=4))  # Pretty-print the results
else:
    print("No data found or an error occurred.")
