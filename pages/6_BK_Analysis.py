import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

# Set page title and layout
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Function to retrieve AWS credentials from Streamlit secrets
def get_aws_credentials():
    """Retrieves AWS credentials from Streamlit secrets."""
    try:
        aws_secrets = st.secrets["aws"]  # Get the entire 'aws' dictionary
        return (
            aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secrets["AWS_SECRET_ACCESS_KEY"],
            aws_secrets.get("AWS_REGION", "us-east-2")  # Default to us-east-2 if not set
        )
    except KeyError:
        st.error("AWS credentials are missing. Check Streamlit secrets configuration.")
        return None, None, None

# Function to fetch data from DynamoDB
@st.cache_data
def get_dynamodb_data(table_name):
    """Fetch data from a specified DynamoDB table and convert it to a Pandas DataFrame."""
    aws_access_key, aws_secret_key, aws_region = get_aws_credentials()
    if not aws_access_key or not aws_secret_key:
        return pd.DataFrame()

    try:
        dynamodb = boto3.resource(
            "dynamodb",
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            region_name=aws_region
        )
        table = dynamodb.Table(table_name)  # Dynamically select the table

        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"Failed to fetch data from DynamoDB: {e}")
        return pd.DataFrame()

# Load data from AWS DynamoDB
listings_data = get_dynamodb_data()

# Ensure data is loaded
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Convert 'sold_date' to datetime format
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Sidebar filters
st.sidebar.header("Filters")

start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))

selected_cities = st.sidebar.multiselect("Select Cities", sorted(listings_data["area_city"].dropna().unique()))
selected_communities = st.sidebar.multiselect("Select Communities", sorted(listings_data["community"].dropna().unique()))
selected_building_types = st.sidebar.multiselect("Select Building Types", sorted(listings_data["building_type"].dropna().unique()))
selected_firms = st.sidebar.multiselect("Select Brokerage Firms", sorted(listings_data["listing_firm"].dropna().unique()))

# **Optimized Filtering with Pandas Query**
query_str = f"(sold_date >= '{start_date}') & (sold_date <= '{end_date}')"

if selected_cities:
    query_str += f" & (area_city in {selected_cities})"
if selected_communities:
    query_str += f" & (community in {selected_communities})"
if selected_building_types:
    query_str += f" & (building_type in {selected_building_types})"
if selected_firms:
    query_str += f" & (listing_firm in {selected_firms})"

filtered_data = listings_data.query(query_str) if query_str else listings_data

# Check if data is empty after filtering
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# Top 10 Brokerages with Most Deals
brokerage_deals = filtered_data["listing_firm"].value_counts().reset_index()
brokerage_deals.columns = ["Brokerage", "Number of Deals"]

# Display KPIs
st.subheader("Brokerage Performance Summary")

col1, col2 = st.columns(2)
col1.metric("Total Deals in Period", filtered_data.shape[0])
col2.metric("Total Brokerages Involved", brokerage_deals.shape[0])

########################## highlighted brokerage



import streamlit as st
import pandas as pd
import plotly.express as px

# Define the brokerage to highlight
highlight_brokerage = "Royal LePage Noralta Real Estate"

# Function to create a bar chart with highlighted brokerage
def create_highlighted_bar_chart(df, x_col, y_col, title):
    """Creates a bar chart where 'Royal LePage Noralta Real Estate' is highlighted in red."""
    df = df.copy()  # Avoid modifying the original DataFrame

    # Assign colors: "red" for the highlight, "royalblue" for others
    df["Color"] = df[x_col].apply(lambda x: "red" if x == highlight_brokerage else "royalblue")

    # Ensure the x-axis is ordered correctly (sorted by y_col values)
    df = df.sort_values(by=y_col, ascending=False)

    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        title=title,
        labels={x_col: "Brokerage", y_col: "Number of Deals"},
        text_auto=True,
        color=df["Color"],  # Assign colors dynamically
        category_orders={x_col: df[x_col].tolist()},  # Ensure correct order
        color_discrete_map={"red": "red", "royalblue": "royalblue"}  # Define color mapping
    )

    return fig

###################   TOP 10 COMBINED BUYER & LISTING FIRMS ####################

# Ensure 'listing_firm' and 'buyer_firm' columns exist before using them
listing_deals = filtered_data["listing_firm"].value_counts().rename("Listing Deals") if "listing_firm" in filtered_data.columns else pd.Series(dtype="int")
buyer_deals = filtered_data["buyer_firm"].value_counts().rename("Buyer Deals") if "buyer_firm" in filtered_data.columns else pd.Series(dtype="int")

# Merge listing and buyer firm counts into a single DataFrame
combined_deals = pd.DataFrame({"Brokerage": listing_deals.index}).merge(
    listing_deals, left_on="Brokerage", right_index=True, how="outer"
).merge(
    pd.DataFrame({"Brokerage": buyer_deals.index}).merge(
        buyer_deals, left_on="Brokerage", right_index=True, how="outer"
    ),
    on="Brokerage",
    how="outer"
).fillna(0)

# Calculate total deals (listing + buyer)
combined_deals["Total Deals"] = combined_deals["Listing Deals"] + combined_deals["Buyer Deals"]

# Sort by total deals in descending order
combined_deals = combined_deals.sort_values(by="Total Deals", ascending=False).head(10)

st.subheader("Top 10 Brokerages (Buyer & Listing Combined)")
if not combined_deals.empty:
    fig_combined = create_highlighted_bar_chart(
        combined_deals,
        x_col="Brokerage",
        y_col="Total Deals",
        title="(Buyer & Listing) Top 10 Brokerages by Total Deals "
    )
    st.plotly_chart(fig_combined)
else:
    st.warning("No data available for the selected filters.")

###################   TOP 10 LISTING FIRMS ####################

# Ensure 'listing_firm' column exists before using it
if "listing_firm" in filtered_data.columns:
    brokerage_deals = filtered_data["listing_firm"].value_counts().reset_index()
    brokerage_deals.columns = ["Brokerage", "Number of Deals"]
    brokerage_deals = brokerage_deals.sort_values(by="Number of Deals", ascending=False).head(10)  # Correct sorting
else:
    brokerage_deals = pd.DataFrame(columns=["Brokerage", "Number of Deals"])

st.subheader("Listing Side - Top 10 Brokerages with Most Deals")
if not brokerage_deals.empty:
    fig = create_highlighted_bar_chart(
        brokerage_deals,
        x_col="Brokerage",
        y_col="Number of Deals",
        title="Top 10 Brokerages by Deals (Listing Side)"
    )
    st.plotly_chart(fig)
else:
    st.warning("No data available for the selected filters.")


###################   TOP 10 BUYER FIRMS ####################

# Ensure 'buyer_firm' column exists before using it
if "buyer_firm" in filtered_data.columns:
    buyer_brokerage_deals = filtered_data["buyer_firm"].value_counts().reset_index()
    buyer_brokerage_deals.columns = ["Brokerage", "Number of Deals"]
    buyer_brokerage_deals = buyer_brokerage_deals.sort_values(by="Number of Deals", ascending=False).head(10)  # Correct sorting
else:
    buyer_brokerage_deals = pd.DataFrame(columns=["Brokerage", "Number of Deals"])

st.subheader("Buyers Side - Top 10 Brokerages with Most Deals")
if not buyer_brokerage_deals.empty:
    fig_buyer = create_highlighted_bar_chart(
        buyer_brokerage_deals,
        x_col="Brokerage",
        y_col="Number of Deals",
        title="Top 10 Buyer Brokerages by Deals"
    )
    st.plotly_chart(fig_buyer)
else:
    st.warning("No data available for the selected filters.")


########################  DEALS PER AGENT

import plotly.express as px
import pandas as pd
import streamlit as st

###################   DAILY DEALS PER AGENT LINE CHART ####################

# Ensure 'sold_date' column exists in filtered_data
if "sold_date" in filtered_data.columns:
    # Step 1: Count deals per brokerage per day
    daily_deals = filtered_data.groupby(["sold_date", "listing_firm"]).size().reset_index(name="Total Deals")
else:
    daily_deals = pd.DataFrame(columns=["sold_date", "listing_firm", "Total Deals"])


### FIX: Fetch brokerage data dynamically BEFORE processing ###
brokerage_data = get_dynamodb_data("brokerage")  # Now it correctly loads the brokerage table

if brokerage_data.empty:
    st.warning("No brokerage data available. Unable to compute Deals per Agent.")

# Step 2: Extract monthly agent count from brokerage table
if not brokerage_data.empty and "Broker" in brokerage_data.columns:
    # Convert brokerage columns to numeric (ignoring non-date columns)
    brokerage_melted = brokerage_data.melt(id_vars=["Broker"], var_name="Month", value_name="Total Agents")

    # Convert Month to datetime format (only considering Year-Month)
    brokerage_melted["Month"] = pd.to_datetime(brokerage_melted["Month"], errors="coerce").dt.to_period("M")

    # Rename Broker column to match listing_firm
    brokerage_melted.rename(columns={"Broker": "listing_firm"}, inplace=True)
else:
    brokerage_melted = pd.DataFrame(columns=["listing_firm", "Month", "Total Agents"])

# Step 3: Merge daily deal data with agent count (using the closest available month)
if not daily_deals.empty and not brokerage_melted.empty:
    daily_deals["Month"] = daily_deals["sold_date"].dt.to_period("M")  # Convert sold_date to Year-Month

    # Merge deals per brokerage per month with the agent count
    deals_per_agent = daily_deals.merge(
        brokerage_melted, on=["listing_firm", "Month"], how="left"
    ).fillna(0)

    # Step 4: Calculate deals per agent
    deals_per_agent["Deals per Agent"] = deals_per_agent["Total Deals"] / deals_per_agent["Total Agents"].replace(0, 1)
else:
    deals_per_agent = pd.DataFrame(columns=["sold_date", "listing_firm", "Deals per Agent"])

# Step 5: Plot the line chart for top 10 brokerages (by total deals)
top_10_brokerages = combined_deals["Brokerage"].tolist()  # Get the top 10 firms

filtered_chart_data = deals_per_agent[deals_per_agent["listing_firm"].isin(top_10_brokerages)]

st.subheader("Daily Deals per Agent for Top 10 Brokerages")
if not filtered_chart_data.empty:
    fig_line = px.line(
        filtered_chart_data,
        x="sold_date",
        y="Deals per Agent",
        color="listing_firm",
        title="Daily Deals per Agent - Top 10 Brokerages",
        labels={"sold_date": "Date", "Deals per Agent": "Deals Per Agent"},
        markers=True
    )
    st.plotly_chart(fig_line)
else:
    st.warning("No data available for the selected filters.")  
