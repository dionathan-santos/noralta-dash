import boto3
import pandas as pd
import streamlit as st
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime

def get_aws_credentials():
    """Retrieves AWS credentials from Streamlit secrets."""
    try:
        aws_secrets = st.secrets["aws"]
        return (
            aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secrets["AWS_SECRET_ACCESS_KEY"],
            aws_secrets.get("AWS_REGION", "us-east-2")
        )
    except KeyError:
        st.error("AWS credentials are missing. Check Streamlit secrets configuration.")
        return None, None, None

def get_dynamodb_data(table_name, start_date=None, end_date=None):
    """
    Fetch data from DynamoDB with optional date filtering.
    
    Args:
        table_name (str): Name of the DynamoDB table
        start_date (datetime, optional): Start date for filtering
        end_date (datetime, optional): End date for filtering
    
    Returns:
        pd.DataFrame: Filtered and processed data
    """
    aws_access_key, aws_secret_key, aws_region = get_aws_credentials()
    if not aws_access_key or not aws_secret_key:
        return pd.DataFrame()

    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        table = dynamodb.Table(table_name)

        # Base scan parameters
        scan_params = {}

        # Add date filtering if dates are provided
        if start_date and end_date:
            scan_params['FilterExpression'] = (
                Key('sold_date').between(
                    start_date.strftime('%Y-%m-%d'), 
                    end_date.strftime('%Y-%m-%d')
                )
            )

        # Perform scan
        response = table.scan(**scan_params)
        items = response.get('Items', [])

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            scan_params['ExclusiveStartKey'] = response['LastEvaluatedKey']
            response = table.scan(**scan_params)
            items.extend(response.get('Items', []))

        # Convert to DataFrame
        df = pd.DataFrame(items)

        # Rename columns to match original MongoDB schema
        column_mapping = {
            'sold_date': 'Sold Date',
            'listing_agent': 'Listing Agent 1 - Agent Name',
            'buyer_agent': 'Buyer Agent 1 - Agent Name',
            'listing_firm': 'Listing Firm 1 - Office Name',
            'buyer_firm': 'Buyer Firm 1 - Office Name',
            'area_city': 'Area/City',
            'community': 'Community',
            'building_type': 'Building Type',
            'sold_price': 'Sold Price'
        }
        df.rename(columns=column_mapping, inplace=True)

        # Convert dates and prices
        df['Sold Date'] = pd.to_datetime(df['Sold Date'], errors='coerce')
        df['Sold Price'] = pd.to_numeric(df['Sold Price'], errors='coerce')

        return df

    except Exception as e:
        st.error(f"DynamoDB Query Error: {str(e)}")
        return pd.DataFrame()

def get_mongodb_data(mongodb_uri, database_name, collection_name, start_date=None, end_date=None):
    """
    Wrapper function to maintain compatibility with existing code.
    Redirects to DynamoDB data retrieval.
    """
    # Map collection names to DynamoDB table names if needed
    table_map = {
        'listings': 'real_estate_listings',
        'brokerage': 'brokerage_data'
    }
    
    table_name = table_map.get(collection_name, collection_name)
    
    return get_dynamodb_data(table_name, start_date, end_date)