import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

###    git add . ; git commit -m "new dash3" ; git push origin main  


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
def get_dynamodb_data():
    """Fetch data from DynamoDB and convert it to a Pandas DataFrame."""
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

        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

        return pd.DataFrame(items)

    except Exception as e:
        st.error(f"Failed to fetch data from DynamoDB: {str(e)}")
        return pd.DataFrame()

# Load data from AWS DynamoDB
listings_data = get_dynamodb_data()

# Ensure data is loaded
if listings_data.empty:
    st.error("No data available to display!")
    st.stop()

# Convert 'sold_date' to datetime format and remove time part
listings_data["sold_date"] = pd.to_datetime(listings_data["sold_date"], errors="coerce").dt.normalize()

# Drop rows with invalid 'sold_date' values to prevent issues in filtering/grouping
listings_data = listings_data.dropna(subset=["sold_date"])

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







import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

# -----------------------------
# Assume your existing code has already:
# - Loaded filtered_data from your "real_estate_listings" table.
# - Defined the sidebar filters (start_date, end_date, etc.).
# -----------------------------

# Function to fetch brokerage data from DynamoDB
@st.cache_data
def get_brokerage_data():
    """Fetch data from the 'brokerage' table in DynamoDB."""
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
        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"Failed to fetch brokerage data: {str(e)}")
        return pd.DataFrame()

# Fetch brokerage data and process it
brokerage_data = get_brokerage_data()

if brokerage_data.empty:
    st.error("No brokerage data available!")
else:
    # Convert the 'Date' column to datetime and filter by the same date range
    brokerage_data["Date"] = pd.to_datetime(brokerage_data["Date"], errors="coerce").dt.normalize()
    brokerage_data = brokerage_data[
        (brokerage_data["Date"] >= pd.to_datetime(start_date)) &
        (brokerage_data["Date"] <= pd.to_datetime(end_date))
    ]
    
    # Process brokerage data and compute the average agents per firm
    brokerage_data["Date"] = pd.to_datetime(brokerage_data["Date"], errors="coerce").dt.normalize()
    brokerage_data = brokerage_data[
        (brokerage_data["Date"] >= pd.to_datetime(start_date)) &
        (brokerage_data["Date"] <= pd.to_datetime(end_date))
    ]
    agents_avg = brokerage_data.groupby("firm")["Value"].mean().reset_index()
    agents_avg.columns = ["Brokerage", "Avg_Agents"]

    # Ensure the highlighted firm has an Avg_Agents value even when its data is missing.
    highlight_firm = "Royal LePage Noralta Real Estate"
    if highlight_firm not in agents_avg["Brokerage"].values:
        # Assign a default average agents value; update default_agents as needed.
        default_agents = 1  # Set to a sensible default if real data is missing.
        agents_avg = pd.concat(
            [agents_avg, pd.DataFrame({"Brokerage": [highlight_firm], "Avg_Agents": [default_agents]})],
            ignore_index=True
        )

    # ------------------------------------------------------------
    # Process listings data to get monthly deals per firm.
    # Both listing and buyer deals are included.
    # ------------------------------------------------------------
    
# ----- Cumulative Deals per Agent Over Time (Daily) -----
# Combine listing and buyer deals and add a deal_count column
listing_deals_df = filtered_data[["sold_date", "listing_firm"]].copy()
listing_deals_df.rename(columns={"listing_firm": "Brokerage"}, inplace=True)
listing_deals_df["deal_count"] = 1

buyer_deals_df = filtered_data[["sold_date", "buyer_firm"]].copy()
buyer_deals_df.rename(columns={"buyer_firm": "Brokerage"}, inplace=True)
buyer_deals_df["deal_count"] = 1

all_deals = pd.concat([listing_deals_df, buyer_deals_df])

# Group daily deals per firm
daily_deals = all_deals.groupby(["Brokerage", "sold_date"], as_index=False)["deal_count"].sum()

# Determine the top 10 firms by total deals and always include the highlighted firm
total_deals = all_deals.groupby("Brokerage")["deal_count"].sum().reset_index().sort_values("deal_count", ascending=False)
top10_firms = total_deals.head(10)["Brokerage"].tolist()
highlight_firm = "Royal LePage Noralta Real Estate"
if highlight_firm not in top10_firms:
    top10_firms.append(highlight_firm)

# Create a full daily date range from the first to the last sold date in the filtered data
date_range = pd.date_range(filtered_data["sold_date"].min(), filtered_data["sold_date"].max(), freq="D")

# For each top firm, reindex its daily deals along the full date range
cum_list = []
for firm in top10_firms:
    firm_data = daily_deals[daily_deals["Brokerage"] == firm].set_index("sold_date")
    firm_data = firm_data.reindex(date_range, fill_value=0).reset_index().rename(columns={"index": "sold_date"})
    firm_data["Brokerage"] = firm
    firm_data["cumulative_deals"] = firm_data["deal_count"].cumsum()
    cum_list.append(firm_data)
cum_deals_df = pd.concat(cum_list, ignore_index=True)

# Merge with agents average data and compute deals per agent
cum_deals_df = cum_deals_df.merge(agents_avg, on="Brokerage", how="left")
cum_deals_df["deals_per_agent"] = cum_deals_df["cumulative_deals"] / cum_deals_df["Avg_Agents"]

# Plot the cumulative deals per agent line chart
fig_cum = px.line(
    cum_deals_df,
    x="sold_date",
    y="deals_per_agent",
    color="Brokerage",
    title="Cumulative Deals per Agent Over Time (Top 10 Firms + Noralta)",
    labels={"sold_date": "Sold Date", "deals_per_agent": "Deals per Agent", "Brokerage": "Firm"}
)
fig_cum.update_xaxes(tickformat="%Y-%m-%d")
st.plotly_chart(fig_cum)












import streamlit as st
import pandas as pd
import plotly.express as px
import boto3
from datetime import datetime

# -------------------------------------------
# Assuming your app already has:
# - filtered_data from your "real_estate_listings" table filtered by the sidebar date range.
# - The sidebar date inputs: start_date, end_date, etc.
# - The get_aws_credentials() function from your existing code.
# -------------------------------------------

# Function to fetch brokerage data from DynamoDB
@st.cache_data
def get_brokerage_data():
    """Fetch data from the 'brokerage' table in DynamoDB."""
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
        items, last_evaluated_key = [], None
        while True:
            response = table.scan(ExclusiveStartKey=last_evaluated_key) if last_evaluated_key else table.scan()
            items.extend(response.get("Items", []))
            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break
        return pd.DataFrame(items)
    except Exception as e:
        st.error(f"Failed to fetch brokerage data: {str(e)}")
        return pd.DataFrame()

# Fetch brokerage data and process it
brokerage_data = get_brokerage_data()

if brokerage_data.empty:
    st.error("No brokerage data available!")
else:
    # Convert the 'Date' column to datetime and filter by the same date range
    brokerage_data["Date"] = pd.to_datetime(brokerage_data["Date"], errors="coerce").dt.normalize()
    brokerage_data = brokerage_data[
        (brokerage_data["Date"] >= pd.to_datetime(start_date)) &
        (brokerage_data["Date"] <= pd.to_datetime(end_date))
    ]
    
    # Process brokerage data and compute the average agents per firm
    brokerage_data["Date"] = pd.to_datetime(brokerage_data["Date"], errors="coerce").dt.normalize()
    brokerage_data = brokerage_data[
        (brokerage_data["Date"] >= pd.to_datetime(start_date)) &
        (brokerage_data["Date"] <= pd.to_datetime(end_date))
    ]
    agents_avg = brokerage_data.groupby("firm")["Value"].mean().reset_index()
    agents_avg.columns = ["Brokerage", "Avg_Agents"]

    # Ensure the highlighted firm has an Avg_Agents value even when its data is missing.
    highlight_firm = "Royal LePage Noralta Real Estate"
    if highlight_firm not in agents_avg["Brokerage"].values:
        # Assign a default average agents value; update default_agents as needed.
        default_agents = 1  # Set to a sensible default if real data is missing.
        agents_avg = pd.concat(
            [agents_avg, pd.DataFrame({"Brokerage": [highlight_firm], "Avg_Agents": [default_agents]})],
            ignore_index=True
        )

    # ------------------------------------------------------------
    # Process listings data to get monthly deals per firm.
    # Both listing and buyer deals are included.
    # ------------------------------------------------------------
    
    # Prepare listing deals
    listing_deals_df = filtered_data[["sold_date", "listing_firm"]].copy()
    listing_deals_df = listing_deals_df.rename(columns={"listing_firm": "Brokerage"})
    listing_deals_df["deal_count"] = 1

    # Prepare buyer deals
    buyer_deals_df = filtered_data[["sold_date", "buyer_firm"]].copy()
    buyer_deals_df = buyer_deals_df.rename(columns={"buyer_firm": "Brokerage"})
    buyer_deals_df["deal_count"] = 1

    # Combine listing and buyer deals
    all_deals = pd.concat([listing_deals_df, buyer_deals_df])
    
# ----- Monthly Deals per Agent -----
# Create a 'month' column for month-level aggregation
all_deals["month"] = pd.to_datetime(all_deals["sold_date"]).dt.to_period("M").dt.to_timestamp()

# Group monthly deals per firm
monthly_deals = all_deals.groupby(["Brokerage", "month"], as_index=False)["deal_count"].sum()

# Determine the top 10 firms and include highlighted firm
total_deals = all_deals.groupby("Brokerage")["deal_count"].sum().reset_index().sort_values("deal_count", ascending=False)
top10_firms = total_deals.head(10)["Brokerage"].tolist()
if highlight_firm not in top10_firms:
    top10_firms.append(highlight_firm)

# Create full month range
min_month = pd.to_datetime(filtered_data["sold_date"]).dt.to_period("M").min().to_timestamp()
max_month = pd.to_datetime(filtered_data["sold_date"]).dt.to_period("M").max().to_timestamp()
month_range = pd.date_range(min_month, max_month, freq="MS")

# Reindex monthly deals for each top firm
monthly_list = []
for firm in top10_firms:
    firm_monthly = monthly_deals[monthly_deals["Brokerage"] == firm].set_index("month")
    firm_monthly = firm_monthly.reindex(month_range, fill_value=0).reset_index().rename(columns={"index": "month"})
    firm_monthly["Brokerage"] = firm
    monthly_list.append(firm_monthly)
monthly_deals_df = pd.concat(monthly_list, ignore_index=True)

# Calculate deals per agent
monthly_deals_df = monthly_deals_df.merge(agents_avg, on="Brokerage", how="left")
monthly_deals_df["deals_per_agent"] = monthly_deals_df["deal_count"] / monthly_deals_df["Avg_Agents"]

# Plot monthly deals
fig_month = px.line(
    monthly_deals_df,
    x="month",
    y="deals_per_agent",
    color="Brokerage",
    title="Monthly Deals per Agent (Top 10 Firms + Noralta)",
    labels={"month": "Month", "deals_per_agent": "Deals per Agent", "Brokerage": "Firm"}
)
fig_month.update_xaxes(tickformat="%Y-%m-%d")
st.plotly_chart(fig_month)












# ---------------------------------------------
# Visualization: Monthly Market Share by Firm (%) - Whole Market
# ---------------------------------------------
st.header("Monthly Market Share by Firm (%) - Top 10 + Noralta")

# Create a copy of filtered_data and add a Month column
market_data = filtered_data.copy()
market_data['Month'] = market_data['sold_date'].dt.to_period('M').dt.to_timestamp()

# Calculate monthly deals per firm for the listing side
monthly_deals_listing = (
    market_data.groupby(['listing_firm', 'Month']).size().reset_index(name='Deals')
)
# Calculate monthly deals per firm for the buyer side
monthly_deals_buyer = (
    market_data.groupby(['buyer_firm', 'Month']).size().reset_index(name='Deals')
)

# Standardize the firm column names for merging
monthly_deals_listing = monthly_deals_listing.rename(columns={'listing_firm': 'Firm'})
monthly_deals_buyer = monthly_deals_buyer.rename(columns={'buyer_firm': 'Firm'})

# Combine the two dataframes (all deals, across the whole market)
all_monthly_deals = pd.concat([monthly_deals_listing, monthly_deals_buyer], axis=0)
all_monthly_deals = all_monthly_deals.groupby(['Firm', 'Month'])['Deals'].sum().reset_index()

# Calculate total deals for each month across the whole market
total_monthly_deals = market_data.groupby('Month').size().reset_index(name='Total Deals')

# Merge firm-level deals with total monthly deals so that each firm's market share is relative to the entire market
market_share = pd.merge(all_monthly_deals, total_monthly_deals, on='Month')
market_share['Market Share (%)'] = (market_share['Deals'] / market_share['Total Deals']) * 100

# Determine the top 10 firms by overall market share (summing market share across months)
overall_market_share = market_share.groupby('Firm')['Market Share (%)'].sum().reset_index()
top_firms = overall_market_share.sort_values('Market Share (%)', ascending=False).head(10)['Firm'].tolist()

# Ensure the highlighted firm is included
highlight_firm = "Royal LePage Noralta Real Estate"
if highlight_firm not in top_firms:
    top_firms.append(highlight_firm)

# Filter the market share data to only include the top firms (from the whole market)
market_share_top = market_share[market_share['Firm'].isin(top_firms)].drop_duplicates(subset=['Firm', 'Month'])

# Create a line chart showing monthly market share for the selected firms
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




