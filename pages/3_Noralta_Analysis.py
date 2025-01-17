import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from pymongo import MongoClient

def get_mongodb_data(mongodb_uri, database_name, collection_name):
    """
    Retrieve data from MongoDB and return as a pandas DataFrame
    """
    try:
        client = MongoClient(mongodb_uri)
        db = client[database_name]
        collection = db[collection_name]
        data = list(collection.find({}, {'_id': 0}))
        df = pd.DataFrame(data)
        client.close()
        return df
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("Noralta Analysis")
    st.write("Aimed at providing insights for Royal LePage Noralta Real Estate.")

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
    min_date = data['Sold Date'].min()
    max_date = data['Sold Date'].max()
    start_date = st.sidebar.date_input("Start Date", value=min_date, min_value=min_date, max_value=max_date)
    end_date = st.sidebar.date_input("End Date", value=max_date, min_value=min_date, max_value=max_date)

    # Filter data for Noralta
    noralta_data = data[
        ((data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate') |
         (data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate')) &
        (data['Sold Date'].dt.date >= start_date) & (data['Sold Date'].dt.date <= end_date)
    ]

    # Tab 1: Noralta's Numbers
    st.header("Noralta's Numbers")

    # Section 1: Overview KPIs
    st.subheader("Overview KPIs")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Listings Closed by Noralta", len(noralta_data))
    with col2:
        total_sales_volume = noralta_data['Sold Price'].sum()
        st.metric("Total Sales Volume", f"${total_sales_volume:,.2f}")
    with col3:
        noralta_dom = int(noralta_data['Days On Market'].mean())
        market_dom = int(data['Days On Market'].mean())
        st.metric("Average DOM", f"{noralta_dom} days", delta=f"{market_dom - noralta_dom} days vs market", delta_color="inverse")
    with col4:
        noralta_sold_ratio = round(noralta_data['Sold Pr / List Pr Ratio'].mean(), 1)
        market_sold_ratio = round(data['Sold Pr / List Pr Ratio'].mean(), 1)
        st.metric("Sold/List Price Ratio", f"{noralta_sold_ratio}%", delta=f"{noralta_sold_ratio - market_sold_ratio:.1f}% vs market", delta_color="normal")

    # Section 2: Market Share Analysis
    st.subheader("Market Share Analysis")
    col1, col2 = st.columns(2)
    with col1:
        # Pie Chart: Noralta’s share of total transactions vs competitors
        total_transactions = len(data)
        noralta_transactions = len(noralta_data)
        other_transactions = total_transactions - noralta_transactions
        fig_pie = px.pie(
            values=[noralta_transactions, other_transactions],
            names=["Noralta", "Competitors"],
            title="Noralta's Share of Total Transactions"
        )
        st.plotly_chart(fig_pie)
    with col2:
        # Bar Chart: Market share breakdown by property type
        property_type_share = noralta_data.groupby('Property Class').size().reset_index(name='Count')
        fig_bar = px.bar(
            property_type_share,
            x='Property Class',
            y='Count',
            title="Market Share by Property Type"
        )
        st.plotly_chart(fig_bar)

    # Section 3: Community Performance
    st.subheader("Community Performance")
    col1, col2 = st.columns(2)
    with col1:
        # Top Communities by Sales Volume
        top_communities_volume = noralta_data.groupby('Community')['Sold Price'].sum().nlargest(10).reset_index()
        fig_volume = px.bar(
            top_communities_volume,
            x='Community',
            y='Sold Price',
            title="Top Communities by Sales Volume"
        )
        st.plotly_chart(fig_volume)
    with col2:
        # Top Communities by Number of Sales
        top_communities_sales = noralta_data.groupby('Community').size().nlargest(10).reset_index(name='Count')
        fig_sales = px.bar(
            top_communities_sales,
            x='Community',
            y='Count',
            title="Top Communities by Number of Sales"
        )
        st.plotly_chart(fig_sales)

    # Heatmap: Geographic sales performance
    st.write("Heatmap: Geographic Sales Performance")
    heatmap_data = noralta_data.groupby('Community')['Sold Price'].sum().reset_index()
    fig_heatmap = px.density_mapbox(
        heatmap_data,
        lat='Community',  # Replace with actual latitude column if available
        lon='Community',  # Replace with actual longitude column if available
        z='Sold Price',
        radius=10,
        center=dict(lat=53.5461, lon=-113.4938),  # Edmonton coordinates
        zoom=9,
        mapbox_style="open-street-map",
        title="Geographic Sales Performance"
    )
    st.plotly_chart(fig_heatmap)

    # Section 4: Trends Over Time
    st.subheader("Trends Over Time")
    monthly_sales = noralta_data.groupby(noralta_data['Sold Date'].dt.to_period('M')).agg({
        'Sold Price': 'sum',
        'Days On Market': 'mean'
    }).reset_index()
    monthly_sales['Sold Date'] = monthly_sales['Sold Date'].dt.to_timestamp()

    fig_trends = go.Figure()
    fig_trends.add_trace(go.Scatter(
        x=monthly_sales['Sold Date'],
        y=monthly_sales['Sold Price'],
        name='Sales Volume',
        line=dict(color='blue')
    ))
    fig_trends.add_trace(go.Scatter(
        x=monthly_sales['Sold Date'],
        y=monthly_sales['Days On Market'],
        name='Average DOM',
        line=dict(color='green'),
        yaxis='y2'
    ))
    fig_trends.update_layout(
        title='Monthly Sales Volume and DOM Trends',
        xaxis_title='Date',
        yaxis_title='Sales Volume',
        yaxis2=dict(title='Average DOM', overlaying='y', side='right'),
        legend_title='Metric'
    )
    st.plotly_chart(fig_trends)

    # Section 5: Efficiency Metrics
    st.subheader("Efficiency Metrics")
    col1, col2 = st.columns(2)
    with col1:
        # Bar Chart: Listing Firm vs Buyer Firm contributions
        listing_firm = len(noralta_data[noralta_data['Listing Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])
        buyer_firm = len(noralta_data[noralta_data['Buyer Firm 1 - Office Name'] == 'Royal LePage Noralta Real Estate'])
        fig_contributions = px.bar(
            x=['Listing Firm', 'Buyer Firm'],
            y=[listing_firm, buyer_firm],
            title="Listing Firm vs Buyer Firm Contributions"
        )
        st.plotly_chart(fig_contributions)
    with col2:
        # Histogram: Distribution of DOM for Noralta vs the market
        fig_dom = px.histogram(
            data,
            x='Days On Market',
            color='Listing Firm 1 - Office Name',
            title="Distribution of DOM: Noralta vs Market",
            barmode='overlay'
        )
        st.plotly_chart(fig_dom)

if __name__ == "__main__":
    main()