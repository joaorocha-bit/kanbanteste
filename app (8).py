import streamlit as st
from streamlit_kanban import kanban

st.set_page_config(layout="wide")
st.title("🏥 Kanban de Altas (Drag & Drop)")

# 1. Dados iniciais simulando um banco de dados
if "pacientes" not in st.session_state:
    st.session_state.pacientes = {
        "1": {"nome": "João Silva", "leito": "101A", "etapa": "Avaliação", "tarefas": {"Receita Emitida": False, "Resumo Assinado": False}},
        "2": {"nome": "Maria Souza", "leito": "205B", "etapa": "Enfermagem", "tarefas": {"Acesso Retirado": True}},
        "3": {"nome": "Carlos Pereira", "leito": "310C", "etapa": "Transporte", "tarefas": {"Pertences Devolvidos": False}}
    }

if "card_selecionado" not in st.session_state:
    st.session_state.card_selecionado = None

# 2. Formatar os dados para a biblioteca Kanban
# O streamlit-kanban geralmente exige uma estrutura de colunas e cards (itens)
board = [
    {"id": "col-1", "title": "Avaliação", "cards": []},
    {"id": "col-2", "title": "Enfermagem", "cards": []},
    {"id": "col-3", "title": "Transporte", "cards": []},
    {"id": "col-4", "title": "Alta Concluída", "cards": []}
]

for pid, dados in st.session_state.pacientes.items():
    # Cria indicadores visuais de texto para as tarefas (já que não podemos ter checkboxes aqui)
    total = len(dados["tarefas"])
    concluidas = sum(1 for status in dados["tarefas"].values() if status)
    status_tarefas = f"✅ {concluidas}/{total} Tarefas" if concluidas == total else f"⏳ {concluidas}/{total} Tarefas"

    card_formatado = {
        "id": pid,
        "title": dados["nome"],
        "description": f"🛏️ Leito: {dados['leito']}\n\n{status_tarefas}"
    }
    
    # Aloca o card na coluna correta
    for col in board:
        if col["title"] == dados["etapa"]:
            col["cards"].append(card_formatado)

# 3. Renderizar o Kanban interativo
# A biblioteca captura eventos, como quando um card é clicado ou arrastado
evento = kanban(board)

# Se um card for arrastado para outra coluna, atualizamos a etapa no nosso banco (session_state)
if evento and evento.get("type") == "CARD_MOVED":
    pid = evento["cardId"]
    nova_coluna_id = evento["toColumnId"]
    # Mapeia o ID da coluna de volta para o nome da etapa
    nome_nova_etapa = next(col["title"] for col in board if col["id"] == nova_coluna_id)
    st.session_state.pacientes[pid]["etapa"] = nome_nova_etapa
    st.rerun()

# Se um card for clicado, salvamos no estado para abrir as opções na barra lateral
if evento and evento.get("type") == "CARD_CLICKED":
    st.session_state.card_selecionado = evento["cardId"]

# 4. Barra Lateral (Sidebar) para preencher o Checklist
with st.sidebar:
    st.header("📋 Ações do Paciente")
    
    if st.session_state.card_selecionado:
        pid = st.session_state.card_selecionado
        dados_paciente = st.session_state.pacientes[pid]
        
        st.subheader(f"Paciente: {dados_paciente['nome']}")
        st.write(f"**Leito:** {dados_paciente['leito']}")
        
        st.divider()
        st.write("**Checklist Crítico:**")
        
        # Checkboxes nativos do Streamlit que atualizam as tarefas do paciente selecionado
        for tarefa, status in dados_paciente["tarefas"].items():
            novo_status = st.checkbox(tarefa, value=status, key=f"chk_{pid}_{tarefa}")
            if novo_status != status:
                st.session_state.pacientes[pid]["tarefas"][tarefa] = novo_status
                st.rerun()
                
        if st.button("Fechar Aba", use_container_width=True):
            st.session_state.card_selecionado = None
            st.rerun()
    else:
        st.info("👆 Clique em um card no Kanban para ver e preencher o checklist de alta.")
