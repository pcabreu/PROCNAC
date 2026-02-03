import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Gestão Nacionalidade v2.0", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Lê a aba NACIONALIDADE
    data = conn.read(worksheet="NACIONALIDADE", ttl="0")
    
    # LIMPEZA DE CABEÇALHO: Pula a linha de título se necessário e padroniza
    # Se a primeira linha for o título 'CONTROLE...', usamos a próxima como header
    if "CONTROLE" in str(data.columns[1]):
        data.columns = data.iloc[0]
        data = data.iloc[1:].reset_index(drop=True)

    # PADRONIZAÇÃO DE COLUNAS: Maiúsculo, sem espaços extras, sem acentos e troca espaço por '_'
    data.columns = [
        str(c).strip().upper()
        .replace(' ', '_')
        .replace('É', 'E')
        .replace('Á', 'A')
        .replace('Ç', 'C')
        .replace('Õ', 'O')
        .replace('-', '_') 
        for c in data.columns
    ]
    
    # Remove linhas onde o Requerente está vazio
    if 'REQUERENTE' in data.columns:
        data = data.dropna(subset=['REQUERENTE'])
    
    return data

# Carrega os dados
df = load_data()

# --- BARRA LATERAL ---
st.sidebar.title("Nacionalidade App 2.0")
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "➕ Inclusão", "📝 Gerenciar Registros"])

# --- MODULO 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Resumo dos Processos")
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        
        # Métricas Seguras
        total = len(df)
        status_col = 'STATUS' if 'STATUS' in df.columns else df.columns[0]
        concluidos = len(df[df[status_col].str.contains('CONCLUÍDO', na=False, case=False)])
        
        col1.metric("Total de Processos", total)
        col2.metric("Concluídos", concluidos)
        
        # Financeiro
        pago_col = 'VALOR_PAGO' if 'VALOR_PAGO' in df.columns else None
        saldo_col = 'SALDO_DEVEDOR' if 'SALDO_DEVEDOR' in df.columns else None
        
        val_pago = pd.to_numeric(df[pago_col], errors='coerce').sum() if pago_col else 0
        val_saldo = pd.to_numeric(df[saldo_col], errors='coerce').sum() if saldo_col else 0
        
        col3.metric("Total Pago", f"R$ {val_pago:,.2f}")
        col4.metric("Saldo Devedor", f"R$ {val_saldo:,.2f}")

        st.divider()
        
        # Gráficos
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(df, names=status_col, title="Status dos Processos", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            artigo_col = 'ARTIGO' if 'ARTIGO' in df.columns else df.columns[0]
            fig2 = px.bar(df, x=artigo_col, title="Processos por Artigo")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Nenhum dado encontrado para gerar o dashboard.")

# --- MODULO 2: INCLUSÃO ---
elif menu == "➕ Inclusão":
    st.header("Cadastrar Novo Processo")
    
    with st.form("form_inclusao", clear_on_submit=True):
        c1, c2 = st.columns(2)
        
        with c1:
            num_proc = st.text_input("Número do Processo")
            requerente = st.text_input("Nome do Requerente")
            aniversario = st.date_input("Aniversário", min_value=datetime(1900, 1, 1))
            cliente = st.text_input("Cliente")
            email = st.text_input("e-Mail")
            
        with c2:
            artigo = st.selectbox("Artigo", ["Art. 1º, nº1, al. d (neto)", "Art. 1º, nº1, al. c (filho)", "Casamento", "Outros"])
            status = st.selectbox("Status", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
            valor_pago = st.number_input("Valor Pago (R$)", min_value=0.0, step=100.0)
            saldo_dev = st.number_input("Saldo Devedor (R$)", min_value=0.0, step=100.0)
        
        observacoes = st.text_area("Observações")
        
        btn_salvar = st.form_submit_button("Salvar na Planilha")
        
        if btn_salvar:
            if requerente:
                # Cria linha para adicionar
                nova_linha = pd.DataFrame([{
                    "NUMERO_DO_PROCESSO": num_proc,
                    "REQUERENTE": requerente,
                    "ANIVERSARIO": aniversario.strftime('%d/%m/%Y'),
                    "CLIENTE": cliente,
                    "E_MAIL": email,
                    "ARTIGO": artigo,
                    "STATUS": status,
                    "VALOR_PAGO": valor_pago,
                    "SALDO_DEVEDOR": saldo_dev,
                    "OBSERVACOES": observacoes
                }])
                
                # Junta com os dados existentes e faz update
                df_updated = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(worksheet="NACIONALIDADE", data=df_updated)
                
                st.success(f"Processo de {requerente} salvo com sucesso!")
                st.cache_data.clear()
            else:
                st.error("O campo 'Requerente' é obrigatório.")

# --- MODULO 3: GERENCIAR (EDITAR / EXCLUIR) ---
elif menu == "📝 Gerenciar Registros":
    st.header("Editar ou Excluir Processos")
    
    if df.empty:
        st.warning("Não há registros para editar.")
    else:
        # Busca por Requerente
        lista_nomes = df['REQUERENTE'].unique()
        selecionado = st.selectbox("Selecione o Requerente", lista_nomes)
        
        # Filtra os dados do selecionado com segurança
        dados_selecionados = df[df['REQUERENTE'] == selecionado]
        
        if not dados_selecionados.empty:
            item = dados_selecionados.iloc[0]
            
            with st.expander(f"Dados Atuais de {selecionado}", expanded=True):
                c1, c2 = st.columns(2)
                
                with c1:
                    ed_proc = st.text_input("Número Processo", value=str(item.get('NUMERO_DO_PROCESSO', '')))
                    ed_niver = st.text_input("Aniversário (Atual)", value=str(item.get('ANIVERSARIO', '')))
                    ed_cliente = st.text_input("Cliente", value=str(item.get('CLIENTE', '')))
                    ed_email = st.text_input("e-Mail", value=str(item.get('E_MAIL', '')))
                
                with c2:
                    ed_status = st.selectbox("Alterar Status", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
                    ed_pago = st.number_input("Valor Pago", value=float(pd.to_numeric(item.get('VALOR_PAGO', 0), errors='coerce')))
                    ed_saldo = st.number_input("Saldo Devedor", value=float(pd.to_numeric(item.get('SALDO_DEVEDOR', 0), errors='coerce')))
                
                ed_obs = st.text_area("Observações", value=str(item.get('OBSERVACOES', '')))
                
                col_btn1, col_btn2 = st.columns(2)
                
                if col_btn1.button("💾 Salvar Alterações"):
                    # Atualiza o DataFrame
                    idx = df[df['REQUERENTE'] == selecionado].index
                    df.loc[idx, 'NUMERO_DO_PROCESSO'] = ed_proc
                    df.loc[idx, 'ANIVERSARIO'] = ed_niver
                    df.loc[idx, 'CLIENTE'] = ed_cliente
                    df.loc[idx, 'E_MAIL'] = ed_email
                    df.loc[idx, 'STATUS'] = ed_status
                    df.loc[idx, 'VALOR_PAGO'] = ed_pago
                    df.loc[idx, 'SALDO_DEVEDOR'] = ed_saldo
                    df.loc[idx, 'OBSERVACOES'] = ed_obs
                    
                    conn.update(worksheet="NACIONALIDADE", data=df)
                    st.success("Alterações salvas!")
                    st.cache_data.clear()
                    st.rerun()

                if col_btn2.button("🗑️ Excluir Registro", type="primary"):
                    df = df[df['REQUERENTE'] != selecionado]
                    conn.update(worksheet="NACIONALIDADE", data=df)
                    st.warning("Registro excluído!")
                    st.cache_data.clear()
                    st.rerun()