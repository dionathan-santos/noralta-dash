import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient
from datetime import datetime

# Function to fetch data from MongoDB (adjust URI, DB, and collection as needed)
def get_mongodb_data(mongodb_uri, database_name, collection_name):
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

# Helper function to preprocess data
def preprocess_data(df):
    if df.empty:
        return df
    # Convert Sold Date to datetime
    df['Sold Date'] = pd.to_datetime(df['Sold Date'], errors='coerce')
    
    # Clean price fields: remove '$' and commas, convert to float
    df['Sold Price'] = df['Sold Price'].str.replace(r'[\$,]', '', regex=True).astype(float)
    df['List Price'] = df['List Price'].str.replace(r'[\$,]', '', regex=True).astype(float)
    
    # Clean Total Flr Area (SF)
    df['Total Flr Area (SF)'] = df['Total Flr Area (SF)'].str.replace(',', '').astype(float)
    
    # Create Year and Month columns for easier filtering
    df['Year'] = df['Sold Date'].dt.year
    df['Month'] = df['Sold Date'].dt.month
    return df

# Function to assign property age categories based on the difference between Sold Date and Year Built
def assign_age_category(row):
    if pd.isna(row['Year Built']) or pd.isna(row['Sold Date']):
        return "Unknown"
    age = row['Sold Date'].year - int(row['Year Built'])
    if age <= 2:
        return "1-2 years"
    elif 3 <= age <= 5:
        return "3-5 years"
    elif age >= 6:
        return "5+ years"
    else:
        return "Unknown"

def main():
    st.title("Market Trends & YoY Comparison: January 2025 vs. January 2023 & 2024")
    st.markdown("""
    This dashboard analyzes sales trends, property preferences, and community performance.
    We compare January data from 2023, 2024, and 2025 as well as review community performance in Q1 2022 and Q1 2023 against January 2025.
    """)

    # ---------------------------
    # I. Global Filters
    # ---------------------------
    st.sidebar.header("Global Filters")
    
    # MongoDB connection settings (adjust credentials as necessary)
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster1.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster1"
    database_name = "real_estate"
    collection_name = "listings"
    
    # Fetch and preprocess the data
    data = get_mongodb_data(mongodb_uri, database_name, collection_name)
    if data.empty:
        st.error("No data available!")
        return
    data = preprocess_data(data)
    
    # City/Area Filter: Start with an empty selection; if nothing selected, use all
    all_cities = sorted(data['Area/City'].dropna().unique())
    selected_cities = st.sidebar.multiselect("Select City/Area", options=all_cities, default=[])
    if not selected_cities:
        selected_cities = all_cities

    # Community Filter: Dynamically filtered based on selected cities; start with empty selection (i.e., all)
    all_communities = sorted(data[data['Area/City'].isin(selected_cities)]['Community'].dropna().unique())
    selected_communities = st.sidebar.multiselect("Select Community", options=all_communities, default=[])
    if not selected_communities:
        selected_communities = all_communities

    # Date filter: Fixed to January for the years 2023, 2024, and 2025.
    jan_data = data[(data['Month'] == 1) & (data['Year'].isin([2023, 2024, 2025]))]
    jan_data = jan_data[jan_data['Area/City'].isin(selected_cities)]
    jan_data = jan_data[jan_data['Community'].isin(selected_communities)]
    
    # ---------------------------
    # II. Sales Trends Comparison
    # ---------------------------
    st.header("Sales Trends Comparison")

    # 1. Total Sales Volume: Count of properties sold in January per year
    sales_volume = jan_data.groupby('Year').size().reset_index(name='Properties Sold')
    fig_sales_volume = px.bar(
        sales_volume,
        x='Year',
        y='Properties Sold',
        title="Number of Properties Sold in January (2023 vs 2024 vs 2025)",
        text_auto=True
    )
    st.plotly_chart(fig_sales_volume)

    # 2. Price Trends: Average Sold Price and List Price in January per year
    price_trends = jan_data.groupby('Year').agg({'Sold Price': 'mean', 'List Price': 'mean'}).reset_index()
    fig_price_trends = px.bar(
        price_trends,
        x='Year',
        y=['Sold Price', 'List Price'],
        barmode='group',
        title="Average Sold Price vs List Price in January (2023 vs 2024 vs 2025)",
        labels={"value": "Price", "variable": "Price Type"},
        text_auto=True
    )
    st.plotly_chart(fig_price_trends)

    # ---------------------------
    # III. Property Preferences Trends
    # ---------------------------
    st.header("Property Preferences Trends")

    # A. Feature Distribution
    # Distribution of Total Bedrooms
    fig_bedrooms = px.histogram(
        jan_data,
        x='Total Bedrooms',
        color='Year',
        barmode='group',
        title="Distribution of Total Bedrooms in January (by Year)",
        text_auto=True,
        height=600
    )
    fig_bedrooms.update_traces(textposition='outside')
    fig_bedrooms.update_layout(margin=dict(b=150))
    st.plotly_chart(fig_bedrooms, use_container_width=True)

    # Distribution of Total Floor Area (SF) with more contrast colours
    contrast_colors = ['#636EFA', '#EF553B', '#00CC96']  # Example contrast colours
    fig_area = px.histogram(
        jan_data,
        x='Total Flr Area (SF)',
        nbins=20,
        color='Year',
        barmode='overlay',
        title="Distribution of Total Floor Area (SF) in January (by Year)",
        color_discrete_sequence=contrast_colors,
        text_auto=True
    )
    fig_area.update_traces(textposition='inside')
    st.plotly_chart(fig_area)

    # Property Class distribution (pie chart – labels shown)
    fig_prop_class = px.pie(
        jan_data,
        names='Property Class',
        title="Property Class Distribution in January (Overall)"
    )
    fig_prop_class.update_traces(textinfo='percent+label')
    st.plotly_chart(fig_prop_class)

    # B. Buyer Preference Dynamics: Trends in property types and styles
    fig_prop_type = px.histogram(
        jan_data,
        x='Property Class',
        color='Year',
        barmode='group',
        title="Property Class Trends in January (by Year)",
        text_auto=True,
        height=600
    )
    fig_prop_type.update_traces(textposition='outside')
    fig_prop_type.update_layout(margin=dict(b=150))
    st.plotly_chart(fig_prop_type, use_container_width=True)

    fig_style = px.histogram(
        jan_data,
        x='Style',
        color='Year',
        barmode='group',
        title="Property Style Trends in January (by Year)",
        text_auto=True,
        height=600
    )
    fig_style.update_traces(textposition='outside')
    fig_style.update_layout(margin=dict(b=150))
    st.plotly_chart(fig_style, use_container_width=True)

    # ---------------------------
    # IV. Property Age Segmentation (YoY Analysis)
    # ---------------------------
    st.header("Property Age Segmentation (YoY Analysis)")
    
    # Create property age category using Year Built and Sold Date
    jan_data['Age Category'] = jan_data.apply(assign_age_category, axis=1)
    
    # Group by Year and Age Category, count number of properties sold
    age_segmentation = jan_data.groupby(['Year', 'Age Category']).size().reset_index(name='Count')
    fig_age_seg = px.bar(
        age_segmentation,
        x='Year',
        y='Count',
        color='Age Category',
        barmode='group',
        title="Sales by Property Age Category in January (2023 vs 2024 vs 2025)",
        text_auto=True
    )
    st.plotly_chart(fig_age_seg)

    # ---------------------------
    # V. Community Performance Comparison
    # ---------------------------
    st.header("Community Performance Comparison (By Community Metrics)")
    st.markdown("""
    This section shows breakdowns for the top communities (by total deals in January) by various metrics:
    - Sales by property age category
    - Sales by total bedrooms
    - Sales by total baths
    - Sales by total floor area (SF) ranges
    - Sales by Days On Market (DOM) ranges
    """)
    
    # Determine the top communities by total deals in January
    community_deals = jan_data.groupby("Community").size().reset_index(name="Deals")
    top_communities = community_deals.sort_values("Deals", ascending=False).head(10)["Community"].tolist()
    top_comm_data = jan_data[jan_data["Community"].isin(top_communities)]
    
    # A. Sales by Property Age Category (by Community)
    st.subheader("Sales by Property Age Category (by Community)")
    age_by_community = top_comm_data.groupby(["Community", "Age Category"]).size().reset_index(name="Count")
    fig_age_comm = px.bar(
        age_by_community,
        x="Community",
        y="Count",
        color="Age Category",
        barmode="group",
        title="Sales by Property Age Category for Top Communities",
        text_auto=True,
        height=600
    )
    fig_age_comm.update_traces(textposition='outside')
    fig_age_comm.update_layout(margin=dict(b=150))
    st.plotly_chart(fig_age_comm, use_container_width=True)
    
    # B. Sales by Total Bedrooms (by Community)
    st.subheader("Sales by Total Bedrooms (by Community)")
    bedrooms_by_community = top_comm_data.groupby(["Community", "Total Bedrooms"]).size().reset_index(name="Count")
    fig_bedrooms_comm = px.bar(
        bedrooms_by_community,
        x="Community",
        y="Count",
        color="Total Bedrooms",
        barmode="group",
        title="Sales by Total Bedrooms for Top Communities",
        text_auto=True
    )
    fig_bedrooms_comm.update_traces(textposition='outside')
    st.plotly_chart(fig_bedrooms_comm)
    
    # C. Sales by Total Baths (by Community)
    st.subheader("Sales by Total Baths (by Community)")
    baths_by_community = top_comm_data.groupby(["Community", "Total Baths"]).size().reset_index(name="Count")
    fig_baths_comm = px.bar(
        baths_by_community,
        x="Community",
        y="Count",
        color="Total Baths",
        barmode="group",
        title="Sales by Total Baths for Top Communities",
        text_auto=True
    )
    fig_baths_comm.update_traces(textposition='outside')
    st.plotly_chart(fig_baths_comm)
    
    # D. Sales by Total Floor Area (SF) Ranges (by Community)
    st.subheader("Sales by Total Floor Area (SF) Ranges (by Community)")
    size_bins = list(range(0, 5001, 500))
    size_labels = [f"{size_bins[i]}-{size_bins[i+1]-1}" for i in range(len(size_bins)-1)]
    top_comm_data["Size Range"] = pd.cut(top_comm_data["Total Flr Area (SF)"], bins=size_bins, labels=size_labels, right=False)
    size_by_community = top_comm_data.groupby(["Community", "Size Range"]).size().reset_index(name="Count")
    fig_size_comm = px.bar(
        size_by_community,
        x="Community",
        y="Count",
        color="Size Range",
        barmode="group",
        title="Sales by Total Floor Area (SF) Ranges for Top Communities",
        text_auto=True
    )
    fig_size_comm.update_traces(textposition='inside')
    st.plotly_chart(fig_size_comm)
    
    # E. Sales by Days On Market (DOM) Ranges (by Community)
    st.subheader("Sales by Days On Market (DOM) Ranges (by Community)")
    dom_bins = [0, 10, 20, 30, 40, 1000]
    dom_labels = ["0-10", "10-20", "20-30", "30-40", "40+"]
    top_comm_data["DOM Range"] = pd.cut(top_comm_data["Days On Market"], bins=dom_bins, labels=dom_labels, right=False)
    dom_by_community = top_comm_data.groupby(["Community", "DOM Range"]).size().reset_index(name="Count")
    fig_dom_comm = px.bar(
        dom_by_community,
        x="Community",
        y="Count",
        color="DOM Range",
        barmode="group",
        title="Sales by Days On Market (DOM) Ranges for Top Communities",
        text_auto=True
    )
    fig_dom_comm.update_traces(textposition='inside')
    st.plotly_chart(fig_dom_comm)
    
    # ---------------------------
    # VI. Summary & Insights
    # ---------------------------
    st.header("Summary & Insights")
    st.markdown("""
    - **Sales Trends:** Compare overall sales volume and pricing trends for January across 2023, 2024, and 2025.
    - **Property Preferences:** Understand shifts in features and property types that appeal to buyers.
    - **Age Segmentation:** Identify which property age groups are most in demand.
    - **Community Performance:** Review detailed community breakdowns by age, bedrooms, baths, size ranges, and DOM ranges.
    
    Use these insights to tailor marketing and sales strategies for the coming quarter.
    """)

if __name__ == "__main__":
    main()
