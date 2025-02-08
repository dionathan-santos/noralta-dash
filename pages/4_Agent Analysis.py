import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from decimal import Decimal

# Set page title and layout
st.set_page_config(page_title="Agent Performance Dashboard", layout="wide")
st.title("Agent Performance Dashboard")

# Initialize AWS DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-2')
table = dynamodb.Table('real_estate_listings')

# Function to fetch data from DynamoDB
def get_dynamodb_data():
    """ Fetch all data from DynamoDB table and convert to Pandas DataFrame. """
    response = table.scan()  # Retrieve all records (consider pagination for large datasets)
    data = response.get('Items', [])
    return pd.DataFrame(data)

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

# Agent name filter (searchable dropdown)
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
all_agents_deals = (
    listings_data.groupby('listing_agent').size() +
    listings_data.groupby('buyer_agent').size()
).sort_values(ascending=False).reset_index(name='Total Deals')

# Rename the 'index' column to 'Agent Name'
all_agents_deals.rename(columns={'index': 'Agent Name'}, inplace=True)

# Add ranking column
all_agents_deals['Ranking'] = all_agents_deals.index + 1

# Sidebar filter for ranking-based search
st.sidebar.header("Ranking-Based Search")

# Add a searchable dropdown for agents by ranking
ranked_agents = all_agents_deals['Agent Name'].tolist()
selected_agent_by_rank = st.sidebar.selectbox(
    "Search Agent by Ranking",
    ranked_agents,
    index=ranked_agents.index(selected_agent) if selected_agent in ranked_agents else 0
)

# Update the selected agent if the user chooses from the ranking-based dropdown
selected_agent = selected_agent_by_rank

# Display the ranking of the selected agent
selected_agent_rank = all_agents_deals[all_agents_deals['Agent Name'] == selected_agent]['Ranking'].values[0]
st.sidebar.write(f"Ranking of {selected_agent}: {selected_agent_rank}")

# Filter data based on sidebar selections
def filter_data(data, start_date, end_date, selected_agent, selected_cities=None, selected_communities=None, selected_building_types=None):
    start_dt = pd.to_datetime(start_date).normalize()
    end_dt = pd.to_datetime(end_date).normalize()

    filtered_data = data[
        (data['sold_date'].dt.normalize() >= start_dt) &
        (data['sold_date'].dt.normalize() <= end_dt)
    ]

    # Filter by agent (both listing and buyer sides)
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

# Check if filtered data is empty
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Convert 'Sold Price' to numeric
filtered_data['sold_price'] = pd.to_numeric(filtered_data['sold_price'], errors='coerce')

# Calculate KPIs
total_deals = filtered_data.shape[0]
gross_sales = filtered_data['sold_price'].sum()
average_price_per_deal = gross_sales / total_deals if total_deals > 0 else 0

# Display KPIs
st.subheader(f"Performance Overview for {selected_agent.title()}")

col1, col2, col3 = st.columns(3)
col1.metric("Total Deals Closed", total_deals)
col2.metric("Total Gross Sales", f"${gross_sales:,.2f}")
col3.metric("Average Price Per Deal", f"${average_price_per_deal:,.2f}")

# Extract firms where the agent worked
listing_firms = filtered_data[filtered_data['listing_agent'] == selected_agent]['listing_firm'].dropna().unique()
buyer_firms = filtered_data[filtered_data['buyer_agent'] == selected_agent]['buyer_firm'].dropna().unique()

# Combine firms
all_firms = sorted(set(listing_firms) | set(buyer_firms))
firm_info = f"Firms: {', '.join(all_firms)}" if all_firms else "No firms found."

st.markdown(firm_info)

# Monthly Deals Line Chart
filtered_data['Month'] = filtered_data['sold_date'].dt.to_period('M').dt.to_timestamp()
monthly_deals = filtered_data.groupby('Month').size().reset_index(name='Deals')

fig_monthly_deals = px.line(
    monthly_deals, x='Month', y='Deals',
    title=f"Monthly Deals for {selected_agent.title()}",
    labels={'Month': 'Month', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_monthly_deals, use_container_width=True)

# Deals by Community Bar Chart
community_deals = filtered_data.groupby(['community', 'area_city']).size().reset_index(name='Deals')
fig_community_deals = px.bar(
    community_deals, x='community', y='Deals',
    title=f"Top Communities for {selected_agent.title()}",
    labels={'community': 'Community', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_community_deals, use_container_width=True)

# Deals by Building Type Bar Chart
building_type_deals = filtered_data.groupby('building_type').size().reset_index(name='Deals')
fig_building_type = px.bar(
    building_type_deals, x='building_type', y='Deals',
    title=f"Deals by Building Type for {selected_agent.title()}",
    labels={'building_type': 'Building Type', 'Deals': 'Number of Deals'}
)
st.plotly_chart(fig_building_type, use_container_width=True)

# Listing vs Buyer Side Distribution Pie Chart
listing_deals = filtered_data[filtered_data['listing_agent'] == selected_agent].shape[0]
buyer_deals = filtered_data[filtered_data['buyer_agent'] == selected_agent].shape[0]

side_distribution = pd.DataFrame({'Side': ['Listing', 'Buyer'], 'Deals': [listing_deals, buyer_deals]})
fig_side_distribution = px.pie(side_distribution, names='Side', values='Deals', title="Listing vs Buyer Side Distribution")
st.plotly_chart(fig_side_distribution, use_container_width=True)
