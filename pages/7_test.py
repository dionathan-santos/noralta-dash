import streamlit as st
import pandas as pd
import boto3

# Set page title and layout
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Retrieve AWS credentials from Streamlit secrets
try:
    aws_secrets = st.secrets["aws"]
    AWS_ACCESS_KEY_ID = aws_secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = aws_secrets["AWS_SECRET_ACCESS_KEY"]
    AWS_REGION = aws_secrets.get("AWS_REGION", "us-east-2")
except Exception as e:
    st.error("Erro ao recuperar as credenciais AWS dos secrets.")
    st.stop()

# Configure the DynamoDB resource
dynamodb = boto3.resource(
    'dynamodb',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# List of DynamoDB tables to scan
table_names = ['brokerage', 'real_estate_listings']

# Dictionary to store DataFrames
dataframes = {}

# Function to scan a DynamoDB table and return its items
def scan_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        data = response.get('Items', [])
        
        # Continue scanning if there are more items
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response.get('Items', []))
            
        return data
    except Exception as e:
        st.error(f"Erro ao escanear a tabela '{table_name}': {e}")
        return []

# Create a DataFrame for each table and store them in the dictionary
for table_name in table_names:
    data = scan_table(table_name)
    if data:
        df = pd.DataFrame(data)
        dataframes[table_name] = df
        st.write(f"Dataframe criado para a tabela: {table_name}")
        st.write(df.head())  # Display the first few rows of the DataFrame
    else:
        st.write(f"Não foi possível criar o dataframe para a tabela: {table_name}")

# Assign the DataFrames to individual variables (defaulting to empty DataFrames if missing)
brokerage_df = dataframes.get('brokerage', pd.DataFrame())
real_estate_listings_df = dataframes.get('real_estate_listings', pd.DataFrame())

# Optionally, display the complete DataFrames in your Streamlit app
st.subheader("Dados completos - Brokerage")
st.dataframe(brokerage_df)

st.subheader("Dados completos - Real Estate Listings")
st.dataframe(real_estate_listings_df)
