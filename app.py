import streamlit as st
from pymongo import MongoClient
import pandas as pd
import plotly.express as px
from datetime import datetime

# MongoDB Connection Function
def get_mongodb_data(uri, database, collection):
    try:
        client = MongoClient(uri)
        db = client[database]
        collection = db[collection]
        data = list(collection.find())
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Error connecting to MongoDB: {e}")
        return pd.DataFrame()

# Filter the data based on user selections
def filter_data(data, start_date, end_date, area_city, community):
    # Filter by date range
    data['Sold Date'] = pd.to_datetime(data['Sold Date'])
    filtered_data = data[(data['Sold Date'] >= pd.Timestamp(start_date)) & (data['Sold Date'] <= pd.Timestamp(end_date))]
    
    # Filter by Area/City
    if area_city:
        filtered_data = filtered_data[filtered_data['Area/City'] == area_city]
    
    # Filter by Community (if selected)
    if community:
        filtered_data = filtered_data[filtered_data['Community'] == community]
    
    return filtered_data

# Streamlit App
def main():
    st.title("Noralta Dashboard")
    st.write("Welcome to the Noralta Dashboard!")

    # MongoDB connection
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority"
    database_name = "real_estate"
    collection_name = "listings"

    # Fetch data
    data = get_mongodb_data(mongodb_uri, database_name, collection_name)
    if data.empty:
        st.error("No data available!")
        return
    
    # Filters
    st.sidebar.header("Filters")
    
    # Date Range Selection (using calendar)
    min_date = pd.to_datetime(data['Sold Date']).min().date()
    max_date = pd.to_datetime(data['Sold Date']).max().date()
    start_date = st.sidebar.date_input("Start Date", min_value=min_date, max_value=max_date, value=min_date)
    end_date = st.sidebar.date_input("End Date", min_value=min_date, max_value=max_date, value=max_date)

    # Dropdown for Area/City
    area_city = st.sidebar.selectbox("Select Area/City", options=[""] + sorted(data['Area/City'].dropna().unique()), index=0)
    
    # Dropdown for Community (filtered by Area/City)
    community = ""
    if area_city:
        community = st.sidebar.selectbox(
            "Select Community", options=[""] + sorted(data[data['Area/City'] == area_city]['Community'].dropna().unique())
        )
    
    # Filter data based on user selections
    filtered_data = filter_data(data, start_date, end_date, area_city, community)
    
    # Visualizations
    st.header("Top 10 Listings and Buyers")
    
    # Bar Chart 1: Top 10 Listing Offices
    listing_counts = filtered_data['Listing Firm 1 - Office Name'].value_counts().head(10)
    fig1 = px.bar(
        x=listing_counts.index,
        y=listing_counts.values,
        labels={"x": "Listing Office", "y": "Count"},
        title="Top 10 Listing Offices by Count",
        text=listing_counts.values  # Add data labels
    )
    fig1.update_traces(textposition=["outside" if val < max(listing_counts.values) * 0.8 else "inside" for val in listing_counts.values])
    st.plotly_chart(fig1)
    
    # Bar Chart 2: Top 10 Buyer Firms
    buyer_counts = filtered_data['Buyer Firm 1 - Office Name'].value_counts().head(10)
    fig2 = px.bar(
        x=buyer_counts.index,
        y=buyer_counts.values,
        labels={"x": "Buyer Firm", "y": "Count"},
        title="Top 10 Buyer Firms by Count",
        text=buyer_counts.values  # Add data labels
    )
    fig2.update_traces(textposition=["outside" if val < max(buyer_counts.values) * 0.8 else "inside" for val in buyer_counts.values])
    st.plotly_chart(fig2)
    
    # Bar Chart 3: Combined Counts
    combined_counts = (
        filtered_data['Listing Firm 1 - Office Name'].value_counts() +
        filtered_data['Buyer Firm 1 - Office Name'].value_counts()
    ).dropna().sort_values(ascending=False).head(10)
    fig3 = px.bar(
        x=combined_counts.index,
        y=combined_counts.values,
        labels={"x": "Office", "y": "Count"},
        title="Top 10 Combined Counts",
        text=combined_counts.values  # Add data labels
    )
    fig3.update_traces(textposition=["outside" if val < max(combined_counts.values) * 0.8 else "inside" for val in combined_counts.values])
    st.plotly_chart(fig3)

if __name__ == "__main__":
    main()
