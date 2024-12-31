import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from utils.data_utils import get_mongodb_data


def calculate_absorption_rate(data, months=6):
    """Calculate absorption rate over the last X months"""
    if data.empty:
        return pd.Series()

    current_date = data['Sold Date'].max()
    start_date = current_date - pd.Timedelta(days=30 * months)
    monthly_data = data[data['Sold Date'] >= start_date].groupby(pd.Grouper(key='Sold Date', freq='M'))

    sales = monthly_data.size()
    inventory = monthly_data['List Price'].count()
    absorption_rate = (sales / inventory * 100).round(2)
    return absorption_rate


def main():
    st.title("Market Analysis")

    # MongoDB connection details
    mongodb_uri = "mongodb+srv://dionathan:910213200287@cluster0.qndlz.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    database_name = "real_estate"
    collection_name = "listings"

    try:
        # Fetch data
        with st.spinner('Loading data...'):
            data = get_mongodb_data(mongodb_uri, database_name, collection_name)

            if data.empty:
                st.error("No data available!")
                return

            # Ensure Sold Date is datetime
            data['Sold Date'] = pd.to_datetime(data['Sold Date'], errors='coerce')

            # Convert numeric columns to appropriate types
            numeric_columns = ['Sold Price', 'List Price', 'TBeds', 'TBaths', 'TFA SF']
            for col in numeric_columns:
                data[col] = pd.to_numeric(data[col], errors='coerce')

        # Filters
        st.sidebar.header("Filters")

        # Date Range with default to January 2024
        min_date = data['Sold Date'].min().date()
        max_date = data['Sold Date'].max().date()
        default_start = datetime(2024, 1, 1).date()
        start_date = st.sidebar.date_input("Start Date", default_start, min_date, max_date)
        end_date = st.sidebar.date_input("End Date", max_date, min_date, max_date)

        # Area/City Multiple Selection
        default_cities = ['Edmonton', 'Spruce Grove', 'Sherwood Park', 'Fort Saskatchewan']
        available_cities = sorted(data['Area/City'].dropna().unique())
        selected_cities = st.sidebar.multiselect(
            "Select Areas/Cities",
            available_cities,
            default=default_cities
        )

        # Class Selection
        classes = sorted(data['Class'].dropna().unique())
        selected_class = st.sidebar.selectbox(
            "Class",
            ['All'] + list(classes)
        )

        # Price Range
        min_price = float(data['Sold Price'].min())
        max_price = float(data['Sold Price'].max())
        price_range = st.sidebar.slider(
            "Price Range ($)",
            float(min_price),
            float(max_price),
            (float(min_price), float(max_price)),
            step=50000.0
        )

        # Style Selection
        styles = sorted(data['Style'].dropna().unique())
        selected_style = st.sidebar.selectbox(
            "Style",
            ['All'] + list(styles)
        )

        # Bedrooms/Bathrooms
        max_beds = int(data['TBeds'].max())
        max_baths = float(data['TBaths'].max())
        beds_range = st.sidebar.slider("Number of Bedrooms", 0, max_beds, (0, max_beds))
        baths_range = st.sidebar.slider("Number of Bathrooms", 0.0, max_baths, (0.0, max_baths))

        # Apply filters
        filtered_data = data[
            (data['Sold Date'].dt.date >= start_date) &
            (data['Sold Date'].dt.date <= end_date) &
            (data['Area/City'].isin(selected_cities)) &
            (data['Sold Price'].between(price_range[0], price_range[1])) &
            (data['TBeds'].between(beds_range[0], beds_range[1])) &
            (data['TBaths'].between(baths_range[0], baths_range[1]))
        ]

        if selected_class != 'All':
            filtered_data = filtered_data[filtered_data['Class'] == selected_class]

        if selected_style != 'All':
            filtered_data = filtered_data[filtered_data['Style'] == selected_style]

        # Create tabs for different visualizations
        tab1, tab2, tab3 = st.tabs(["Price Analysis", "Market Metrics", "Geographic Analysis"])

        with tab1:
            # Average List Price vs Sold Price over time
            monthly_prices = filtered_data.groupby(pd.Grouper(key='Sold Date', freq='M')).agg({
                'List Price': 'mean',
                'Sold Price': 'mean'
            }).reset_index()

            fig1 = go.Figure()
            fig1.add_trace(go.Scatter(x=monthly_prices['Sold Date'], y=monthly_prices['List Price'],
                                      name='List Price', line=dict(color='blue')))
            fig1.add_trace(go.Scatter(x=monthly_prices['Sold Date'], y=monthly_prices['Sold Price'],
                                      name='Sold Price', line=dict(color='green')))
            fig1.update_layout(title='Average List vs Sold Price Over Time',
                               xaxis_title='Date',
                               yaxis_title='Price ($)')
            st.plotly_chart(fig1, use_container_width=True)

            # Price distribution histogram
            fig2 = px.histogram(filtered_data, x='Sold Price', nbins=50,
                                title='Price Distribution')
            st.plotly_chart(fig2, use_container_width=True)

            # Box plots of prices by Class
            fig3 = px.box(filtered_data, x='Class', y='Sold Price',
                          title='Price Distribution by Class')
            st.plotly_chart(fig3, use_container_width=True)

        with tab2:
            # Sale-to-List Price ratio trends
            filtered_data['Sale/List Ratio'] = (filtered_data['Sold Price'] / filtered_data['List Price'] * 100)
            monthly_ratio = filtered_data.groupby(pd.Grouper(key='Sold Date', freq='M'))['Sale/List Ratio'].mean().reset_index()

            fig4 = px.line(monthly_ratio, x='Sold Date', y='Sale/List Ratio',
                           title='Average Sale-to-List Price Ratio Over Time')
            fig4.add_hline(y=100, line_dash="dash", line_color="red")
            st.plotly_chart(fig4, use_container_width=True)

            # Monthly sales volume
            monthly_counts = filtered_data.groupby(pd.Grouper(key='Sold Date', freq='M')).size().reset_index()
            monthly_counts.columns = ['Date', 'Count']

            fig5 = px.line(monthly_counts, x='Date', y='Count',
                           title='Monthly Sales Volume')
            st.plotly_chart(fig5, use_container_width=True)

            # Average size by price range
            filtered_data['Price Range'] = pd.qcut(filtered_data['Sold Price'], q=5,
                                                   labels=['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'])
            avg_size_by_price = filtered_data.groupby('Price Range')['TFA SF'].mean().reset_index()

            fig6 = px.bar(avg_size_by_price, x='Price Range', y='TFA SF',
                          title='Average Square Footage by Price Range')
            st.plotly_chart(fig6, use_container_width=True)

        with tab3:
            # Sales volume by community
            community_sales = filtered_data['Community'].value_counts().head(10).reset_index()
            community_sales.columns = ['Community', 'Count']

            fig7 = px.bar(community_sales, x='Community', y='Count',
                          title='Top 10 Communities by Sales Volume')
            st.plotly_chart(fig7, use_container_width=True)

            # Absorption rate trends
            absorption_rates = calculate_absorption_rate(filtered_data)

            fig8 = px.line(absorption_rates, title='Monthly Absorption Rate')
            fig8.update_layout(yaxis_title='Absorption Rate (%)')
            st.plotly_chart(fig8, use_container_width=True)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        return


if __name__ == "__main__":
    main()
