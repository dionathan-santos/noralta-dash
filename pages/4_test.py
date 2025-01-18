import streamlit as st
import pandas as pd
import plotly.express as px
from pymongo import MongoClient

# MongoDB connection
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

# Main function
def main():
    st.title("Under Construction")
    st.write("This page is under construction.")

    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Monthly Report", "2024 Market Performance", "Forecasting"])

    # Content for the "Monthly Report" tab
    with tab1:
        st.header("Monthly Report")
        st.write("This section will display monthly performance metrics for agents.")
        # Add your monthly report content here (e.g., charts, tables, etc.)

    # Content for the "2024 Market Performance" tab
    with tab2:
        st.header("2024 Market Performance")
        st.write("This section will analyze market trends and performance for 2024.")

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

        #### Market Trends
        st.header("Market Trends")

        # Volume of Transactions by Property Class
        st.subheader("Volume of Transactions by Property Class")
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Edmonton Only**")
            edmonton_data = data[data['Area/City'] == 'Edmonton']
            fig1 = px.bar(
                edmonton_data.groupby('Property Class').size().reset_index(name='Count'),
                x='Property Class',
                y='Count',
                title="Volume of Transactions (Edmonton)"
            )
            st.plotly_chart(fig1)
            st.write("**Analysis:** Add your analysis here.")

        with col2:
            st.write("**Greater Edmonton**")
            greater_edmonton_data = data[data['Area/City'].isin(['Edmonton', 'Other Areas'])]
            fig2 = px.bar(
                greater_edmonton_data.groupby('Property Class').size().reset_index(name='Count'),
                x='Property Class',
                y='Count',
                title="Volume of Transactions (Greater Edmonton)"
            )
            st.plotly_chart(fig2)
            st.write("**Analysis:** Add your analysis here.")

        # Average Sold Prices vs. List Prices
        st.subheader("Average Sold Prices vs. List Prices")
        col3, col4 = st.columns(2)

        with col3:
            st.write("**Edmonton Only**")
            fig3 = px.line(
                edmonton_data.groupby('Sold Date').agg({'Sold Price': 'mean', 'List Price': 'mean'}).reset_index(),
                x='Sold Date',
                y=['Sold Price', 'List Price'],
                title="Average Sold vs List Prices (Edmonton)"
            )
            st.plotly_chart(fig3)
            st.write("**Analysis:** Add your analysis here.")

        with col4:
            st.write("**Greater Edmonton**")
            fig4 = px.line(
                greater_edmonton_data.groupby('Sold Date').agg({'Sold Price': 'mean', 'List Price': 'mean'}).reset_index(),
                x='Sold Date',
                y=['Sold Price', 'List Price'],
                title="Average Sold vs List Prices (Greater Edmonton)"
            )
            st.plotly_chart(fig4)
            st.write("**Analysis:** Add your analysis here.")

        # Days on Market (DOM) Analysis
        st.subheader("Days on Market (DOM) Analysis")
        col5, col6 = st.columns(2)

        with col5:
            st.write("**Edmonton Only**")
            fig5 = px.bar(
                edmonton_data.groupby('Property Class')['Days On Market'].mean().reset_index(),
                x='Property Class',
                y='Days On Market',
                title="Average DOM by Property Class (Edmonton)"
            )
            st.plotly_chart(fig5)
            st.write("**Analysis:** Add your analysis here.")

        with col6:
            st.write("**Greater Edmonton**")
            fig6 = px.bar(
                greater_edmonton_data.groupby('Property Class')['Days On Market'].mean().reset_index(),
                x='Property Class',
                y='Days On Market',
                title="Average DOM by Property Class (Greater Edmonton)"
            )
            st.plotly_chart(fig6)
            st.write("**Analysis:** Add your analysis here.")

        #### Geographical Insights
        st.header("Geographical Insights")

        # Performance by Area/Community
        st.subheader("Performance by Area/Community")
        areas = sorted(data['Community'].dropna().unique())
        selected_areas = st.multiselect("Select Areas/Communities", areas, default=areas[:2])

        if selected_areas:
            area_data = data[data['Community'].isin(selected_areas)]
            fig7 = px.line(
                area_data.groupby(['Community', 'Sold Date']).size().reset_index(name='Count'),
                x='Sold Date',
                y='Count',
                color='Community',
                title="Sales Volume by Area/Community"
            )
            st.plotly_chart(fig7)
            st.write("**Analysis:** Add your analysis here.")

        # Top 10 Neighbourhoods in Edmonton
        st.subheader("Top 10 Neighbourhoods in Edmonton")
        edmonton_neighbourhoods = data[data['Area/City'] == 'Edmonton']
        top_neighbourhoods = edmonton_neighbourhoods.groupby('Community').agg(
            Avg_Price=('Sold Price', 'mean'),
            Demand=('Sold Date', 'count')
        ).reset_index().sort_values(by='Demand', ascending=False).head(10)

        fig8 = px.scatter(
            top_neighbourhoods,
            x='Avg_Price',
            y='Demand',
            text='Community',
            title="Top 10 Neighbourhoods by Average Price and Demand"
        )
        st.plotly_chart(fig8)
        st.write("**Analysis:** Add your analysis here.")

    # Content for the "Forecasting" tab
    with tab3:
        st.header("Forecasting")
        st.write("This section will provide forecasts for future agent performance and market trends.")
        # Add your forecasting content here (e.g., predictive models, trends, etc.)

if __name__ == "__main__":
    main()