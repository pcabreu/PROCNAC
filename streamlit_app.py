import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# Configuração da Página
st.set_page_config(page_title="Gestão Nacionalidade v3.2", layout="wide")

# Conexão com Google Sheets
conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    # Lemos a planilha assumindo que a LINHA 1 é o cabeçalho
    data = conn.read(worksheet="NACIONALIDADE", ttl="0")
    
    # PADRONIZAÇÃO DE COLUNAS (Transforma tudo em MAIÚSCULO e remove espaços)
    data.columns = [
        str(c).strip().upper()
        .replace(' ', '_').replace('É', 'E').replace('Á', 'A')
        .replace('Ç', 'C').replace('Õ', 'O').replace('/', '_')
        for c in data.columns
    ]
    
    # Converte ID para número e remove linhas totalmente vazias
    if 'ID' in data.columns:
        data['ID'] = pd.to_numeric(data['ID'], errors='coerce')
    
    # Remove apenas se o Requerente for nulo (evita deletar a tabela toda)
    data = data.dropna(subset=['REQUERENTE'])
    
    # Limpeza de valores financeiros (preenche vazios com 0)
    cols_fin = ['VALOR_HONORARIOS', 'VALOR_PAGO', 'SALDO_DEVEDOR']
    for col in cols_fin:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
            
    return data

def clean_val(val):
    if pd.isna(val) or str(val).lower() == 'nan':
        return ""
    return str(val)

df = load_data()

# --- MENU LATERAL ---
st.sidebar.title("Nacionalidade App")
menu = st.sidebar.radio("Navegação", ["📊 Dashboard", "➕ Inclusão", "📝 Gerenciar Registros"])

# --- DASHBOARD ---
if menu == "📊 Dashboard":
    st.header("Resumo Geral")
    if not df.empty:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Processos", len(df))
        c2.metric("Concluídos", len(df[df['STATUS'].str.contains('CONCLUÍDO', na=False, case=False)]))
        c3.metric("Total Recebido", f"R$ {df['VALOR_PAGO'].sum():,.2f}")
        c4.metric("Saldo Devedor", f"R$ {df['SALDO_DEVEDOR'].sum():,.2f}")
        
        st.divider()
        fig = px.pie(df, names='STATUS', title="Status dos Processos", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Planilha vazia.")

# --- INCLUSÃO ---
elif menu == "➕ Inclusão":
    st.header("Novo Cadastro")
    
    # ID Sequencial Robusto
    proximo_id = int(df['ID'].max() + 1) if not df.empty and not pd.isna(df['ID'].max()) else 1
    st.write(f"ID do Registro: **{proximo_id}**")
    
    with st.form("form_add", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            req = st.text_input("Requerente *")
            cli = st.text_input("Cliente")
            mail = st.text_input("e-Mail")
            aniv = st.date_input("Aniversário", format="DD/MM/YYYY")
        with c2:
            art = st.selectbox("Artigo", ["Neto", "Filho", "Casamento", "Outros"])
            sts = st.selectbox("Status", ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"])
            hon = st.number_input("Honorários (R$)", min_value=0.0)
            pag = st.number_input("Valor Pago Inicial (R$)", min_value=0.0)
            
        obs = st.text_area("Observações")
        if st.form_submit_button("Salvar"):
            if req:
                nova_linha = pd.DataFrame([{
                    "ID": proximo_id, "REQUERENTE": req, "CLIENTE": cli, "E_MAIL": mail,
                    "ANIVERSARIO": aniv.strftime('%d/%m/%Y'), "ARTIGO": art, "STATUS": sts,
                    "VALOR_HONORARIOS": hon, "VALOR_PAGO": pag, "SALDO_DEVEDOR": hon - pag,
                    "OBSERVACOES": obs
                }])
                df_novo = pd.concat([df, nova_linha], ignore_index=True)
                conn.update(worksheet="NACIONALIDADE", data=df_novo)
                st.success("Salvo com sucesso!")
                st.cache_data.clear()
            else:
                st.error("Nome obrigatório!")

# --- GERENCIAR ---
elif menu == "📝 Gerenciar Registros":
    st.header("Editar ou Excluir")
    if not df.empty:
        nome_sel = st.selectbox("Selecione o Requerente", sorted(df['REQUERENTE'].unique()))
        item = df[df['REQUERENTE'] == nome_sel].iloc[0]
        
        with st.form("form_edit"):
            c1, c2 = st.columns(2)
            with c1:
                ed_cli = st.text_input("Cliente", value=clean_val(item.get('CLIENTE')))
                ed_mail = st.text_input("e-Mail", value=clean_val(item.get('E_MAIL')))
                ed_aniv = st.text_input("Aniversário", value=clean_val(item.get('ANIVERSARIO')))
            with c2:
                # Segurança para o menu de Status
                lista_status = ["SUBMETIDO", "EM ANÁLISE", "DILIGÊNCIA", "DECISÃO", "CONCLUÍDO"]
                st_planilha = str(item.get('STATUS', 'SUBMETIDO')).strip().upper()
                idx_st = lista_status.index(st_planilha) if st_planilha in lista_status else 0
                ed_sts = st.selectbox("Status", lista_status, index=idx_st)
                
                ed_hon = st.number_input("Honorários", value=float(item.get('VALOR_HONORARIOS', 0)))
                ed_pag = st.number_input("Pago", value=float(item.get('VALOR_PAGO', 0)))
            
            ed_obs = st.text_area("Observações", value=clean_val(item.get('OBSERVACOES')))
            
            col_b1, col_b2 = st.columns(2)
            if col_b1.form_submit_button("Gravar"):
                idx = df[df['REQUERENTE'] == nome_sel].index
                df.loc[idx, ['CLIENTE', 'E_MAIL', 'ANIVERSARIO', 'STATUS', 'VALOR_HONORARIOS', 'VALOR_PAGO', 'SALDO_DEVEDOR', 'OBSERVACOES']] = \
                    [ed_cli, ed_mail, ed_aniv, ed_sts, ed_hon, ed_pag, ed_hon - ed_pag, ed_obs]
                conn.update(worksheet="NACIONALIDADE", data=df)
                st.success("Atualizado!")
                st.cache_data.clear()
                st.rerun()
            
            if col_b2.form_submit_button("🗑️ Excluir", type="secondary"):
                df_exc = df[df['REQUERENTE'] != nome_sel]
                conn.update(worksheet="NACIONALIDADE", data=df_exc)
                st.warning("Excluído!")
                st.cache_data.clear()
                st.rerun()
