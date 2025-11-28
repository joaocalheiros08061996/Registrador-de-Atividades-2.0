# Tela Principal da Aplicação

from typing import Optional, Any, List, Dict  # typing helpers
from kivy.uix.screenmanager import Screen     # tela base do Kivy
from kivy.uix.popup import Popup               # para popups de erro/sucesso
from kivy.uix.label import Label               # rótulos/textos
from kivy.uix.togglebutton import ToggleButton # botões que mantêm estado (down/normal)
from kivy.uix.button import Button             # botão normal (ainda usado em KV)
from kivymd.app import MDApp                   # app KivyMD para pegar user_id e app instance
import src.handle_db as db                     # módulo de acesso a dados (Supabase)

# Imports para finalização automática das atividades
from kivy.clock import Clock
from datetime import datetime, date
import threading

# Cores (RGBA 0-1): ajuste como preferir
NORMAL_COLOR: tuple = (1, 1, 1, 1)            # cor normal do botão (branco)
SELECTED_COLOR: tuple = (0.2, 0.6, 0.2, 1)    # cor quando selecionado (verde)
DISABLED_COLOR: tuple = (0.7, 0.7, 0.7, 1)    # cor quando desabilitado (cinza claro)

class MainScreen(Screen):
    """
    MainScreen: tela principal onde o usuário seleciona tipos de atividade,
    inicia e finaliza atividades, e visualiza o status atual.

    A classe controla:
    - a criação dinâmica dos botões de tipo de atividade (ToggleButtons),
    - o estado da atividade em andamento (current_activity_id),
    - atualizações da interface (labels, caixa de atividade ativa),
    - comunicação com o módulo de banco de dados (`src.handle_db`).

    Observação:
    - Espera-se que o arquivo KV contenha widgets com ids:
      'activity_buttons', 'selected_activity_label', 'descricao_text',
      'status_label', 'start_button', 'end_button', 'active_box', 'active_label'
    """
    # Anotações de tipo para atributos de instância
    current_activity_id: Optional[int] = None           # id da atividade em andamento (se houver)
    selected_activity_type: Optional[str] = None        # texto do tipo de atividade selecionado
    selected_button: Optional[ToggleButton] = None      # referência ao ToggleButton atualmente selecionado

    def __init__(self, **kwargs:Any) -> None:
        
        """
        Inicializador da tela.
        Cria atributos de estado e chama o inicializador da superclasse Screen.
        """
        super().__init__(**kwargs)           # inicializa a parte de Screen do Kivy
        # definir estado inicial: nenhuma atividade selecionada / em andamento
        self.current_activity_id = None     # nenhuma atividade em andamento inicialmente
        self.selected_activity_type = None  # nenhum tipo selecionado inicialmente
        self.selected_button = None         # nenhuma referência a botão selecionado

        # helpers para auto-finalização (executa às 11:30 e 17:40 uma vez por dia)
        self._auto_finalize_event = None
        self._auto_finalize_last_date = {"11:28": None, "16:10": None}

    def carregar_atividades(self) -> None:
        """
        Cria os ToggleButtons dinamicamente a partir de uma lista de tipos de atividade.
        Registra handlers para manter estado visual persistente quando o usuário selecionar.
        Também verifica se já existe uma atividade em andamento (para manter o estado).
        """
         # obter a instância do app (para acessar app.user_id se preciso)
        self.app = MDApp.get_running_app() # tipo: ignore[assignment]
        # lista de tipos predefinidos (pode ser externalizada para config)
        activity_types = [
            "Pesquisa e Desenvolvimento",
            "Atendimento de Fábrica",
            "Documentação",
            "Gabaritos e Dispositivos",
            "Cadastro",
            "Reuniões",
            "Custos",
            "Finame",
            "RNC",
            "Outros",
        ]

        activity_buttons = self.ids.activity_buttons # container (GridLayout dentro de um ScrollView)
        activity_buttons.clear_widgets() # limpar quaisquer widgets existentes

        # Criar ToggleButtons em grupo 'activity' (apenas 1 fica 'down' ao mesmo tempo)
        for activity_type in activity_types:
            # criar um toggle que mantém estado 'down' quando clicado
            btn = ToggleButton(
                text=activity_type,  # texto exibido no botão
                size_hint_y=None,    # altura fixa (usa 'height')
                height=48,           # altura em pixels (ou dp conforme configuração)
                group='activity',    # grupo: garante que apenas um por vez esteja 'down'
                background_color=NORMAL_COLOR, # cor de fundo padrão
                allow_no_selection=False # não permite que nenhum fique selecionado se clicar novamente
            )
            # quando o estado muda, atualiza a seleção
            # ligar o evento de mudança de estado (state) ao método on_activity_toggled
            # usa lambda com parâmetro default para capturar activity_type corretamente
            btn.bind(state=lambda inst, st, at=activity_type: self.on_activity_toggled(inst, st, at))
            # adicionar o botão ao container
            activity_buttons.add_widget(btn)

        # depois de criar botões, verificar se há atividade já em andamento
        self.verificar_atividade_em_andamento()

    def on_activity_toggled(self, inst: ToggleButton, state: str, activity_type: str) -> None:
        """
        Handler chamado quando o estado de um ToggleButton muda.
        - inst: instância do ToggleButton que mudou.
        - state: string 'down' ou 'normal'.
        - activity_type: label do tipo de atividade associado a esse botão.
        """ 
        # se o botão foi pressionado (estado 'down')
        if state == 'down':
              # grava referência ao botão selecionado e ao tipo selecionado
            self.selected_button = inst
            self.selected_activity_type = activity_type
            # tenta mudar a cor do botão para cor de selecionado
            try:
                inst.background_color = SELECTED_COLOR
            except Exception:
                # se por algum motivo não puder setar cor, falha silenciosa
                pass
            # atualizar label de seleção (na interface) para mostrar qual foi escolhido
            try:
                self.ids.selected_activity_label.text = f"Selecionado: {activity_type}"
            except Exception:
                # se o id não existir ou outro problema, ignora
                pass
        else:
            # estado voltou a 'normal' (desselecionado) -> restaurar cor
            try:
                inst.background_color = NORMAL_COLOR
            except Exception:
                pass
            # se o botão liberado era o que estava registrado como selecionado,
            # então limpamos a seleção registrada
            if self.selected_button is inst:
                self.selected_button = None
                self.selected_activity_type = None
                try:
                    # atualizar label para indicar que nada está selecionado
                    self.ids.selected_activity_label.text = "Nenhuma atividade selecionada"
                except Exception:
                    pass

    def acao_iniciar(self) -> None:
        """
        Ação disparada pelo botão 'Iniciar'.
        - Verifica se existe um tipo selecionado.
        - Lê o texto de descrição (se houver).
        - Chama handle_db.iniciar_nova_atividade para registrar no Supabase.
        - Atualiza UI (status label, caixa de atividade ativa, botões).
        """
        # garantir que o usuário selecionou um tipo
        if not self.selected_activity_type:
            self.show_error("Por favor, selecione um tipo de atividade.")
            return
        # ler descrição (se existir campo no KV)
        descricao: str = ""
        try:
            descricao = self.ids.descricao_text.text
        except Exception:
            # se id não existir, manter string vazia
            pass

        try:
            # iniciar atividade no DB; get_running_app().user_id fornece o usuário atual
            self.current_activity_id = db.iniciar_nova_atividade(
                self.selected_activity_type, descricao, MDApp.get_running_app().user_id
            )
            # atualizar label de status para mostrar atividade em andamento
            try:
                self.ids.status_label.text = f"Em andamento: {self.selected_activity_type}"
            except Exception:
                pass
            # mostrar a caixa que indica atividade ativa e ajustar estado dos controles
            self._show_active_box(self.selected_activity_type)
            self._set_state_em_andamento(True)
        except Exception as e:
            # se ocorrer erro ao iniciar no DB, mostrar popup de erro
            self.show_error(f"Falha ao iniciar atividade:\n{e}")

    def acao_finalizar(self) -> None:
        """
        Ação disparada pelo botão 'Finalizar'.
        - Verifica se há atividade em andamento (current_activity_id).
        - Chama handle_db.finalizar_atividade para marcar fim e calcular horas.
        - Atualiza a interface, limpa seleção e esconde a caixa de atividade.
        """
        # se não há atividade em andamento, mostrar erro
        if not self.current_activity_id:
            self.show_error("Não há atividade em andamento para finalizar.")
            return

        try:
            # pedir ao módulo DB para finalizar a atividade corrente
            db.finalizar_atividade(self.current_activity_id)
            # mostrar popup de sucesso
            self.show_success("Atividade finalizada com sucesso.")
            # resetar id e estado local
            self.current_activity_id = None

            # limpar seleção visual: define estado do botão selecionado para 'normal'
            if self.selected_button:
                try:
                    # setar state para 'normal' dispara on_activity_toggled, que reverte cor
                    self.selected_button.state = 'normal'   
                    self.selected_button = None
                except Exception:
                    pass
             # resetar atributos locais
            self.selected_activity_type = None
            try:
                self.ids.selected_activity_label.text = "Nenhuma atividade selecionada"
                self.ids.descricao_text.text = ""
                self.ids.status_label.text = "Pronto para começar."
            except Exception:
                pass

            # esconder a caixa que indica atividade em andamento e ajustar controles
            self._show_active_box(None)
            self._set_state_em_andamento(False)
        except Exception as e:
            # erro ao finalizar: exibir mensagem
            self.show_error(f"Falha ao finalizar atividade:\n{e}")

    def verificar_atividade_em_andamento(self) -> None:
        """
        Verifica no banco se existe uma atividade sem fim (em andamento) para o usuário atual.
        - Se encontrar, atualiza a UI marcando o botão correspondente como 'down'
          e exibindo a caixa de atividade em andamento.
        - Se não encontrar, garante que os controles estejam no estado 'pronto'.
        """
        try:
            # pegar user_id do app
            user_id: Optional[str] = MDApp.get_running_app().user_id
            # chamar função do módulo DB que retorna a última atividade em andamento (ou None)
            row: Optional[Dict[str, Any]] = db.buscar_atividade_em_andamento(user_id)
            if row:
                # existe atividade em andamento -> ajustar UI
                self.current_activity_id = row.get("id") # id do registro
                tipo = row.get("tipo_atividade")         # tipo armazenado no DB
                self.selected_activity_type = tipo

                # tenta marcar o ToggleButton correspondente como 'down'
                for btn in list(self.ids.activity_buttons.children):
                    # comparar texto do botão com o tipo vindo do DB
                    if getattr(btn, 'text', None) == tipo:
                        btn.state = 'down'      # dispara on_activity_toggled -> atualiza cor e label
                        self.selected_button = btn
                    else:
                        # opcional: deixar os outros habilitados mas não selecionados
                        pass

                # atualizar texto/descrição/status na UI com dados retornados
                self.ids.selected_activity_label.text = f"Continuando: {tipo}"
                self.ids.descricao_text.text = row.get("descricao") or ""
                self.ids.status_label.text = f"Continuando: {tipo}"
                # mostrar caixa de atividade ativ
                self._show_active_box(tipo)
                # ajustar estados dos botões (iniciar/desligar) conforme em andamento
                self._set_state_em_andamento(True)
            else:
                 # não há atividade em andamento: ajustar estado para pronto
                self._set_state_em_andamento(False)
        except Exception as e:
             # log simples no console e garantir que UI fique no estado pronto
            print("Aviso: falha ao verificar atividade em andamento:", e)
            self._set_state_em_andamento(False)

    def _set_state_em_andamento(self, em_andamento: bool) -> None:
        """
        Ajusta habilitação/desabilitação dos controles da UI dependendo se
        há uma atividade em andamento (em_andamento=True) ou não.
        """
        try:
            # habilita/desabilita os botões iniciar/finalizar e o campo de descrição
            self.ids.start_button.disabled = em_andamento
            self.ids.end_button.disabled = not em_andamento
            self.ids.descricao_text.disabled = em_andamento
        except Exception:
             # se algum id não existir, apenas ignorar (robustez)
            pass

        # Opcional: desabilitar todos os botões de atividade exceto o selecionado
        for btn in list(self.ids.activity_buttons.children):
            try:
                # se preferir evitar troca de seleção enquanto atividade em andamento:
                btn.disabled = em_andamento and (btn is not self.selected_button)
            except Exception:
                pass

    def _show_active_box(self, tipo_atividade_or_none: Optional[str]) -> None:
        """
        Mostra ou esconde a caixa que exibe a atividade em andamento.
        - Se for passado um tipo (string), a caixa aparece com o texto apropriado.
        - Se for passado None, a caixa é escondida.
        """
        try:
            if tipo_atividade_or_none:
                # mostrar e preencher texto
                self.ids.active_box.height = 48
                self.ids.active_box.opacity = 1
                self.ids.active_label.text = f"Atividade em andamento: {tipo_atividade_or_none}"
            else:
                 # esconder
                self.ids.active_box.height = 0
                self.ids.active_box.opacity = 0
                self.ids.active_label.text = ""
        except Exception:
            # falha silenciosa para robustez caso ids não existam
            pass

    def show_error(self, message: str) -> None:
        """
        Mostra um popup de erro com a mensagem fornecida.
        """
        # cria Popup com título 'Erro' e conteúdo Label com a mensagem
        popup = Popup(title='Erro', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open() # abre o popup na tela

    def show_success(self, message: str) -> None:
        """
        Mostra um popup de sucesso com a mensagem fornecida.
        """
        popup = Popup(title='Sucesso', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def logout(self) -> None:
        """
        Realiza logout: limpa app.user_id e volta para a tela de login.
        """
        app = MDApp.get_running_app() # pega a instância corrente do app
        app.user_id = ""              # limpa identificador do usuário logado
        app.sm.current = 'login'      # troca a tela para o login


    # -------------------------
    # Auto-finalizador por horário
    # -------------------------

    def on_pre_enter(self, *args) -> None:
        """
        Ao entrar na tela principal, inicia o agendador que checa os horários.
        """
        try:
            self.start_auto_finalizer()
        except Exception:
            pass

    def on_leave(self, *args) -> None:
        """
        Ao sair da tela principal, para o agendador.
        """
        try:
            self.stop_auto_finalizer()
        except Exception:
            pass

    def start_auto_finalizer(self) -> None:
        """
        Inicia um Clock que verifica os horários a cada 30 segundos.
        """
        if self._auto_finalize_event is None:
            # checar a cada 30s (pode ajustar para 60s se preferir)
            self._auto_finalize_event = Clock.schedule_interval(self._auto_finalize_check, 30)

    def stop_auto_finalizer(self) -> None:
        """
        Cancela o Clock de checagem.
        """
        if self._auto_finalize_event is not None:
            try:
                self._auto_finalize_event.cancel()
            except Exception:
                pass
            self._auto_finalize_event = None

    def _auto_finalize_check(self, dt) -> None:
        """
        Executado periodicamente pelo Clock. Se o horário for 11:30 ou 17:40
        e ainda não rodou hoje, tenta finalizar a atividade em andamento.
        """
        try:
            now = datetime.now(db.TIMEZONE)  # usa TIMEZONE definido em handle_db.py
            hhmm = now.strftime("%H:%M")
            today = now.date()
            targets = ("11:28", "16:10")

            # Se for um horário alvo e ainda não foi executado hoje
            if hhmm in targets and self._auto_finalize_last_date.get(hhmm) != today:
                # marcar como executado hoje (independente se há atividade) para evitar repetições
                self._auto_finalize_last_date[hhmm] = today

                # se existe atividade em andamento, finalize-a (em thread para não travar UI)
                if self.current_activity_id:
                    activity_id = self.current_activity_id

                    def worker_finalize(act_id: int, time_str: str) -> None:
                        try:
                            db.finalizar_atividade(act_id)
                        except Exception as e:
                            # mostrar erro na UI thread
                            Clock.schedule_once(lambda _dt: self.show_error(f"Falha ao finalizar automaticamente: {e}"), 0)
                            return
                        # sucesso: atualizar UI na thread principal
                        Clock.schedule_once(lambda _dt: self._on_auto_finalized_success(time_str), 0)

                    threading.Thread(target=worker_finalize, args=(activity_id, hhmm), daemon=True).start()
                else:
                    # não havia atividade — só registramos a execução (já feito acima)
                    pass
        except Exception as e:
            # prevenir que exceções atrapalhem o Clock
            print("Erro no auto-finalizador:", e)

    def _on_auto_finalized_success(self, time_str: str) -> None:
        """
        Chamado na UI thread após a finalização automática ser bem sucedida.
        Atualiza o estado local e a interface.
        """
        try:
            self.show_success(f"Atividade finalizada automaticamente às {time_str}.")
        except Exception:
            pass

        # resetar estado local equivalente ao que faz acao_finalizar()
        try:
            self.current_activity_id = None
            if self.selected_button:
                try:
                    self.selected_button.state = 'normal'
                    self.selected_button = None
                except Exception:
                    pass
            self.selected_activity_type = None
            try:
                self.ids.selected_activity_label.text = "Nenhuma atividade selecionada"
                self.ids.descricao_text.text = ""
                self.ids.status_label.text = "Pronto para começar."
            except Exception:
                pass
            self._show_active_box(None)
            self._set_state_em_andamento(False)
        except Exception as e:
            print("Erro ao atualizar UI após auto-finalização:", e)
