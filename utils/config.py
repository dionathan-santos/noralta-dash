import os
import streamlit as st

def get_aws_credentials():
    """
    Get AWS credentials from either Streamlit secrets or environment variables.
    Returns a tuple of (access_key, secret_key, region)
    """
    # Try to get from Streamlit secrets first
    try:
        aws_access_key = st.secrets["AWS_ACCESS_KEY_ID"]
        aws_secret_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
        aws_region = st.secrets.get("AWS_REGION", "us-east-2")
    except Exception:
        # If not in secrets, try environment variables
        aws_access_key = os.environ.get("AWS_ACCESS_KEY_ID")
        aws_secret_key = os.environ.get("AWS_SECRET_ACCESS_KEY")
        aws_region = os.environ.get("AWS_REGION", "us-east-2")

    # Verify we have the required credentials
    if not aws_access_key or not aws_secret_key:
        raise ValueError("""
            AWS credentials not found. Please configure either:
            1. Streamlit secrets with AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
            2. Environment variables AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY
        """)

    return aws_access_key, aws_secret_key, aws_region