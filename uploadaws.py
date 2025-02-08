import boto3
import pandas as pd
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

# Load CSV file
csv_file_path = "combined_data (2).csv"
df = pd.read_csv(csv_file_path)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table('real_estate_listings')

def safe_decimal(value):
    """ Convert values to Decimal while handling NaN and missing values. """
    try:
        if pd.isna(value) or value == "" or value is None:
            return Decimal("0")
        return Decimal(str(value).replace("$", "").replace(",", ""))
    except Exception as e:
        print(f"Error converting value to Decimal: {value} -> {e}")
        return Decimal("0")

def create_item(row):
    return {
        'listing_id_#': str(row['Listing ID #']),
        'sold_date': str(row.get('Sold Date', 'N/A')),
        'property_class': str(row['Property Class']) if not pd.isna(row['Property Class']) else 'N/A',
        'area_city': str(row['Area/City']) if not pd.isna(row['Area/City']) else 'N/A',
        'community': str(row['Community']) if not pd.isna(row['Community']) else 'N/A',
        'building_type': str(row['Building Type']) if not pd.isna(row['Building Type']) else 'N/A',
        'style': str(row['Style']) if not pd.isna(row['Style']) else 'N/A',
        'address': str(row['Address']) if not pd.isna(row['Address']) else 'N/A',
        'status': str(row['Status']) if not pd.isna(row['Status']) else 'N/A',
        'list_price': safe_decimal(row.get('List Price', '0')),
        'sold_price': safe_decimal(row.get('Sold Price', '0')),
        'total_bedrooms': safe_decimal(row.get('Total Bedrooms', '0')),
        'total_baths': safe_decimal(row.get('Total Baths', '0')),
        'year_built': safe_decimal(row.get('Year Built', '0')),
        'price_per_sqft': safe_decimal(row.get('Price Per SQFT', '0')),
        'listing_agent': str(row['Listing Agent 1 - Agent Name']) if not pd.isna(row['Listing Agent 1 - Agent Name']) else 'N/A',
        'buyer_agent': str(row['Buyer Agent 1 - Agent Name']) if not pd.isna(row['Buyer Agent 1 - Agent Name']) else 'N/A',
        'listing_firm': str(row['Listing Firm 1 - Office Name']) if not pd.isna(row['Listing Firm 1 - Office Name']) else 'N/A',
        'buyer_firm': str(row['Buyer Firm 1 - Office Name']) if not pd.isna(row['Buyer Firm 1 - Office Name']) else 'N/A',
    }

def batch_write_items(items):
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)

def upload_data():
    # Convert DataFrame to list of items
    items = [create_item(row) for _, row in df.iterrows()]
    
    # Split items into chunks of 25 (DynamoDB batch limit)
    chunk_size = 25
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    # Use ThreadPoolExecutor for parallel processing
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(batch_write_items, chunks)

    print("Data uploaded successfully!")

if __name__ == "__main__":
    upload_data()
