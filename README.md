registro_atividades/
├── src/
│   ├── __init__.py       
│   ├── main.py
│   ├── login.py
│   ├── gui.py            
│   └── handle_db.py      
├── kv/
│   ├── login.kv
│   └── main.kv
├── assets/
│   └── logo.png          
├── .env
├── requirements.txt
├── README.md
├── .gitignore            # Ignore: venv/, __pycache__/, *.pyc, dist/, build/
└── setup.py              # Opcional para pip install -e .

I. Como executar: 

git clone https://github.com/seuusuario/registro_atividades.git
cd registro_atividades
Criar ambiente virtual:  python -m venv venv
Ativar ambiente virtual: venv/Scripts/activate
Instale as dependências: pip install -r requirements.txt
Execute: python -m src.main

II. Criação de Executável: 

# limpar builds antigos (opcional, recomendado)
Remove-Item -Recurse -Force .\build  -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .\dist   -ErrorAction SilentlyContinue
Remove-Item -Force .\RegistroAtividades.spec -ErrorAction SilentlyContinue

# comando final ONEFILE sem console (sem assets)
pyinstaller --noconfirm --clean --onefile --noconsole --name Registro_Atividades2.0 `
--add-data "kv/login.kv;kv" `
--add-data "kv/main.kv;kv" `
--add-data ".env;." `
--add-data "assets;assets" `
src/main.py


