"""
Kanban de Altas Hospitalares - piloto
Autor: piloto para testes (dados 100% fictícios)

Execução local:
    pip install -r requirements.txt
    streamlit run app.py
"""

import json
from datetime import date, timedelta

import streamlit as st

st.set_page_config(
    page_title="Kanban de Altas Hospitalares",
    page_icon="🏥",
    layout="wide",
)

# --------------------------------------------------------------------------- #
# CONFIGURAÇÃO DAS ETAPAS (edite aqui para mudar o fluxo)
# --------------------------------------------------------------------------- #
ETAPAS = [
    {"id": "previsao", "nome": "Alta prevista", "cor": "#3E7CB1", "icone": "🗓️"},
    {"id": "preparo", "nome": "Em preparo", "cor": "#D98324", "icone": "⚙️"},
    {"id": "pendencias", "nome": "Com pendência", "cor": "#C0392B", "icone": "⚠️"},
    {"id": "liberado", "nome": "Liberado p/ sair", "cor": "#7D5BA6", "icone": "🚪"},
    {"id": "concluida", "nome": "Alta efetivada", "cor": "#2E8B57", "icone": "✅"},
]

ETAPA_IDS = [e["id"] for e in ETAPAS]
ETAPA_FINAL = "concluida"

# Itens críticos que precisam estar cumpridos antes da alta sair
CHECKLIST = [
    "Sumário de alta preenchido",
    "Receitas e prescrição de casa entregues",
    "Conciliação medicamentosa revisada",
    "Orientação ao paciente / acompanhante",
    "Retorno ambulatorial agendado",
    "Exames e laudos pendentes liberados",
    "Transporte / remoção definido",
    "Liberação administrativa (convênio / faturamento)",
]

RISCOS = ["Baixo", "Médio", "Alto"]
COR_RISCO = {"Baixo": "#2E8B57", "Médio": "#D98324", "Alto": "#C0392B"}


# --------------------------------------------------------------------------- #
# DADOS FICTÍCIOS
# --------------------------------------------------------------------------- #
def dados_ficticios():
    hoje = date.today()

    def card(cid, nome, idade, sexo, leito, setor, dx, medico, conv, dias, risco,
             etapa, feitos, obs=""):
        return {
            "id": cid,
            "nome": nome,
            "idade": idade,
            "sexo": sexo,
            "leito": leito,
            "setor": setor,
            "diagnostico": dx,
            "medico": medico,
            "convenio": conv,
            "previsao": (hoje + timedelta(days=dias)).isoformat(),
            "risco": risco,
            "etapa": etapa,
            "checks": {item: (item in feitos) for item in CHECKLIST},
            "obs": obs,
        }

    return [
        card("PAC-001", "Maria Aparecida Souza", 72, "F", "301-A", "Clínica Médica",
             "ICC descompensada", "Dr. Renato Lima", "Unimed", 0, "Alto",
             "pendencias",
             ["Sumário de alta preenchido", "Conciliação medicamentosa revisada"],
             "Aguarda vaga em home care para oxigenoterapia."),
        card("PAC-002", "João Batista Ferreira", 58, "M", "212-B", "Cardiologia",
             "Pós-IAM sem supra", "Dra. Carla Nunes", "SUS", 0, "Médio",
             "liberado", CHECKLIST[:6],
             "Familiar chega às 14h para buscar."),
        card("PAC-003", "Ana Clara Ribeiro", 34, "F", "405", "Obstetrícia",
             "Pós-parto cesárea (D2)", "Dr. Marcos Tavares", "Bradesco Saúde", 0, "Baixo",
             "preparo",
             ["Orientação ao paciente / acompanhante"],
             "Teste do pezinho do RN já coletado."),
        card("PAC-004", "Sebastião Moreira", 81, "M", "118-A", "Clínica Médica",
             "Pneumonia comunitária", "Dr. Renato Lima", "SUS", 1, "Alto",
             "previsao", [],
             "Mora sozinho — avaliar rede de apoio com serviço social."),
        card("PAC-005", "Patrícia Gomes Alves", 46, "F", "220", "Cirurgia Geral",
             "Pós-colecistectomia videolaparoscópica", "Dra. Helena Prado", "Amil", 0, "Baixo",
             "liberado", CHECKLIST[:5] + [CHECKLIST[6]],
             "Falta liberação do faturamento."),
        card("PAC-006", "Carlos Eduardo Pinto", 67, "M", "307-B", "Neurologia",
             "AVC isquêmico em reabilitação", "Dr. Felipe Andrade", "SulAmérica", 2, "Alto",
             "previsao", [],
             "Necessita transporte em maca e fisioterapia domiciliar."),
        card("PAC-007", "Luiza Martins Dias", 29, "F", "410", "Ortopedia",
             "Pós-osteossíntese de tíbia", "Dra. Helena Prado", "SUS", 1, "Médio",
             "preparo",
             ["Sumário de alta preenchido", "Receitas e prescrição de casa entregues"],
             "Aguardando muletas da fisioterapia."),
        card("PAC-008", "Antônio Carlos Ramos", 75, "M", "115-B", "Clínica Médica",
             "DPOC exacerbado", "Dr. Renato Lima", "Unimed", 0, "Médio",
             "concluida", CHECKLIST,
             "Alta efetivada às 10h32."),
        card("PAC-009", "Rosa Maria Beltrão", 63, "F", "308-A", "Nefrologia",
             "DRC em hemodiálise — internação por hipervolemia", "Dra. Carla Nunes", "SUS", 1,
             "Alto", "pendencias",
             ["Conciliação medicamentosa revisada"],
             "Confirmar vaga na clínica de diálise de origem."),
        card("PAC-010", "Fernando Queiroz", 51, "M", "206", "Cirurgia Geral",
             "Pós-herniorrafia inguinal", "Dra. Helena Prado", "Porto Seguro", 0, "Baixo",
             "preparo", ["Sumário de alta preenchido"], ""),
    ]


# --------------------------------------------------------------------------- #
# ESTADO
# --------------------------------------------------------------------------- #
if "cards" not in st.session_state:
    st.session_state.cards = dados_ficticios()
if "log" not in st.session_state:
    st.session_state.log = []


def get_card(cid):
    return next(c for c in st.session_state.cards if c["id"] == cid)


def progresso(card):
    feitos = sum(1 for v in card["checks"].values() if v)
    return feitos, len(CHECKLIST)


def mover(cid, direcao):
    card = get_card(cid)
    i = ETAPA_IDS.index(card["etapa"])
    novo = max(0, min(len(ETAPA_IDS) - 1, i + direcao))
    if novo == i:
        return
    destino = ETAPA_IDS[novo]

    # Regra de segurança: só efetiva a alta com checklist 100% concluído
    feitos, total = progresso(card)
    if destino == ETAPA_FINAL and feitos < total:
        st.toast(
            f"⛔ {card['nome']}: faltam {total - feitos} item(ns) do checklist crítico.",
            icon="⚠️",
        )
        return

    card["etapa"] = destino
    st.session_state.log.insert(
        0, f"{card['id']} — {card['nome']} → {ETAPAS[novo]['nome']}"
    )
    st.rerun()


def marcar_todos(cid, valor=True):
    card = get_card(cid)
    for item in CHECKLIST:
        card["checks"][item] = valor
    st.rerun()


# --------------------------------------------------------------------------- #
# ESTILO
# --------------------------------------------------------------------------- #
st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    .col-head {
        border-radius: 10px; padding: 8px 12px; color: #fff;
        font-weight: 600; font-size: 0.95rem; margin-bottom: 10px;
        display: flex; justify-content: space-between; align-items: center;
    }
    .pill {
        display:inline-block; padding: 1px 9px; border-radius: 12px;
        font-size: 0.70rem; font-weight: 600; color: #fff; margin-right: 4px;
    }
    .card-nome {font-size: 0.95rem; font-weight: 700; line-height: 1.25; margin-bottom: 2px;}
    .card-meta {font-size: 0.78rem; opacity: 0.75; line-height: 1.35;}
    .card-dx {font-size: 0.80rem; margin-top: 6px;}
    </style>
    """,
    unsafe_allow_html=True,
)


# --------------------------------------------------------------------------- #
# SIDEBAR — filtros e ações
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🏥 Gestão de Altas")
    st.caption("Piloto com dados fictícios — sem dados reais de pacientes.")

    st.subheader("Filtros")
    setores = sorted({c["setor"] for c in st.session_state.cards})
    f_setor = st.multiselect("Setor", setores, default=setores)
    f_risco = st.multiselect("Risco de readmissão", RISCOS, default=RISCOS)
    f_busca = st.text_input("Buscar (nome, leito ou ID)", "")
    ocultar_alta = st.checkbox("Ocultar altas efetivadas", value=False)

    st.divider()
    st.subheader("Ações")
    if st.button("🔄 Restaurar dados de exemplo", use_container_width=True):
        st.session_state.cards = dados_ficticios()
        st.session_state.log = []
        st.rerun()

    st.download_button(
        "📥 Exportar quadro (JSON)",
        data=json.dumps(st.session_state.cards, ensure_ascii=False, indent=2),
        file_name="quadro_altas.json",
        mime="application/json",
        use_container_width=True,
    )

    if st.session_state.log:
        st.divider()
        st.subheader("Movimentações")
        for linha in st.session_state.log[:8]:
            st.caption(f"• {linha}")


def visivel(c):
    if ocultar_alta and c["etapa"] == ETAPA_FINAL:
        return False
    if c["setor"] not in f_setor or c["risco"] not in f_risco:
        return False
    if f_busca:
        alvo = f"{c['nome']} {c['leito']} {c['id']}".lower()
        if f_busca.lower() not in alvo:
            return False
    return True


cards_visiveis = [c for c in st.session_state.cards if visivel(c)]


# --------------------------------------------------------------------------- #
# CABEÇALHO E INDICADORES
# --------------------------------------------------------------------------- #
st.title("Kanban de Altas Hospitalares")
st.caption("Arraste o fluxo com os botões ◀ ▶ e marque os itens críticos em cada card.")

hoje_iso = date.today().isoformat()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Pacientes no quadro", len(cards_visiveis))
m2.metric("Altas previstas hoje",
          sum(1 for c in cards_visiveis if c["previsao"] == hoje_iso))
m3.metric("Com pendência",
          sum(1 for c in cards_visiveis if c["etapa"] == "pendencias"))
m4.metric("Efetivadas",
          sum(1 for c in cards_visiveis if c["etapa"] == ETAPA_FINAL))

st.divider()


# --------------------------------------------------------------------------- #
# QUADRO KANBAN
# --------------------------------------------------------------------------- #
colunas = st.columns(len(ETAPAS), gap="small")

for col, etapa in zip(colunas, ETAPAS):
    do_etapa = [c for c in cards_visiveis if c["etapa"] == etapa["id"]]
    idx_etapa = ETAPA_IDS.index(etapa["id"])

    with col:
        st.markdown(
            f"<div class='col-head' style='background:{etapa['cor']}'>"
            f"<span>{etapa['icone']} {etapa['nome']}</span>"
            f"<span>{len(do_etapa)}</span></div>",
            unsafe_allow_html=True,
        )

        if not do_etapa:
            st.caption("_Sem pacientes nesta etapa._")

        for card in do_etapa:
            feitos, total = progresso(card)
            atrasado = card["previsao"] < hoje_iso and card["etapa"] != ETAPA_FINAL

            with st.container(border=True):
                st.markdown(
                    f"<div class='card-nome'>{card['nome']}</div>"
                    f"<div class='card-meta'>{card['idade']}a · {card['sexo']} · "
                    f"Leito {card['leito']} · {card['id']}</div>"
                    f"<div class='card-meta'>{card['setor']} · {card['medico']}</div>"
                    f"<div class='card-dx'>🩺 {card['diagnostico']}</div>",
                    unsafe_allow_html=True,
                )

                tag_data = "🔴 atrasada" if atrasado else f"📅 {card['previsao'][8:]}/{card['previsao'][5:7]}"
                st.markdown(
                    f"<div style='margin-top:8px'>"
                    f"<span class='pill' style='background:{COR_RISCO[card['risco']]}'>"
                    f"risco {card['risco'].lower()}</span>"
                    f"<span class='pill' style='background:#555'>{card['convenio']}</span>"
                    f"<span class='pill' style='background:#444'>{tag_data}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                st.progress(feitos / total, text=f"Checklist {feitos}/{total}")

                with st.expander("Checklist crítico de alta"):
                    for i, item in enumerate(CHECKLIST):
                        card["checks"][item] = st.checkbox(
                            item,
                            value=card["checks"][item],
                            key=f"chk_{card['id']}_{i}",
                        )
                    if st.button("Marcar todos", key=f"all_{card['id']}",
                                 use_container_width=True):
                        marcar_todos(card["id"])

                    obs = st.text_area(
                        "Observações",
                        value=card["obs"],
                        key=f"obs_{card['id']}",
                        height=80,
                        placeholder="Anote pendências, contatos, combinados...",
                    )
                    card["obs"] = obs

                b1, b2 = st.columns(2)
                b1.button(
                    "◀",
                    key=f"back_{card['id']}",
                    use_container_width=True,
                    disabled=idx_etapa == 0,
                    on_click=mover,
                    args=(card["id"], -1),
                    help="Voltar etapa",
                )
                b2.button(
                    "▶",
                    key=f"fwd_{card['id']}",
                    use_container_width=True,
                    disabled=idx_etapa == len(ETAPAS) - 1,
                    on_click=mover,
                    args=(card["id"], 1),
                    help="Avançar etapa",
                )

st.divider()
st.caption(
    "Protótipo para validação de fluxo. Dados fictícios — não inserir informação "
    "real de paciente antes de definir hospedagem, autenticação e conformidade com a LGPD."
)
