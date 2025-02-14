import streamlit as st
import pandas as pd
import boto3
import time

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

# Function to run an Athena query and convert the results into a DataFrame
def run_athena_query(query, database, output_location, aws_key, aws_secret, region):
    client = boto3.client(
        'athena',
        aws_access_key_id=aws_key,
        aws_secret_access_key=aws_secret,
        region_name=region
    )
    try:
        response = client.start_query_execution(
            QueryString=query,
            QueryExecutionContext={'Database': database},
            ResultConfiguration={'OutputLocation': output_location}
        )
    except Exception as e:
        st.error(f"Error starting Athena query: {e}")
        return pd.DataFrame()  # Return an empty DataFrame on failure

    execution_id = response['QueryExecutionId']

    # Wait until the query succeeds
    while True:
        execution = client.get_query_execution(QueryExecutionId=execution_id)
        state = execution['QueryExecution']['Status']['State']
        if state in ['SUCCEEDED', 'FAILED', 'CANCELLED']:
            break
        time.sleep(1)

    if state != 'SUCCEEDED':
        st.error(f"Query failed with state: {state}")
        return pd.DataFrame()  # return an empty dataframe on failure

    result = client.get_query_results(QueryExecutionId=execution_id)
    
    # Extract column names
    column_info = result['ResultSet']['ResultSetMetadata']['ColumnInfo']
    columns = [col['Label'] for col in column_info]
    
    # Skip the header row and parse the rest of the rows
    rows = []
    for row in result['ResultSet']['Rows'][1:]:
        rows.append([col.get('VarCharValue', None) for col in row['Data']])
    
    return pd.DataFrame(rows, columns=columns)

# Retrieve AWS credentials
aws_key, aws_secret, region = get_aws_credentials()
if aws_key is None:
    st.stop()

# Athena configuration (update with your actual database and S3 bucket details)
database = "your_database_name"          # Replace with your Athena database name
output_location = "s3://your-bucket/path/" # Replace with your S3 bucket/folder for query results

# Define queries for each table
query_real_estate = "SELECT * FROM real_estate_listings"
query_brokerage = "SELECT * FROM brokerage"

# Get data as DataFrames
df_real_estate = run_athena_query(query_real_estate, database, output_location, aws_key, aws_secret, region)
df_brokerage = run_athena_query(query_brokerage, database, output_location, aws_key, aws_secret, region)

# Display the data in the Streamlit app
st.subheader("Real Estate Listings")
st.dataframe(df_real_estate)

st.subheader("Brokerage Data")
st.dataframe(df_brokerage)
