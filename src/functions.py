# functions.py
import sys
import os
from kivy.resources import resource_add_path
from dotenv import load_dotenv

def adicionar_caminhos_kv() -> None:

    '''Essa função verifica se o programa está rodando nesse modo onefile (ou seja, se sys._MEIPASS existe). 
    Caso esteja, ela chama resource_add_path(sys._MEIPASS), que diz ao Kivy para 
    procurar arquivos de recursos (como .kv e imagens) dentro dessa pasta temporária. 
    Assim, mesmo empacotado em um único executável, o app ainda consegue encontrar e carregar corretamente seus layouts e imagens.'''

    # Se executável onefile extrair arquivos, adiciona o caminho de recursos para Kivy
    if getattr(sys, '_MEIPASS', None):
        resource_add_path(os.path.join(sys._MEIPASS))

def carregar_env() -> None:

    '''Essa função carrega os arquivos .kv que definem a interface gráfica da aplicação (login.kv e main.kv).
     No Kivy, esses arquivos descrevem os layouts e estilos da tela. 
     Essa função garante que eles sejam lidos e aplicados antes que as telas sejam criadas, 
     permitindo que os widgets e telas apareçam como esperado.
     Prioridade:
      1) .env externo (arquivo ao lado do exe)
      2) .env embutido extraído em sys._MEIPASS (quando onefile)
      3) variáveis do sistema (os.environ)'''
    
    # 1) pasta do executável (quando empacotado) ou cwd em dev
    if getattr(sys, "frozen", False):
        exe_dir = os.path.dirname(sys.executable)
    else:
        exe_dir = os.path.abspath(os.getcwd())

    external_env = os.path.join(exe_dir, ".env")
    if os.path.exists(external_env):
        load_dotenv(external_env)
        return

    # 2) .env embutido extraído em _MEIPASS (onefile)
    base = getattr(sys, "_MEIPASS", None)
    if base:
        bundled_env = os.path.join(base, ".env")
        if os.path.exists(bundled_env):
            load_dotenv(bundled_env)
            return

    # 3) se nada encontrado, não faz nada (usa variáveis do sistema, se existirem)
    return

# Agora importa o Kivy / telas
from kivy.lang import Builder
from kivymd.app import MDApp
from kivy.core.text import LabelBase
from kivy.uix.screenmanager import ScreenManager
from kivy.properties import StringProperty

# Importar telas só após carregar env
from src.GUI_login import LoginScreen
from src.GUI_principal import MainScreen


def carregar_arquivos_kv() -> None: 

    '''Essa função carrega os arquivos .kv que definem a interface gráfica da aplicação (login.kv e main.kv).
     No Kivy, esses arquivos descrevem os layouts e estilos da tela. 
     Essa função garante que eles sejam lidos e aplicados antes que as telas sejam criadas, 
     permitindo que os widgets e telas apareçam como esperado.'''
     
    # Carregar os arquivos KV (devem estar na mesma pasta do exe / ou embutidos)
    Builder.load_file('kv/login.kv')
    Builder.load_file('kv/main.kv')

class ActivityTrackerApp(MDApp):

    '''Essa é a classe principal do aplicativo, que herda de MDApp (a versão do KivyMD para aplicativos com Material Design).

    1) Define uma propriedade user_id que pode ser usada em várias partes do app para identificar o usuário logado.
    2) Configura o tema (cores, estilo claro/escuro).
    3) Cria um ScreenManager, que permite alternar entre diferentes telas.
    4) Adiciona duas telas principais: a de login (LoginScreen) e a de atividades (MainScreen).

    Quando chamamos .run(), essa classe inicializa o aplicativo, carrega o layout e mantém a interface funcionando até o usuário fechar.'''

    user_id: StringProperty = StringProperty("")
    sm: ScreenManager  # Type annotation para o screen manager

    def build(self) -> ScreenManager:

        # Tema do APP:
        self.theme_cls.primary_palette = "Teal" # Muda a paleta de cores
        self.theme_cls.theme_style = "Light" # Alterna entre tema claro e escuro
        self.theme_cls.material_style = "M3"  # Material Design 3 (mais moderno)

        # Gerenciador de Telas: 
        self.sm = ScreenManager()
        self.sm.add_widget(LoginScreen(name='login'))
        self.sm.add_widget(MainScreen(name='main'))
        return self.sm