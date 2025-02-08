import boto3
session = boto3.Session()
credentials = session.get_credentials()

if credentials is None:
    print("No AWS credentials found!")
else:
    print("AWS credentials found!")
