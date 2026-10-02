# Colégio Betânia – Sistema de Gestão Escolar
Flask + SQLite · tema escuro com laranja/dourado · 3 painéis (Aluno, Professor, Betânia ADM)

## Estrutura
    colegio_betania/
    ├── app.py             rotas, login por perfil, painéis, segurança
    ├── database.py        cria betania.db (esquema + dados de teste)
    ├── requirements.txt
    ├── iniciar.bat        arranque com duplo clique (Windows)
    ├── iniciar.sh         arranque (Mac/Linux)
    ├── static/style.css   estilos dos 3 painéis e do login
    ├── static/logo.jpg    logótipo do colégio (troque aqui, mantendo o nome)
    └── templates/         login, admin, lista, professor, aluno, boletim, *_base, em_breve

## Executar (3 formas)
**A) Windows – mais fácil:** duplo clique em `iniciar.bat`.
**B) Mac/Linux:** `./iniciar.sh`
**C) Manual:**
    python -m venv venv
    venv\Scripts\activate            (Mac/Linux: source venv/bin/activate)
    pip install -r requirements.txt
    python database.py               (cria a base com dados de teste)
    python app.py
Depois abra http://127.0.0.1:5000 (parar: Ctrl + C).

Para repor os dados de teste: apague `betania.db` e execute `python database.py`.

## Executar no VS Code
1. Instale o VS Code (code.visualstudio.com) e a extensão **Python** (da Microsoft).
2. Menu **Ficheiro > Abrir Pasta** e escolha `colegio_betania`.
3. Menu **Terminal > Novo Terminal**.
4. Execute, um de cada vez:
       python -m venv venv
       venv\Scripts\activate            (Mac/Linux: source venv/bin/activate)
       pip install -r requirements.txt
       python database.py
       python app.py
5. Ctrl + clique em http://127.0.0.1:5000 no terminal (ou abra no navegador).
Se o VS Code perguntar pelo interpretador Python, escolha o que está em `venv`.
Se o PowerShell bloquear o `activate`, execute uma vez:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` ou use o terminal "Command Prompt".

## Partilhar com amigos (link temporário)
1. Instale o cloudflared (Windows): `winget install Cloudflare.cloudflared` (feche e abra o terminal depois).
2. Terminal 1, na pasta do projeto: `venv\Scripts\activate` e `python app.py` (sem debug).
3. Terminal 2 (novo): `cloudflared tunnel --url http://localhost:5000`
4. Copie o endereço `https://....trycloudflare.com` que aparece e envie aos amigos.
O link muda de cada vez e só funciona enquanto o PC e os 2 terminais estiverem ligados.
Use só dados de teste: qualquer pessoa com o link pode tentar entrar.

## Publicar no Render (link para todos)
1. Envie os ficheiros do projeto (sem `venv`, sem `betania.db`) para um repositório no GitHub.
2. render.com > New + > Web Service > escolha o repositório.
3. Build Command: `pip install -r requirements.txt`
   Start Command: `gunicorn app:app --workers 1 --bind 0.0.0.0:$PORT`
   Instance Type: Free. Em Environment, crie `SECRET_KEY` com uma frase longa.
4. Create Web Service e espere o deploy. O link é `https://NOME.onrender.com`.
No plano grátis a app adormece após ~15 min sem visitas e os dados voltam ao início ao reiniciar.

## Contas de teste
| Perfil | Email | Senha |
|---|---|---|
| Betânia ADM | admin@betania.ao | admin123 |
| Professor (Matemática, 10ª A e 10ª B) | manuel@betania.ao | prof123 |
| Professora (Português, 10ª A e 11ª A) | ana@betania.ao | prof123 |
| Aluno (10ª A) | beatriz@betania.ao | aluno123 |
| Aluno (10ª A, com notas negativas) | carlos@betania.ao | aluno123 |
| Aluno (11ª A, sem notas) | edson@betania.ao | aluno123 |

## Segurança implementada
Senhas com hash (werkzeug), consultas SQL parametrizadas, rotas protegidas por perfil,
professor só lança notas nas suas turmas, notas validadas (0–20).
Antes de produção: defina `SECRET_KEY`, desligue `debug=True`, use HTTPS.

## Ainda em desenvolvimento (abrem página "em desenvolvimento")
Gestão (criar/editar alunos, professores, turmas), faltas, horários, tesouraria, certificados,
pautas finais, upload de fotografias, protecção CSRF e recuperação de senha.
