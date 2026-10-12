import sqlite3
import logging
import secrets
import init_db as db
import config as c

logger = logging.getLogger(__name__)


def create_person(info: dict):
    con = db.db()
    try:
        cursor = con.cursor()
        cursor.execute("""
            INSERT INTO pessoa(nome, genero, localizacao, data_nascimento, tipo)
            VALUES (?, ?, ?, ?, ?);
        """, (info["nome"], info["genero"], info["localizacao"],
              info["data_nascimento"], info["tipo"]))
        
        pessoa_id = cursor.lastrowid

        subtype_id = create_subtype(info, pessoa_id, cursor)
        codigo = save_code(cursor, pessoa_id)

        con.commit()
        logger.info("Pessoa %s criada (%s %s), código %s",
                    pessoa_id, info["tipo"], subtype_id, codigo)
        return pessoa_id, subtype_id, codigo

    except (KeyError, ValueError) as e:
        con.rollback()
        logger.warning("Dados inválidos ao criar pessoa: %s", e)
        raise

    except sqlite3.Error:
        con.rollback()
        logger.exception("Falha ao salvar pessoa no banco")
        raise

    finally:
        con.close()

def create_subtype(info: dict, pessoa_id: int, cursor):
    if info["tipo"] == "crianca":
        cursor.execute("""
            INSERT INTO crianca(pessoa_id, nome_resp, telefone_resp, instagram_resp, email_resp)
            VALUES (?, ?, ?, ?, ?);
        """, (pessoa_id, info["nome_resp"], info["telefone_resp"],
              normalize_instagram(info.get("instagram_resp")), info.get("email_resp")))

    elif info["tipo"] == "adulto":
        cursor.execute("""
            INSERT INTO adulto(pessoa_id, telefone, instagram, email)
            VALUES (?, ?, ?, ?);
        """, (pessoa_id, info["telefone"], normalize_instagram(info["instagram"]), info["email"]))

    else:
        raise ValueError(f"Tipo de pessoa inválido: {info['tipo']!r}")

    return cursor.lastrowid

def generate_code() -> str:
    return "".join(secrets.choice(c.ALFABETO) for _ in range(c.TAMANHO))

def save_code(cursor, pessoa_id: int, tentativas: int = 5) -> str:
    for _ in range(tentativas):
        codigo = generate_code()
        try:
            cursor.execute(
                "INSERT INTO codigo(pessoa_id, codigo) VALUES (?, ?)",
                (pessoa_id, codigo),
            )
            return codigo
        except sqlite3.IntegrityError as e:
            if "UNIQUE" not in str(e):
                raise
            logger.warning("Código repetido gerado, tentando de novo")
    raise RuntimeError("Não foi possível gerar um código único")

def normalize_code(code: str) -> str:
    return code.strip().upper()

def normalize_instagram(insta: str | None) -> str | None:
    if not insta:
        return None
    insta = insta.strip().lstrip("@").strip()
    return f"@{insta}" if insta else None

def find_person(code: str):
    """Busca a pessoa pelo código. Não altera nada no banco."""
    code = normalize_code(code)
    con = db.db()
    try:
        row = con.execute("""
            SELECT p.id, p.nome, p.tipo, c.codigo, c.presenca,
                   COALESCE(a.instagram, cr.instagram_resp) AS instagram,
                   cr.nome_resp
            FROM codigo c
            JOIN pessoa p ON p.id = c.pessoa_id
            LEFT JOIN adulto a ON a.pessoa_id = p.id
            LEFT JOIN crianca cr ON cr.pessoa_id = p.id
            WHERE c.codigo = ? AND p.ativo = 1
        """, (code,)).fetchone()

        if row is None:
            logger.info("Código não encontrado: %s", code)
            return None

        logger.info("Pessoa %s encontrada com o código %s", row["nome"], code)
        return dict(row)

    except sqlite3.Error:
        logger.exception("Falha ao buscar código %s", code)
        raise

    finally:
        con.close()

def confirm_presence(code: str) -> bool:
    """Marca presença. Retorna True se marcou agora, False se já estava presente.
    Levanta LookupError se o código não existir."""
    code = normalize_code(code)
    con = db.db()
    try:
        cursor = con.execute(
            "UPDATE codigo SET presenca = 1 WHERE codigo = ? AND presenca = 0",
            (code,),
        )
        con.commit()

        if cursor.rowcount:
            logger.info("Presença confirmada: %s", code)
            return True

        exists = con.execute(
            "SELECT 1 FROM codigo WHERE codigo = ?", (code,)
        ).fetchone()
        if exists is None:
            raise LookupError(f"Código não encontrado: {code}")

        logger.info("Código %s já estava com presença confirmada", code)
        return False

    except sqlite3.Error:
        con.rollback()
        logger.exception("Falha ao confirmar presença de %s", code)
        raise

    finally:
        con.close()

def list_people(only_present: bool = False):
    """Todos os inscritos ativos; com only_present=True, só quem fez check-in."""
    con = db.db()
    try:
        rows = con.execute(f"""
            SELECT p.nome, p.tipo, c.codigo, c.presenca,
                   COALESCE(a.instagram, cr.instagram_resp) AS instagram
            FROM codigo c
            JOIN pessoa p ON p.id = c.pessoa_id
            LEFT JOIN adulto a ON a.pessoa_id = p.id
            LEFT JOIN crianca cr ON cr.pessoa_id = p.id
            WHERE p.ativo = 1 {"AND c.presenca = 1" if only_present else ""}
            ORDER BY p.nome
        """).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()

def list_present():
    return list_people(only_present=True)

def present_instagrams() -> list[str]:
    """Instagrams únicos (adultos + responsáveis das crianças) de quem está presente."""
    vistos = set()
    result = []
    for pessoa in list_present():
        insta = normalize_instagram(pessoa["instagram"])
        if insta and insta.lower() not in vistos:
            vistos.add(insta.lower())
            result.append(insta)
    return result

def format_mentions(sep: str = " ") -> str:
    """Texto pronto para colar na legenda/story."""
    return sep.join(present_instagrams())


if __name__ == "__main__":
    db.open_db()

    pessoa_id, subtype_id, codigo = create_person({
        "nome": "Marcos Martins",
        "genero": "masculino",
        "localizacao": "Espanha",
        "data_nascimento": "2002-05-15",
        "tipo": "adulto",
        "telefone": "668517505",
        "instagram": "@marcos.sev7n",
        "email": "marquinhos@gmail.com",
    })
    print("Código de check-in:", codigo)