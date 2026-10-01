import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json

# ==========================================
# CONFIGURAÇÃO DA PÁGINA STREAMLIT
# ==========================================
st.set_page_config(
    page_title="Kanban de Alta Hospitalar",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ==========================================
# CONSTANTES E CONFIGURAÇÕES DO KANBAN
# ==========================================
ETAPAS_KANBAN = [
    {"nome": "Altas Previstas", "cor": "#e8f2ff", "borda": "#2f80ed", "icone": "📅"},
    {"nome": "Altas Prescritas", "cor": "#e6f9f0", "borda": "#27ae60", "icone": "📄"},
    {"nome": "Altas Administrativas", "cor": "#f3e8ff", "borda": "#9b51e0", "icone": "📋"},
    {"nome": "Processo de Enfermagem", "cor": "#fff8e6", "borda": "#f2994a", "icone": "🩺"},
    {"nome": "Transporte", "cor": "#e0f7fa", "borda": "#00acc1", "icone": "🚑"},
    {"nome": "Pendência Paciente/Familiar", "cor": "#ffebee", "borda": "#eb5757", "icone": "👥"},
    {"nome": "Alta Realizada", "cor": "#e8f5e9", "borda": "#2e7d32", "icone": "✅"}
]

LISTA_ETAPAS_NOMES = [e["nome"] for e in ETAPAS_KANBAN]

STATUS_ENFERMAGEM = [
    "Sem pendência", "Ag medicação", "Ag transfusão", "Paciente com dor", 
    "Ag exame", "Aguarda retirada de cateter", "Ag avaliação médica", 
    "Ag. Fisioterapia", "Ag Curativo", "Ag orientações de enfermagem", 
    "Ag plano educacional"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# ==========================================
# ESTILIZAÇÃO CSS CUSTOMIZADA
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #f8fafc; }
    
    .header-container {
        display: flex; align-items: center; justify-content: space-between;
        background-color: #ffffff; padding: 15px 25px; border-radius: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04); margin-bottom: 20px;
    }
    .brand-title { font-size: 24px; font-weight: 800; color: #0f172a; margin: 0; }
    .brand-subtitle { font-size: 13px; color: #64748b; margin: 0; }

    .metric-card {
        background-color: #ffffff; padding: 16px; border-radius: 12px;
        border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        display: flex; align-items: center; justify-content: space-between;
    }
    .metric-value { font-size: 24px; font-weight: 700; color: #0f172a; }
    .metric-label { font-size: 12px; font-weight: 600; color: #64748b; }

    .kanban-header {
        padding: 10px 14px; border-radius: 8px; font-weight: 700;
        font-size: 13px; display: flex; justify-content: space-between;
        align-items: center; margin-bottom: 12px;
    }
    .patient-card {
        background-color: #ffffff; border-radius: 10px; padding: 12px;
        margin-bottom: 12px; border: 1px solid #e2e8f0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02); transition: all 0.2s ease;
    }
    .patient-card:hover { box-shadow: 0 4px 8px rgba(0,0,0,0.06); }
    .patient-name { font-size: 14px; font-weight: 700; color: #1e293b; margin-bottom: 2px; }
    .patient-info { font-size: 11px; color: #64748b; margin-bottom: 4px; }
    .badge-status {
        background-color: #feefc3; color: #b06000; font-size: 10px;
        font-weight: 700; padding: 3px 8px; border-radius: 12px; display: inline-block;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# GESTÃO DE ESTADO (Session State)
# ==========================================
def inicializar_estado():
    if 'client_gsheets' not in st.session_state:
        st.session_state['client_gsheets'] = None
    if 'planilha_ativa' not in st.session_state:
        st.session_state['planilha_ativa'] = None
    if 'dados_df' not in st.session_state:
        st.session_state['dados_df'] = None
    if 'idx_cabecalho' not in st.session_state:
        st.session_state['idx_cabecalho'] = 0
    
    if 'checklist_padrao' not in st.session_state:
        st.session_state['checklist_padrao'] = [
            "Conferência de exames de alta",
            "Receituário entregue ao paciente",
            "Orientações de enfermagem explicadas",
            "Acompanhante ciente do horário",
            "Cateteres e acessos retirados"
        ]
        
    if 'checklist_estados' not in st.session_state:
        st.session_state['checklist_estados'] = {}

# ==========================================
# INTEGRAÇÃO ROBUSTA COM GOOGLE SHEETS
# ==========================================
def conectar_google_sheets(arquivo_credenciais, url_planilha):
    try:
        credenciais_dict = json.load(arquivo_credenciais)
        credentials = Credentials.from_service_account_info(credenciais_dict, scopes=SCOPES)
        client = gspread.authorize(credentials)
        planilha = client.open_by_url(url_planilha)
        st.session_state['client_gsheets'] = client
        st.session_state['planilha_ativa'] = planilha
        return True
    except Exception as e:
        st.error(f"Erro na autenticação com o Google Sheets: {e}")
        return False

def carregar_dados_aba(aba_nome):
    try:
        planilha = st.session_state['planilha_ativa']
        ws = planilha.worksheet(aba_nome)
        
        # Leitura bruta de todas as células para evitar erro com cabeçalhos problemáticos
        linhas = ws.get_all_values()
        
        if not linhas or len(linhas) < 2:
            st.session_state['dados_df'] = pd.DataFrame()
            return

        # Busca dinâmica da linha de cabeçalhos (analisa as primeiras 5 linhas)
        idx_cabecalho = 0
        for i, linha in enumerate(linhas[:5]):
            linha_upper = [str(cell).strip().upper() for cell in linha]
            if any(k in linha_upper for k in ["NOME", "LEITO", "UI", "HORA ALTA MÉDICA", "HORA ALTA HOSPITALAR"]):
                idx_cabecalho = i
                break

        cabecalhos_brutos = [str(cell).strip().upper() for cell in linhas[idx_cabecalho]]
        
        # Garante que cada nome de coluna seja único
        cabecalhos_unicos = []
        contagem = {}
        for col in cabecalhos_brutos:
            col_nome = col if col != "" else "COLUNA_VAZIA"
            if col_nome in contagem:
                contagem[col_nome] += 1
                cabecalhos_unicos.append(f"{col_nome}_{contagem[col_nome]}")
            else:
                contagem[col_nome] = 1
                cabecalhos_unicos.append(col_nome)

        # Trata as linhas de dados
        dados = linhas[idx_cabecalho + 1:]
        largura = len(cabecalhos_unicos)
        dados_normalizados = [row + [""] * (largura - len(row)) for row in dados]
        dados_normalizados = [row[:largura] for row in dados_normalizados]

        df = pd.DataFrame(dados_normalizados, columns=cabecalhos_unicos)
        
        # Remove linhas inteiramente vazias
        df = df[df.apply(lambda r: "".join(map(str, r.values)).strip() != "", axis=1)].reset_index(drop=True)

        if df.empty:
            st.session_state['dados_df'] = df
            return

        # Garante que as colunas essenciais do Kanban existam no DataFrame
        if "ETAPA_KANBAN" not in df.columns:
            df["ETAPA_KANBAN"] = LISTA_ETAPAS_NOMES[0]
            
        if "STATUS_ENFERMAGEM" not in df.columns:
            df["STATUS_ENFERMAGEM"] = STATUS_ENFERMAGEM[0]

        st.session_state['dados_df'] = df
        st.session_state['idx_cabecalho'] = idx_cabecalho
    except Exception as e:
        st.error(f"Erro ao carregar dados da aba '{aba_nome}': {e}")
        st.session_state['dados_df'] = pd.DataFrame()

def atualizar_celula_gsheets(aba_nome, linha_pandas, nome_coluna, novo_valor):
    # Atualiza em memória para resposta instantânea na interface
    st.session_state['dados_df'].at[linha_pandas, nome_coluna] = novo_valor
    try:
        ws = st.session_state['planilha_ativa'].worksheet(aba_nome)
        idx_cabecalho = st.session_state.get('idx_cabecalho', 0)
        linha_cabecalho_real = idx_cabecalho + 1
        
        cabecalhos_brutos = [str(c).strip().upper() for c in ws.row_values(linha_cabecalho_real)]
        
        # Se a coluna não existir na planilha física do Google Sheets, cria automaticamente
        if nome_coluna not in cabecalhos_brutos:
            cabecalhos_brutos.append(nome_coluna)
            col_index = len(cabecalhos_brutos)
            ws.update_cell(linha_cabecalho_real, col_index, nome_coluna)
        else:
            col_index = cabecalhos_brutos.index(nome_coluna) + 1
            
        row_index = linha_pandas + idx_cabecalho + 2 
        ws.update_cell(row_index, col_index, str(novo_valor))
    except Exception as e:
        st.error(f"Erro ao salvar dados no Google Sheets: {e}")

def obter_valor_campo(row, nome_base, padrao='--:--'):
    """Auxiliar para ler valores de colunas mesmo se tiverem sufixos de duplicidade."""
    for c in row.index:
        if str(c).startswith(nome_base):
            val = str(row[c]).strip()
            if val:
                return val
    return padrao

# ==========================================
# INTERFACE PRINCIPAL DO APLICATIVO
# ==========================================
def main():
    inicializar_estado()
    
    st.markdown("""
        <div class="header-container">
            <div>
                <h1 class="brand-title">🏥 VidaMais | Kanban de Alta Hospitalar</h1>
                <p class="brand-subtitle">Gestão visual em tempo real de altas previstas, prescritas e realizadas.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ Conexão Google Sheets & Checklist Institucional", expanded=(st.session_state['planilha_ativa'] is None)):
        col_cfg1, col_cfg2 = st.columns(2)
        
        with col_cfg1:
            st.subheader("1. Conexão Google Sheets")
            arquivo_credenciais = st.file_uploader("Enviar JSON (Conta de Serviço)", type=['json'])
            url_planilha = st.text_input("Link da Planilha Google Sheets:")
            if st.button("🔌 Conectar e Carregar Planilha", use_container_width=True):
                if arquivo_credenciais and url_planilha:
                    if conectar_google_sheets(arquivo_credenciais, url_planilha):
                        st.success("Conectado com sucesso!")
                        st.rerun()
                else:
                    st.warning("Forneça o arquivo de credenciais e a URL da planilha.")

        with col_cfg2:
            st.subheader("2. Checklist Padrão da Instituição")
            st.caption("Qualquer item adicionado aqui é padronizado em **todos** os cards de pacientes.")
            
            for idx, item in enumerate(list(st.session_state['checklist_padrao'])):
                c_item, c_del = st.columns([0.85, 0.15])
                c_item.text(f"• {item}")
                if c_del.button("❌", key=f"del_chk_{idx}"):
                    st.session_state['checklist_padrao'].pop(idx)
                    st.rerun()
                    
            novo_item_chk = st.text_input("Novo item de checklist:")
            if st.button("➕ Adicionar Item Padrão", use_container_width=True):
                if novo_item_chk:
                    st.session_state['checklist_padrao'].append(novo_item_chk)
                    st.rerun()

    if st.session_state['planilha_ativa'] is None:
        st.info("👆 Acesse o painel de configurações acima para conectar sua planilha do Google Sheets.")
        return

    # --- NAVEGAÇÃO E FILTROS ---
    st.markdown("### 🔍 Filtros e Navegação")
    
    abas_disponiveis = [ws.title for ws in st.session_state['planilha_ativa'].worksheets()]
    
    f_col1, f_col2, f_col3, f_col4 = st.columns([2, 2, 2, 2])
    with f_col1:
        aba_selecionada = st.selectbox("📅 Data (Aba):", options=abas_disponiveis)
    
    if st.session_state['dados_df'] is None or st.session_state.get('aba_atual') != aba_selecionada:
        carregar_dados_aba(aba_selecionada)
        st.session_state['aba_atual'] = aba_selecionada

    df = st.session_state['dados_df']

    if df is not None and not df.empty:
        col_ui = [c for c in df.columns if c.startswith("UI")]
        setores = ["Todos"] + list(df[col_ui[0]].unique()) if col_ui else ["Todos"]
        
        with f_col2:
            filtro_ui = st.selectbox("Unidade / Setor:", options=setores)
        with f_col3:
            filtro_busca = st.text_input("Buscar por Nome ou Leito:", placeholder="Ex: 301A ou Maria")
        with f_col4:
            st.write(" ")
            if st.button("🔄 Sincronizar com Nuvem", use_container_width=True):
                carregar_dados_aba(aba_selecionada)
                st.rerun()

        df_filtrado = df.copy()
        if filtro_ui != "Todos" and col_ui:
            df_filtrado = df_filtrado[df_filtrado[col_ui[0]] == filtro_ui]
        if filtro_busca:
            term = filtro_busca.lower()
            cols_busca = [c for c in df_filtrado.columns if any(k in c for k in ["NOME", "LEITO"])]
            mascara = False
            for col in cols_busca:
                mascara = mascara | df_filtrado[col].astype(str).str.lower().str.contains(term)
            df_filtrado = df_filtrado[mascara]

        # --- CARDS DE INDICADORES ---
        st.markdown("<br>", unsafe_allow_html=True)
        m1, m2, m3, m4 = st.columns(4)
        
        total_prev = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Altas Previstas"])
        total_presc = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Altas Prescritas"])
        total_pend = len(df_filtrado[df_filtrado['ETAPA_KANBAN'].isin(["Processo de Enfermagem", "Pendência Paciente/Familiar"])])
        total_realiz = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Alta Realizada"])

        m1.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Previstas Hoje</div><div class="metric-value">{total_prev}</div></div><div style="font-size:28px;">📅</div></div>', unsafe_allow_html=True)
        m2.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Prescritas</div><div class="metric-value">{total_presc}</div></div><div style="font-size:28px;">📄</div></div>', unsafe_allow_html=True)
        m3.markdown(f'<div class="metric-card"><div><div class="metric-label">Pendências Críticas</div><div class="metric-value">{total_pend}</div></div><div style="font-size:28px;">⚠️</div></div>', unsafe_allow_html=True)
        m4.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Realizadas</div><div class="metric-value">{total_realiz}</div></div><div style="font-size:28px;">✅</div></div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # --- QUADRO KANBAN (7 COLUNAS) ---
        cols_kanban = st.columns(len(ETAPAS_KANBAN))

        for idx, cfg in enumerate(ETAPAS_KANBAN):
            nome_etapa = cfg["nome"]
            with cols_kanban[idx]:
                df_col = df_filtrado[df_filtrado['ETAPA_KANBAN'] == nome_etapa]
                
                st.markdown(f"""
                    <div class="kanban-header" style="background-color: {cfg['cor']}; border-left: 4px solid {cfg['borda']}; color: #1e293b;">
                        <span>{cfg['icone']} {nome_etapa}</span>
                        <span style="background: white; padding: 2px 8px; border-radius: 10px; font-size: 11px;">{len(df_col)}</span>
                    </div>
                """, unsafe_allow_html=True)

                for orig_idx, row in df_col.iterrows():
                    leito = obter_valor_campo(row, 'LEITO', 'N/A')
                    ui = obter_valor_campo(row, 'UI', 'N/A')
                    nome = obter_valor_campo(row, 'NOME', 'Sem Nome')
                    hora_med = obter_valor_campo(row, 'HORA ALTA MÉDICA', '--:--')
                    hora_hosp = obter_valor_campo(row, 'HORA ALTA HOSPITALAR', '--:--')
                    status_enf = row.get('STATUS_ENFERMAGEM', 'Sem pendência')
                    
                    paciente_key = f"p_{aba_selecionada}_{orig_idx}"

                    st.markdown(f"""
                        <div class="patient-card">
                            <div style="display:flex; justify-content:space-between; align-items:center;">
                                <span class="patient-name">👤 {nome}</span>
                            </div>
                            <div class="patient-info"><b>Leito:</b> {leito} | <b>UI:</b> {ui}</div>
                            <div class="patient-info"><b>A. Médica:</b> {hora_med} | <b>A. Hosp:</b> {hora_hosp}</div>
                            {f'<div class="badge-status">{status_enf}</div>' if nome_etapa == "Processo de Enfermagem" else ''}
                        </div>
                    """, unsafe_allow_html=True)

                    nova_etapa = st.selectbox(
                        "Mover para:",
                        options=LISTA_ETAPAS_NOMES,
                        index=LISTA_ETAPAS_NOMES.index(nome_etapa),
                        key=f"mov_{paciente_key}",
                        label_visibility="collapsed"
                    )
                    if nova_etapa != nome_etapa:
                        atualizar_celula_gsheets(aba_selecionada, orig_idx, "ETAPA_KANBAN", nova_etapa)
                        st.rerun()

                    if nome_etapa == "Processo de Enfermagem":
                        st_enf = st.selectbox(
                            "Status Enfermagem:",
                            options=STATUS_ENFERMAGEM,
                            index=STATUS_ENFERMAGEM.index(status_enf) if status_enf in STATUS_ENFERMAGEM else 0,
                            key=f"enf_{paciente_key}",
                            label_visibility="collapsed"
                        )
                        if st_enf != status_enf:
                            atualizar_celula_gsheets(aba_selecionada, orig_idx, "STATUS_ENFERMAGEM", st_enf)
                            st.rerun()

                    with st.popover("📋 Checklist Padronizado"):
                        st.write(f"**Checklist de Alta: {nome}**")
                        if paciente_key not in st.session_state['checklist_estados']:
                            st.session_state['checklist_estados'][paciente_key] = {}

                        for item_padrao in st.session_state['checklist_padrao']:
                            checked = st.session_state['checklist_estados'][paciente_key].get(item_padrao, False)
                            val = st.checkbox(item_padrao, value=checked, key=f"chk_{paciente_key}_{item_padrao}")
                            st.session_state['checklist_estados'][paciente_key][item_padrao] = val

                    st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid #f1f5f9;'>", unsafe_allow_html=True)

        # --- ANÁLISE GRÁFICA ---
        st.markdown("<br>---", unsafe_allow_html=True)
        st.subheader("📊 Relatórios do Dia")
        
        g1, g2 = st.columns([1.5, 1])
        with g1:
            st.markdown("**Pacientes por Etapa do Kanban**")
            chart_data = df_filtrado['ETAPA_KANBAN'].value_counts().reset_index()
            chart_data.columns = ['Etapa', 'Pacientes']
            fig = px.bar(chart_data, x='Etapa', y='Pacientes', color='Etapa', text_auto=True)
            fig.update_layout(showlegend=False, height=280, margin=dict(l=10, r=10, t=20, b=10))
            st.plotly_chart(fig, use_container_width=True)

        with g2:
            st.markdown("**Gargalos no Processo de Enfermagem**")
            df_enf = df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Processo de Enfermagem"]
            if not df_enf.empty:
                chart_enf = df_enf['STATUS_ENFERMAGEM'].value_counts().reset_index()
                chart_enf.columns = ['Pendência', 'Qtd']
                fig_enf = px.pie(chart_enf, names='Pendência', values='Qtd', hole=0.4)
                fig_enf.update_layout(height=280, margin=dict(l=10, r=10, t=20, b=10))
                st.plotly_chart(fig_enf, use_container_width=True)
            else:
                st.info("Nenhuma pendência mapeada na etapa de Enfermagem no momento.")

if __name__ == "__main__":
    main()
