# login.py
"""
login.py - versão comentada e com type annotations.

Este módulo fornece:
- funções utilitárias para armazenar/verificar usuários locais (com PBKDF2 + salt),
- a classe LoginScreen (Kivy Screen) que expõe:
    - fazer_login(username, password)
    - criar_conta_popup()
    - handlers para Tab/Enter (mudar foco e submeter)
    - popups informativos
O armazenamento é persistente no diretório de dados do usuário
(e.g. %APPDATA%/RegistroAtividades/users.json no Windows).
"""
from typing import Optional, Dict, Any
import os
import sys
import json
import base64
import hashlib
import secrets
from pathlib import Path

from kivy.uix.screenmanager import Screen
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.app import App
from kivy.core.window import Window

# -------------------------
# Utilitários de persistência
# -------------------------


def get_user_store_path() -> Path:
    """
    Retorna o caminho para o ficheiro users.json usado para persistir credenciais.
    Escolhe diretório apropriado por plataforma:
      - Windows: %APPDATA%/RegistroAtividades/users.json
      - macOS: ~/Library/Application Support/RegistroAtividades/users.json
      - Linux: ~/.local/share/RegistroAtividades/users.json
    Garante que a pasta exista.
    """
    # detectar plataforma e escolher base path
    if sys.platform.startswith("win"):
        # usa APPDATA se disponível, caso contrário Home
        base = os.getenv("APPDATA") or Path.home()
    elif sys.platform == "darwin":
        # macOS convention
        base = Path.home() / "Library" / "Application Support"
    else:
        # linux/unix convention
        base = Path.home() / ".local" / "share"

     # criar pasta específica da aplicação e garantir existência
    folder = Path(base) / "RegistroAtividades"
    folder.mkdir(parents=True, exist_ok=True) # cria se não existir
    # devolver o caminho completo para users.json
    return folder / "users.json"


def hash_password(password: str, salt: Optional[bytes] = None, iterations: int = 200_000) -> Dict[str, Any]:
    """
    Gera um registro contendo salt (base64), hash (base64) e numero de iteracoes.
    - password: senha em texto puro
    - salt: bytes opcionais (se None, gera novo salt seguro com secrets.token_bytes)
    - iterations: número de iterações PBKDF2 (aumente para maior resistência)
    Retorna dicionário: {"salt": ..., "hash": ..., "iters": iterations}
    """
    # gerar salt se não fornecido
    if salt is None:
        salt = secrets.token_bytes(16) # 16 bytes = 128 bits de salt
    # codificar senha para bytes
    pwd = password.encode('utf-8')
    # executar PBKDF2-HMAC-SHA256
    dk = hashlib.pbkdf2_hmac('sha256', pwd, salt, iterations)
    # retornar salt e hash codificados em base64 para fácil serialização JSON
    return {
        "salt": base64.b64encode(salt).decode('ascii'),
        "hash": base64.b64encode(dk).decode('ascii'),
        "iters": iterations
    }

def verify_password(password: str, salt_b64: str, hash_b64: str, iterations: int) -> bool:
    """
    Verifica se a senha fornecida corresponde ao hash/salt armazenados.
    - password: senha em texto puro a verificar
    - salt_b64, hash_b64: strings em base64 recuperadas do armazenamento
    - iterations: número de iterações usadas
    Retorna True se coincidir, False caso contrário.
    """
    # decodificar salt e hash de base64 para bytes
    salt = base64.b64decode(salt_b64)
    expected = base64.b64decode(hash_b64)
    # recalcular derived key com os mesmos parâmetros
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    # usar compare_digest para mitigar timing attacks
    return secrets.compare_digest(dk, expected)

def load_users() -> Dict[str, Dict[str, Any]]:
    """
    Carrega o ficheiro users.json e retorna um dicionário de usuários.
    Estrutura: { username: {"salt": "...", "hash": "...", "iters": 200000}, ... }
    Se o ficheiro não existir, retorna um dicionário vazio.
    """
    path = get_user_store_path()
    # se não existir, retorna vazio (primeira execução)
    if not path.exists():
        return {}  # vazio
    try:
        # abrir e ler JSON
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        # em caso de erro (arquivo corrompido, permission), retornar vazio para não quebrar app
        return {}

def save_users(users: Dict[str, Dict[str, Any]]) -> None:
    """
    Persiste o dicionário de usuários (users) no ficheiro users.json.
    Sobrescreve o anterior de forma atômica (melhoria possível: escrever temp + rename).
    """
    path = get_user_store_path()
    # abrir em modo escrita e dump JSON formatado
    with open(path, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# -------------------------
# Classe de autenticação (Kivy Screen)
# -------------------------

class LoginScreen(Screen):
    """
    LoginScreen: tela de login e criação de conta local.

    Principais funcionalidades:
    - fazer_login(username, password): valida localmente usando users.json
    - criar_conta_popup(): popup para criar novo usuário (gera salt+hash e salva)
    - tratamento de teclas Tab/Enter para melhorar UX

    Observação de segurança:
    - As senhas não são armazenadas em texto claro; utiliza PBKDF2-HMAC-SHA256 com salt.
    - Ainda assim, armazenamento local em arquivo pode ser extraído por usuários com acesso ao sistema.
    - Para produção/escala, use backend centralizado e autenticação segura.
    """

    def fazer_login(self, username: str, password: str) -> None:
        """
        Tenta autenticar o usuário localmente:
        - limpa espaços
        - carrega users.json
        - se usuário não existir -> mensagem
        - senão, verifica senha via verify_password
        - em caso de sucesso, define app.user_id e troca para a tela 'main'
        """
        # normalizar inputs (evita None)
        username = (username or "").strip()
        password = (password or "").strip()

         # validar preenchimento
        if not username or not password:
            self.show_error("Por favor, preencha todos os campos.")
            return
        
        # carregar dicionário de usuários
        users: Dict[str, Dict[str, Any]] = load_users()
        record: Optional[Dict[str, Any]] = users.get(username)

        # se usuário não encontrado -> instruir a criar conta
        if not record:
            self.show_error("Usuário não encontrado. Cadastre-se primeiro.")
            return
        
        # verificar senha com tratamento de exceção
        try:
            ok: bool= verify_password(
                password, 
                record["salt"], 
                record["hash"], 
                int(record.get("iters", 200000))
                )
        
        except Exception:
            # em caso de qualquer erro (dados corrompidos) considerar inválido
            ok = False

        if ok:
            # login bem sucedido: pegar instância do app e navegar para main
            app = App.get_running_app()
            app.user_id = username           # armazenar user_id na App
            app.sm.current = 'main'          # trocar para a tela principal
            try:
                # tentar disparar carregamento das atividades na main screen (se existir)
                main_screen = app.sm.get_screen('main')
                main_screen.carregar_atividades()
            except Exception:
                # falha em notificar main screen é não-fatal aqui
                pass
        else:
            # senha incorreta: informar usuário e limpar campo senha (se existir)
            self.show_error("Usuário ou senha incorretos.")
            try:
                self.ids.password.text = ""
            except Exception:
                pass

    def criar_conta_popup(self) -> None:
        """
        Abre um Popup simples para criar nova conta local.
        O popup contém campos: username, password, confirm_password.
        - valida preenchimento, igualdade de senhas e unicidade de usuário.
        - gera hash+salt via hash_password e salva em users.json
        """
        # imports locais para widget creation (evita import no topo se não usado)
        from kivy.uix.boxlayout import BoxLayout
        from kivy.uix.textinput import TextInput
        from kivy.uix.button import Button
        from kivy.uix.label import Label

        # construir layout vertical do popup
        layout = BoxLayout(orientation='vertical', padding=8, spacing=8)

        # etiqueta e campo de usuário
        layout.add_widget(Label(text="Novo usuário:"))
        username_input = TextInput(multiline=False)
        layout.add_widget(username_input)

        # etiqueta e campo de senha
        layout.add_widget(Label(text="Senha:"))
        password_input = TextInput(password=True, multiline=False)
        layout.add_widget(password_input)

        # etiqueta e campo de confirmação de senha
        layout.add_widget(Label(text="Confirmar senha:"))
        confirm_input = TextInput(password=True, multiline=False)
        layout.add_widget(confirm_input)

        # botões OK / Cancel em linha
        buttons = BoxLayout(size_hint_y=None, height=40, spacing=8)
        ok_btn = Button(text="Criar")
        cancel_btn = Button(text="Cancelar")
        buttons.add_widget(ok_btn)
        buttons.add_widget(cancel_btn)
        layout.add_widget(buttons)

        # criar popup com layout
        popup = Popup(title="Criar Conta", content=layout, size_hint=(0.9, 0.6))

        # callback para cancelar -> fechar popup
        def on_cancel(inst: Any) -> None:
            popup.dismiss()


        def on_create(inst: Any) -> None:
            # ler campos (normalizar)
            user: str = (username_input.text or "").strip()
            pwd: str = (password_input.text or "").strip()
            conf: str = (confirm_input.text or "").strip()

             # validações básicas
            if not user or not pwd:
                self.show_error("Preencha usuário e senha.")
                return
            if pwd != conf:
                self.show_error("Senha e confirmação não coincidem.")
                return
            
            # carregar usuários existentes
            users: Dict[str, Dict[str, Any]] = load_users()
            if user in users:
                self.show_error("Usuário já existe. Escolha outro nome.")
                return
            
            # gerar hash + salt e salvar no dicionário
            rec: Dict[str, Any] = hash_password(pwd)
            users[user] = rec
            try:
                # salvar persistente
                save_users(users)
            except Exception as e:
                # caso falhe ao salvar (permissão/disco), informar usuário
                self.show_error(f"Falha ao salvar usuário: {e}")
                return
            
            # tudo OK -> fechar popup e informar usuário
            popup.dismiss()
            self._show_info("Conta criada com sucesso. Faça login.")

        # ligar callbacks aos botões
        ok_btn.bind(on_release=on_create)
        cancel_btn.bind(on_release=on_cancel)

         # abrir popup
        popup.open()

    def _show_info(self, message: str) -> None:
        """
        Mostra um popup informativo (não-erro).
        """
        popup = Popup(title='Info', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    def show_error(self, message: str) -> None:
        """
        Mostra um popup de erro com a mensagem fornecida.
        """
        popup = Popup(title='Erro', content=Label(text=message), size_hint=(0.8, 0.4))
        popup.open()

    # -------------------------
    # Handlers de teclado (Tab/Enter)
    # -------------------------
    
    def on_pre_enter(self, *args: Any) -> None:
        """
        Vincula o handler de teclado quando a tela vai aparecer.
        Isso permite capturar Tab/Enter e melhorar a navegação do usuário.
        """
        Window.bind(on_key_down=self._on_key_down)

    def on_leave(self, *args: Any) -> None:
        """
        Desvincula o handler quando a tela deixa de estar ativa,
        evitando múltiplas ligações e efeitos colaterais.
        """
        try:
            Window.unbind(on_key_down=self._on_key_down)
        except Exception:
            # se já foi desvinculado, ignora
            pass

    def _on_key_down(self, window: Any, key: int, scancode: int, codepoint: Optional[str], modifiers: Any) -> bool:
        """
        Handler global de key_down:
        - Tab (key == 9 ou codepoint == '\\t'): troca foco entre username e password
        - Enter/Return (key == 13 ou codepoint em '\\r'|'\\n'): submete o formulário se ambos preenchidos
        Retorna True se tratou a tecla, False caso contrário.
        """
        # proteção geral para evitar que exceções atrapalhem o loop de eventos
        try:
            # Tab: alterna foco entre os campos
            if key == 9 or codepoint == '\t':
                try:
                    if self.ids.username.focus:
                        # mover foco do username para password
                        self.ids.username.focus = False
                        self.ids.password.focus = True
                    elif self.ids.password.focus:
                        # mover foco de password para username
                        self.ids.password.focus = False
                        self.ids.username.focus = True
                    else:
                        # nenhum tinha foco: setar no username
                        self.ids.username.focus = True
                except Exception:
                    # se ids não existirem, ignora
                    pass
                return True

            # Enter/Return: tenta submeter se ambos campos preenchidos
            if key == 13 or (codepoint in ('\r', '\n') if codepoint is not None else False):
                try:
                    u: str = self.ids.username.text.strip()
                    p: str = self.ids.password.text.strip()
                    if u and p:
                        # submeter login
                        self.fazer_login(u, p)
                except Exception:
                    pass
                return True

        except Exception:
            # evitar que exceções não tratadas quebrem o event loop
            pass

        # não tratado: retornar False para permitir comportamento padrão
        return False
