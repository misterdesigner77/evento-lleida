import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, model_validator

import log  # noqa: F401  (configura o logging)
import init_db as db
import function as f

API_TOKEN = os.getenv("API_TOKEN")  # se definido, o bot precisa mandar o header X-API-Token


@asynccontextmanager
async def lifespan(_app):
    db.open_db()
    yield


app = FastAPI(title="Evento Lleida", lifespan=lifespan)


def check_token(x_api_token: str | None = Header(default=None)):
    if API_TOKEN and x_api_token != API_TOKEN:
        raise HTTPException(401, "Token inválido")


class PessoaIn(BaseModel):
    nome: str
    genero: Literal["masculino", "feminino", "outros"]
    localizacao: str
    data_nascimento: str  # YYYY-MM-DD
    tipo: Literal["crianca", "adulto"]
    # adulto
    telefone: str | None = None
    instagram: str | None = None
    email: str | None = None
    # crianca
    nome_resp: str | None = None
    telefone_resp: str | None = None
    instagram_resp: str | None = None
    email_resp: str | None = None

    @model_validator(mode="after")
    def campos_do_tipo(self):
        obrigatorios = (
            ["telefone", "instagram", "email"] if self.tipo == "adulto"
            else ["nome_resp", "telefone_resp"]
        )
        faltando = [c for c in obrigatorios if not getattr(self, c)]
        if faltando:
            raise ValueError(f"Campos obrigatórios para {self.tipo}: {', '.join(faltando)}")
        return self


@app.get("/health")
def health():
    """Usado pelo Docker para saber se a API já está de pé."""
    return {"status": "ok"}


@app.post("/pessoas", status_code=201, dependencies=[Depends(check_token)])
def criar_pessoa(pessoa: PessoaIn):
    try:
        pessoa_id, _, codigo = f.create_person(pessoa.model_dump())
    except (sqlite3.IntegrityError, ValueError) as e:
        raise HTTPException(400, str(e))
    return {"pessoa_id": pessoa_id, "codigo": codigo}


@app.get("/codigos/{codigo}", dependencies=[Depends(check_token)])
def buscar(codigo: str):
    pessoa = f.find_person(codigo)
    if pessoa is None:
        raise HTTPException(404, "Código não encontrado")
    return pessoa


@app.post("/codigos/{codigo}/presenca", dependencies=[Depends(check_token)])
def confirmar(codigo: str):
    try:
        marcou_agora = f.confirm_presence(codigo)
    except LookupError:
        raise HTTPException(404, "Código não encontrado")
    return {"codigo": f.normalize_code(codigo), "ja_estava_presente": not marcou_agora}


@app.get("/pessoas", dependencies=[Depends(check_token)])
def inscritos():
    return f.list_people()


@app.get("/presentes", dependencies=[Depends(check_token)])
def presentes():
    return f.list_present()


@app.get("/presentes/instagrams", dependencies=[Depends(check_token)])
def instagrams():
    lista = f.present_instagrams()
    return {"total": len(lista), "instagrams": lista, "texto": " ".join(lista)}
