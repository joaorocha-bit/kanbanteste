import streamlit as st
import pandas as pd
import plotly.express as px
from io import BytesIO

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
    "Sem pendência",
    "Ag medicação", 
    "Ag transfusão", 
    "Paciente com dor", 
    "Ag exame", 
    "Aguarda retirada de cateter", 
    "Ag avaliação médica", 
    "Ag. Fisioterapia", 
    "Ag Curativo", 
    "Ag orientações de enfermagem", 
    "Ag plano educacional"
]

COLUNAS_ESPERADAS = ["LEITO", "UI", "NOME", "HORA ALTA MÉDICA", "HORA ALTA HOSPITALAR"]

# ==========================================
# ESTILIZAÇÃO CSS CUSTOMIZADA (Cards e Kanban)
# ==========================================
st.markdown("""
    <style>
    .kanban-card {
        background-color: #f9f9f9;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #0052cc;
        color: #333;
    }
    .kanban-title {
        font-size: 16px;
        font-weight: bold;
        margin-bottom: 5px;
        color: #1f1f1f;
    }
    .kanban-info {
        font-size: 12px;
        margin: 2px 0;
        color: #555;
    }
    .kanban-column-header {
        text-align: center;
        padding: 10px;
        background-color: #e3e8ee;
        border-radius: 5px;
        font-weight: bold;
        margin-bottom: 10px;
        color: #333;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# FUNÇÕES DE ESTADO E PROCESSAMENTO
# ==========================================
def inicializar_estado():
    """Inicializa variáveis na sessão do Streamlit."""
    if 'dados_excel' not in st.session_state:
        st.session_state['dados_excel'] = None  # Guardará dicionário de abas -> DataFrames
    if 'abas_disponiveis' not in st.session_state:
        st.session_state['abas_disponiveis'] = []
    if 'checklists' not in st.session_state:
        st.session_state['checklists'] = {} # Formato: { 'Nome_Paciente': ['item1', 'item2'] }

def carregar_planilha(arquivo):
    """Lê a planilha Excel e carrega as abas."""
    try:
        # Lê todas as abas do Excel
        xls = pd.read_excel(arquivo, sheet_name=None)
        st.session_state['dados_excel'] = xls
        st.session_state['abas_disponiveis'] = list(xls.keys())
        
        # Garante que todas as planilhas tenham as colunas necessárias de estado
        for aba, df in xls.items():
            if 'ETAPA_KANBAN' not in df.columns:
                df['ETAPA_KANBAN'] = ETAPAS_KANBAN[0] # Começa em Altas Previstas
            if 'STATUS_ENFERMAGEM' not in df.columns:
                df['STATUS_ENFERMAGEM'] = STATUS_ENFERMAGEM[0]
            # Formata datas caso existam
            df.columns = [str(c).strip().upper() for c in df.columns]
            
        st.success("Planilha carregada com sucesso!")
    except Exception as e:
        st.error(f"Erro ao carregar o arquivo Excel: {e}")

def gerar_excel_download():
    """Gera um arquivo Excel em memória para download a partir do estado atual."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for aba, df in st.session_state['dados_excel'].items():
            df.to_excel(writer, index=False, sheet_name=aba)
    return output.getvalue()

def mudar_etapa(aba, index_linha, nova_etapa):
    """Atualiza a etapa do paciente no dataframe."""
    st.session_state['dados_excel'][aba].at[index_linha, 'ETAPA_KANBAN'] = nova_etapa

def atualizar_status_enfermagem(aba, index_linha, novo_status):
    """Atualiza o status de enfermagem do paciente."""
    st.session_state['dados_excel'][aba].at[index_linha, 'STATUS_ENFERMAGEM'] = novo_status

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
def main():
    inicializar_estado()
    
    st.title("🏥 Kanban de Altas Hospitalares")
    
    # ------------------------------------------
    # SIDEBAR - Controles, Upload e Download
    # ------------------------------------------
    with st.sidebar:
        st.header("⚙️ Configurações")
        
        arquivo_upado = st.file_uploader("1. Importe a Base de Dados (Excel)", type=['xlsx', 'xls'])
        
        if arquivo_upado is not None:
            # Botão para processar o arquivo para não rodar a cada refresh se não quiser
            if st.button("Carregar Dados"):
                carregar_planilha(arquivo_upado)
                
        st.divider()
        
        if st.session_state['dados_excel'] is not None:
            aba_selecionada = st.selectbox(
                "2. Selecione a Data (Aba)", 
                options=st.session_state['abas_disponiveis']
            )
            
            st.divider()
            st.subheader("💾 Exportar Dados")
            excel_bytes = gerar_excel_download()
            st.download_button(
                label="📥 Baixar Planilha Atualizada",
                data=excel_bytes,
                file_name=f"Altas_Atualizadas.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    # ------------------------------------------
    # ÁREA PRINCIPAL - Dashboard e Kanban
    # ------------------------------------------
    if st.session_state['dados_excel'] is None:
        st.info("👈 Por favor, faça o upload de uma planilha Excel na barra lateral para começar.")
        st.write("**Colunas esperadas na planilha:** LEITO, UI, NOME, HORA ALTA MÉDICA, HORA ALTA HOSPITALAR")
        return

    # Pega o dataframe da aba (data) atual
    df_atual = st.session_state['dados_excel'][aba_selecionada]
    
    # Validação de colunas básicas
    colunas_faltantes = [col for col in COLUNAS_ESPERADAS if col not in df_atual.columns]
    if colunas_faltantes:
        st.warning(f"Atenção! As seguintes colunas não foram encontradas nesta aba: {', '.join(colunas_faltantes)}. O sistema tentará funcionar, mas algumas informações ficarão em branco.")

    # --- MÉTRICAS ---
    with st.expander("📊 Visão Geral do Dia (Dashboard)", expanded=False):
        col_m1, col_m2, col_m3 = st.columns(3)
        total_altas = len(df_atual)
        altas_realizadas = len(df_atual[df_atual['ETAPA_KANBAN'] == "Alta Realizada"])
        altas_pendentes = total_altas - altas_realizadas
        
        col_m1.metric("Total de Pacientes no Dia", total_altas)
        col_m2.metric("Altas Realizadas", altas_realizadas)
        col_m3.metric("Altas Pendentes", altas_pendentes)
        
        # Gráfico simples
        contagem_etapas = df_atual['ETAPA_KANBAN'].value_counts().reset_index()
        contagem_etapas.columns = ['Etapa', 'Quantidade']
        fig = px.bar(contagem_etapas, x='Etapa', y='Quantidade', title="Distribuição de Pacientes por Etapa")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.subheader(f"📅 Kanban - Data: {aba_selecionada}")

    # --- RENDERIZAÇÃO DO KANBAN ---
    # Cria 7 colunas no layout do Streamlit
    cols = st.columns(len(ETAPAS_KANBAN))
    
    for idx_etapa, etapa in enumerate(ETAPAS_KANBAN):
        with cols[idx_etapa]:
            # Cabeçalho da Coluna Kanban
            st.markdown(f'<div class="kanban-column-header">{etapa}</div>', unsafe_allow_html=True)
            
            # Filtra os pacientes que estão nesta etapa
            df_etapa = df_atual[df_atual['ETAPA_KANBAN'] == etapa]
            
            for index, row in df_etapa.iterrows():
                # Extração segura das informações (caso a coluna não exista)
                nome = row.get('NOME', 'Desconhecido')
                leito = row.get('LEITO', 'N/A')
                ui = row.get('UI', 'N/A')
                hora_med = row.get('HORA ALTA MÉDICA', '--:--')
                hora_hosp = row.get('HORA ALTA HOSPITALAR', '--:--')
                status_enf_atual = row.get('STATUS_ENFERMAGEM', 'Sem pendência')
                
                # Chave única para controle de componentes do paciente (usando index original para evitar duplicação de nomes iguais)
                paciente_id = f"{aba_selecionada}_{index}"
                
                # HTML do Card Visual
                st.markdown(f"""
                <div class="kanban-card">
                    <div class="kanban-title">🛏️ {leito} | {ui}</div>
                    <div class="kanban-info"><b>Nome:</b> {nome}</div>
                    <div class="kanban-info"><b>A. Médica:</b> {hora_med}</div>
                    <div class="kanban-info"><b>A. Hospitalar:</b> {hora_hosp}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Controles interativos logo abaixo do card (usando componentes Streamlit)
                
                # 1. Troca de Etapa (Movimentar Card)
                nova_etapa = st.selectbox(
                    "Mover para:", 
                    options=ETAPAS_KANBAN, 
                    index=ETAPAS_KANBAN.index(etapa),
                    key=f"move_{paciente_id}",
                    label_visibility="collapsed"
                )
                if nova_etapa != etapa:
                    mudar_etapa(aba_selecionada, index, nova_etapa)
                    st.rerun() # Atualiza a tela imediatamente
                
                # 2. Se estiver na etapa de Processo de Enfermagem, mostra status
                if etapa == "Processo de Enfermagem":
                    novo_status_enf = st.selectbox(
                        "Status de Enfermagem:",
                        options=STATUS_ENFERMAGEM,
                        index=STATUS_ENFERMAGEM.index(status_enf_atual) if status_enf_atual in STATUS_ENFERMAGEM else 0,
                        key=f"status_enf_{paciente_id}"
                    )
                    if novo_status_enf != status_enf_atual:
                        atualizar_status_enfermagem(aba_selecionada, index, novo_status_enf)
                        st.rerun()
                
                # 3. Checklist Expansível
                with st.expander("📋 Checklist do Paciente"):
                    if paciente_id not in st.session_state['checklists']:
                        st.session_state['checklists'][paciente_id] = []
                    
                    # Mostrar itens existentes
                    itens_checklist = st.session_state['checklists'][paciente_id]
                    if len(itens_checklist) == 0:
                        st.write("Nenhum item cadastrado.")
                    else:
                        for i, item in enumerate(itens_checklist):
                            # Um checkbox simples. Como não queremos persistir 'marcado/desmarcado' permanentemente na planilha,
                            # deixamos no estado volátil da UI.
                            st.checkbox(item, key=f"chk_{paciente_id}_{i}")
                            
                    # Adicionar novo item
                    novo_item = st.text_input("Novo item:", key=f"new_item_{paciente_id}")
                    if st.button("➕ Adicionar", key=f"btn_add_{paciente_id}"):
                        if novo_item:
                            st.session_state['checklists'][paciente_id].append(novo_item)
                            st.rerun()

                st.write("---") # Divisor entre os cards

if __name__ == "__main__":
    main()
