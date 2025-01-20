import streamlit as st
import pandas as pd
import plotly.express as px
from utils.data_utils import get_mongodb_data  # Assuming this utility exists for MongoDB data fetching

# Set page title and layout
st.set_page_config(page_title="Agent Performance Dashboard", layout="wide")
st.title("Agent Performance Dashboard")

def load_and_normalize_data(mongodb_uri, database_name):
    # Fetch listings data from MongoDB
    listings_data = get_mongodb_data(mongodb_uri, database_name, "listings")

    # Normalize agent and firm names
    for col in ['Listing Agent 1 - Agent Name', 'Buyer Agent 1 - Agent Name',
                'Listing Firm 1 - Office Name', 'Buyer Firm 1 - Office Name']:
        listings_data[col] = listings_data[col].str.lower().str.strip()

    # Convert 'Sold Date' to datetime
    listings_data['Sold Date'] = pd.to_datetime(listings_data['Sold Date'], errors='coerce')

    return listings_data

# MongoDB connection details
mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
database_name = "real_estate"

# Load data
listings_data = load_and_normalize_data(mongodb_uri, database_name)

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
all_agents = sorted(set(listings_data['Listing Agent 1 - Agent Name'].dropna().unique()) |
                    set(listings_data['Buyer Agent 1 - Agent Name'].dropna().unique()))
selected_agent = st.sidebar.selectbox("Select Agent", all_agents)

# Area/City filter
selected_cities = st.sidebar.multiselect("Select Area/City", sorted(listings_data['Area/City'].dropna().unique()))

# Community filter
selected_communities = st.sidebar.multiselect("Select Community", sorted(listings_data['Community'].dropna().unique()))

# Building type filter
selected_building_types = st.sidebar.multiselect("Select Building Type", sorted(listings_data['Building Type'].dropna().unique()))

def filter_data(data, start_date, end_date, selected_agent, selected_cities=None, selected_communities=None, selected_building_types=None):
    # Filter by date range
    filtered_data = data[(data['Sold Date'] >= pd.Timestamp(start_date)) &
                         (data['Sold Date'] <= pd.Timestamp(end_date))]

    # Filter by agent (both listing and buyer sides)
    filtered_data = filtered_data[
        (filtered_data['Listing Agent 1 - Agent Name'] == selected_agent) |
        (filtered_data['Buyer Agent 1 - Agent Name'] == selected_agent)
    ]

    # Apply additional filters
    if selected_cities:
        filtered_data = filtered_data[filtered_data['Area/City'].isin(selected_cities)]
    if selected_communities:
        filtered_data = filtered_data[filtered_data['Community'].isin(selected_communities)]
    if selected_building_types:
        filtered_data = filtered_data[filtered_data['Building Type'].isin(selected_building_types)]

    return filtered_data

# Apply filters
filtered_data = filter_data(listings_data, start_date, end_date, selected_agent, selected_cities, selected_communities, selected_building_types)

# Check if filtered data is empty
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Clean and convert 'Sold Price' to numeric
filtered_data['Sold Price'] = pd.to_numeric(
    filtered_data['Sold Price'].replace('[\$,]', '', regex=True),
    errors='coerce'  # Convert invalid values to NaN
)

# Check if 'Sold Price' contains NaN values
if filtered_data['Sold Price'].isna().all():
    st.error("No valid 'Sold Price' data found for the selected filters!")
    st.stop()

# Calculate total deals (listing + buyer)
total_deals = (
    filtered_data[filtered_data['Listing Agent 1 - Agent Name'] == selected_agent].shape[0] +
    filtered_data[filtered_data['Buyer Agent 1 - Agent Name'] == selected_agent].shape[0]
)

# Calculate gross sales
gross_sales = filtered_data['Sold Price'].sum()

# Calculate average price per deal
average_price_per_deal = gross_sales / total_deals if total_deals > 0 else 0

# Calculate market share
total_market_deals = listings_data[
    (listings_data['Sold Date'].notna()) &
    (listings_data['Sold Date'] >= pd.Timestamp(start_date)) &
    (listings_data['Sold Date'] <= pd.Timestamp(end_date))
].shape[0]
market_share = (total_deals / total_market_deals * 100) if total_market_deals > 0 else 0

# Calculate ranking (compared to other agents)
all_agents_deals = (
    listings_data.groupby('Listing Agent 1 - Agent Name').size() +
    listings_data.groupby('Buyer Agent 1 - Agent Name').size()
).sort_values(ascending=False)
agent_ranking = all_agents_deals.index.get_loc(selected_agent) + 1 if selected_agent in all_agents_deals.index else "N/A"

# Display KPIs
st.subheader(f"Performance Overview for {selected_agent.title()}")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Deals Closed", total_deals)
col2.metric("Total Gross Sales", f"${gross_sales:,.2f}")
col3.metric("Average Price Per Deal", f"${average_price_per_deal:,.2f}")
col4.metric("Market Share", f"{market_share:.2f}%")
col5.metric("Ranking", agent_ranking)

# Group by month and calculate deals
filtered_data['Month'] = filtered_data['Sold Date'].dt.to_period('M').dt.to_timestamp()
monthly_deals = filtered_data.groupby('Month').size().reset_index(name='Deals')

# Plot line chart
fig_monthly_deals = px.line(
    monthly_deals,
    x='Month',
    y='Deals',
    title=f"Monthly Deals for {selected_agent.title()}",
    labels={'Month': 'Month', 'Deals': 'Number of Deals'},
    hover_data={'Deals': ':.0f'}
)
fig_monthly_deals.update_traces(mode='lines+markers', marker=dict(size=8))
fig_monthly_deals.update_layout(
    xaxis=dict(tickangle=-45),
    margin=dict(b=120)
)
st.plotly_chart(fig_monthly_deals, use_container_width=True)

# Group by month and calculate gross sales
monthly_gross_sales = filtered_data.groupby('Month')['Sold Price'].sum().reset_index()

# Plot line chart
fig_gross_sales = px.line(
    monthly_gross_sales,
    x='Month',
    y='Sold Price',
    title=f"Monthly Gross Sales for {selected_agent.title()}",
    labels={'Month': 'Month', 'Sold Price': 'Gross Sales ($)'},
    hover_data={'Sold Price': ':.2f'}
)
fig_gross_sales.update_traces(mode='lines+markers', marker=dict(size=8))
fig_gross_sales.update_layout(
    xaxis=dict(tickangle=-45),
    margin=dict(b=120)
)
st.plotly_chart(fig_gross_sales, use_container_width=True)

# Group by community and calculate total deals
community_deals = filtered_data.groupby('Community').size().reset_index(name='Deals').sort_values(by='Deals', ascending=False).head(10)

# Plot bar chart for top 10 communities
fig_community_deals = px.bar(
    community_deals,
    x='Community',
    y='Deals',
    title=f"Top 10 Communities for {selected_agent.title()}",
    labels={'Community': 'Community', 'Deals': 'Number of Deals'},
    hover_data={'Deals': ':.0f'}
)
fig_community_deals.update_layout(
    xaxis=dict(tickangle=-45),
    margin=dict(b=120)
)
st.plotly_chart(fig_community_deals, use_container_width=True)


# Group by building type and calculate total deals
building_type_deals = filtered_data.groupby('Building Type').size().reset_index(name='Deals')

# Plot bar chart for building type
fig_building_type = px.bar(
    building_type_deals,
    x='Building Type',
    y='Deals',
    title=f"Deals by Building Type for {selected_agent.title()}",
    labels={'Building Type': 'Building Type', 'Deals': 'Number of Deals'},
    hover_data={'Deals': ':.0f'}
)
fig_building_type.update_layout(
    xaxis=dict(tickangle=-45),
    margin=dict(b=120)
)
st.plotly_chart(fig_building_type, use_container_width=True)


# Calculate deals for listing and buyer sides
listing_deals = filtered_data[filtered_data['Listing Agent 1 - Agent Name'] == selected_agent].shape[0]
buyer_deals = filtered_data[filtered_data['Buyer Agent 1 - Agent Name'] == selected_agent].shape[0]

# Create a DataFrame for the pie chart
side_distribution = pd.DataFrame({
    'Side': ['Listing', 'Buyer'],
    'Deals': [listing_deals, buyer_deals]
})

# Plot pie chart
fig_side_distribution = px.pie(
    side_distribution,
    names='Side',
    values='Deals',
    title=f"Listing vs Buyer Side Distribution for {selected_agent.title()}",
    hover_data={'Deals': ':.0f'}
)
st.plotly_chart(fig_side_distribution, use_container_width=True)
