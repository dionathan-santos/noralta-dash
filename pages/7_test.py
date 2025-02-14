import streamlit as st
import pandas as pd
import boto3

# Set page title and layout
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Function to retrieve AWS credentials from Streamlit secrets
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
        st.error("AWS credentials missing. Check Streamlit secrets.")
        return None, None, None

# Retrieve AWS credentials
aws_key, aws_secret, region = get_aws_credentials()
if aws_key is None:
    st.stop()

# Create DynamoDB resource
dynamodb = boto3.resource(
    "dynamodb",
    aws_access_key_id=aws_key,
    aws_secret_access_key=aws_secret,
    region_name=region
)

# Function to scan a DynamoDB table and return a DataFrame
def scan_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        data = response.get('Items', [])
        # Handle pagination in case of large tables
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response.get('Items', []))
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error scanning table '{table_name}': {e}")
        return pd.DataFrame()

# Retrieve data from the DynamoDB tables
df_real_estate = scan_table("real_estate_listings")
df_brokerage = scan_table("brokerage")

# Display the dataframes in the Streamlit app
st.subheader("Real Estate Listings")
st.dataframe(df_real_estate)

st.subheader("Brokerage Data")
st.dataframe(df_brokerage)
