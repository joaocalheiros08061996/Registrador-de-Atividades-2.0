📌 README.md — Registrador de Atividades 2.0
📘 Sobre o Projeto

Registrador de Atividades 2.0 é um aplicativo desktop desenvolvido em Python + Kivy, integrado ao Supabase para armazenamento seguro dos dados.
O objetivo é registrar início e fim de atividades realizadas em ambiente corporativo, fornecendo controle, histórico e rastreabilidade.

O sistema pode ser executado diretamente via Python ou distribuído como executável .exe, facilitando o uso por pessoas que não precisam ter Python instalado.

🧱 Arquitetura do Projeto
```text
registro_atividades/
├── src/
│   ├── __init__.py            # Inicialização do módulo
│   ├── main.py                # Ponto de entrada da aplicação
│   ├── login.py               # Lógica de autenticação
│   ├── gui.py                 # Controladores de interface (Kivy)
│   └── handle_db.py           # Integração com banco (Supabase)
├── kv/
│   ├── login.kv               # Interface de login
│   └── main.kv                # Interface principal
├── assets/
│   └── logo.png               # Logo do aplicativo
├── .env                       # Configurações sensíveis (chaves Supabase)
├── requirements.txt           # Dependências do projeto
├── README.md                  # Documentação
├── .gitignore                 # Ignora venv/, __pycache__/, build/, dist/ etc.
└── setup.py                   # (Opcional) Instalação via pip -e
```

🚀 Como Executar Localmente
🔽 1. Clonar o repositório
git clone https://github.com/seuusuario/registro_atividades.git
cd registro_atividades

🏗 2. Criar ambiente virtual

Windows:

python -m venv venv
venv\Scripts\activate


Linux/macOS:

python3 -m venv venv
source venv/bin/activate

📦 3. Instalar dependências
pip install -r requirements.txt

🔐 4. Criar arquivo .env

O arquivo .env deve conter suas credenciais do Supabase, por exemplo:

SUPABASE_URL=...
SUPABASE_KEY=...


⚠️ Esse arquivo não deve ser commitado para o GitHub.

▶️ 5. Executar a aplicação
python -m src.main

🖥 Distribuição — Gerar Executável (Windows)

O projeto utiliza PyInstaller para gerar o executável .exe.

1. Limpar builds antigos (opcional, recomendado)
Remove-Item -Recurse -Force .\build  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\dist   -ErrorAction SilentlyContinue
Remove-Item -Force .\RegistroAtividades.spec -ErrorAction SilentlyContinue

2. Gerar executável final (onefile, sem console)
pyinstaller --noconfirm --clean --onefile --noconsole --name Registro_Atividades2.0 `
--add-data "kv/login.kv;kv" `
--add-data "kv/main.kv;kv" `
--add-data ".env;." `
--add-data "assets;assets" `
src/main.py


O executável será criado em:

dist/Registro_Atividades2.0.exe


Você pode distribuir esse .exe para outros usuários.

🧰 Tecnologias Utilizadas

Python 3.10+

Kivy (interface gráfica)

Supabase (banco de dados e autenticação)

PyInstaller (empacotamento em executável)

dotenv (configurações sensíveis)

🧪 Possíveis Evoluções

Tela de relatórios exportável para Excel/CSV

Sistema de permissões por cargos

Dashboard administrativo

Notificações automáticas

Registro offline com sincronização posterior

🤝 Contribuindo

Pull requests são bem-vindos!
Sugestões, melhorias e correções podem ser enviadas pelo GitHub Issues.

📄 Licença

Este projeto pode utilizar a licença da sua preferência
(adicione uma LICENSE caso queira tornar o projeto open source).

Se quiser, posso inserir automaticamente este README.md no seu projeto, formatar um .gitignore ideal para Python/Kivy/PyInstaller ou ajustar o texto para um tom mais corporativo ou mais amigável.
