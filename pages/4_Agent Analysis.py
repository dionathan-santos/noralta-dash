import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import os

# Set page title and layout
st.set_page_config(page_title="Agent Performance Dashboard", layout="wide")
st.title("Agent Performance Dashboard")

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
def fetch_dynamodb_data(table_name):
    """Generic function to fetch data from any DynamoDB table"""
    aws_access_key, aws_secret_key, aws_region = get_aws_credentials()

    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        table = dynamodb.Table(table_name)
        response = table.scan()
        items = response['Items']

        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            items.extend(response['Items'])

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"Error accessing {table_name}: {str(e)}")
        return pd.DataFrame()


# Load data from both tables
listings_data = fetch_dynamodb_data("real_estate_listings")
brokerage_data = fetch_dynamodb_data("brokerage")

# Check both datasets
if listings_data.empty or brokerage_data.empty:
    st.error("Missing required data!")
    st.stop()

# Convert 'sold_date' to datetime format
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Sidebar filters
st.sidebar.header("Filters")

start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

all_agents = sorted(set(listings_data["listing_agent"].dropna().unique()) | set(listings_data["buyer_agent"].dropna().unique()))
selected_agent = st.sidebar.selectbox("Select Agent", all_agents)

selected_cities = st.sidebar.multiselect("Select Area/City", sorted(listings_data["area_city"].dropna().unique()))
selected_communities = st.sidebar.multiselect("Select Community", sorted(listings_data["community"].dropna().unique()))
selected_building_types = st.sidebar.multiselect("Select Building Type", sorted(listings_data["building_type"].dropna().unique()))

# Calculate rankings for all agents (based on total deals)
all_agents_deals = listings_data["listing_agent"].value_counts().add(
    listings_data["buyer_agent"].value_counts(), fill_value=0
).reset_index()
all_agents_deals.columns = ["Agent Name", "Total Deals"]
all_agents_deals["Ranking"] = all_agents_deals["Total Deals"].rank(method="dense", ascending=False).astype(int)

# Ranking-based search
st.sidebar.header("Ranking-Based Search")
ranked_agents = all_agents_deals["Agent Name"].tolist()
selected_agent_by_rank = st.sidebar.selectbox("Search Agent by Ranking", ranked_agents)

selected_agent = selected_agent_by_rank  # Override selection with ranking choice

# Display agent ranking
selected_agent_rank = all_agents_deals.loc[all_agents_deals["Agent Name"] == selected_agent, "Ranking"].values
if len(selected_agent_rank) > 0:
    st.sidebar.write(f"Ranking of {selected_agent}: {selected_agent_rank[0]}")

# **Optimized Filtering with Pandas Query**
query_str = f"(sold_date >= '{start_date}') & (sold_date <= '{end_date}')"
query_str += f" & ((listing_agent == '{selected_agent}') | (buyer_agent == '{selected_agent}'))"

if selected_cities:
    query_str += f" & (area_city in {selected_cities})"
if selected_communities:
    query_str += f" & (community in {selected_communities})"
if selected_building_types:
    query_str += f" & (building_type in {selected_building_types})"

filtered_data = listings_data.query(query_str) if query_str else listings_data

# Check if data is empty after filtering
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Convert 'sold_price' to numeric
filtered_data["sold_price"] = pd.to_numeric(filtered_data["sold_price"], errors="coerce")

# Calculate KPIs
total_deals = filtered_data.shape[0]
gross_sales = filtered_data["sold_price"].sum()
average_price_per_deal = gross_sales / total_deals if total_deals > 0 else 0

# Display KPIs
st.subheader(f"Performance Overview for {selected_agent}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Deals Closed", total_deals)
col2.metric("Total Gross Sales", f"${gross_sales:,.2f}")
col3.metric("Average Price Per Deal", f"${average_price_per_deal:,.2f}")

# Extract firms where the agent worked
listing_firms = filtered_data[filtered_data["listing_agent"] == selected_agent]["listing_firm"].dropna().unique()
buyer_firms = filtered_data[filtered_data["buyer_agent"] == selected_agent]["buyer_firm"].dropna().unique()
all_firms = sorted(set(listing_firms) | set(buyer_firms))
st.markdown(f"Firms: {', '.join(all_firms)}" if all_firms else "No firms found.")

# Monthly Deals Line Chart
filtered_data["Month"] = filtered_data["sold_date"].dt.to_period("M").dt.to_timestamp()
monthly_deals = filtered_data.groupby("Month").size().reset_index(name="Deals")

fig_monthly_deals = px.line(
    monthly_deals, x="Month", y="Deals",
    title=f"Monthly Deals for {selected_agent}",
    labels={"Month": "Month", "Deals": "Number of Deals"}
)
st.plotly_chart(fig_monthly_deals, use_container_width=True)

# Deals by Community Bar Chart
community_deals = filtered_data.groupby(["community", "area_city"]).size().reset_index(name="Deals")
fig_community_deals = px.bar(
    community_deals, x="community", y="Deals",
    title=f"Top Communities for {selected_agent}",
    labels={"community": "Community", "Deals": "Number of Deals"}
)
st.plotly_chart(fig_community_deals, use_container_width=True)
