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
        (data['Community'].isin(selected_communities) if selected_communities else True)
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





    # Combine deals from both Listing and Buyer sides
    listing_deals = noralta_data.groupby('Listing Agent 1 - Agent Name').size().reset_index(name='Total Deals')
    buyer_deals = noralta_data.groupby('Buyer Agent 1 - Agent Name').size().reset_index(name='Total Deals')

    # Combine deals from both sides
    all_deals = pd.concat([listing_deals, buyer_deals]).groupby('Listing Agent 1 - Agent Name').sum().reset_index()

    # Calculate total deals and ranks
    all_deals['Total Deals'] = all_deals['Total Deals'].fillna(0)
    all_deals['Rank'] = all_deals['Total Deals'].rank(method='dense', ascending=False).astype(int)

    # KPIs
    st.subheader("KPIs")

    col1, col2 = st.columns(2)

    with col1:
        st.metric("Total Listings Closed by Noralta", len(noralta_data))

    with col2:
        avg_deals_per_agent = all_deals['Total Deals'].mean()
        st.metric("Average Number of Closed Deals per Agent", f"{avg_deals_per_agent:.1f}")

    st.write("")  # Add a blank line for better readability

    col3, col4 = st.columns(2)
    bottom_agents = all_deals.sort_values(by='Total Deals').head(5)
    with col3:
        top_agents = all_deals.nlargest(5, 'Total Deals')
        st.write("Top 5 Performing Agents (Total Deals):")
        st.table(top_agents)

    with col4:
        bottom_agents = all_deals.nsmallest(5, 'Total Deals')
        st.write("Bottom 5 Performing Agents (Total Deals):")
        st.table(bottom_agents)

    # Download button for complete table
    st.download_button(
        label="Download Complete Agent Data",
        data=all_deals.to_csv(index=False),
        file_name='agent_data.csv',
        mime='text/csv'
    )






    # Community Dominance
    st.subheader("Community Dominance")

    community_sales = noralta_data.groupby('Community').size().nlargest(5)
    st.bar_chart(community_sales)

    community_market_share = noralta_data.groupby('Community').size() / filtered_data.groupby('Community').size()
    community_market_share = community_market_share.dropna().sort_values(ascending=False).head(5)
    st.bar_chart(community_market_share)

    # Listing Efficiency
    st.subheader("Listing Efficiency")

    noralta_dom = noralta_data['Days On Market'].mean()
    market_dom = filtered_data['Days On Market'].mean()
    noralta_sold_ratio = noralta_data['Sold Pr / List Pr Ratio'].mean()
    market_sold_ratio = filtered_data['Sold Pr / List Pr Ratio'].mean()

    listing_efficiency = pd.DataFrame({
        'Metric': ['Average Days on Market', 'Sold Price/List Price Ratio'],
        'Noralta': [noralta_dom, noralta_sold_ratio],
        'Market': [market_dom, market_sold_ratio]
    })

    st.dataframe(listing_efficiency)

    # Revenue Contribution
    st.subheader("Revenue Contribution")

    total_sales_volume = noralta_data['Sold Price'].sum()
    st.metric("Total Sales Volume Attributable to Noralta", f"${total_sales_volume:,.2f}")

    top_agents_contribution = noralta_data.groupby('Listing Agent 1 - Agent Name')['Sold Price'].sum().nlargest(5)
    st.bar_chart(top_agents_contribution)

    top_communities_contribution = noralta_data.groupby('Community')['Sold Price'].sum().nlargest(5)
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