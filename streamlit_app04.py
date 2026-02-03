import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Gestão Nacionalidade v3.1", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    data = conn.read(worksheet="NACIONALIDADE", ttl="0")
    
    # PADRONIZAÇÃO DE CABEÇALHO
    if "CONTROLE" in str(data.columns[1]):
        data.columns = data.iloc[0]
        data = data.iloc[1:].reset_index(drop=True)

    data.columns = [
        str(c).strip().upper()
        .replace(' ', '_')
        .replace('É', 'E').replace('Á', 'A').replace('Ç', 'C').replace('Õ', 'O')
        .replace('/', '_').replace('-', '_').replace('__', '_')
        for c in data.columns
    ]
    
    if 'ID' in data.columns:
        data['ID'] = pd.to_numeric(data['ID'], errors='coerce')
    
    if 'REQUERENTE' in data.columns:
        data = data.dropna(subset=['REQUERENTE'])
    
    return data

# Função auxiliar para limpar o texto "nan"
def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan':
        return ""
    return str(val)

df = load_data()

# --- BARRA LATERAL ---
st.sidebar.title("Nacionalidade App 3.1")
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "➕ Inclusão", "📝 Gerenciar Registros"])

# --- MODULO 1: DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Painel de Indicadores")
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        total = len(df)
        status_col = 'STATUS' if 'STATUS' in df.columns else df.columns[0]
        concluidos = len(df[df[status_col].astype(str).str.contains('CONCLUÍDO', na=False, case=False)])
        
        col1.metric("Total de Processos", total)
        col2.metric("Concluídos", concluidos)
        
        pago_val = pd.to_numeric(df.get('VALOR_PAGO', 0), errors='coerce').sum()
        saldo_val = pd.to_numeric(df.get('SALDO_DEVEDOR', 0), errors='coerce').sum()
        
        col3.metric("Total Recebido", f"R$ {pago_val:,.2f}")
        col4.metric("Saldo em Aberto", f"R$ {saldo_val:,.2f}")
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            fig1 = px.pie(df, names=status_col, title="Distribuição por Status", hole=0.4)
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            art_col = 'ARTIGO' if 'ARTIGO' in df.columns else df.columns[0]
            fig2 = px.bar(df, x=art_col, title="Processos por Artigo/Tipo")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Aguardando dados.")

# --- MODULO 2: INCLUSÃO ---
elif menu == "➕ Inclusão":
    st.header("Novo Cadastro")
    proximo_id = int(df['ID'].max() + 1) if not df.empty and pd.notnull(df['ID'].max()) else 1
    st.info(f"Próximo ID: **{proximo_id}**")
    
    with st.form("form_inclusao", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            requerente = st.text_input("Nome do Requerente *")
            cliente = st.text_input("Cliente")
            email = st.text_input("e-Mail")
            aniversario = st.date_input("Aniversário", min_value=datetime(1900, 1, 1), format="DD/MM/YYYY")
        with c2:
            artigo = st.selectbox("Artigo", ["Art. 1º, nº1, al. d (neto)", "Art. 1º, nº1, al. c (filho)", "Casamento", "Outros"])
            status = st.selectbox("Status Inicial", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
            v_honorarios = st.number_input("Valor Honorários (R$)", min_value=0.0, step=100.0)
            v_pago = st.number_input("Valor Pago Inicial (R$)", min_value=0.0, step=100.0)
        
        observacoes = st.text_area("Observações")
        if st.form_submit_button("✅ Finalizar Inclusão"):
            if requerente:
                saldo_calc = v_honorarios - v_pago
                nova_linha = pd.DataFrame([{
                    "ID": proximo_id, "REQUERENTE": requerente, "CLIENTE": cliente, "E_MAIL": email,
                    "ANIVERSARIO": aniversario.strftime('%d/%m/%Y'), "ARTIGO": artigo, "STATUS": status,
                    "VALOR_HONORARIOS": v_honorarios, "VALOR_PAGO": v_pago, "SALDO_DEVEDOR": saldo_calc,
                    "OBSERVACOES": observacoes
                }])
                df_final = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(worksheet="NACIONALIDADE", data=df_final)
                st.success(f"Registro {proximo_id} salvo!")
                st.cache_data.clear()
            else:
                st.error("O nome do Requerente é obrigatório.")

# --- MODULO 3: GERENCIAR ---
elif menu == "📝 Gerenciar Registros":
    st.header("Manutenção de Dados")
    if df.empty:
        st.warning("Sem dados.")
    else:
        lista_nomes = sorted(df['REQUERENTE'].unique())
        selecionado = st.selectbox("Pesquisar Requerente", lista_nomes)
        dados_req = df[df['REQUERENTE'] == selecionado]
        
        if not dados_req.empty:
            item = dados_req.iloc[0]
            with st.expander(f"Editar: {selecionado}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    # Aplicando clean_val para remover o "nan"
                    ed_cliente = st.text_input("Cliente", value=clean_val(item.get('CLIENTE')))
                    ed_email = st.text_input("e-Mail", value=clean_val(item.get('E_MAIL')))
                    ed_niver = st.text_input("Aniversário", value=clean_val(item.get('ANIVERSARIO')))
                    ed_obs = st.text_area("Observações", value=clean_val(item.get('OBSERVACOES')))
                
                with c2:
                    # Correção do ValueError do Status
                    lista_status = ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"]
                    status_planilha = str(item.get('STATUS', 'SUBMETIDO')).strip().upper()
                    idx_status = lista_status.index(status_planilha) if status_planilha in lista_status else 0
                    
                    ed_status = st.selectbox("Status", lista_status, index=idx_status)
                    ed_hon = st.number_input("Valor Honorários", value=float(pd.to_numeric(item.get('VALOR_HONORARIOS', 0), errors='coerce') or 0.0))
                    ed_pago = st.number_input("Valor Pago", value=float(pd.to_numeric(item.get('VALOR_PAGO', 0), errors='coerce') or 0.0))
                    ed_saldo = ed_hon - ed_pago
                    st.write(f"**Saldo Calculado:** R$ {ed_saldo:,.2f}")

                if st.button("💾 Gravar Alterações"):
                    idx = df[df['REQUERENTE'] == selecionado].index
                    df.loc[idx, ['CLIENTE', 'E_MAIL', 'ANIVERSARIO', 'STATUS', 'VALOR_HONORARIOS', 'VALOR_PAGO', 'SALDO_DEVEDOR', 'OBSERVACOES']] = \
                        [ed_cliente, ed_email, ed_niver, ed_status, ed_hon, ed_pago, ed_saldo, ed_obs]
                    
                    conn.update(worksheet="NACIONALIDADE", data=df)
                    st.success("Atualizado!")
                    st.cache_data.clear()
                    st.rerun()

                if st.button("🗑️ Excluir permanentemente", type="primary"):
                    df = df[df['REQUERENTE'] != selecionado]
                    conn.update(worksheet="NACIONALIDADE", data=df)
                    st.cache_data.clear()
                    st.rerun()
