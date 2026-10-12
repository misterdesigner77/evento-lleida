
CREATE TABLE IF NOT EXISTS pessoa (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    genero TEXT NOT NULL CHECK (genero in ('masculino', 'feminino', 'outros')),
    localizacao TEXT NOT NULL,
    data_nascimento TEXT NOT NULL,
    tipo TEXT NOT NULL CHECK (tipo in ('crianca', 'adulto')),
    ativo INTEGER DEFAULT 1
) STRICT;

CREATE TABLE IF NOT EXISTS crianca (
    pessoa_id INTEGER PRIMARY KEY,
    nome_resp TEXT NOT NULL,
    telefone_resp TEXT NOT NULL,
    instagram_resp TEXT,
    email_resp TEXT,
    FOREIGN KEY (pessoa_id) REFERENCES pessoa(id)
) STRICT ;

CREATE TABLE IF NOT EXISTS adulto (
    pessoa_id INTEGER PRIMARY KEY,
    telefone TEXT NOT NULL,
    instagram TEXT NOT NULL,
    email TEXT NOT NULL,
    FOREIGN KEY (pessoa_id) REFERENCES pessoa(id)
) STRICT ;

CREATE TABLE IF NOT EXISTS codigo (
    pessoa_id INTEGER NOT NULL,
    codigo TEXT NOT NULL UNIQUE,
    presenca INTEGER DEFAULT 0,
    FOREIGN KEY (pessoa_id) REFERENCES pessoa(id)
) STRICT ;
