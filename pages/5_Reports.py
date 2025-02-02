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
    mongodb_uri = "mongodb+srv://your_username:your_password@cluster0.example.mongodb.net/?retryWrites=true&w=majority"
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
        text_auto=True
    )
    fig_bedrooms.update_traces(textposition='outside')
    st.plotly_chart(fig_bedrooms)

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
        title="Property Class Distribution in January (Overall)",
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
        text_auto=True
    )
    fig_prop_type.update_traces(textposition='outside')
    st.plotly_chart(fig_prop_type)

    fig_style = px.histogram(
        jan_data,
        x='Style',
        color='Year',
        barmode='group',
        title="Property Style Trends in January (by Year)",
        text_auto=True
    )
    fig_style.update_traces(textposition='outside')
    st.plotly_chart(fig_style)

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
    st.header("Community Performance Comparison")
    st.markdown("""
    Compare key performance metrics for communities:
    - **Q1 2022 & Q1 2023:** Aggregated performance in the first quarter.
    - **January 2025:** Performance in January 2025.
    """)
    
    # Prepare Q1 data for 2022 and 2023
    q1_data = data[(data['Year'].isin([2022, 2023])) & (data['Month'].isin([1, 2, 3]))]
    q1_data = q1_data[q1_data['Area/City'].isin(selected_cities)]
    q1_data = q1_data[q1_data['Community'].isin(selected_communities)]
    
    # For January 2025, we already have jan_data (filtered above)
    def compute_metrics(df, period_label):
        metrics = df.groupby('Community').agg(
            Deals=('Sold Date', 'count'),
            Avg_DOM=('Days On Market', 'mean'),
            Avg_Sold_Price=('Sold Price', 'mean')
        ).reset_index()
        metrics['Period'] = period_label
        return metrics

    metrics_q1_2022 = compute_metrics(q1_data[q1_data['Year'] == 2022], "Q1 2022")
    metrics_q1_2023 = compute_metrics(q1_data[q1_data['Year'] == 2023], "Q1 2023")
    metrics_jan25 = compute_metrics(jan_data[jan_data['Year'] == 2025], "January 2025")
    
    # Combine metrics for community performance comparison
    community_metrics = pd.concat([metrics_q1_2022, metrics_q1_2023, metrics_jan25])
    
    # --- Deals: Top 10 Communities by Total Deals ---
    # First, aggregate deals by community across periods.
    deals_agg = community_metrics.groupby("Community")["Deals"].sum().reset_index()
    top10_deals = deals_agg.sort_values("Deals", ascending=False).head(10)["Community"].tolist()
    deals_chart_data = community_metrics[community_metrics["Community"].isin(top10_deals)]
    fig_deals = px.bar(
        deals_chart_data,
        x='Community',
        y='Deals',
        color='Period',
        barmode='group',
        title="Top 10 Communities (by Deals)",
        text_auto=True
    )
    st.plotly_chart(fig_deals)
    
    # --- Average DOM: Top 10 Communities with Lowest Average DOM ---
    # We take the overall average DOM per community (across periods)
    dom_agg = community_metrics.groupby("Community")["Avg_DOM"].mean().reset_index()
    top10_low_dom = dom_agg.sort_values("Avg_DOM", ascending=True).head(10)["Community"].tolist()
    dom_chart_data = community_metrics[community_metrics["Community"].isin(top10_low_dom)]
    fig_dom = px.bar(
        dom_chart_data,
        x='Community',
        y='Avg_DOM',
        color='Period',
        barmode='group',
        title="Top 10 Communities (Lowest Avg DOM)",
        text_auto=True
    )
    st.plotly_chart(fig_dom)
    
    # --- Average Sold Price: Top 10 Communities with Highest Avg Sold Price ---
    price_agg = community_metrics.groupby("Community")["Avg_Sold_Price"].mean().reset_index()
    top10_high_price = price_agg.sort_values("Avg_Sold_Price", ascending=False).head(10)["Community"].tolist()
    price_chart_data_high = community_metrics[community_metrics["Community"].isin(top10_high_price)]
    fig_price_high = px.bar(
        price_chart_data_high,
        x='Community',
        y='Avg_Sold_Price',
        color='Period',
        barmode='group',
        title="Top 10 Communities (Highest Avg Sold Price)",
        text_auto=True
    )
    st.plotly_chart(fig_price_high)
    
    # --- Average Sold Price: Top 10 Communities with Lowest Avg Sold Price ---
    top10_low_price = price_agg.sort_values("Avg_Sold_Price", ascending=True).head(10)["Community"].tolist()
    price_chart_data_low = community_metrics[community_metrics["Community"].isin(top10_low_price)]
    fig_price_low = px.bar(
        price_chart_data_low,
        x='Community',
        y='Avg_Sold_Price',
        color='Period',
        barmode='group',
        title="Top 10 Communities (Lowest Avg Sold Price)",
        text_auto=True
    )
    st.plotly_chart(fig_price_low)
    
    # ---------------------------
    # VI. Summary & Insights
    # ---------------------------
    st.header("Summary & Insights")
    st.markdown("""
    - **Sales Trends:** Compare overall sales volume and pricing trends for January across 2023, 2024, and 2025.
    - **Property Preferences:** Understand shifts in features and property types that appeal to buyers.
    - **Age Segmentation:** Identify which property age groups are most in demand.
    - **Community Performance:** Evaluate if communities that performed well in Q1 2022/2023 are maintaining their pace in January 2025.
    
    Use these insights to tailor marketing and sales strategies for the coming quarter.
    """)

if __name__ == "__main__":
    main()
