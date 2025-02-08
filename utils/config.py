import os
import streamlit as st

def get_aws_credentials():
    """
    Get AWS credentials from Streamlit secrets.
    Returns a tuple of (access_key, secret_key, region)
    """
    # Debugging: Print available secret keys
    st.write("Available Secrets Keys:", list(st.secrets.keys()))

    # Credential retrieval methods
    credential_methods = [
        # 1. Direct root-level access
        lambda: (
            st.secrets.get("AWS_ACCESS_KEY_ID"),
            st.secrets.get("AWS_SECRET_ACCESS_KEY")
        ),
        
        # 2. AWS section access
        lambda: (
            st.secrets.get("aws", {}).get("AWS_ACCESS_KEY_ID"),
            st.secrets.get("aws", {}).get("AWS_SECRET_ACCESS_KEY")
        ),
        
        # 3. Environment variables fallback
        lambda: (
            os.environ.get("AWS_ACCESS_KEY_ID"),
            os.environ.get("AWS_SECRET_ACCESS_KEY")
        )
    ]

    # Try each credential retrieval method
    for method in credential_methods:
        try:
            aws_access_key, aws_secret_key = method()
            if aws_access_key and aws_secret_key:
                # Mask the keys for logging
                masked_access_key = f"{aws_access_key[:4]}...{aws_access_key[-4:]}"
                st.info(f"AWS Access Key found: {masked_access_key}")
                return aws_access_key, aws_secret_key, "us-east-2"
        except Exception as e:
            st.write(f"Credential method failed: {e}")

    # If no credentials found
    error_message = """
    ❌ AWS Credentials Configuration Error ❌

    Credentials could not be found. Please configure:

    Option 1: Streamlit Cloud Secrets
    - Add AWS_ACCESS_KEY_ID
    - Add AWS_SECRET_ACCESS_KEY

    Option 2: Environment Variables
    - Set AWS_ACCESS_KEY_ID
    - Set AWS_SECRET_ACCESS_KEY

    Current available secret keys: {}
    """.format(list(st.secrets.keys()))
    
    st.error(error_message)
    raise ValueError(error_message)