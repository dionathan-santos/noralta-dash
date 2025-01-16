import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import seaborn as sns
from pymongo import MongoClient
import numpy as np
from utils.data_utils import get_mongodb_data, filter_data

def get_mongodb_data(mongodb_uri, database_name, collection_name):
    """
    Retrieve data from MongoDB and return as a pandas DataFrame
    """
    try:
        # Create a MongoDB client
        client = MongoClient(mongodb_uri)

        # Get the database
        db = client[database_name]

        # Get the collection
        collection = db[collection_name]

        # Retrieve all documents from the collection
        data = list(collection.find({}, {'_id': 0}))  # Exclude MongoDB _id field

        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Close the connection
        client.close()

        if df.empty:
            st.error("No data retrieved from MongoDB")

        return df

    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("Noralta Analysis")
    st.write("Detailed analysis specific to Noralta.")

    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"
    collection_name = "listings"

    # Fetch data
    data = get_mongodb_data(mongodb_uri, database_name, collection_name)
    if data.empty:
        st.error("No data available!")
        return

    # Data preprocessing
    data['Sold Date'] = pd.to_datetime(data['Sold Date'])
    data['Sold Price'] = data['Sold Price'].str.replace('$', '').str.replace(',', '').astype(float)
    data['List Price'] = data['List Price'].str.replace('$', '').str.replace(',', '').astype(float)
    data['Total Flr Area (SF)'] = data['Total Flr Area (SF)'].str.replace(',', '').astype(float)

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Date Range
    min_date = data['Sold Date'].min()
    max_date = data['Sold Date'].max()
    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)
    start_date = st.sidebar.date_input("Start Date", value=default_start, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=default_end, min_value=min_date, max_value=max_date)

    # Agent-Specific
    all_agents = sorted(set(data['Listing Agent 1 - Agent Name'].dropna().unique()) | set(data['Buyer Agent 1 - Agent Name'].dropna().unique()))
    selected_agents = st.sidebar.multiselect("Select Agents", all_agents)

    # Area/City
    cities = sorted(data['Area/City'].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select Cities", cities)

    # Community
    communities = sorted(data['Community'].dropna().unique())
    selected_communities = st.sidebar.multiselect("Select Communities", communities)

    # Property Type
    property_types = sorted(data['Property Class'].dropna().unique())
    selected_property_types = st.sidebar.multiselect("Select Property Types", property_types)

    # Building Type
    building_types = sorted(data['Building Type'].dropna().unique())
    selected_building_types = st.sidebar.multiselect("Select Building Types", building_types)

    # Transaction Type
    transaction_types = ['Listing Firm', 'Buyer Firm', 'Dual Representation']
    selected_transaction_type = st.sidebar.selectbox("Select Transaction Type", transaction_types)

    # Price Range
    max_price = int(data['Sold Price'].max())
    price_range = st.sidebar.text_input("Price Range (format: min-max)", f"0-{max_price}")
    try:
        min_price, max_price = map(int, price_range.split('-'))
    except:
        min_price, max_price = 0, data['Sold Price'].max()

    # Year Built
    years = sorted(data['Year Built'].dropna().unique())
    selected_years = st.sidebar.multiselect("Select Years Built", years)

    # Days on Market (DOM)
    max_dom = int(data['Days On Market'].max())
    dom_range = st.sidebar.slider("Days on Market", 0, max_dom, (0, max_dom))

    # Apply filters
    mask = (
        (data['Sold Date'].dt.date >= start_date) &
        (data['Sold Date'].dt.date <= end_date) &
        (data['Sold Price'].between(min_price, max_price)) &
        (data['Days On Market'].between(dom_range[0], dom_range[1])) &
        (data['Year Built'].isin(selected_years) if selected_years else True) &
        (data['Property Class'].isin(selected_property_types) if selected_property_types else True) &
        (data['Building Type'].isin(selected_building_types) if selected_building_types else True) &
        (data['Community'].isin(selected_communities) if selected_communities else True) &
        (data['Area/City'].isin(selected_cities) if selected_cities else True)
    )

    if selected_agents:
        mask &= (
            (data['Listing Agent 1 - Agent Name'].isin(selected_agents)) |
            (data['Buyer Agent 1 - Agent Name'].isin(selected_agents))
        )

    if selected_transaction_type == 'Listing Firm':
        mask &= data['Listing Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Buyer Firm':
        mask &= data['Buyer Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Dual Representation':
        mask &= (data['Listing Firm 1 - Office Name'] == data['Buyer Firm 1 - Office Name'])

    filtered_data = data[mask]

    # Filter for Noralta
    noralta_data = filtered_data[
        (filtered_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate') |
        (filtered_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate')
    ]

    # Filter data for Royal LePage Noralta Real Estate
    noralta_data_date_filtered = noralta_data[
        (noralta_data['Sold Date'].dt.date >= start_date) & (noralta_data['Sold Date'].dt.date <= end_date)
    ]

    # Calculate deals from both Listing and Buyer sides
    listing_deals = noralta_data_date_filtered.groupby('Listing Agent 1 - Agent Name').size().reset_index(name='Total Deals')
    buyer_deals = noralta_data_date_filtered.groupby('Buyer Agent 1 - Agent Name').size().reset_index(name='Total Deals')

    # Rename columns for consistency
    listing_deals = listing_deals.rename(columns={'Listing Agent 1 - Agent Name': 'Agent Name'})
    buyer_deals = buyer_deals.rename(columns={'Buyer Agent 1 - Agent Name': 'Agent Name'})

    # Calculate total deals and ranks
    listing_deals['Rank'] = listing_deals['Total Deals'].rank(method='dense', ascending=False).astype(int)
    buyer_deals['Rank'] = buyer_deals['Total Deals'].rank(method='dense', ascending=False).astype(int)

    # Calculate top 5 agents for listings and buyers
    top_listings_agents = listing_deals.nlargest(5, 'Total Deals')[['Agent Name', 'Total Deals', 'Rank']]
    top_buyers_agents = buyer_deals.nlargest(5, 'Total Deals')[['Agent Name', 'Total Deals', 'Rank']]

    # Display tables
    st.write("")  # Add a blank line for better readability
    col1, col2 = st.columns(2)

    with col1:
        st.write("Top 5 Performing Agents (Listings):")
        st.table(top_listings_agents)

    with col2:
        st.write("Top 5 Performing Agents (Buyers):")
        st.table(top_buyers_agents)

    # Download button for combined table
    combined_agents = pd.concat([listing_deals, buyer_deals]).groupby('Agent Name').sum().reset_index()
    st.download_button(
        label="Download Combined Agent Data",
        data=combined_agents.to_csv(index=False),
        file_name='combined_agent_data.csv',
        mime='text/csv'
    )





    # KPIs
    st.subheader("KPIs")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Listings Closed by Noralta", len(noralta_data))

    with col2:
        avg_deals_per_agent = noralta_data.groupby('Listing Agent 1 - Agent Name').size().mean()
        st.metric("Average Number of Closed Deals per Agent", f"{avg_deals_per_agent:.1f}")

    st.write("")  # Add a blank line for better readability

    col3, col4 = st.columns(2)





    # Community Dominance
    st.subheader("Community Dominance")

    community_sales = noralta_data.groupby('Community').size().nlargest(10)
    st.bar_chart(community_sales)





    # Listing Efficiency
    st.subheader("Listing Efficiency")

    # Create two columns for the KPIs
    col1, col2 = st.columns(2)

    # Format the metrics
    noralta_dom = int(noralta_data['Days On Market'].mean())
    market_dom = int(filtered_data['Days On Market'].mean())
    noralta_sold_ratio = round(noralta_data['Sold Pr / List Pr Ratio'].mean(), 1)
    market_sold_ratio = round(filtered_data['Sold Pr / List Pr Ratio'].mean(), 1)

    # Calculate the differences for the delta
    dom_delta = market_dom - noralta_dom
    ratio_delta = noralta_sold_ratio - market_sold_ratio

    with col1:
        st.metric(
            label="Average Days on Market",
            value=f"{noralta_dom} days",
            delta=f"{-dom_delta} days vs market" if dom_delta > 0 else f"{abs(dom_delta)} days vs market",
            delta_color="inverse"
        )

    with col2:
        st.metric(
            label="Sold/List Price Ratio",
            value=f"{noralta_sold_ratio}%",
            delta=f"{ratio_delta:.1f}% vs market",
            delta_color="normal"
        )






    # Revenue Contribution
    st.subheader("Revenue Contribution")

    total_sales_volume = noralta_data['Sold Price'].sum()
    st.metric("Total Sales Volume Attributable to Noralta", f"${total_sales_volume:,.2f}")

    top_agents_contribution = noralta_data.groupby('Listing Agent 1 - Agent Name')['Sold Price'].sum().nlargest(10)
    st.bar_chart(top_agents_contribution)

    top_communities_contribution = noralta_data.groupby('Community')['Sold Price'].sum().nlargest(10)
    st.bar_chart(top_communities_contribution)

    # Market Trends
    st.subheader("Market Trends")

    monthly_sales = noralta_data.groupby(noralta_data['Sold Date'].dt.to_period('M')).agg({
        'Sold Price': 'sum',
        'Days On Market': 'mean'
    }).reset_index()

    monthly_sales['Sold Date'] = monthly_sales['Sold Date'].dt.to_timestamp()

    fig_trends = go.Figure()
    fig_trends.add_trace(go.Scatter(x=monthly_sales['Sold Date'], y=monthly_sales['Sold Price'],
                                    name='Sales Volume', line=dict(color='blue')))
    fig_trends.add_trace(go.Scatter(x=monthly_sales['Sold Date'], y=monthly_sales['Days On Market'],
                                    name='Average DOM', line=dict(color='green'), yaxis='y2'))
    fig_trends.update_layout(title='Noralta Performance Over Time',
                            xaxis_title='Date',
                            yaxis_title='Sales Volume',
                            yaxis2=dict(title='Average DOM', overlaying='y', side='right'),
                            legend_title='Metric')
    st.plotly_chart(fig_trends)

if __name__ == "__main__":
    main()