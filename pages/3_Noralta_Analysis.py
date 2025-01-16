import streamlit as st  
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import locale
import seaborn as sns
from pymongo import MongoClient
import numpy as np

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

    # Sidebar Filters
    st.sidebar.header("Filters")

    # Date Range
    min_date = data['Sold Date'].min()
    max_date = data['Sold Date'].max()
    default_start = datetime(2024, 1, 1)
    default_end = datetime(2024, 12, 31)

    start_date = st.sidebar.date_input("Start Date",
                                       value=default_start,
                                       min_value=min_date,
                                       max_value=max_date)
    end_date = st.sidebar.date_input("End Date",
                                     value=default_end,
                                     min_value=min_date,
                                     max_value=max_date)

    # Agent-Specific
    all_agents = sorted(set(data['Listing Agent 1 - Agent Name'].dropna().unique()) |
                        set(data['Buyer Agent 1 - Agent Name'].dropna().unique()))
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
    dom_range = st.sidebar.slider("Days on Market", 0, 201, (0, 200))

    # Apply filters
    mask = (
        (data['Sold Date'].dt.date >= start_date) &
        (data['Sold Date'].dt.date <= end_date) &
        (data['Sold Price'].between(min_price, max_price)) &
        (data['Days On Market'].between(dom_range[0], dom_range[1] if dom_range[1] < 200 else 200))
    )

    if selected_agents:
        mask &= (
            (data['Listing Agent 1 - Agent Name'].isin(selected_agents)) |
            (data['Buyer Agent 1 - Agent Name'].isin(selected_agents))
        )

    if selected_communities:
        mask &= data['Community'].isin(selected_communities)

    if selected_property_types:
        mask &= data['Property Class'].isin(selected_property_types)

    if selected_years:
        mask &= data['Year Built'].isin(selected_years)

    if selected_building_types:
        mask &= data['Building Type'].isin(selected_building_types)

    if selected_transaction_type == 'Listing Firm':
        mask &= data['Listing Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Buyer Firm':
        mask &= data['Buyer Firm 1 - Office Name'].notna()
    elif selected_transaction_type == 'Dual Representation':
        mask &= (data['Listing Firm 1 - Office Name'] == data['Buyer Firm 1 - Office Name'])

    # Move this line outside of the if statements
    filtered_data = data[mask] if 'mask' in locals() else data

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