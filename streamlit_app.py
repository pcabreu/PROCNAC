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
    
    # 1. Definir o nome correto da coluna (usando o que padronizamos anteriormente)
    # Se você usou o código de limpeza anterior, a coluna agora é 'REQUERENTE'
    col_nome = 'REQUERENTE' if 'REQUERENTE' in df.columns else 'Requerente'
    
    if df.empty:
        st.warning("A planilha parece estar vazia ou não foi carregada corretamente.")
    else:
        # 2. Criar a lista de seleção
        lista_requerentes = df[col_nome].dropna().unique()
        selecao = st.selectbox("Selecione o Requerente para editar", lista_requerentes)
        
        # 3. Filtrar com segurança (Evita o erro de 'out-of-bounds')
        dados_filtrados = df[df[col_nome] == selecao]
        
        if not dados_filtrados.empty:
            item_data = dados_filtrados.iloc[0] # Agora é seguro usar o índice 0
            
            with st.expander(f"Editar dados de: {selecao}"):
                # Usamos .get() para não quebrar se a coluna sumir
                status_atual = item_data.get('STATUS', 'N/A')
                st.info(f"Status atual: {status_atual}")
                
                novo_status = st.selectbox("Novo Status", 
                                         ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
                
                if st.button("Salvar Alteração"):
                    # Atualiza o DataFrame original
                    df.loc[df[col_nome] == selecao, 'STATUS'] = novo_status
                    conn.update(worksheet="NACIONALIDADE", data=df)
                    st.success("Alteração salva com sucesso!")
                    st.cache_data.clear() # Limpa o cache para atualizar o Dashboard
        else:
            st.error("Não encontramos dados para este Requerente. Tente atualizar a página.")
