import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
import os
from decimal import Decimal

# Set page title and layout
st.set_page_config(page_title="Agent Performance Dashboard", layout="wide")
st.title("Agent Performance Dashboard")

# Load AWS credentials securely from Streamlit secrets
aws_access_key = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
aws_region = st.secrets.get("AWS_REGION", "us-east-2")

# Initialize AWS DynamoDB with secure credentials
dynamodb = boto3.resource(
    'dynamodb',
    region_name=aws_region,
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key
)

table = dynamodb.Table('real_estate_listings')

# Function to fetch all data from DynamoDB
def get_dynamodb_data():
    """ Fetch data from DynamoDB and convert to Pandas DataFrame. """
    items = []
    last_evaluated_key = None

    # Handle pagination for large datasets
    while True:
        if last_evaluated_key:
            response = table.scan(ExclusiveStartKey=last_evaluated_key)
        else:
            response = table.scan()

        items.extend(response.get('Items', []))
        last_evaluated_key = response.get('LastEvaluatedKey')

        if not last_evaluated_key:
            break

    return pd.DataFrame(items)

# Load data from AWS DynamoDB
listings_data = get_dynamodb_data()

# Convert Sold Date to datetime format
if not listings_data.empty:
    listings_data['sold_date'] = pd.to_datetime(
        listings_data['sold_date'], errors='coerce'
    ).dt.normalize()

# Check if data is loaded
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Sidebar filters
st.sidebar.header("Filters")

# Date range filter
start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

# Agent name filter
all_agents = sorted(set(listings_data['listing_agent'].dropna().unique()) |
                    set(listings_data['buyer_agent'].dropna().unique()))
selected_agent = st.sidebar.selectbox("Select Agent", all_agents)

# Area/City filter
selected_cities = st.sidebar.multiselect("Select Area/City", sorted(listings_data['area_city'].dropna().unique()))

# Community filter
selected_communities = st.sidebar.multiselect("Select Community", sorted(listings_data['community'].dropna().unique()))

# Building type filter
selected_building_types = st.sidebar.multiselect("Select Building Type", sorted(listings_data['building_type'].dropna().unique()))

# Calculate rankings for all agents (based on total deals)
all_agents_deals = listings_data['listing_agent'].value_counts().add(
    listings_data['buyer_agent'].value_counts(), fill_value=0
).reset_index()
all_agents_deals.columns = ['Agent Name', 'Total Deals']
all_agents_deals = all_agents_deals.sort_values(by='Total Deals', ascending=False).reset_index(drop=True)
all_agents_deals['Ranking'] = all_agents_deals.index + 1

# Sidebar filter for ranking-based search
st.sidebar.header("Ranking-Based Search")
ranked_agents = all_agents_deals['Agent Name'].tolist()
selected_agent_by_rank = st.sidebar.selectbox(
    "Search Agent by Ranking", ranked_agents,
    index=ranked_agents.index(selected_agent) if selected_agent in ranked_agents else 0
)

# Update selected agent if changed via ranking dropdown
selected_agent = selected_agent_by_rank

# Display agent ranking
selected_agent_rank = all_agents_deals.loc[all_agents_deals['Agent Name'] == selected_agent, 'Ranking'].values
if len(selected_agent_rank) > 0:
    st.sidebar.write(f"Ranking of {selected_agent}: {selected_agent_rank[0]}")

# Function to filter data
def filter_data(data, start_date, end_date, selected_agent, selected_cities, selected_communities, selected_building_types):
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()

    filtered_data = data[
        (data['sold_date'].dt.normalize() >= start_dt) &
        (data['sold_date'].dt.normalize() <= end_dt)
    ]

    # Filter by agent (listing or buyer)
    filtered_data = filtered_data[
        (filtered_data['listing_agent'] == selected_agent) |
        (filtered_data['buyer_agent'] == selected_agent)
    ]

    # Apply additional filters
    if selected_cities:
        filtered_data = filtered_data[filtered_data['area_city'].isin(selected_cities)]
    if selected_communities:
        filtered_data = filtered_data[filtered_data['community'].isin(selected_communities)]
    if selected_building_types:
        filtered_data = filtered_data[filtered_data['building_type'].isin(selected_building_types)]

    return filtered_data

# Apply filters
filtered_data = filter_data(listings_data, start_date, end_date, selected_agent, selected_cities, selected_communities, selected_building_types)

# Check if data is empty after filtering
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Convert 'sold_price' to numeric
filtered_data['sold_price'] = pd.to_numeric(filtered_data['sold_price'], errors='coerce')

# Calculate KPIs
total_deals = filtered_data.shape[0]
gross_sales = filtered_data['sold_price'].sum()
average_price_per_deal = gross_sales / total_deals if total_deals > 0 else 0

# Display KPIs
st.subheader(f"Performance Overview for {selected_agent}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Deals Closed", total_deals)
col2.metric("Total Gross Sales", f"${gross_sales:,.2f}")
col3.metric("Average Price Per Deal", f"${average_price_per_deal:,.2f}")

# Extract firms where the agent worked
listing_firms = filtered_data[filtered_data['listing_agent'] == selected_agent]['listing_firm'].dropna().unique()
buyer_firms = filtered_data[filtered_data['buyer_agent'] == selected_agent]['buyer_firm'].dropna().unique()
all_firms = sorted(set(listing_firms) | set(buyer_firms))
st.markdown(f"Firms: {', '.join(all_firms)}" if all_firms else "No firms found.")

# Monthly Deals Line Chart
filtered_data['Month'] = filtered_data['sold_date'].dt.to_period('M').dt.to_timestamp()
monthly_deals = filtered_data.groupby('Month').size().reset_index(name='Deals')

fig_monthly_deals = px.line(
    monthly_deals, x='Month', y='Deals',
    title=f"Monthly Deals for {selected_agent}",
    labels={'Month': 'Month', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_monthly_deals, use_container_width=True)

# Deals by Community Bar Chart
community_deals = filtered_data.groupby(['community', 'area_city']).size().reset_index(name='Deals')
fig_community_deals = px.bar(
    community_deals, x='community', y='Deals',
    title=f"Top Communities for {selected_agent}",
    labels={'community': 'Community', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_community_deals, use_container_width=True)

# Deals by Building Type Bar Chart
building_type_deals = filtered_data.groupby('building_type').size().reset_index(name='Deals')
fig_building_type = px.bar(
    building_type_deals, x='building_type', y='Deals',
    title=f"Deals by Building Type for {selected_agent}",
    labels={'building_type': 'Building Type', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_building_type, use_container_width=True)
