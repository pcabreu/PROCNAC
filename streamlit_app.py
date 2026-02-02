import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Gestão de Nacionalidade", layout="wide")

# Conexão com a planilha
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # ttl=0 garante que os dados não fiquem em cache e sejam sempre lidos do Google Sheets
    return conn.read(worksheet="NACIONALIDADE", ttl="0")

df = load_data()

# --- BARRA LATERAL ---
st.sidebar.title("Nacionalidade App")
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "➕ Novo Processo", "📝 Gerenciar Registros"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Indicadores de Processos")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total de Processos", len(df))
    col2.metric("Processos Concluídos", len(df[df['Status'] == 'CONCLUÍDO']))
    
    # Cálculo financeiro simples (removendo símbolos de moeda se existirem)
    total_pago = pd.to_numeric(df['Valor_Pago'], errors='coerce').sum()
    col3.metric("Total Recebido", f"R$ {total_pago:,.2f}")
    
    saldo_total = pd.to_numeric(df['Saldo_Devedor'], errors='coerce').sum()
    col4.metric("Saldo a Receber", f"R$ {saldo_total:,.2f}")

    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        fig_status = px.pie(df, names='Status', title='Distribuição por Status', hole=0.4)
        st.plotly_chart(fig_status)
    with c2:
        fig_artigo = px.bar(df, x='Artigo', title='Processos por Artigo/Tipo')
        st.plotly_chart(fig_artigo)

# --- INCLUSÃO ---
elif menu == "➕ Novo Processo":
    st.header("Cadastrar Novo Requerente")
    with st.form("add_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            processo = st.text_input("Número do Processo")
            requerente = st.text_input("Nome do Requerente")
            artigo = st.selectbox("Artigo", ["Neto", "Filho", "Casamento", "Outros"])
        with col2:
            status = st.selectbox("Status Atual", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
            valor_pago = st.number_input("Valor Pago", min_value=0.0)
        
        obs = st.text_area("Observações")
        
        if st.form_submit_button("Salvar na Planilha"):
            new_row = pd.DataFrame([{
                "ID": len(df) + 1, "Processo": processo, "Requerente": requerente,
                "Artigo": artigo, "Status": status, "Valor_Pago": valor_pago, "Observacoes": obs
            }])
            updated_df = pd.concat([df, new_row], ignore_index=True)
            conn.update(worksheet="NACIONALIDADE", data=updated_df)
            st.success("Processo cadastrado com sucesso!")
            st.cache_data.clear()

# --- ALTERAÇÃO / EXCLUSÃO ---
elif menu == "📝 Gerenciar Registros":
    st.header("Editar ou Excluir Processos")
    
    # Seleção do registro pelo Requerente
    selecao = st.selectbox("Selecione o Requerente para editar", df['Requerente'].unique())
    item_data = df[df['Requerente'] == selecao].iloc[0]
    
    with st.expander(f"Editar dados de: {selecao}"):
        novo_status = st.selectbox("Alterar Status", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"], 
                                   index=["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"].index(item_data['Status']))
        novo_saldo = st.number_input("Atualizar Saldo Devedor", value=float(item_data['Saldo_Devedor']) if pd.notnull(item_data['Saldo_Devedor']) else 0.0)
        
        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("Confirmar Alterações"):
            df.loc[df['Requerente'] == selecao, 'Status'] = novo_status
            df.loc[df['Requerente'] == selecao, 'Saldo_Devedor'] = novo_saldo
            conn.update(worksheet="NACIONALIDADE", data=df)
            st.success("Dados atualizados!")
            
        if col_btn2.button("❌ EXCLUIR PROCESSO", type="primary"):
            df = df[df['Requerente'] != selecao]
            conn.update(worksheet="NACIONALIDADE", data=df)
            st.warning("Registro removido.")
            st.rerun()