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
        aws_secrets = st.secrets["aws"]
        return (
            aws_secrets["AWS_ACCESS_KEY_ID"],
            aws_secrets["AWS_SECRET_ACCESS_KEY"],
            aws_secrets.get("AWS_REGION", "us-east-2")
        )
    except KeyError:
        st.error("AWS credentials missing. Check Streamlit secrets.")
        return None, None, None

# Function to fetch real estate listings data
@st.cache_data
def get_dynamodb_data():
    """Fetch data from real_estate_listings table."""
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
        table = dynamodb.Table("real_estate_listings")

        items = []
        response = table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"DynamoDB error: {str(e)}")
        return pd.DataFrame()

# Function to fetch brokerage data
@st.cache_data
def get_brokerage_data():
    """Fetch data from brokerage table."""
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
        table = dynamodb.Table("brokerage")

        items = []
        response = table.scan()
        items.extend(response.get("Items", []))

        while "LastEvaluatedKey" in response:
            response = table.scan(ExclusiveStartKey=response["LastEvaluatedKey"])
            items.extend(response.get("Items", []))

        # Transform data
        brokerage_df = pd.DataFrame(items)

        # Validate required columns
        required_columns = {'brokerage_name', 'report_date', 'agent_count'}
        if not required_columns.issubset(brokerage_df.columns):
            missing = required_columns - set(brokerage_df.columns)
            st.error(f"Missing columns in brokerage data: {missing}")
            return pd.DataFrame()

        # Rename and transform
        brokerage_df = brokerage_df.rename(columns={
            "brokerage_name": "Firm",
            "report_date": "Month",
            "agent_count": "Active Agents"
        })

        brokerage_df["Month"] = pd.to_datetime(brokerage_df["Month"]).dt.to_period("M").dt.to_timestamp()
        brokerage_df["Active Agents"] = pd.to_numeric(brokerage_df["Active Agents"], errors="coerce")

        return brokerage_df.dropna(subset=["Firm", "Month"])

    except Exception as e:
        st.error(f"Brokerage data error: {str(e)}")
        return pd.DataFrame()

# Load data
listings_data = get_dynamodb_data()
brokerage_data = get_brokerage_data()

# Data validation
if listings_data.empty or brokerage_data.empty:
    st.error("Failed to load required data")
    st.stop()

# Data processing for listings
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()
listings_data = listings_data.dropna(subset=["sold_date", "listing_firm", "buyer_firm"])

# -------------------- Load and Preprocess Listings Data --------------------

listings_data = get_dynamodb_data()
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Convert 'sold_date' to datetime and remove time portion
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()
listings_data = listings_data.dropna(subset=["sold_date"])

# ----------------------- Sidebar Filters -----------------------
st.sidebar.header("Filters")
start_date = st.sidebar.date_input("Start Date", pd.Timestamp("2024-01-01"))
end_date = st.sidebar.date_input("End Date", pd.Timestamp("2024-12-31"))
selected_cities = st.sidebar.multiselect("Select Cities", sorted(listings_data["area_city"].dropna().unique()))
selected_communities = st.sidebar.multiselect("Select Communities", sorted(listings_data["community"].dropna().unique()))
selected_building_types = st.sidebar.multiselect("Select Building Types", sorted(listings_data["building_type"].dropna().unique()))
selected_firms = st.sidebar.multiselect("Select Brokerage Firms", sorted(listings_data["listing_firm"].dropna().unique()))

# Build query string using proper pandas query syntax (using @ for external variables)
query_str = f"(sold_date >= '{start_date}') and (sold_date <= '{end_date}')"
if selected_cities:
    query_str += " and (area_city in @selected_cities)"
if selected_communities:
    query_str += " and (community in @selected_communities)"
if selected_building_types:
    query_str += " and (building_type in @selected_building_types)"
if selected_firms:
    query_str += " and (listing_firm in @selected_firms)"

filtered_data = listings_data.query(query_str)
if filtered_data.empty:
    st.warning("No data found for the selected filters!")
    st.stop()

# ----------------------- KPI Summary -----------------------
st.subheader("Brokerage Performance Summary")
total_deals = filtered_data.shape[0]
brokerage_deals_counts = filtered_data["listing_firm"].value_counts().reset_index()
brokerage_deals_counts.columns = ["Brokerage", "Number of Deals"]

col1, col2 = st.columns(2)
col1.metric("Total Deals in Period", total_deals)
col2.metric("Total Brokerages Involved", brokerage_deals_counts.shape[0])

# ----------------------- Compute Monthly Deals and Average Deals per Agent -----------------------

# Prepare market_data with Month column for grouping
market_data = filtered_data.copy()
market_data["Month"] = pd.to_datetime(market_data["sold_date"]).dt.to_period("M").dt.to_timestamp()

# Compute monthly deals from listing side and buyer side
monthly_deals_listing = (
    market_data.groupby(["listing_firm", "Month"]).size().reset_index(name="Deals")
).rename(columns={"listing_firm": "Firm"})
monthly_deals_buyer = (
    market_data.groupby(["buyer_firm", "Month"]).size().reset_index(name="Deals")
).rename(columns={"buyer_firm": "Firm"})

# Combine deals from both sides
all_monthly_deals = pd.concat([monthly_deals_listing, monthly_deals_buyer], axis=0)
all_monthly_deals = all_monthly_deals.groupby(["Firm", "Month"], as_index=False)["Deals"].sum()

# Determine top 10 firms overall by total deals
overall_deals = all_monthly_deals.groupby("Firm", as_index=False)["Deals"].sum()
top_firms = overall_deals.sort_values("Deals", ascending=False).head(10)["Firm"].tolist()

# Filter for the top 10 firms
top_monthly_deals = all_monthly_deals[all_monthly_deals["Firm"].isin(top_firms)]

# Load brokerage data and filter to top firms
brokerage_data = get_brokerage_data()
top_brokerage_data = brokerage_data[brokerage_data["Firm"].isin(top_firms)]

# Merge monthly deals with brokerage data on Firm and Month
merged_data = pd.merge(top_monthly_deals, top_brokerage_data, on=["Firm", "Month"], how="left")

# Compute average deals per agent (handle zero or missing agent counts)
merged_data["Avg Deals per Agent"] = merged_data.apply(
    lambda row: round(row["Deals"] / row["Active Agents"], 2)
    if pd.notnull(row["Active Agents"]) and row["Active Agents"] > 0 else 0,
    axis=1
)

final_table = merged_data[["Firm", "Month", "Avg Deals per Agent", "Active Agents"]].sort_values(["Firm", "Month"])
st.subheader("Monthly Average Deals Per Agent & Active Agents for Top 10 Firms")
st.dataframe(final_table)

# ----------------------- Monthly Market Share Visualization -----------------------

st.header("Monthly Market Share by Firm (%) - Top 10 + Noralta")

# Reuse market_data with Month column
# Compute deals per firm (listing and buyer) across the whole market
monthly_deals_listing = (
    market_data.groupby(["listing_firm", "Month"]).size().reset_index(name="Deals")
).rename(columns={"listing_firm": "Firm"})
monthly_deals_buyer = (
    market_data.groupby(["buyer_firm", "Month"]).size().reset_index(name="Deals")
).rename(columns={"buyer_firm": "Firm"})

all_monthly_deals = pd.concat([monthly_deals_listing, monthly_deals_buyer], axis=0)
all_monthly_deals = all_monthly_deals.groupby(["Firm", "Month"], as_index=False)["Deals"].sum()

# Get total monthly deals across market
total_monthly_deals = market_data.groupby("Month", as_index=False).size().rename(columns={"size": "Total Deals"})
total_monthly_deals.columns = ["Month", "Total Deals"]

market_share = pd.merge(all_monthly_deals, total_monthly_deals, on="Month")
market_share["Market Share (%)"] = (market_share["Deals"] / market_share["Total Deals"]) * 100

# Determine top 10 firms by overall market share
overall_market_share = market_share.groupby("Firm", as_index=False)["Market Share (%)"].sum()
top_market_firms = overall_market_share.sort_values("Market Share (%)", ascending=False).head(10)["Firm"].tolist()

# Ensure the highlighted firm is included
highlight_firm = "Royal LePage Noralta Real Estate"
if highlight_firm not in top_market_firms:
    top_market_firms.append(highlight_firm)

market_share_top = market_share[market_share["Firm"].isin(top_market_firms)].drop_duplicates(subset=["Firm", "Month"])

fig_market_share = px.line(
    market_share_top,
    x='Month',
    y='Market Share (%)',
    color='Firm',
    markers=True,
    title="Monthly Market Share by Firm (%) - Top 10 + Noralta"
)
fig_market_share.update_layout(
    xaxis_title="Month",
    yaxis_title="Market Share (%)",
    legend_title="Firm",
    margin=dict(b=120)
)
fig_market_share.update_xaxes(tickformat="%Y-%m-%d")
st.plotly_chart(fig_market_share, use_container_width=True)

# ----------------------- Highlighted Bar Charts for Brokerages -----------------------

# Function to create a bar chart with highlighted brokerage
def create_highlighted_bar_chart(df, x_col, y_col, title):
    """
    Creates a bar chart where 'Royal LePage Noralta Real Estate' (the highlighted brokerage)
    is shown in red while all others are in royalblue.
    """
    df = df.copy()
    df["Color"] = df[x_col].apply(lambda x: "red" if x == highlight_firm else "royalblue")
    df = df.sort_values(by=y_col, ascending=False)
    fig = px.bar(
        df,
        x=x_col,
        y=y_col,
        title=title,
        text_auto=True,
        color="Color",
        category_orders={x_col: df[x_col].tolist()},
        color_discrete_map={"red": "red", "royalblue": "royalblue"}
    )
    return fig

# --- Top 10 Brokerages Combined (Buyer & Listing) ---
if "listing_firm" in filtered_data.columns and "buyer_firm" in filtered_data.columns:
    listing_deals = filtered_data["listing_firm"].value_counts().rename("Listing Deals")
    buyer_deals = filtered_data["buyer_firm"].value_counts().rename("Buyer Deals")

    combined_deals = pd.DataFrame({"Brokerage": listing_deals.index}).merge(
        listing_deals, left_on="Brokerage", right_index=True, how="outer"
    ).merge(
        pd.DataFrame({"Brokerage": buyer_deals.index}).merge(
            buyer_deals, left_on="Brokerage", right_index=True, how="outer"
        ),
        on="Brokerage",
        how="outer"
    ).fillna(0)

    combined_deals["Total Deals"] = combined_deals["Listing Deals"] + combined_deals["Buyer Deals"]
    combined_deals = combined_deals.sort_values(by="Total Deals", ascending=False).head(10)

    st.subheader("Top 10 Brokerages (Buyer & Listing Combined)")
    if not combined_deals.empty:
        fig_combined = create_highlighted_bar_chart(
            combined_deals,
            x_col="Brokerage",
            y_col="Total Deals",
            title="(Buyer & Listing) Top 10 Brokerages by Total Deals"
        )
        st.plotly_chart(fig_combined)
    else:
        st.warning("No data available for the selected filters.")
else:
    st.warning("Required columns for combined deals analysis are missing.")

# --- Top 10 Listing Firms ---
if "listing_firm" in filtered_data.columns:
    listing_deals = filtered_data["listing_firm"].value_counts().reset_index()
    listing_deals.columns = ["Brokerage", "Number of Deals"]
    listing_deals = listing_deals.sort_values(by="Number of Deals", ascending=False).head(10)
    st.subheader("Listing Side - Top 10 Brokerages with Most Deals")
    if not listing_deals.empty:
        fig_listing = create_highlighted_bar_chart(
            listing_deals,
            x_col="Brokerage",
            y_col="Number of Deals",
            title="Top 10 Brokerages by Deals (Listing Side)"
        )
        st.plotly_chart(fig_listing)
    else:
        st.warning("No data available for the selected filters.")
else:
    st.warning("Column 'listing_firm' not found in the data.")

# --- Top 10 Buyer Firms ---
if "buyer_firm" in filtered_data.columns:
    buyer_deals = filtered_data["buyer_firm"].value_counts().reset_index()
    buyer_deals.columns = ["Brokerage", "Number of Deals"]
    buyer_deals = buyer_deals.sort_values(by="Number of Deals", ascending=False).head(10)
    st.subheader("Buyers Side - Top 10 Brokerages with Most Deals")
    if not buyer_deals.empty:
        fig_buyer = create_highlighted_bar_chart(
            buyer_deals,
            x_col="Brokerage",
            y_col="Number of Deals",
            title="Top 10 Buyer Brokerages by Deals"
        )
        st.plotly_chart(fig_buyer)
    else:
        st.warning("No data available for the selected filters.")
else:
    st.warning("Column 'buyer_firm' not found in the data.")