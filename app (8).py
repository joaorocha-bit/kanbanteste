"""
Kanban de Altas Hospitalares - piloto
Drag-and-drop + checklist dentro do card (clique no card abre o diálogo).
Dados 100% fictícios.

Execução local:
    pip install -r requirements.txt
    streamlit run app.py
"""

import json
from datetime import date, timedelta

import streamlit as st

try:
    from streamlit_kanban_board_goviceversa import kanban_board
except ImportError:
    st.error(
        "Componente não instalado. Rode `pip install -r requirements.txt` "
        "(ou `pip install streamlit-kanban-board-goviceversa`)."
    )
    st.stop()

st.set_page_config(
    page_title="Kanban de Altas Hospitalares",
    page_icon="🏥",
    layout="wide",
)

# --------------------------------------------------------------------------- #
# CONFIGURAÇÃO
# --------------------------------------------------------------------------- #
ETAPAS = [
    {"id": "previsao", "name": "🗓️ Alta prevista", "color": "#3E7CB1"},
    {"id": "preparo", "name": "⚙️ Em preparo", "color": "#D98324"},
    {"id": "pendencias", "name": "⚠️ Com pendência", "color": "#C0392B"},
    {"id": "liberado", "name": "🚪 Liberado p/ sair", "color": "#7D5BA6"},
    {"id": "concluida", "name": "✅ Alta efetivada", "color": "#2E8B57"},
]
ETAPA_NOME = {e["id"]: e["name"] for e in ETAPAS}
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
             "Alto", "previsao", [],
             "Necessita transporte em maca e fisioterapia domiciliar."),
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
for chave, valor in {
    "cards": None, "log": [], "evento": None,
    "paciente_aberto": None, "mostrar_dialog": False, "board_rev": 0,
}.items():
    if chave not in st.session_state:
        st.session_state[chave] = dados_ficticios() if chave == "cards" else valor


def get_card(cid):
    return next(c for c in st.session_state.cards if c["id"] == cid)


def progresso(card):
    return sum(1 for v in card["checks"].values() if v), len(CHECKLIST)


# --------------------------------------------------------------------------- #
# MONTAGEM DO CARD PARA O COMPONENTE
# --------------------------------------------------------------------------- #
def para_componente(card):
    """Converte o paciente no formato de 'deal' esperado pelo componente."""
    feitos, total = progresso(card)
    pendentes = [i for i, ok in card["checks"].items() if not ok]
    atrasado = card["previsao"] < date.today().isoformat() and card["etapa"] != ETAPA_FINAL
    pct = int(100 * feitos / total)
    cor_barra = "#2E8B57" if feitos == total else ("#D98324" if feitos else "#C0392B")

    # Checklist desenhado dentro do card (visual; a edição é no diálogo)
    linhas = "".join(
        f"<div style='font-size:10.5px;line-height:1.5;"
        f"color:{'#2E8B57' if card['checks'][i] else '#8a94a6'}'>"
        f"{'☑' if card['checks'][i] else '☐'} {i}</div>"
        for i in CHECKLIST
    )
    html = f"""
    <div style="margin-top:6px">
      <div style="font-size:11px;margin-bottom:3px">
        🩺 {card['diagnostico']}
      </div>
      <div style="background:#e6e9ef;border-radius:5px;height:7px;overflow:hidden">
        <div style="width:{pct}%;height:7px;background:{cor_barra}"></div>
      </div>
      <div style="font-size:10.5px;margin:3px 0 5px 0;font-weight:600">
        Checklist {feitos}/{total}{' · ⏰ alta atrasada' if atrasado else ''}
      </div>
      {linhas}
      <div style="font-size:10px;color:#8a94a6;margin-top:5px">
        {'✅ pronto para efetivar alta' if not pendentes else f'⏳ {len(pendentes)} pendência(s)'}
        · clique para editar
      </div>
    </div>
    """

    return {
        "id": card["id"],
        "stage": card["etapa"],
        "deal_id": f"{ICONE_RISCO[card['risco']]} {card['id']} · Leito {card['leito']}",
        "company_name": card["nome"],
        "product_type": card["setor"],
        "date": card["previsao"],
        "underwriter": card["medico"],
        "priority": "high" if card["risco"] == "Alto" else
                    ("medium" if card["risco"] == "Médio" else "low"),
        "source": "VV" if card["risco"] == "Alto" else "OF",
        "custom_html": html,
    }


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
st.caption("Arraste o card para mudar de etapa · clique no card para abrir o checklist.")

hoje_iso = date.today().isoformat()
m1, m2, m3, m4 = st.columns(4)
m1.metric("Pacientes no quadro", len(cards_visiveis))
m2.metric("Altas previstas hoje", sum(1 for c in cards_visiveis if c["previsao"] == hoje_iso))
m3.metric("Com pendência", sum(1 for c in cards_visiveis if c["etapa"] == "pendencias"))
m4.metric("Efetivadas", sum(1 for c in cards_visiveis if c["etapa"] == ETAPA_FINAL))


# --------------------------------------------------------------------------- #
# QUADRO
# --------------------------------------------------------------------------- #
resultado = kanban_board(
    stages=ETAPAS,
    deals=[para_componente(c) for c in cards_visiveis],
    height=780,
    key=f"kanban_altas_{st.session_state.board_rev}",
)

# ---- Trata o arraste --------------------------------------------------------
if resultado and resultado.get("moved_deal"):
    mov = resultado["moved_deal"]
    assinatura = ("move", mov.get("deal_id"), mov.get("to_stage"))

    if assinatura != st.session_state.evento:
        st.session_state.evento = assinatura
        card = get_card(mov["deal_id"])
        destino = mov["to_stage"]
        feitos, total = progresso(card)

        # Regra crítica: só efetiva a alta com checklist 100% concluído
        if destino == ETAPA_FINAL and feitos < total:
            st.error(
                f"⛔ **{card['nome']}** não pode ir para *Alta efetivada*: "
                f"faltam {total - feitos} item(ns) do checklist crítico."
            )
            st.session_state.board_rev += 1   # devolve o card à coluna de origem
            st.rerun()
        elif card["etapa"] != destino:
            card["etapa"] = destino
            st.session_state.log.insert(
                0, f"{card['id']} — {card['nome']} → {ETAPA_NOME[destino]}"
            )
            st.rerun()

# ---- Trata o clique no card -------------------------------------------------
if resultado and resultado.get("clicked_deal"):
    cid = resultado["clicked_deal"].get("id") or resultado["clicked_deal"].get("deal_id")
    if cid and st.session_state.paciente_aberto != cid:
        st.session_state.paciente_aberto = cid
        st.session_state.mostrar_dialog = True


# --------------------------------------------------------------------------- #
# DIÁLOGO DO CARD — checklist editável
# --------------------------------------------------------------------------- #
if st.session_state.mostrar_dialog and st.session_state.paciente_aberto:
    card = get_card(st.session_state.paciente_aberto)

    @st.dialog(f"🏥 {card['nome']} · Leito {card['leito']}", width="large")
    def detalhes():
        feitos, total = progresso(card)

        st.markdown(
            f"**{card['idade']} anos · {card['sexo']} · {card['id']}**  \n"
            f"{card['setor']} · {card['medico']} · {card['convenio']}  \n"
            f"🩺 {card['diagnostico']}  \n"
            f"Etapa: **{ETAPA_NOME[card['etapa']]}** · Previsão: {card['previsao']} · "
            f"Risco: {ICONE_RISCO[card['risco']]} {card['risco']}"
        )
        st.progress(feitos / total, text=f"Checklist crítico {feitos}/{total}")
        st.divider()

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

        card["obs"] = st.text_area(
            "Observações", value=card["obs"], key=f"obs_{card['id']}", height=90,
            placeholder="Pendências, contatos, combinados...",
        )

        if st.button("Fechar", type="primary", use_container_width=True):
            st.session_state.mostrar_dialog = False
            st.session_state.paciente_aberto = None
            st.session_state.board_rev += 1
            st.rerun()

    detalhes()

st.caption(
    "Protótipo para validação de fluxo. Dados fictícios — não inserir informação real "
    "de paciente antes de definir hospedagem, autenticação e conformidade com a LGPD."
)
