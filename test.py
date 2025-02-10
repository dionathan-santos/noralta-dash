import boto3

# Initialize DynamoDB client
dynamodb = boto3.client('dynamodb', region_name='us-east-2')  # Replace with your AWS region

# List all tables
tables = dynamodb.list_tables()['TableNames']

# Function to get full schema of a table
def get_full_schema(table_name):
    # Get table description
    table_description = dynamodb.describe_table(TableName=table_name)
    
    # Extract primary key attributes
    key_attributes = {attr['AttributeName']: attr['AttributeType'] for attr in table_description['Table']['AttributeDefinitions']}
    
    # Scan a small portion of the table to detect additional attributes
    try:
        scan_response = dynamodb.scan(TableName=table_name, Limit=10)  # Scan a few records
    except Exception as e:
        print(f"Error scanning table {table_name}: {e}")
        return

    # Extract non-key attributes
    all_attributes = key_attributes.copy()  # Start with known key attributes
    
    for item in scan_response.get('Items', []):
        for key, value in item.items():
            if key not in all_attributes:
                # Determine type from DynamoDB JSON format
                dtype = list(value.keys())[0]  # Extract type (e.g., 'S', 'N', 'BOOL')
                all_attributes[key] = dtype

    # Print schema
    print(f"\nSchema for table: {table_name}")
    for column, dtype in all_attributes.items():
        print(f"Column: {column}, Type: {dtype}")
    print("-" * 40)

# Loop through tables and print full schema
for table in tables:
    get_full_schema(table)
