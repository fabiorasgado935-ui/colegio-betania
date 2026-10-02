import os, sqlite3
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, flash, g, abort)
from werkzeug.security import check_password_hash

app = Flask(__name__)
# Sem SECRET_KEY definida, gera uma chave aleatória (as sessões terminam ao reiniciar o servidor)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24).hex()
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")
DB = os.path.join(os.path.dirname(__file__), "betania.db")

if not os.path.exists(DB):  # primeira execução (também em servidores como o Render)
    import database
    database.main()

# Nomes de tabela vêm SEMPRE desta lista fixa; valores do utilizador vão por "?".
TABELAS = {"aluno": "alunos", "professor": "professores", "admin": "administradores"}


def db():
    if "db" not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def registar(utilizador, acao, estado="Registado"):
    db().execute("INSERT INTO auditoria (utilizador, acao, estado) VALUES (?,?,?)", (utilizador, acao, estado))
    db().commit()


@app.context_processor
def contexto_painel():
    if session.get("role") not in ("admin", "aluno", "professor"):
        return {}
    n = session.get("nome", "").split()
    return {"ano": db().execute("SELECT MAX(ano_lectivo) FROM turmas").fetchone()[0],
            "iniciais": (n[0][0] + n[-1][0]).upper() if n else "?"}


@app.teardown_appcontext
def fechar_db(_):
    conn = g.pop("db", None)
    if conn:
        conn.close()


def requer(role):
    def deco(f):
        @wraps(f)
        def wrapper(*a, **k):
            if session.get("role") != role:
                return redirect(url_for("login", role=role))
            return f(*a, **k)
        return wrapper
    return deco


# ---------- Autenticação ----------
@app.route("/")
def index():
    return redirect(url_for("login", role="aluno"))


@app.route("/login/<role>", methods=["GET", "POST"])
def login(role):
    if role not in TABELAS:
        return redirect(url_for("index"))
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = db().execute(f"SELECT * FROM {TABELAS[role]} WHERE email = ?", (email,)).fetchone()
        if u and check_password_hash(u["senha_hash"], request.form.get("senha", "")):
            session.clear()
            session.update(role=role, uid=u["id"], nome=u["nome"])
            registar(u["nome"], f"Início de sessão ({role})", "Concluído")
            return redirect(url_for(role))
        registar(email or "desconhecido", f"Tentativa de acesso falhada ({role})", "Falhou")
        flash("Email ou senha incorrectos.")
    return render_template("login.html", role=role)


AJUDA = {"recuperar-senha": "Recuperar palavra-passe", "cadastro": "Cadastro",
         "consultar-cadastro": "Consultar cadastro", "suporte": "Suporte"}


@app.route("/ajuda/<slug>")
def ajuda(slug):
    if slug not in AJUDA:
        abort(404)
    return render_template("ajuda.html", titulo=AJUDA[slug])


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


# ---------- Administração ----------
LISTAS = {
    "alunos": ("Alunos", "SELECT a.id, a.nome, a.email, t.nome_turma AS turma "
                         "FROM alunos a LEFT JOIN turmas t ON t.id = a.turma_id ORDER BY a.nome"),
    "professores": ("Professores", "SELECT id, nome, email, disciplina FROM professores ORDER BY nome"),
    "turmas": ("Turmas", "SELECT id, nome_turma, ano_lectivo FROM turmas ORDER BY nome_turma"),
}


@app.route("/admin")
@requer("admin")
def admin():
    cont = lambda t: db().execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]  # t fixo, não vem do utilizador
    stats = {"alunos": cont("alunos"), "professores": cont("professores"), "turmas": cont("turmas"),
             "pendencias": db().execute("SELECT COUNT(*) FROM alunos WHERE turma_id IS NULL").fetchone()[0]}
    registos = db().execute("SELECT * FROM auditoria ORDER BY id DESC LIMIT 6").fetchall()
    return render_template("admin.html", stats=stats, registos=registos)


MODULOS = {"tesouraria": "Tesouraria / Propinas", "matriculas": "Matrícula / Inscrições",
           "certificados": "Emissão de Certificados", "homologar-pauta": "Homologar Pauta",
           "configuracoes": "Configurações", "criar-turma": "Criar Turma",
           "abrir-caderneta": "Abrir Caderneta", "emitir-pauta": "Emitir Pauta", "notificar": "Notificar"}


@app.route("/admin/modulo/<slug>")
@requer("admin")
def admin_modulo(slug):
    if slug not in MODULOS:
        abort(404)
    return render_template("em_breve.html", titulo=MODULOS[slug], base_tpl="admin_base.html", volta="admin")


@app.route("/admin/lista/<tipo>")
@requer("admin")
def admin_lista(tipo):
    if tipo not in LISTAS:
        abort(404)
    titulo, sql = LISTAS[tipo]
    linhas = db().execute(sql).fetchall()
    return render_template("lista.html", titulo=titulo, linhas=linhas)


# ---------- Professor ----------
def dados_professor():
    return db().execute("SELECT * FROM professores WHERE id = ?", (session["uid"],)).fetchone()


@app.route("/professor")
@requer("professor")
def professor():
    prof = dados_professor()
    turmas = db().execute(
        "SELECT t.* FROM turmas t JOIN professor_turmas pt ON pt.turma_id = t.id "
        "WHERE pt.professor_id = ? ORDER BY t.nome_turma", (prof["id"],)).fetchall()
    ids = [t["id"] for t in turmas]
    turma_id = request.args.get("turma", type=int)
    if turma_id not in ids:  # sem turma válida (ou de outro professor): usa a primeira atribuída
        turma_id = ids[0] if ids else None
    tri = request.args.get("trimestre", 1, type=int)
    if tri not in (1, 2, 3):
        tri = 1
    turma_atual = next((t for t in turmas if t["id"] == turma_id), None)
    alunos = []
    if turma_atual:
        alunos = db().execute(
            "SELECT a.id, a.nome, n.mac, n.npp, n.npt FROM alunos a "
            "LEFT JOIN notas n ON n.aluno_id = a.id AND n.disciplina = ? AND n.trimestre = ? "
            "WHERE a.turma_id = ? ORDER BY a.nome", (prof["disciplina"], tri, turma_id)).fetchall()
    return render_template("professor.html", prof=prof, turmas=turmas, turma=turma_atual, tri=tri, alunos=alunos)


MODULOS_PROF = {"perfil": "Perfil", "sumarios-faltas": "Sumários e Faltas", "carga-horaria": "Carga Horária",
                "pautas-finais": "Pautas Finais", "justificativas": "Justificativas", "circulares": "Circulares"}


@app.route("/professor/modulo/<slug>")
@requer("professor")
def professor_modulo(slug):
    if slug not in MODULOS_PROF:
        abort(404)
    return render_template("em_breve.html", titulo=MODULOS_PROF[slug], base_tpl="professor_base.html", volta="professor")


def parse_nota(v):
    try:
        x = float((v or "").replace(",", "."))
    except ValueError:
        return None
    return x if 0 <= x <= 20 else None


@app.route("/professor/notas", methods=["POST"])
@requer("professor")
def salvar_notas():
    prof = dados_professor()
    turma = request.form.get("turma", type=int)
    tri = request.form.get("trimestre", type=int)
    if tri not in (1, 2, 3):
        abort(400)
    if not db().execute("SELECT 1 FROM professor_turmas WHERE professor_id = ? AND turma_id = ?",
                        (prof["id"], turma)).fetchone():
        abort(403)  # professor só lança notas nas suas turmas
    for a in db().execute("SELECT id FROM alunos WHERE turma_id = ?", (turma,)).fetchall():
        v = [parse_nota(request.form.get(f"{k}_{a['id']}")) for k in ("mac", "npp", "npt")]
        if any(x is not None for x in v):
            db().execute(
                "INSERT INTO notas (aluno_id, disciplina, mac, npp, npt, trimestre) VALUES (?,?,?,?,?,?) "
                "ON CONFLICT(aluno_id, disciplina, trimestre) DO UPDATE SET "
                "mac = excluded.mac, npp = excluded.npp, npt = excluded.npt",
                (a["id"], prof["disciplina"], *v, tri))
    db().commit()
    registar(prof["nome"], f"Lançamento de notas – {prof['disciplina']} ({tri}º trimestre)", "Concluído")
    flash("Notas guardadas.")
    return redirect(url_for("professor", turma=turma, trimestre=tri))


# ---------- Aluno ----------
MODULOS_ALUNO = {"perfil": "Perfil", "horario": "Horário", "faltas": "Faltas", "grelha": "Grelha Curricular",
                 "cartao": "Cartão", "justificativas": "Justificativas", "convocatorias": "Convocatórias",
                 "documentos": "Documentos", "folhas-de-prova": "Folhas de prova", "informacoes": "Informações",
                 "exames-especiais": "Exames Especiais", "melhoria-de-notas": "Melhoria de Notas",
                 "configuracoes-perfil": "Configurações do Perfil", "suporte": "Suporte",
                 "registo-actividades": "Registo de Actividades"}
COMPLETA = "mac IS NOT NULL AND npp IS NOT NULL AND npt IS NOT NULL"


@app.route("/aluno")
@requer("aluno")
def aluno():
    d = db()
    eu = d.execute("SELECT a.id, a.nome, a.turma_id, t.nome_turma FROM alunos a "
                   "LEFT JOIN turmas t ON t.id = a.turma_id WHERE a.id = ?", (session["uid"],)).fetchone()
    rank_tri = request.args.get("rank", 0, type=int)
    if rank_tri not in (0, 1, 2, 3):
        rank_tri = 0
    mel_tri = request.args.get("melhores", 0, type=int)
    if mel_tri not in (0, 1, 2, 3):
        mel_tri = 0
    r = d.execute(f"SELECT COALESCE(SUM((mac+npp+npt)/3.0 >= 10),0) AS pos, COALESCE(SUM((mac+npp+npt)/3.0 < 10),0) AS neg "
                  f"FROM notas WHERE aluno_id = ? AND {COMPLETA}", (eu["id"],)).fetchone()
    total = r["pos"] + r["neg"]
    pp = round(r["pos"] * 100 / total) if total else 0
    tot = {"total": total, "pos": r["pos"], "neg": r["neg"], "pp": pp, "pn": 100 - pp if total else 0}
    meus_tri = {x[0] for x in d.execute("SELECT DISTINCT trimestre FROM notas WHERE aluno_id = ?", (eu["id"],))}
    melhores = d.execute(f"SELECT disciplina, ROUND(AVG((mac+npp+npt)/3.0),1) AS m FROM notas "
                         f"WHERE aluno_id = ? AND {COMPLETA} AND (? = 0 OR trimestre = ?) "
                         f"GROUP BY disciplina ORDER BY m DESC LIMIT 3", (eu["id"], mel_tri, mel_tri)).fetchall()
    ranking, liberados = [], set()
    if eu["turma_id"]:
        liberados = {r[0] for r in d.execute(
            "SELECT DISTINCT n.trimestre FROM notas n JOIN alunos a ON a.id = n.aluno_id "
            "WHERE a.turma_id = ?", (eu["turma_id"],))}
        ranking = d.execute(
            "SELECT a.id, a.nome, ROUND(AVG((n.mac+n.npp+n.npt)/3.0),1) AS pont FROM alunos a "
            "JOIN notas n ON n.aluno_id = a.id WHERE a.turma_id = ? AND n.mac IS NOT NULL "
            "AND n.npp IS NOT NULL AND n.npt IS NOT NULL AND (? = 0 OR n.trimestre = ?) "
            "GROUP BY a.id ORDER BY pont DESC", (eu["turma_id"], rank_tri, rank_tri)).fetchall()
    return render_template("aluno.html", eu=eu, tot=tot, melhores=melhores, meus_tri=meus_tri,
                           mel_tri=mel_tri, ranking=ranking, liberados=liberados, rank_tri=rank_tri)


@app.route("/aluno/boletim")
@requer("aluno")
def aluno_boletim():
    tri = request.args.get("trimestre", 1, type=int)
    turma = db().execute("SELECT t.nome_turma FROM alunos a LEFT JOIN turmas t ON t.id = a.turma_id "
                         "WHERE a.id = ?", (session["uid"],)).fetchone()
    notas = db().execute("SELECT disciplina, mac, npp, npt FROM notas "
                         "WHERE aluno_id = ? AND trimestre = ? ORDER BY disciplina",
                         (session["uid"], tri)).fetchall()
    boletim = []
    for n in notas:
        vals = [n["mac"], n["npp"], n["npt"]]
        mt = round(sum(vals) / 3, 1) if None not in vals else None
        boletim.append({**dict(n), "mt": mt})
    return render_template("boletim.html", boletim=boletim, tri=tri, turma=turma["nome_turma"])


@app.route("/aluno/modulo/<slug>")
@requer("aluno")
def aluno_modulo(slug):
    if slug not in MODULOS_ALUNO:
        abort(404)
    return render_template("em_breve.html", titulo=MODULOS_ALUNO[slug], base_tpl="aluno_base.html", volta="aluno")


if __name__ == "__main__":
    if not os.path.exists(DB):
        import database; database.main()
    with sqlite3.connect(DB) as c:  # bases antigas: cria a tabela de auditoria se faltar
        c.execute("CREATE TABLE IF NOT EXISTS auditoria (id INTEGER PRIMARY KEY AUTOINCREMENT, "
                  "data_hora TEXT NOT NULL DEFAULT (datetime('now','localtime')), "
                  "utilizador TEXT NOT NULL, acao TEXT NOT NULL, estado TEXT NOT NULL)")
    # debug só com DEBUG=1 (nunca ligue o debug ao partilhar o link na internet)
    app.run(debug=os.environ.get("DEBUG") == "1")
