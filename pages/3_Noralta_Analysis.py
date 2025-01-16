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
    st.write("Detailed analysis specific to Noralta properties.")

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

    # Filters
    st.sidebar.header("Filters")
    min_date = data['Sold Date'].min().date()
    max_date = data['Sold Date'].max().date()
    start_date = st.sidebar.date_input("Start Date", min_date, min_date, max_date)
    end_date = st.sidebar.date_input("End Date", max_date, min_date, max_date)
    area_city = st.sidebar.selectbox("Select Area/City", ["Noralta"] if "Noralta" in data['Area/City'].unique() else [""])
    
    filtered_data = filter_data(data, start_date, end_date, area_city)

    # Time-Based Analysis
    st.subheader("Time-Based Analysis")

    # Sold Listings Over Time
    st.subheader("Sold Listings Over Time")

    # Group by month
    monthly_sales = filtered_data.groupby(filtered_data['Sold Date'].dt.to_period('M')).agg({
        'Sold Price': 'count'
    }).reset_index()

    # Flatten the multi-level columns
    monthly_sales.columns = ['Sold Date', 'Total Sales #']
    monthly_sales['Sold Date'] = monthly_sales['Sold Date'].dt.to_timestamp()

    # Create the figure
    fig_sales = go.Figure()

    # Add a line for total sales
    fig_sales.add_trace(go.Scatter(
        x=monthly_sales['Sold Date'],
        y=monthly_sales['Total Sales #'],
        name='Total Sales',
        line=dict(color='blue', width=2),
        hovertemplate=(
            'Date: %{x}<br>' +
            'Total Sales #: %{y}<br>'
        )
    ))

    # Update layout
    fig_sales.update_layout(
        title='Number of Properties Sold per Month',
        xaxis_title='Date',
        yaxis_title='Number of Sales'
    )

    # Display the chart
    st.plotly_chart(fig_sales)

    # Average Sold Price Over Time
    st.subheader("Average Sold Price Over Time")

    # Group by month
    monthly_avg_price = filtered_data.groupby(filtered_data['Sold Date'].dt.to_period('M')).agg({
        'Sold Price': 'mean'
    }).reset_index()

    # Flatten the multi-level columns
    monthly_avg_price.columns = ['Sold Date', 'Average Sold Price']
    monthly_avg_price['Sold Date'] = monthly_avg_price['Sold Date'].dt.to_timestamp()

    # Create the figure
    fig_avg_price = go.Figure()

    # Add a line for average sold price
    fig_avg_price.add_trace(go.Scatter(
        x=monthly_avg_price['Sold Date'],
        y=monthly_avg_price['Average Sold Price'],
        name='Average Sold Price',
        line=dict(color='green', width=2),
        hovertemplate=(
            'Date: %{x}<br>' +
            'Average Sold Price: $%{y:,.2f}<br>'
        )
    ))

    # Update layout
    fig_avg_price.update_layout(
        title='Average Sold Price Over Time',
        xaxis_title='Date',
        yaxis_title='Average Sold Price ($)'
    )

    # Display the chart
    st.plotly_chart(fig_avg_price)

    # Visualization: Distribution of Property Types in Noralta
    property_type_counts = filtered_data['Property Class'].value_counts()
    fig = px.pie(
        values=property_type_counts.values,
        names=property_type_counts.index,
        title="Distribution of Property Class in Noralta",
    )
    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()