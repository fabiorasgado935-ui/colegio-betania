"""Cria betania.db com o esquema e dados de teste. Executar: python database.py"""
import os, sqlite3
from werkzeug.security import generate_password_hash as h

DB = os.path.join(os.path.dirname(__file__), "betania.db")

SCHEMA = """
PRAGMA foreign_keys = ON;
DROP TABLE IF EXISTS auditoria;
DROP TABLE IF EXISTS notas;
DROP TABLE IF EXISTS professor_turmas;
DROP TABLE IF EXISTS alunos;
DROP TABLE IF EXISTS professores;
DROP TABLE IF EXISTS administradores;
DROP TABLE IF EXISTS turmas;

CREATE TABLE turmas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome_turma TEXT NOT NULL,
  ano_lectivo TEXT NOT NULL
);
CREATE TABLE alunos (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL,
  turma_id INTEGER REFERENCES turmas(id)
);
CREATE TABLE professores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL,
  disciplina TEXT NOT NULL
);
CREATE TABLE administradores (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  nome TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  senha_hash TEXT NOT NULL
);
-- Atribuição de turmas a professores (necessária para "as suas turmas")
CREATE TABLE professor_turmas (
  professor_id INTEGER NOT NULL REFERENCES professores(id),
  turma_id INTEGER NOT NULL REFERENCES turmas(id),
  PRIMARY KEY (professor_id, turma_id)
);
CREATE TABLE auditoria (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  data_hora TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  utilizador TEXT NOT NULL,
  acao TEXT NOT NULL,
  estado TEXT NOT NULL
);
CREATE TABLE notas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  aluno_id INTEGER NOT NULL REFERENCES alunos(id),
  disciplina TEXT NOT NULL,
  mac REAL CHECK (mac BETWEEN 0 AND 20),
  npp REAL CHECK (npp BETWEEN 0 AND 20),
  npt REAL CHECK (npt BETWEEN 0 AND 20),
  trimestre INTEGER NOT NULL CHECK (trimestre IN (1,2,3)),
  UNIQUE (aluno_id, disciplina, trimestre)
);
"""

def main():
    c = sqlite3.connect(DB)
    c.executescript(SCHEMA)
    c.executemany("INSERT INTO turmas (nome_turma, ano_lectivo) VALUES (?,?)",
                  [("10ª A", "2026/2027"), ("10ª B", "2026/2027"), ("11ª A", "2026/2027")])
    c.execute("INSERT INTO administradores (nome,email,senha_hash) VALUES (?,?,?)",
              ("Direcção Betânia", "admin@betania.ao", h("admin123")))
    c.executemany("INSERT INTO professores (nome,email,senha_hash,disciplina) VALUES (?,?,?,?)", [
        ("Prof. Manuel Santos", "manuel@betania.ao", h("prof123"), "Matemática"),
        ("Profª Ana Pereira", "ana@betania.ao", h("prof123"), "Português")])
    c.executemany("INSERT INTO professor_turmas VALUES (?,?)", [(1,1),(1,2),(2,1),(2,3)])
    c.executemany("INSERT INTO alunos (nome,email,senha_hash,turma_id) VALUES (?,?,?,?)", [
        ("Beatriz Gomes", "beatriz@betania.ao", h("aluno123"), 1),
        ("Carlos Ndala", "carlos@betania.ao", h("aluno123"), 1),
        ("Dalila Fernandes", "dalila@betania.ao", h("aluno123"), 2),
        ("Edson Cativa", "edson@betania.ao", h("aluno123"), 3)])
    c.executemany("INSERT INTO notas (aluno_id,disciplina,mac,npp,npt,trimestre) VALUES (?,?,?,?,?,?)", [
        (1,"Matemática",14,15,13,1), (1,"Português",16,14,15,1),
        (2,"Matemática",10,9,11,1), (2,"Português",6,7,5,1), (3,"Matemática",17,16,18,1)])
    c.executemany("INSERT INTO auditoria (utilizador,acao,estado) VALUES (?,?,?)", [
        ("Secretaria", "Matrícula de aluno – 11ª A", "Registado"),
        ("Prof. Manuel Santos", "Lançamento de notas – Matemática (1º trimestre)", "Concluído"),
        ("Betânia ADM", "Criação de turma 10ª B", "Registado"),
        ("Betânia ADM", "Emissão de pauta – 1º trimestre", "Aprovado")])
    c.commit(); c.close()
    print("Base de dados criada:", DB)

if __name__ == "__main__":
    main()
