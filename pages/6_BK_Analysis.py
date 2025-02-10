import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

# Set page title and layout
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Function to retrieve AWS credentials from Streamlit secrets
def get_aws_credentials():
    """Retrieves AWS credentials from Streamlit secrets."""
    try:
        aws_secrets = st.secrets["aws"]  # Get the entire 'aws' dictionary
        return (
            aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secrets["AWS_SECRET_ACCESS_KEY"],
            aws_secrets.get("AWS_REGION", "us-east-2")  # Default to us-east-2 if not set
        )
    except KeyError:
        st.error("AWS credentials are missing. Check Streamlit secrets configuration.")
        return None, None, None

# Function to fetch data from DynamoDB
@st.cache_data
def get_dynamodb_data():
    """Fetch data from DynamoDB and convert it to a Pandas DataFrame."""
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
        table = dynamodb.Table("real_estate_listings")

        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"Failed to fetch data from DynamoDB: {str(e)}")
        return pd.DataFrame()

# Load data from AWS DynamoDB
listings_data = get_dynamodb_data()

# Ensure data is loaded
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Convert 'sold_date' to datetime format
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Sidebar filters
st.sidebar.header("Filters")

start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

selected_cities = st.sidebar.multiselect("Select Cities", sorted(listings_data["area_city"].dropna().unique()))
selected_communities = st.sidebar.multiselect("Select Communities", sorted(listings_data["community"].dropna().unique()))
selected_building_types = st.sidebar.multiselect("Select Building Types", sorted(listings_data["building_type"].dropna().unique()))
selected_firms = st.sidebar.multiselect("Select Brokerage Firms", sorted(listings_data["listing_firm"].dropna().unique()))

# **Optimized Filtering with Pandas Query**
query_str = f"(sold_date >= '{start_date}') & (sold_date <= '{end_date}')"

if selected_cities:
    query_str += f" & (area_city in {selected_cities})"
if selected_communities:
    query_str += f" & (community in {selected_communities})"
if selected_building_types:
    query_str += f" & (building_type in {selected_building_types})"
if selected_firms:
    query_str += f" & (listing_firm in {selected_firms})"

filtered_data = listings_data.query(query_str) if query_str else listings_data

# Check if data is empty after filtering
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Top 10 Brokerages with Most Deals
brokerage_deals = filtered_data["listing_firm"].value_counts().reset_index()
brokerage_deals.columns = ["Brokerage", "Number of Deals"]

# Display KPIs
st.subheader("Brokerage Performance Summary")

col1, col2 = st.columns(2)
col1.metric("Total Deals in Period", filtered_data.shape[0])
col2.metric("Total Brokerages Involved", brokerage_deals.shape[0])


###################   TOP 10 LINSTING FIRMS ####################

# Plot Bar Chart for Top 10 Brokerages
st.subheader("Linsting Side - Top 10 Brokerages with Most Deals")
if not brokerage_deals.empty:
    fig = px.bar(
        brokerage_deals.head(10),
        x="Brokerage",
        y="Number of Deals",
        title="Top 10 Brokerages by Deals",
        labels={"Number of Deals": "Number of Properties Sold"},
        text_auto=True
    )
    st.plotly_chart(fig)
else:
    st.warning("No data available for the selected filters.")



###################   TOP 10 BUYER FIRMS ####################


# Top 10 Buyer Brokerages with Most Deals
buyer_brokerage_deals = filtered_data["buyer_firm"].value_counts().reset_index()
buyer_brokerage_deals.columns = ["Buyer Brokerage", "Number of Deals"]

# Display Chart for Buyer Brokerages
st.subheader("Top 10 Buyer Brokerages with Most Deals")
if not buyer_brokerage_deals.empty:
    fig_buyer = px.bar(
        buyer_brokerage_deals.head(10),
        x="Buyer Brokerage",
        y="Number of Deals",
        title="Top 10 Buyer Brokerages by Deals",
        labels={"Number of Deals": "Number of Properties Purchased"},
        text_auto=True
    )
    st.plotly_chart(fig_buyer)
else:
    st.warning("No data available for the selected filters.")


###################   TOP 10 COMBINED BUYER & LISTING FIRMS ####################

# Combine Listing and Buyer Firm Deals
combined_brokerage_deals = (
    filtered_data["listing_firm"].value_counts()
    .add(filtered_data["buyer_firm"].value_counts(), fill_value=0)
    .reset_index()
)
combined_brokerage_deals.columns = ["Brokerage", "Total Deals"]

# Display Chart for Combined Brokerages
st.subheader("Top 10 Brokerages (Buyer & Listing Combined)")
if not combined_brokerage_deals.empty:
    fig_combined = px.bar(
        combined_brokerage_deals.head(10),
        x="Brokerage",
        y="Total Deals",
        title="Top 10 Brokerages by Total Deals (Buyer & Listing)",
        labels={"Total Deals": "Number of Transactions"},
        text_auto=True
    )
    st.plotly_chart(fig_combined)
else:
    st.warning("No data available for the selected filters.")
