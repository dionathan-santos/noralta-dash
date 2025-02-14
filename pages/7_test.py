import streamlit as st
import pandas as pd
import boto3

# Configurar título e layout da página
st.set_page_config(page_title="Brokerage Performance Analysis", layout="wide")
st.title("Brokerage Performance Analysis")

# Recuperar as credenciais da AWS dos secrets do Streamlit
try:
    aws_secrets = st.secrets["aws"]
    AWS_ACCESS_KEY_ID = aws_secrets["AWS_ACCESS_KEY_ID"]
    AWS_SECRET_ACCESS_KEY = aws_secrets["AWS_SECRET_ACCESS_KEY"]
    AWS_REGION = aws_secrets.get("AWS_REGION", "us-east-2")
    # Verifica se há token de sessão (credenciais temporárias)
    AWS_SESSION_TOKEN = aws_secrets.get("AWS_SESSION_TOKEN")
except Exception as e:
    st.error("Erro ao recuperar as credenciais AWS dos secrets.")
    st.stop()

# Configurar o recurso DynamoDB, incluindo o token de sessão se existir
dynamodb_params = {
    'aws_access_key_id': AWS_ACCESS_KEY_ID,
    'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,
    'region_name': AWS_REGION
}
if AWS_SESSION_TOKEN:
    dynamodb_params['aws_session_token'] = AWS_SESSION_TOKEN

dynamodb = boto3.resource('dynamodb', **dynamodb_params)

# Lista das tabelas DynamoDB a serem escaneadas
table_names = ['brokerage', 'real_estate_listings']

# Dicionário para armazenar os dataframes
dataframes = {}

# Função para escanear uma tabela do DynamoDB e retornar os itens
def scan_table(table_name):
    try:
        table = dynamodb.Table(table_name)
        response = table.scan()
        data = response.get('Items', [])
        
        # Continuar escaneando se houver mais itens
        while 'LastEvaluatedKey' in response:
            response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            data.extend(response.get('Items', []))
        return data
    except Exception as e:
        st.error(f"Erro ao escanear a tabela '{table_name}': {e}")
        return []

# Criar um dataframe para cada tabela e armazená-lo no dicionário
for table_name in table_names:
    data = scan_table(table_name)
    if data:
        df = pd.DataFrame(data)
        dataframes[table_name] = df
        st.write(f"Dataframe criado para a tabela: {table_name}")
        st.write(df.head())  # Exibe as primeiras linhas do dataframe
    else:
        st.write(f"Não foi possível criar o dataframe para a tabela: {table_name}")

# Atribuir os dataframes a variáveis individuais (padrão para DataFrame vazio se não existir)
brokerage_df = dataframes.get('brokerage', pd.DataFrame())
real_estate_listings_df = dataframes.get('real_estate_listings', pd.DataFrame())

# Exibir os dataframes completos na página do Streamlit
st.subheader("Dados completos - Brokerage")
st.dataframe(brokerage_df)

st.subheader("Dados completos - Real Estate Listings")
st.dataframe(real_estate_listings_df)
