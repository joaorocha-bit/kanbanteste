"""
Kanban de Altas Hospitalares - piloto com drag-and-drop
Dados 100% fictícios.

Execução local:
    pip install -r requirements.txt
    streamlit run app.py
"""

import json
from datetime import date, timedelta

import streamlit as st
from streamlit_sortables import sort_items

st.set_page_config(
    page_title="Kanban de Altas Hospitalares",
    page_icon="🏥",
    layout="wide",
)

# --------------------------------------------------------------------------- #
# CONFIGURAÇÃO
# --------------------------------------------------------------------------- #
ETAPAS = [
    {"id": "previsao", "nome": "🗓️ Alta prevista", "cor": "#3E7CB1"},
    {"id": "preparo", "nome": "⚙️ Em preparo", "cor": "#D98324"},
    {"id": "pendencias", "nome": "⚠️ Com pendência", "cor": "#C0392B"},
    {"id": "liberado", "nome": "🚪 Liberado p/ sair", "cor": "#7D5BA6"},
    {"id": "concluida", "nome": "✅ Alta efetivada", "cor": "#2E8B57"},
]
ETAPA_IDS = [e["id"] for e in ETAPAS]
ETAPA_NOME = {e["id"]: e["nome"] for e in ETAPAS}
ETAPA_FINAL = "concluida"

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

ICONE_RISCO = {"Baixo": "🟢", "Médio": "🟡", "Alto": "🔴"}
RISCOS = list(ICONE_RISCO)


# --------------------------------------------------------------------------- #
# DADOS FICTÍCIOS
# --------------------------------------------------------------------------- #
def dados_ficticios():
    hoje = date.today()

    def card(cid, nome, idade, sexo, leito, setor, dx, medico, conv, dias, risco,
             etapa, feitos, obs=""):
        return {
            "id": cid, "nome": nome, "idade": idade, "sexo": sexo, "leito": leito,
            "setor": setor, "diagnostico": dx, "medico": medico, "convenio": conv,
            "previsao": (hoje + timedelta(days=dias)).isoformat(), "risco": risco,
            "etapa": etapa, "obs": obs,
            "checks": {item: (item in feitos) for item in CHECKLIST},
        }

    return [
        card("PAC-001", "Maria Aparecida Souza", 72, "F", "301-A", "Clínica Médica",
             "ICC descompensada", "Dr. Renato Lima", "Unimed", 0, "Alto", "pendencias",
             [CHECKLIST[0], CHECKLIST[2]],
             "Aguarda vaga em home care para oxigenoterapia."),
        card("PAC-002", "João Batista Ferreira", 58, "M", "212-B", "Cardiologia",
             "Pós-IAM sem supra", "Dra. Carla Nunes", "SUS", 0, "Médio", "liberado",
             CHECKLIST[:6], "Familiar chega às 14h para buscar."),
        card("PAC-003", "Ana Clara Ribeiro", 34, "F", "405", "Obstetrícia",
             "Pós-parto cesárea (D2)", "Dr. Marcos Tavares", "Bradesco Saúde", 0,
             "Baixo", "preparo", [CHECKLIST[3]], "Teste do pezinho do RN já coletado."),
        card("PAC-004", "Sebastião Moreira", 81, "M", "118-A", "Clínica Médica",
             "Pneumonia comunitária", "Dr. Renato Lima", "SUS", 1, "Alto", "previsao",
             [], "Mora sozinho — avaliar rede de apoio com serviço social."),
        card("PAC-005", "Patrícia Gomes Alves", 46, "F", "220", "Cirurgia Geral",
             "Pós-colecistectomia videolaparoscópica", "Dra. Helena Prado", "Amil", 0,
             "Baixo", "liberado", CHECKLIST[:5] + [CHECKLIST[6]],
             "Falta liberação do faturamento."),
        card("PAC-006", "Carlos Eduardo Pinto", 67, "M", "307-B", "Neurologia",
             "AVC isquêmico em reabilitação", "Dr. Felipe Andrade", "SulAmérica", 2,
             "Alto", "previsao", [], "Necessita transporte em maca e fisioterapia domiciliar."),
        card("PAC-007", "Luiza Martins Dias", 29, "F", "410", "Ortopedia",
             "Pós-osteossíntese de tíbia", "Dra. Helena Prado", "SUS", 1, "Médio",
             "preparo", CHECKLIST[:2], "Aguardando muletas da fisioterapia."),
        card("PAC-008", "Antônio Carlos Ramos", 75, "M", "115-B", "Clínica Médica",
             "DPOC exacerbado", "Dr. Renato Lima", "Unimed", 0, "Médio", "concluida",
             CHECKLIST, "Alta efetivada às 10h32."),
        card("PAC-009", "Rosa Maria Beltrão", 63, "F", "308-A", "Nefrologia",
             "DRC — internação por hipervolemia", "Dra. Carla Nunes", "SUS", 1,
             "Alto", "pendencias", [CHECKLIST[2]],
             "Confirmar vaga na clínica de diálise de origem."),
        card("PAC-010", "Fernando Queiroz", 51, "M", "206", "Cirurgia Geral",
             "Pós-herniorrafia inguinal", "Dra. Helena Prado", "Porto Seguro", 0,
             "Baixo", "preparo", [CHECKLIST[0]], ""),
    ]


# --------------------------------------------------------------------------- #
# ESTADO
# --------------------------------------------------------------------------- #
if "cards" not in st.session_state:
    st.session_state.cards = dados_ficticios()
if "log" not in st.session_state:
    st.session_state.log = []
if "board_rev" not in st.session_state:
    st.session_state.board_rev = 0   # muda o key do componente para forçar redesenho


def get_card(cid):
    return next(c for c in st.session_state.cards if c["id"] == cid)


def progresso(card):
    return sum(1 for v in card["checks"].values() if v), len(CHECKLIST)


def rotulo(card):
    """Texto mostrado dentro do card arrastável (multilinha via white-space: pre-line)."""
    feitos, total = progresso(card)
    barra = "▰" * feitos + "▱" * (total - feitos)
    atraso = " ⏰" if card["previsao"] < date.today().isoformat() \
        and card["etapa"] != ETAPA_FINAL else ""
    d = card["previsao"]
    return (
        f"{ICONE_RISCO[card['risco']]} {card['nome']}{atraso}\n"
        f"{card['id']} · Leito {card['leito']} · {card['idade']}a {card['sexo']}\n"
        f"{card['setor']} · {card['medico']}\n"
        f"🩺 {card['diagnostico']}\n"
        f"{barra}  {feitos}/{total} · 📅 {d[8:]}/{d[5:7]}"
    )


# --------------------------------------------------------------------------- #
# ESTILO DO COMPONENTE DE DRAG-AND-DROP
# --------------------------------------------------------------------------- #
ESTILO_KANBAN = """
.sortable-component {
    display: flex;
    gap: 10px;
    align-items: flex-start;
    background-color: transparent;
    font-family: "Source Sans Pro", sans-serif;
}
.sortable-container {
    flex: 1 1 0;
    min-width: 0;
    background-color: rgba(128,128,128,0.10);
    border-radius: 10px;
    padding: 6px;
}
.sortable-container-header {
    background-color: #46546b;
    color: #ffffff;
    border-radius: 8px;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 0.86rem;
    text-align: center;
}
.sortable-container-body { min-height: 120px; padding-top: 6px; }
.sortable-item {
    background-color: #ffffff;
    color: #1f2933;
    border: 1px solid rgba(0,0,0,0.10);
    border-left: 5px solid #46546b;
    border-radius: 8px;
    padding: 9px 10px;
    margin-bottom: 8px;
    font-size: 0.76rem;
    line-height: 1.38;
    white-space: pre-line;
    text-align: left;
    cursor: grab;
    box-shadow: 0 1px 3px rgba(0,0,0,0.12);
}
.sortable-item:hover { box-shadow: 0 3px 8px rgba(0,0,0,0.20); }
"""


# --------------------------------------------------------------------------- #
# SIDEBAR
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("🏥 Gestão de Altas")
    st.caption("Piloto com dados fictícios — sem dados reais de pacientes.")

    st.subheader("Filtros")
    setores = sorted({c["setor"] for c in st.session_state.cards})
    f_setor = st.multiselect("Setor", setores, default=setores)
    f_risco = st.multiselect("Risco de readmissão", RISCOS, default=RISCOS)
    ocultar_alta = st.checkbox("Ocultar altas efetivadas", value=False)

    st.divider()
    if st.button("🔄 Restaurar dados de exemplo", use_container_width=True):
        st.session_state.cards = dados_ficticios()
        st.session_state.log = []
        st.session_state.board_rev += 1
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
    return c["setor"] in f_setor and c["risco"] in f_risco


cards_visiveis = [c for c in st.session_state.cards if visivel(c)]


# --------------------------------------------------------------------------- #
# CABEÇALHO
# --------------------------------------------------------------------------- #
st.title("Kanban de Altas Hospitalares")
st.caption("Arraste os cards entre as colunas para mudar a etapa. "
           "Abaixo do quadro você marca o checklist crítico de cada paciente.")

hoje_iso = date.today().isoformat()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Pacientes no quadro", len(cards_visiveis))
m2.metric("Altas previstas hoje", sum(1 for c in cards_visiveis if c["previsao"] == hoje_iso))
m3.metric("Com pendência", sum(1 for c in cards_visiveis if c["etapa"] == "pendencias"))
m4.metric("Efetivadas", sum(1 for c in cards_visiveis if c["etapa"] == ETAPA_FINAL))


# --------------------------------------------------------------------------- #
# QUADRO ARRASTÁVEL
# --------------------------------------------------------------------------- #
rotulo_para_id = {rotulo(c): c["id"] for c in cards_visiveis}

quadro = [
    {
        "header": f"{e['nome']}  ({sum(1 for c in cards_visiveis if c['etapa'] == e['id'])})",
        "items": [rotulo(c) for c in cards_visiveis if c["etapa"] == e["id"]],
    }
    for e in ETAPAS
]

resultado = sort_items(
    quadro,
    multi_containers=True,
    custom_style=ESTILO_KANBAN,
    key=f"kanban_{st.session_state.board_rev}",
)

# Aplica o resultado do arraste ao estado
if resultado:
    houve_mudanca = False
    bloqueios = []
    for coluna, etapa in zip(resultado, ETAPAS):
        for item in coluna["items"]:
            cid = rotulo_para_id.get(item)
            if cid is None:
                continue
            card = get_card(cid)
            if card["etapa"] == etapa["id"]:
                continue

            feitos, total = progresso(card)
            if etapa["id"] == ETAPA_FINAL and feitos < total:
                bloqueios.append((card, total - feitos))
                continue

            card["etapa"] = etapa["id"]
            st.session_state.log.insert(
                0, f"{card['id']} — {card['nome']} → {ETAPA_NOME[etapa['id']]}"
            )
            houve_mudanca = True

    if bloqueios:
        for card, faltam in bloqueios:
            st.error(
                f"⛔ **{card['nome']}** não pode ir para *Alta efetivada*: "
                f"faltam {faltam} item(ns) do checklist crítico."
            )
        st.session_state.board_rev += 1   # devolve o card para a coluna de origem
        st.rerun()

    if houve_mudanca:
        st.session_state.board_rev += 1
        st.rerun()


# --------------------------------------------------------------------------- #
# PAINEL DO PACIENTE — checklist e observações
# --------------------------------------------------------------------------- #
st.divider()
st.subheader("Checklist crítico de alta")

if not cards_visiveis:
    st.info("Nenhum paciente com os filtros atuais.")
    st.stop()

opcoes = {f"{c['id']} — {c['nome']} ({c['leito']})": c["id"] for c in cards_visiveis}
escolha = st.selectbox("Paciente", list(opcoes), index=0)
card = get_card(opcoes[escolha])
feitos, total = progresso(card)

esq, dir_ = st.columns([2, 3])

with esq:
    with st.container(border=True):
        st.markdown(f"### {card['nome']}")
        st.markdown(
            f"**{card['idade']} anos · {card['sexo']} · Leito {card['leito']}**  \n"
            f"{card['setor']} · {card['medico']}  \n"
            f"Convênio: {card['convenio']}  \n"
            f"Etapa atual: **{ETAPA_NOME[card['etapa']]}**  \n"
            f"Previsão de alta: {card['previsao']}  \n"
            f"Risco de readmissão: {ICONE_RISCO[card['risco']]} {card['risco']}"
        )
        st.markdown(f"🩺 *{card['diagnostico']}*")
        st.progress(feitos / total, text=f"Checklist {feitos}/{total}")

with dir_:
    with st.container(border=True):
        c1, c2 = st.columns(2)
        for i, item in enumerate(CHECKLIST):
            alvo = c1 if i < len(CHECKLIST) / 2 else c2
            novo = alvo.checkbox(item, value=card["checks"][item],
                                 key=f"chk_{card['id']}_{i}")
            if novo != card["checks"][item]:
                card["checks"][item] = novo
                st.session_state.board_rev += 1
                st.rerun()

        b1, b2 = st.columns(2)
        if b1.button("✔️ Marcar todos", use_container_width=True):
            for item in CHECKLIST:
                card["checks"][item] = True
            st.session_state.board_rev += 1
            st.rerun()
        if b2.button("✖️ Limpar todos", use_container_width=True):
            for item in CHECKLIST:
                card["checks"][item] = False
            st.session_state.board_rev += 1
            st.rerun()

        obs = st.text_area("Observações", value=card["obs"],
                           key=f"obs_{card['id']}", height=90,
                           placeholder="Pendências, contatos, combinados...")
        card["obs"] = obs

st.caption(
    "Protótipo para validação de fluxo. Dados fictícios — não inserir informação real "
    "de paciente antes de definir hospedagem, autenticação e conformidade com a LGPD."
)
