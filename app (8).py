import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

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
        background-color: #ffffff; padding: 12px 20px; border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05); margin-bottom: 15px;
    }
    .brand-title { font-size: 20px; font-weight: 800; color: #0f172a; margin: 0; }
    .brand-subtitle { font-size: 12px; color: #64748b; margin: 0; }

    .metric-card {
        background-color: #ffffff; padding: 12px 16px; border-radius: 10px;
        border: 1px solid #e2e8f0; box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        display: flex; align-items: center; justify-content: space-between;
    }
    .metric-value { font-size: 22px; font-weight: 700; color: #0f172a; }
    .metric-label { font-size: 11px; font-weight: 600; color: #64748b; }

    /* SEPARAÇÃO VISUAL DAS COLUNAS DO KANBAN */
    div[data-testid="stColumn"]:has(.kanban-header) {
        background-color: #f1f5f9;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 10px 8px !important;
    }

    /* CABEÇALHO DO KANBAN */
    .kanban-header {
        padding: 6px 10px;
        border-radius: 8px;
        font-weight: 700;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
        height: 52px;
        min-height: 52px;
        box-sizing: border-box;
    }

    /* CARD COMPLETO E UNIFICADO (UTILIZANDO CONTAINER NATIVO DO STREAMLIT) */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.patient-name-compact) {
        background-color: #f8fafc !important;
        border-radius: 14px !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
        padding: 14px !important;
        margin-bottom: 10px !important;
    }

    /* AJUSTE DO ESPAÇAMENTO INTERNO DO CARD */
    div[data-testid="stVerticalBlockBorderWrapper"]:has(.patient-name-compact) > div[data-testid="stVerticalBlock"] {
        gap: 0.4rem !important;
    }

    .patient-bed { font-size: 12px; font-weight: 600; color: #64748b; }
    .patient-name-compact { font-size: 15px; font-weight: 800; color: #0f172a; margin: 2px 0 4px 0; text-transform: uppercase; }
    .patient-time-compact { font-size: 12px; color: #475569; display: flex; gap: 6px; align-items: center; margin-bottom: 4px; }
    .badge-status-compact {
        background-color: #f8fafc; color: #92400e; font-size: 11px;
        font-weight: 700; padding: 3px 8px; border-radius: 12px; display: inline-block; margin-bottom: 6px;
    }

    /* BOTÃO "VER DETALHES" SUTIL DENTRO DO CARD */
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stPopover"] {
        width: 100%;
        margin-top: 4px;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stPopover"] > button {
        width: 100% !important;
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 8px !important;
        color: #1e3a8a !important;
        font-size: 13px !important;
        font-weight: 600 !important;
        padding: 4px 12px !important;
        min-height: 36px !important;
        box-shadow: none !important;
        transition: all 0.2s ease;
    }
    div[data-testid="stVerticalBlockBorderWrapper"] div[data-testid="stPopover"] > button:hover {
        background-color: #f8fafc !important;
        border-color: #cbd5e1 !important;
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
            {"nome": "Conferência de exames de alta", "etapas_obrigatorias": ["Altas Prescritas"]},
            {"nome": "Receituário entregue ao paciente", "etapas_obrigatorias": ["Altas Prescritas"]},
            {"nome": "Orientações de enfermagem explicadas", "etapas_obrigatorias": ["Processo de Enfermagem"]},
            {"nome": "Acompanhante ciente do horário", "etapas_obrigatorias": []},
            {"nome": "Cateteres e acessos retirados", "etapas_obrigatorias": ["Transporte", "Alta Realizada"]}
        ]
    else:
        novos_items = []
        for item in st.session_state['checklist_padrao']:
            if isinstance(item, str):
                novos_items.append({"nome": item, "etapas_obrigatorias": []})
            else:
                novos_items.append(item)
        st.session_state['checklist_padrao'] = novos_items

# ==========================================
# INTEGRAÇÃO E BANCO DE DADOS (GOOGLE SHEETS)
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
        linhas = ws.get_all_values()
        
        if not linhas or len(linhas) < 2:
            st.session_state['dados_df'] = pd.DataFrame()
            return

        idx_cabecalho = 0
        for i, linha in enumerate(linhas[:5]):
            linha_upper = [str(cell).strip().upper() for cell in linha]
            if any(k in linha_upper for k in ["NOME", "LEITO", "UI", "HORA ALTA MÉDICA", "HORA ALTA HOSPITALAR"]):
                idx_cabecalho = i
                break

        cabecalhos_brutos = [str(cell).strip().upper() for cell in linhas[idx_cabecalho]]
        
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

        dados = linhas[idx_cabecalho + 1:]
        largura = len(cabecalhos_unicos)
        dados_normalizados = [row + [""] * (largura - len(row)) for row in dados]
        dados_normalizados = [row[:largura] for row in dados_normalizados]

        df = pd.DataFrame(dados_normalizados, columns=cabecalhos_unicos)
        df = df[df.apply(lambda r: "".join(map(str, r.values)).strip() != "", axis=1)].reset_index(drop=True)

        if df.empty:
            st.session_state['dados_df'] = df
            return

        if "ETAPA_KANBAN" not in df.columns:
            df["ETAPA_KANBAN"] = LISTA_ETAPAS_NOMES[0]
        if "STATUS_ENFERMAGEM" not in df.columns:
            df["STATUS_ENFERMAGEM"] = STATUS_ENFERMAGEM[0]
        if "HISTORICO_LOGS" not in df.columns:
            df["HISTORICO_LOGS"] = "[]"
        if "CHECKLIST_JSON" not in df.columns:
            df["CHECKLIST_JSON"] = "{}"

        st.session_state['dados_df'] = df
        st.session_state['idx_cabecalho'] = idx_cabecalho
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        st.session_state['dados_df'] = pd.DataFrame()

def atualizar_celula_gsheets(aba_nome, linha_pandas, nome_coluna, novo_valor):
    st.session_state['dados_df'].at[linha_pandas, nome_coluna] = novo_valor
    try:
        ws = st.session_state['planilha_ativa'].worksheet(aba_nome)
        idx_cabecalho = st.session_state.get('idx_cabecalho', 0)
        linha_cabecalho_real = idx_cabecalho + 1
        
        cabecalhos_brutos = [str(c).strip().upper() for c in ws.row_values(linha_cabecalho_real)]
        
        if nome_coluna not in cabecalhos_brutos:
            cabecalhos_brutos.append(nome_coluna)
            col_index = len(cabecalhos_brutos)
            ws.update_cell(linha_cabecalho_real, col_index, nome_coluna)
        else:
            col_index = cabecalhos_brutos.index(nome_coluna) + 1
            
        row_index = linha_pandas + idx_cabecalho + 2 
        ws.update_cell(row_index, col_index, str(novo_valor))
    except Exception as e:
        st.error(f"Erro ao salvar no Google Sheets: {e}")

def registrar_evento_log(aba_nome, linha_pandas, tipo_evento, detalhe):
    df = st.session_state['dados_df']
    logs_str = df.at[linha_pandas, 'HISTORICO_LOGS'] if 'HISTORICO_LOGS' in df.columns else "[]"
    
    try:
        logs = json.loads(logs_str) if logs_str else []
    except:
        logs = []

    novo_log = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "evento": tipo_evento,
        "detalhe": detalhe
    }
    logs.append(novo_log)
    logs_json = json.dumps(logs, ensure_ascii=False)
    atualizar_celula_gsheets(aba_nome, linha_pandas, "HISTORICO_LOGS", logs_json)

def obter_valor_campo(row, nome_base, padrao='--:--'):
    for c in row.index:
        if str(c).startswith(nome_base):
            val = str(row[c]).strip()
            if val:
                return val
    return padrao

# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
def main():
    inicializar_estado()
    
    # --- HEADER PRINCIPAL ---
    st.markdown("""
        <div class="header-container">
            <div>
                <h1 class="brand-title"> Kanban de Alta Hospitalar</h1>
                <p class="brand-subtitle">Gestão visual e monitoramento de fluxo de alta hospitalar.</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- GERENCIAMENTO DE CHECKLIST ---
    with st.expander("📋 Configuração de Checklist Padrão e Trava de Segurança", expanded=False):
        st.caption("Cadastre os itens de checklist e defina em quais etapas do Kanban eles são **obrigatórios**.")
        
        for idx, item in enumerate(st.session_state['checklist_padrao']):
            col_idx, col_nome, col_etapas, col_del = st.columns([0.05, 0.4, 0.45, 0.1])
            col_idx.write(f"**#{idx+1}**")
            col_nome.write(f"**{item['nome']}**")
            
            etapas_sel = col_etapas.multiselect(
                "Obrigatório para entrar na(s) etapa(s):",
                options=LISTA_ETAPAS_NOMES,
                default=item.get('etapas_obrigatorias', []),
                key=f"cfg_etapas_{idx}",
                label_visibility="collapsed"
            )
            item['etapas_obrigatorias'] = etapas_sel

            if col_del.button("❌", key=f"del_chk_item_{idx}"):
                st.session_state['checklist_padrao'].pop(idx)
                st.rerun()

        st.divider()
        st.subheader("➕ Adicionar Novo Item ao Checklist")
        c_add1, c_add2, c_add3 = st.columns([0.45, 0.45, 0.1])
        novo_nome_item = c_add1.text_input("Descrição do item:", placeholder="Ex: Receituário entregue")
        novas_etapas_req = c_add2.multiselect("Obrigatório para entrar nas etapas:", options=LISTA_ETAPAS_NOMES)
        
        if c_add3.button("Salvar", use_container_width=True):
            if novo_nome_item.strip():
                st.session_state['checklist_padrao'].append({
                    "nome": novo_nome_item.strip(),
                    "etapas_obrigatorias": novas_etapas_req
                })
                st.rerun()

    if st.session_state['planilha_ativa'] is None:
        st.warning("⚠️ Planilha não conectada! Por favor, configure a conexão no painel na parte inferior da página.")

    # --- FILTROS E NAVEGAÇÃO ---
    if st.session_state['planilha_ativa'] is not None:
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
                filtro_busca = st.text_input("Buscar Nome ou Leito:", placeholder="Ex: 301A ou Maria")
            with f_col4:
                st.write(" ")
                if st.button("🔄 Sincronizar Dados", use_container_width=True):
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

            # --- METRIC CARDS ---
            st.markdown("<br>", unsafe_allow_html=True)
            m1, m2, m3, m4 = st.columns(4)
            
            total_prev = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Altas Previstas"])
            total_presc = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Altas Prescritas"])
            total_pend = len(df_filtrado[df_filtrado['ETAPA_KANBAN'].isin(["Processo de Enfermagem", "Pendência Paciente/Familiar"])])
            total_realiz = len(df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Alta Realizada"])

            m1.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Previstas</div><div class="metric-value">{total_prev}</div></div><div style="font-size:24px;">📅</div></div>', unsafe_allow_html=True)
            m2.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Prescritas</div><div class="metric-value">{total_presc}</div></div><div style="font-size:24px;">📄</div></div>', unsafe_allow_html=True)
            m3.markdown(f'<div class="metric-card"><div><div class="metric-label">Pendências Críticas</div><div class="metric-value">{total_pend}</div></div><div style="font-size:24px;">⚠️</div></div>', unsafe_allow_html=True)
            m4.markdown(f'<div class="metric-card"><div><div class="metric-label">Altas Realizadas</div><div class="metric-value">{total_realiz}</div></div><div style="font-size:24px;">✅</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            # --- QUADRO KANBAN ---
            cols_kanban = st.columns(len(ETAPAS_KANBAN))

            for idx, cfg in enumerate(ETAPAS_KANBAN):
                nome_etapa = cfg["nome"]
                with cols_kanban[idx]:
                    df_col = df_filtrado[df_filtrado['ETAPA_KANBAN'] == nome_etapa]
                    
                    st.markdown(f"""
                        <div class="kanban-header" style="background-color: {cfg['cor']}; border-left: 4px solid {cfg['borda']};">
                            <div style="display: flex; align-items: center; gap: 6px; line-height: 1.25; font-size: 11px; font-weight: 700; color: #1e293b;">
                                <span>{cfg['icone']}</span>
                                <span>{nome_etapa}</span>
                            </div>
                            <span style="background: white; padding: 2px 7px; border-radius: 10px; font-size: 11px; font-weight: 800; color: #0f172a; box-shadow: 0 1px 2px rgba(0,0,0,0.06); flex-shrink: 0;">
                                {len(df_col)}
                            </span>
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

                        # CARD UNIFICADO DO PACIENTE (CONTAINER NATIVO STREAMLIT)
                        with st.container(border=True):
                            st.markdown(f"""
                                <div class="patient-bed">Leito {leito} &nbsp;|&nbsp; {ui}</div>
                                <div class="patient-name-compact">{nome}</div>
                                <div class="patient-time-compact">
                                    <span>⏱ <b>Médica:</b> {hora_med}</span>
                                    <span>|</span>
                                    <span><b>Hosp:</b> {hora_hosp}</span>
                                </div>
                                {f'<div class="badge-status-compact">⚠️ {status_enf}</div>' if nome_etapa == "Processo de Enfermagem" and status_enf != "Sem pendência" else ''}
                            """, unsafe_allow_html=True)

                            # BOTÃO SUTIL "VER DETALHES"
                            with st.popover("Ver detalhes", use_container_width=True):
                                st.subheader(f"👤 {nome}")
                                st.caption(f"Leito: {leito} | Unidade: {ui}")
                                st.write(f"⏱️ **Alta Médica:** {hora_med} | **Alta Hospitalar:** {hora_hosp}")
                                st.divider()

                                chk_json_str = row.get('CHECKLIST_JSON', '{}')
                                try:
                                    chk_estado_dict = json.loads(chk_json_str) if chk_json_str else {}
                                except:
                                    chk_estado_dict = {}

                                # 1. Movimentação de Etapa
                                st.write("➡️ **Mover Etapa do Paciente:**")
                                nova_etapa = st.selectbox(
                                    "Selecione a nova etapa:",
                                    options=LISTA_ETAPAS_NOMES,
                                    index=LISTA_ETAPAS_NOMES.index(nome_etapa),
                                    key=f"mov_{paciente_key}"
                                )

                                if nova_etapa != nome_etapa:
                                    pendencias = []
                                    idx_nova = LISTA_ETAPAS_NOMES.index(nova_etapa)
                                    idx_atual = LISTA_ETAPAS_NOMES.index(nome_etapa)

                                    if idx_nova > idx_atual:
                                        for item_cfg in st.session_state['checklist_padrao']:
                                            item_nome = item_cfg['nome']
                                            etapas_req = item_cfg.get('etapas_obrigatorias', [])
                                            
                                            item_exigido = False
                                            for req in etapas_req:
                                                if req in LISTA_ETAPAS_NOMES:
                                                    if LISTA_ETAPAS_NOMES.index(req) <= idx_nova:
                                                        item_exigido = True
                                                        break

                                            if item_exigido:
                                                is_checked = chk_estado_dict.get(item_nome, False)
                                                if not is_checked:
                                                    pendencias.append(f"• **{item_nome}** (exigido para: {', '.join(etapas_req)})")

                                    if pendencias:
                                        st.error(f"🚨 **Ação Bloqueada!** Faltam itens obrigatórios para avançar para '{nova_etapa}':\n\n" + "\n".join(pendencias))
                                    else:
                                        atualizar_celula_gsheets(aba_selecionada, orig_idx, "ETAPA_KANBAN", nova_etapa)
                                        registrar_evento_log(aba_selecionada, orig_idx, "MUDANCA_ETAPA", f"De '{nome_etapa}' para '{nova_etapa}'")
                                        st.rerun()

                                # 2. Status de Enfermagem
                                if nova_etapa == "Processo de Enfermagem":
                                    st.write("🩺 **Pendência de Enfermagem:**")
                                    st_enf = st.selectbox(
                                        "Selecione o status:",
                                        options=STATUS_ENFERMAGEM,
                                        index=STATUS_ENFERMAGEM.index(status_enf) if status_enf in STATUS_ENFERMAGEM else 0,
                                        key=f"enf_{paciente_key}"
                                    )
                                    if st_enf != status_enf:
                                        atualizar_celula_gsheets(aba_selecionada, orig_idx, "STATUS_ENFERMAGEM", st_enf)
                                        registrar_evento_log(aba_selecionada, orig_idx, "STATUS_ENFERMAGEM", f"Status alterado para '{st_enf}'")
                                        st.rerun()

                                st.divider()

                                # 3. Checklist
                                st.write("📋 **Checklist Padronizado de Alta:**")
                                houve_mudanca_chk = False
                                
                                for item_cfg in st.session_state['checklist_padrao']:
                                    item_nome = item_cfg['nome']
                                    etapas_req = item_cfg.get('etapas_obrigatorias', [])
                                    
                                    label_tag = f" 🔒 *(Obrigatório: {', '.join(etapas_req)})*" if etapas_req else ""
                                    val_atual = chk_estado_dict.get(item_nome, False)
                                    
                                    novo_val = st.checkbox(f"{item_nome}{label_tag}", value=val_atual, key=f"chk_{paciente_key}_{item_nome}")
                                    
                                    if novo_val != val_atual:
                                        chk_estado_dict[item_nome] = novo_val
                                        houve_mudanca_chk = True
                                        acao = "Marcado" if novo_val else "Desmarcado"
                                        registrar_evento_log(aba_selecionada, orig_idx, "CHECKLIST", f"{acao} item: '{item_nome}'")

                                if houve_mudanca_chk:
                                    novo_chk_json = json.dumps(chk_estado_dict, ensure_ascii=False)
                                    atualizar_celula_gsheets(aba_selecionada, orig_idx, "CHECKLIST_JSON", novo_chk_json)
                                    st.rerun()

                                # 4. Histórico
                                with st.expander("📜 Histórico de Alterações (Timestamps)"):
                                    logs_str = row.get('HISTORICO_LOGS', '[]')
                                    try:
                                        logs_list = json.loads(logs_str) if logs_str else []
                                    except:
                                        logs_list = []

                                    if logs_list:
                                        for lg in reversed(logs_list):
                                            st.caption(f"🕒 **{lg.get('timestamp')}** - [{lg.get('evento')}]: {lg.get('detalhe')}")
                                    else:
                                        st.caption("Nenhum histórico registrado ainda.")

            # --- INDICADORES DE TEMPO E LEAD TIME ---
            st.markdown("<br>---", unsafe_allow_html=True)
            st.subheader("📈 Indicadores de Tempo & Lead Time")

            tab_ind1, tab_ind2 = st.tabs(["⏱️ Tempo Médio do Processo", "📊 Gargalos do Dia"])

            with tab_ind1:
                dados_tempo = []
                for _, r in df_filtrado.iterrows():
                    logs_raw = r.get('HISTORICO_LOGS', '[]')
                    try:
                        l_list = json.loads(logs_raw) if logs_raw else []
                    except:
                        l_list = []
                    
                    t_inicio = None
                    t_fim = None
                    for lg in l_list:
                        if lg.get('evento') == 'MUDANCA_ETAPA':
                            if not t_inicio:
                                t_inicio = datetime.strptime(lg.get('timestamp'), "%Y-%m-%d %H:%M:%S")
                            if "Alta Realizada" in lg.get('detalhe', ''):
                                t_fim = datetime.strptime(lg.get('timestamp'), "%Y-%m-%d %H:%M:%S")

                    if t_inicio and t_fim:
                        duracao_min = (t_fim - t_inicio).total_seconds() / 60.0
                        dados_tempo.append({"Paciente": r.get('NOME', 'Sem nome'), "Duracao_Minutos": duracao_min})

                if dados_tempo:
                    df_tempos = pd.DataFrame(dados_tempo)
                    media_minutos = df_tempos['Duracao_Minutos'].mean()
                    
                    col_t1, col_t2 = st.columns(2)
                    col_t1.metric("Tempo Médio de Processo (Abertura -> Finalização)", f"{int(media_minutos)} min")
                    
                    fig_hist = px.histogram(df_tempos, x="Duracao_Minutos", nbins=10, title="Distribuição do Tempo de Alta (Minutos)")
                    col_t2.plotly_chart(fig_hist, use_container_width=True)
                else:
                    st.info("ℹ Os tempos médios serão exibidos conforme as movimentações de etapas forem finalizadas como 'Alta Realizada'.")

            with tab_ind2:
                g1, g2 = st.columns(2)
                with g1:
                    chart_data = df_filtrado['ETAPA_KANBAN'].value_counts().reset_index()
                    chart_data.columns = ['Etapa', 'Pacientes']
                    fig = px.bar(chart_data, x='Etapa', y='Pacientes', color='Etapa', text_auto=True, title="Pacientes por Etapa")
                    fig.update_layout(showlegend=False, height=280)
                    st.plotly_chart(fig, use_container_width=True)

                with g2:
                    df_enf = df_filtrado[df_filtrado['ETAPA_KANBAN'] == "Processo de Enfermagem"]
                    if not df_enf.empty:
                        chart_enf = df_enf['STATUS_ENFERMAGEM'].value_counts().reset_index()
                        chart_enf.columns = ['Pendência', 'Qtd']
                        fig_enf = px.pie(chart_enf, names='Pendência', values='Qtd', hole=0.4, title="Gargalos na Enfermagem")
                        fig_enf.update_layout(height=280)
                        st.plotly_chart(fig_enf, use_container_width=True)
                    else:
                        st.info("Nenhuma pendência mapeada na Enfermagem no momento.")

    # ==========================================
    # PAINEL DE CONEXÃO GOOGLE SHEETS (RODAPÉ)
    # ==========================================
    st.markdown("<br><br>---", unsafe_allow_html=True)
    with st.expander("🔌 Conexão e Configuração do Google Sheets (Avançado)", expanded=(st.session_state['planilha_ativa'] is None)):
        st.caption("Painel administrativo para autenticação e conexão com a base de dados.")
        
        col_conn1, col_conn2 = st.columns(2)
        with col_conn1:
            arquivo_credenciais = st.file_uploader("Upload do arquivo JSON de Credenciais", type=['json'])
        with col_conn2:
            url_planilha = st.text_input("Link / URL da Planilha Google Sheets:")

        if st.button("🔌 Conectar e Salvar Conexão", use_container_width=True):
            if arquivo_credenciais and url_planilha:
                if conectar_google_sheets(arquivo_credenciais, url_planilha):
                    st.success("Conectado com sucesso ao Google Sheets!")
                    st.rerun()
            else:
                st.warning("Envie o arquivo de credenciais JSON e o link da planilha.")

if __name__ == "__main__":
    main()
