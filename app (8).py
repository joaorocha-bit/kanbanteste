import streamlit as st

# 1. Configuração inicial da página
st.set_page_config(page_title="Kanban de Altas Hospitalares", layout="wide")
st.title("🏥 Kanban de Altas Hospitalares (Piloto)")

# 2. Definição das etapas do processo de alta
ETAPAS = [
    "Avaliação Médica", 
    "Preparo Enfermagem", 
    "Aguardando Transporte", 
    "Alta Concluída"
]

# 3. Inicialização dos dados fictícios no Session State
# Isso garante que a página não "esqueça" os dados quando for recarregada
if "pacientes" not in st.session_state:
    st.session_state.pacientes = {
        "1": {
            "nome": "João Silva", "leito": "101A", "diagnostico": "Pneumonia", 
            "etapa": "Avaliação Médica",
            "tarefas": {"Receita Médica Emitida": False, "Resumo de Alta Assinado": False}
        },
        "2": {
            "nome": "Maria Souza", "leito": "205B", "diagnostico": "Pós-operatório Apendicite", 
            "etapa": "Preparo Enfermagem",
            "tarefas": {"Orientações Passadas": False, "Acesso Venoso Retirado": True}
        },
        "3": {
            "nome": "Carlos Pereira", "leito": "310C", "diagnostico": "Insuficiência Cardíaca", 
            "etapa": "Aguardando Transporte",
            "tarefas": {"Transporte Confirmado": True, "Pertences Devolvidos": False}
        },
        "4": {
            "nome": "Ana Oliveira", "leito": "102A", "diagnostico": "Asma Exacerbada", 
            "etapa": "Avaliação Médica",
            "tarefas": {"Receita Médica Emitida": True, "Resumo de Alta Assinado": False}
        }
    }

# 4. Funções de controle (Mover cards e atualizar tarefas)
def mover_paciente(paciente_id, direcao):
    etapa_atual = st.session_state.pacientes[paciente_id]["etapa"]
    idx_atual = ETAPAS.index(etapa_atual)
    
    if direcao == "avancar" and idx_atual < len(ETAPAS) - 1:
        st.session_state.pacientes[paciente_id]["etapa"] = ETAPAS[idx_atual + 1]
    elif direcao == "voltar" and idx_atual > 0:
        st.session_state.pacientes[paciente_id]["etapa"] = ETAPAS[idx_atual - 1]

def atualizar_tarefa(paciente_id, tarefa):
    # Inverte o status do checkbox
    status_atual = st.session_state.pacientes[paciente_id]["tarefas"][tarefa]
    st.session_state.pacientes[paciente_id]["tarefas"][tarefa] = not status_atual

# 5. Construção da Interface do Kanban
colunas = st.columns(len(ETAPAS))

for idx, etapa in enumerate(ETAPAS):
    with colunas[idx]:
        # Cabeçalho da coluna
        st.subheader(etapa)
        
        # Filtra os pacientes que estão na etapa atual
        pacientes_na_etapa = {k: v for k, v in st.session_state.pacientes.items() if v["etapa"] == etapa}
        
        # Cria um "card" para cada paciente
        for pid, p_dados in pacientes_na_etapa.items():
            # O border=True cria a aparência de um card contornado
            with st.container(border=True):
                st.markdown(f"**👤 {p_dados['nome']}**")
                st.markdown(f"🛏️ **Leito:** {p_dados['leito']}  \n🩺 **Diag:** {p_dados['diagnostico']}")
                
                st.markdown("**Checklist Crítico:**")
                # Renderiza os checkboxes para as tarefas do paciente
                for tarefa, concluida in p_dados["tarefas"].items():
                    st.checkbox(
                        tarefa, 
                        value=concluida, 
                        key=f"chk_{pid}_{tarefa}", # Chave única para evitar conflitos no Streamlit
                        on_change=atualizar_tarefa, 
                        args=(pid, tarefa)
                    )
                
                st.write("") # Espaçamento
                
                # Botões de navegação do card
                c1, c2 = st.columns(2)
                with c1:
                    if idx > 0:
                        st.button("⬅️ Voltar", key=f"v_{pid}", on_click=mover_paciente, args=(pid, "voltar"), use_container_width=True)
                with c2:
                    if idx < len(ETAPAS) - 1:
                        # Estiliza o botão de avanço como "primário" se todas as tarefas estiverem concluídas
                        todas_tarefas_ok = all(p_dados["tarefas"].values())
                        tipo_botao = "primary" if todas_tarefas_ok else "secondary"
                        st.button("Avançar ➡️", key=f"a_{pid}", on_click=mover_paciente, args=(pid, "avancar"), type=tipo_botao, use_container_width=True)