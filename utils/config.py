import os
import streamlit as st
import json

def get_aws_credentials():
    """
    Get AWS credentials from either Streamlit secrets or environment variables.
    Returns a tuple of (access_key, secret_key, region)
    """
    # Debug: Print out all available secrets
    try:
        st.write("Available Secrets:", json.dumps(dict(st.secrets), indent=2))
    except Exception as e:
        st.write(f"Error accessing secrets: {e}")

    # Try multiple ways to access credentials
    aws_access_key = None
    aws_secret_key = None
    aws_region = "us-east-2"

    # Multiple access methods
    credential_attempts = [
        # Direct root-level access
        lambda: (st.secrets.get("AWS_ACCESS_KEY_ID"), st.secrets.get("AWS_SECRET_ACCESS_KEY")),
        
        # AWS section access
        lambda: (st.secrets.get("aws", {}).get("AWS_ACCESS_KEY_ID"), 
                 st.secrets.get("aws", {}).get("AWS_SECRET_ACCESS_KEY")),
        
        # Dictionary-style access
        lambda: (st.secrets.get("AWS_ACCESS_KEY_ID"), st.secrets.get("AWS_SECRET_ACCESS_KEY")),
        
        # Environment variables fallback
        lambda: (os.environ.get("AWS_ACCESS_KEY_ID"), os.environ.get("AWS_SECRET_ACCESS_KEY"))
    ]

    # Try each method to get credentials
    for attempt in credential_attempts:
        try:
            aws_access_key, aws_secret_key = attempt()
            if aws_access_key and aws_secret_key:
                break
        except Exception as e:
            st.write(f"Credentials attempt failed: {e}")

    # Verify we have the required credentials
    if not aws_access_key or not aws_secret_key:
        error_message = """
        AWS credentials not found. Please configure:
        1. Streamlit Cloud Secrets with:
           - AWS_ACCESS_KEY_ID
           - AWS_SECRET_ACCESS_KEY
        2. Or set environment variables:
           - AWS_ACCESS_KEY_ID
           - AWS_SECRET_ACCESS_KEY
        
        Current available secrets: {}
        """.format(list(st.secrets.keys()) if hasattr(st, 'secrets') else "No secrets found")
        
        st.error(error_message)
        raise ValueError(error_message)

    return aws_access_key, aws_secret_key, aws_region