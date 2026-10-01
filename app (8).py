import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json

# ==========================================
# CONFIGURAÇÃO INICIAL DA PÁGINA
# ==========================================
st.set_page_config(
    page_title="Kanban de Altas Hospitalares",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# CONSTANTES E LISTAS DE OPÇÕES
# ==========================================
ETAPAS_KANBAN = [
    "Altas Previstas",
    "Altas Prescritas",
    "Altas Administrativas",
    "Processo de Enfermagem",
    "Transporte",
    "Pendência Paciente/Familiar",
    "Alta Realizada"
]

STATUS_ENFERMAGEM = [
    "Sem pendência", "Ag medicação", "Ag transfusão", "Paciente com dor", 
    "Ag exame", "Aguarda retirada de cateter", "Ag avaliação médica", 
    "Ag. Fisioterapia", "Ag Curativo", "Ag orientações de enfermagem", 
    "Ag plano educacional"
]

COLUNAS_ESPERADAS = ["LEITO", "UI", "NOME", "HORA ALTA MÉDICA", "HORA ALTA HOSPITALAR"]

# Escopos necessários para a API do Google
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==========================================
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ==========================================
st.markdown("""
    <style>
    .kanban-card {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #00a65a;
        color: #333;
    }
    .kanban-title { font-size: 16px; font-weight: bold; margin-bottom: 5px; color: #1f1f1f; }
    .kanban-info { font-size: 12px; margin: 2px 0; color: #555; }
    .kanban-column-header {
        text-align: center; padding: 10px; background-color: #e3e8ee;
        border-radius: 5px; font-weight: bold; margin-bottom: 10px; color: #333;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE INTEGRAÇÃO COM GOOGLE SHEETS
# ==========================================
def inicializar_estado():
    if 'client_gsheets' not in st.session_state:
        st.session_state['client_gsheets'] = None
    if 'planilha_ativa' not in st.session_state:
        st.session_state['planilha_ativa'] = None
    if 'dados_df' not in st.session_state:
        st.session_state['dados_df'] = None
    if 'checklists' not in st.session_state:
        st.session_state['checklists'] = {}

def conectar_google_sheets(arquivo_credenciais, url_planilha):
    """Autentica no Google Sheets usando o JSON e abre a planilha pelo URL."""
    try:
        credenciais_dict = json.load(arquivo_credenciais)
        credentials = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
        client = gspread.authorize(credentials)
        
        planilha = client.open_by_url(url_planilha)
        st.session_state['client_gsheets'] = client
        st.session_state['planilha_ativa'] = planilha
        st.success("Conectado ao Google Sheets com sucesso!")
        return True
    except Exception as e:
        st.error(f"Erro ao conectar: {e}")
        return False

def carregar_dados_aba(aba_nome):
    """Lê os dados da aba selecionada e garante as colunas de controle."""
    planilha = st.session_state['planilha_ativa']
    ws = planilha.worksheet(aba_nome)
    
    # Pega todos os registros. Retorna lista de dicionários
    registros = ws.get_all_records()
    df = pd.DataFrame(registros)
    
    if df.empty:
        st.warning(f"A aba '{aba_nome}' está vazia ou sem cabeçalhos.")
        st.session_state['dados_df'] = df
        return

    # Garante que as colunas de status existam na planilha na nuvem
    cabecalhos = ws.row_values(1)
    precisa_atualizar_cabecalho = False
    
    if "ETAPA_KANBAN" not in cabecalhos:
        cabecalhos.append("ETAPA_KANBAN")
        df["ETAPA_KANBAN"] = ETAPAS_KANBAN[0]
        precisa_atualizar_cabecalho = True
        
    if "STATUS_ENFERMAGEM" not in cabecalhos:
        cabecalhos.append("STATUS_ENFERMAGEM")
        df["STATUS_ENFERMAGEM"] = STATUS_ENFERMAGEM[0]
        precisa_atualizar_cabecalho = True

    if precisa_atualizar_cabecalho:
        ws.update(range_name=f"A1:{gspread.utils.rowcol_to_a1(1, len(cabecalhos))}", values=[cabecalhos])
        # Preenche valores default se acabou de criar
        if not df.empty:
             ws.update(
                 range_name=f"{gspread.utils.rowcol_to_a1(2, cabecalhos.index('ETAPA_KANBAN')+1)}:{gspread.utils.rowcol_to_a1(len(df)+1, cabecalhos.index('ETAPA_KANBAN')+1)}",
                 values=[[ETAPAS_KANBAN[0]]] * len(df)
             )
             ws.update(
                 range_name=f"{gspread.utils.rowcol_to_a1(2, cabecalhos.index('STATUS_ENFERMAGEM')+1)}:{gspread.utils.rowcol_to_a1(len(df)+1, cabecalhos.index('STATUS_ENFERMAGEM')+1)}",
                 values=[[STATUS_ENFERMAGEM[0]]] * len(df)
             )

    st.session_state['dados_df'] = df

def atualizar_celula_gsheets(aba_nome, linha_pandas, nome_coluna, novo_valor):
    """Atualiza o DataFrame local e espelha a mudança na célula exata do Google Sheets."""
    # Atualiza local (UI imediata)
    st.session_state['dados_df'].at[linha_pandas, nome_coluna] = novo_valor
    
    # Atualiza Google Sheets
    try:
        ws = st.session_state['planilha_ativa'].worksheet(aba_nome)
        cabecalhos = ws.row_values(1)
        
        # +1 porque no Sheets a lista de colunas começa em 1. 
        # +2 na linha porque linha 1 é cabeçalho e pandas index começa em 0.
        col_index = cabecalhos.index(nome_coluna) + 1
        row_index = linha_pandas + 2 
        
        ws.update_cell(row_index, col_index, novo_valor)
    except Exception as e:
        st.error(f"Erro ao salvar na nuvem: {e}")

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
def main():
    inicializar_estado()
    
    st.title("🏥 Kanban de Altas Hospitalares - Google Sheets")
    
    # ------------------------------------------
    # SIDEBAR - Conexão e Navegação
    # ------------------------------------------
    with st.sidebar:
        st.header("⚙️ Conexão Google Sheets")
        
        arquivo_credenciais = st.file_uploader("1. Envie o JSON (Conta de Serviço)", type=['json'])
        url_planilha = st.text_input("2. Link da Planilha Google Sheets:")
        
        if st.button("🔌 Conectar e Carregar"):
            if arquivo_credenciais and url_planilha:
                conectar_google_sheets(arquivo_credenciais, url_planilha)
            else:
                st.error("Forneça o arquivo JSON e a URL da planilha.")
                
        st.divider()
        
        # Se estiver conectado, carrega a lista de abas
        if st.session_state['planilha_ativa'] is not None:
            abas = [ws.title for ws in st.session_state['planilha_ativa'].worksheets()]
            aba_selecionada = st.selectbox("📅 Selecione o Dia (Aba):", options=abas)
            
            if st.button("🔄 Atualizar Dados desta Aba"):
                with st.spinner("Sincronizando com a nuvem..."):
                    carregar_dados_aba(aba_selecionada)
                    
            st.caption("Ações no Kanban salvam automaticamente na planilha.")

    # ------------------------------------------
    # ÁREA PRINCIPAL - Dashboard e Kanban
    # ------------------------------------------
    if st.session_state['dados_df'] is None:
        st.info("👈 Conecte-se ao Google Sheets no painel lateral esquerdo e clique em 'Atualizar Dados' para visualizar o Kanban.")
        return

    df_atual = st.session_state['dados_df']
    
    if df_atual.empty:
        st.warning("A aba selecionada não possui dados (pacientes).")
        return

    # --- MÉTRICAS ---
    with st.expander("📊 Visão Geral do Dia", expanded=False):
        col_m1, col_m2, col_m3 = st.columns(3)
        total_altas = len(df_atual)
        altas_realizadas = len(df_atual[df_atual['ETAPA_KANBAN'] == "Alta Realizada"])
        
        col_m1.metric("Total de Pacientes no Dia", total_altas)
        col_m2.metric("Altas Realizadas", altas_realizadas)
        col_m3.metric("Altas Pendentes", total_altas - altas_realizadas)
        
        contagem = df_atual['ETAPA_KANBAN'].value_counts().reset_index()
        contagem.columns = ['Etapa', 'Quantidade']
        fig = px.bar(contagem, x='Etapa', y='Quantidade', title="Pacientes por Etapa")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")

    # --- RENDERIZAÇÃO DO KANBAN ---
    cols = st.columns(len(ETAPAS_KANBAN))
    
    for idx_etapa, etapa in enumerate(ETAPAS_KANBAN):
        with cols[idx_etapa]:
            st.markdown(f'<div class="kanban-column-header">{etapa}</div>', unsafe_allow_html=True)
            
            # Pacientes nesta etapa
            df_etapa = df_atual[df_atual['ETAPA_KANBAN'] == etapa]
            
            for index, row in df_etapa.iterrows():
                nome = row.get('NOME', 'Desconhecido')
                leito = row.get('LEITO', 'N/A')
                ui = row.get('UI', 'N/A')
                hora_med = row.get('HORA ALTA MÉDICA', '--:--')
                hora_hosp = row.get('HORA ALTA HOSPITALAR', '--:--')
                status_enf_atual = row.get('STATUS_ENFERMAGEM', 'Sem pendência')
                
                paciente_id = f"{aba_selecionada}_{index}"
                
                # Card
                st.markdown(f"""
                <div class="kanban-card">
                    <div class="kanban-title">🛏️️ {leito} | {ui}</div>
                    <div class="kanban-info"><b>Nome:</b> {nome}</div>
                    <div class="kanban-info"><b>A. Médica:</b> {hora_med}</div>
                    <div class="kanban-info"><b>A. Hospitalar:</b> {hora_hosp}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # 1. Movimentação (Atualiza local e nuvem)
                nova_etapa = st.selectbox(
                    "Mover para:", 
                    options=ETAPAS_KANBAN, 
                    index=ETAPAS_KANBAN.index(etapa),
                    key=f"move_{paciente_id}",
                    label_visibility="collapsed"
                )
                if nova_etapa != etapa:
                    atualizar_celula_gsheets(aba_selecionada, index, "ETAPA_KANBAN", nova_etapa)
                    st.rerun()
                
                # 2. Status Enfermagem
                if etapa == "Processo de Enfermagem":
                    novo_status_enf = st.selectbox(
                        "Status Enfermagem:",
                        options=STATUS_ENFERMAGEM,
                        index=STATUS_ENFERMAGEM.index(status_enf_atual) if status_enf_atual in STATUS_ENFERMAGEM else 0,
                        key=f"status_enf_{paciente_id}"
                    )
                    if novo_status_enf != status_enf_atual:
                        atualizar_celula_gsheets(aba_selecionada, index, "STATUS_ENFERMAGEM", novo_status_enf)
                        st.rerun()
                
                # 3. Checklist Local
                with st.expander("📋 Checklist"):
                    if paciente_id not in st.session_state['checklists']:
                        st.session_state['checklists'][paciente_id] = []
                    
                    itens_checklist = st.session_state['checklists'][paciente_id]
                    for i, item in enumerate(itens_checklist):
                        st.checkbox(item, key=f"chk_{paciente_id}_{i}")
                            
                    novo_item = st.text_input("Novo item:", key=f"new_item_{paciente_id}")
                    if st.button("➕ Add", key=f"btn_add_{paciente_id}"):
                        if novo_item:
                            st.session_state['checklists'][paciente_id].append(novo_item)
                            st.rerun()

                st.write("---")

if __name__ == "__main__":
    main()
