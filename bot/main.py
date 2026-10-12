import asyncio
import html
import logging
import re
from datetime import date, datetime

from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message

import log  # noqa: F401  (configura o logging)
from .config import ADMINS, CODE_RE, BOT_TOKEN
from .api import Api

from .helpers import kb, chunks, MENU

logger = logging.getLogger(__name__)

class Cadastro(StatesGroup):
    tipo = State()
    campo = State()
    revisar = State()


PASSOS = {
    "adulto": ["nome", "genero", "localizacao", "data_nascimento", "telefone", "instagram", "email"],
    "crianca": ["nome", "genero", "localizacao", "data_nascimento",
                "nome_resp", "telefone_resp", "instagram_resp", "email_resp"],
}
OPCIONAIS = {"instagram_resp", "email_resp"}

PERGUNTAS = {
    "adulto": {
        "nome": "¿Cuál es tu <b>nombre completo</b>? (ej: Rudson Reis)",
        "genero": "Género:",
        "localizacao": "¿Vives en <b>Lleida</b>?",
        "data_nascimento": "¿Fecha de nacimiento? (DD/MM/AAAA)",
        "telefone": "Tu <b>teléfono</b>:",
        "instagram": "Tu <b>Instagram</b> (ej: @tu.perfil):",
        "email": "Tu <b>email</b>:",
    },
    "crianca": {
        "nome": "¿Cuál es el <b>nombre completo del niño/a</b>?",
        "genero": "Género del niño/a:",
        "localizacao": "¿El niño/a vive en <b>Lleida</b>?",
        "data_nascimento": "¿Fecha de nacimiento del niño/a? (DD/MM/AAAA)",
        "nome_resp": "<b>Nombre del responsable</b>:",
        "telefone_resp": "<b>Teléfono del responsable</b>:",
        "instagram_resp": "<b>Instagram del responsable</b> (opcional):",
        "email_resp": "<b>Email del responsable</b> (opcional):",
    },
}

ROTULOS = {
    "nome": "Nombre", "genero": "Género", "localizacao": "Vive en Lleida",
    "data_nascimento": "Nacimiento", "telefone": "Teléfono", "instagram": "Instagram",
    "email": "Email", "nome_resp": "Responsable", "telefone_resp": "Tel. responsable",
    "instagram_resp": "Insta responsable", "email_resp": "Email responsable",
}

TIPOS = {"adulto": "adulto", "crianca": "niño/a"}
GENERO_TXT = {"masculino": "Masculino", "feminino": "Femenino", "outros": "Otro"}

# só interessa saber se é de Lleida; o resto vai como "Otra" (coluna é NOT NULL)
LLEIDA, OUTRA = "Lleida", "Otra"

GENEROS = kb([(t, f"gen:{v}") for v, t in GENERO_TXT.items()])
LOCAL = kb([("✅ Sí", f"loc:{LLEIDA}"), ("❌ No", f"loc:{OUTRA}")])

# campos respondidos com botão: campo -> (prefixo do callback, teclado)
ESCOLHAS = {"genero": ("gen", GENEROS), "localizacao": ("loc", LOCAL)}


def v_data(t: str) -> str:
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"):
        try:
            d = datetime.strptime(t, fmt).date()
            break
        except ValueError:
            continue
    else:
        raise ValueError("Fecha no válida. Usa DD/MM/AAAA, ej: 15/05/2002.")
    if not (1900 < d.year and d <= date.today()):
        raise ValueError("Esa fecha no parece correcta, revísala.")
    return d.isoformat()


def v_telefone(t: str) -> str:
    if len(re.sub(r"\D", "", t)) < 9:
        raise ValueError("Teléfono no válido. Envíalo con prefijo, solo números.")
    return t


def v_email(t: str) -> str:
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", t):
        raise ValueError("Email no válido.")
    return t.lower()


def v_instagram(t: str) -> str:
    t = t.strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", t):
        raise ValueError("Instagram no válido. Envía solo el @, ej: @tu.perfil")
    return "@" + t


def v_texto(t: str) -> str:
    if len(t) < 2:
        raise ValueError("Demasiado corto, inténtalo de nuevo.")
    return t


VALIDADORES = {
    "data_nascimento": v_data, "telefone": v_telefone, "telefone_resp": v_telefone,
    "email": v_email, "email_resp": v_email,
    "instagram": v_instagram, "instagram_resp": v_instagram,
}

public = Router()


async def perguntar(msg: Message, state: FSMContext):
    d = await state.get_data()
    passos = PASSOS[d["tipo"]]
    if d["i"] >= len(passos):
        return await revisar(msg, state)

    campo = passos[d["i"]]
    teclado = None
    if campo in ESCOLHAS:
        teclado = ESCOLHAS[campo][1]
    elif campo in OPCIONAIS:
        teclado = kb([("Saltar ⏭", "pular")])
    await state.set_state(Cadastro.campo)
    await msg.answer(PERGUNTAS[d["tipo"]][campo], reply_markup=teclado)


async def avancar(msg: Message, state: FSMContext, valor):
    d = await state.get_data()
    campo = PASSOS[d["tipo"]][d["i"]]
    await state.update_data({campo: valor, "i": d["i"] + 1})
    await perguntar(msg, state)


async def revisar(msg: Message, state: FSMContext):
    d = await state.get_data()
    linhas = [f"<b>Revisa tus datos</b> ({TIPOS[d['tipo']]}):\n"]
    for campo in PASSOS[d["tipo"]]:
        valor = d.get(campo)
        if campo == "data_nascimento":
            valor = date.fromisoformat(valor).strftime("%d/%m/%Y")
        elif campo == "genero":
            valor = GENERO_TXT[valor]
        elif campo == "localizacao":
            valor = "Sí" if valor == LLEIDA else "No"
        linhas.append(f"{ROTULOS[campo]}: {html.escape(valor or '—')}")
    await state.set_state(Cadastro.revisar)
    await msg.answer("\n".join(linhas),
                     reply_markup=kb([("✅ Confirmar", "confirmar")], [("🔄 Empezar de nuevo", "novo")]))


@public.message(CommandStart())
async def start(msg: Message, state: FSMContext):
    await state.clear()
    texto = ("¡Hola! 👋 Aquí puedes hacer la <b>inscripción para el evento</b>.\n"
             "Al final recibirás un <b>código</b> para mostrar en la entrada.")
    if msg.from_user.id in ADMINS:
        texto += "\n\n🔧 Eres admin: /admin"
    await msg.answer(texto, reply_markup=MENU)


@public.message(Command("cancelar"))
async def cancelar(msg: Message, state: FSMContext):
    await state.clear()
    await msg.answer("Inscripción cancelada.", reply_markup=MENU)


@public.callback_query(F.data == "novo")
async def novo(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Cadastro.tipo)
    await cb.message.answer("La inscripción es para:",
                            reply_markup=kb([("🧑 Adulto (yo mismo/a)", "tipo:adulto")],
                                            [("🧒 Niño/a (soy el responsable)", "tipo:crianca")]))
    await cb.answer()


@public.callback_query(Cadastro.tipo, F.data.startswith("tipo:"))
async def escolher_tipo(cb: CallbackQuery, state: FSMContext):
    await state.update_data(tipo=cb.data.split(":", 1)[1], i=0)
    await cb.message.edit_reply_markup(reply_markup=None)
    await perguntar(cb.message, state)
    await cb.answer()


async def campo_atual(state: FSMContext) -> str:
    d = await state.get_data()
    return PASSOS[d["tipo"]][d["i"]]


@public.callback_query(Cadastro.campo, F.data.regexp(r"^(gen|loc):"))
async def escolher_opcao(cb: CallbackQuery, state: FSMContext):
    prefixo, valor = cb.data.split(":", 1)
    campo = await campo_atual(state)
    if campo not in ESCOLHAS or ESCOLHAS[campo][0] != prefixo:
        return await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await avancar(cb.message, state, valor)
    await cb.answer()


@public.callback_query(Cadastro.campo, F.data == "pular")
async def pular(cb: CallbackQuery, state: FSMContext):
    if await campo_atual(state) not in OPCIONAIS:
        return await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await avancar(cb.message, state, None)
    await cb.answer()


@public.message(Cadastro.campo, F.text)
async def receber_campo(msg: Message, state: FSMContext):
    campo = await campo_atual(state)
    if campo in ESCOLHAS:
        return await msg.answer("Elige una opción:", reply_markup=ESCOLHAS[campo][1])

    try:
        valor = VALIDADORES.get(campo, v_texto)(msg.text.strip())
    except ValueError as e:
        return await msg.answer(f"⚠️ {e}")
    await avancar(msg, state, valor)


@public.callback_query(Cadastro.revisar, F.data == "confirmar")
async def confirmar_cadastro(cb: CallbackQuery, state: FSMContext, api: Api):
    d = await state.get_data()
    dados = {k: d.get(k) for k in PASSOS[d["tipo"]]}
    dados["tipo"] = d["tipo"]

    await state.clear()  # antes da API: evita cadastro duplicado com clique duplo
    await cb.message.edit_reply_markup(reply_markup=None)
    try:
        r = await api.criar(dados)
    except Exception:
        await state.set_data(d)
        await state.set_state(Cadastro.revisar)
        await cb.message.edit_reply_markup(
            reply_markup=kb([("✅ Confirmar", "confirmar")], [("🔄 Empezar de nuevo", "novo")]))
        raise
    await cb.message.answer(
        f"🎉 ¡Inscripción completada!\n\nTu código:\n\n<b><code>{r['codigo']}</code></b>\n\n"
        "Muestra este código en la entrada del evento. ¡Guarda este mensaje!",
        reply_markup=kb([("➕ Inscribir a otra persona", "novo")]),
    )
    await cb.answer()


@public.message(StateFilter(None))
async def fora_do_fluxo(msg: Message):
    await msg.answer("Pulsa el botón para empezar la inscripción:", reply_markup=MENU)


@public.message(Cadastro.tipo)
@public.message(Cadastro.revisar)
async def use_botoes(msg: Message):
    await msg.answer("Usa los botones de arriba 👆 (o /cancelar)")


# ---------------------------------------------------------------- admin

admin = Router()
admin.message.filter(F.from_user.id.in_(ADMINS))
admin.callback_query.filter(F.from_user.id.in_(ADMINS))


def ficha(p: dict) -> str:
    e = html.escape
    linhas = [f"<b>{e(p['nome'])}</b> ({TIPOS.get(p['tipo'], e(p['tipo']))})",
              f"Código: <code>{e(p['codigo'])}</code>"]
    if p.get("nome_resp"):
        linhas.append(f"Responsable: {e(p['nome_resp'])}")
    linhas.append(f"Instagram: {e(p['instagram'] or '—')}")
    return "\n".join(linhas)


@admin.message(Command("admin"))
async def admin_ajuda(msg: Message):
    await msg.answer(
        "🔧 <b>Admin</b>\n\n"
        "Envía el <b>código</b> (ej: <code>H567</code>) para hacer el check-in.\n"
        "/mencoes — @ de todos los presentes, listo para pegar\n"
        "/presentes — lista de quién ya ha llegado\n"
        "/inscritos — todos los inscritos (✅ = ya ha llegado)"
    )


@admin.message(Command("mencoes"))
async def mencoes(msg: Message, api: Api):
    data = await api.instagrams()
    if not data["total"]:
        return await msg.answer("Todavía no hay nadie presente con Instagram.")
    await msg.answer(f"<b>{data['total']}</b> perfiles (toca el texto para copiar):")
    for parte in chunks(data["instagrams"], " "):
        await msg.answer(f"<code>{html.escape(parte)}</code>")


@admin.message(Command("presentes"))
async def presentes(msg: Message, api: Api):
    pessoas = await api.presentes()
    if not pessoas:
        return await msg.answer("Todavía no hay nadie presente.")
    linhas = [f"<b>{len(pessoas)} presentes</b>"] + [
        f"• {html.escape(p['nome'])} <code>{p['codigo']}</code> {html.escape(p['instagram'] or '')}"
        for p in pessoas
    ]
    for parte in chunks(linhas, "\n"):
        await msg.answer(parte)


@admin.message(Command("inscritos"))
async def inscritos(msg: Message, api: Api):
    pessoas = await api.inscritos()
    if not pessoas:
        return await msg.answer("Todavía no hay nadie inscrito.")
    chegaram = sum(p["presenca"] for p in pessoas)
    linhas = [f"<b>{len(pessoas)} inscritos</b> ({chegaram} presentes)"] + [
        f"{'✅' if p['presenca'] else '⬜'} {html.escape(p['nome'])} <code>{p['codigo']}</code> "
        f"{html.escape(p['instagram'] or '')}"
        for p in pessoas
    ]
    for parte in chunks(linhas, "\n"):
        await msg.answer(parte)


@admin.message(StateFilter(None), F.text.regexp(CODE_RE))
async def checkin(msg: Message, api: Api):
    cod = msg.text.strip().upper()
    p = await api.buscar(cod)
    if p is None:
        return await msg.answer(f"Código <code>{cod}</code> no encontrado.")
    if p["presenca"]:
        return await msg.answer(ficha(p) + "\n\n⚠️ <b>Ya estaba presente.</b>")
    await msg.answer(ficha(p), reply_markup=kb([("✅ Confirmar asistencia", f"ok:{cod}"),
                                                ("❌ Cancelar", "nao")]))


@admin.callback_query(F.data.startswith("ok:"))
async def confirmar_presenca(cb: CallbackQuery, api: Api):
    r = await api.confirmar(cb.data.split(":", 1)[1])
    if r is None:
        return await cb.answer("Código no encontrado", show_alert=True)
    status = "⚠️ Ya estaba presente." if r["ja_estava_presente"] else "✅ ¡Asistencia confirmada!"
    await cb.message.edit_text(f"{cb.message.html_text}\n\n<b>{status}</b>")
    await cb.answer()


@admin.callback_query(F.data == "nao")
async def nao_confirmar(cb: CallbackQuery):
    await cb.message.edit_text(f"{cb.message.html_text}\n\n<i>Cancelado.</i>")
    await cb.answer()


# ---------------------------------------------------------------- main

async def erro(event):
    logger.exception("Erro no bot", exc_info=event.exception)
    upd = event.update
    alvo = upd.message or (upd.callback_query and upd.callback_query.message)
    if alvo:
        await alvo.answer("⚠️ Ha ocurrido un error. Inténtalo de nuevo en unos instantes.")
    return True


async def main():
    if not ADMINS:
        logger.warning("ADMIN_ID não definido: funções de admin desativadas")
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    api = Api()
    dp = Dispatcher(api=api)  # injeta `api` nos handlers
    dp.errors.register(erro)
    dp.include_router(admin)   # antes do público, pra o admin pegar os códigos
    dp.include_router(public)
    try:
        await dp.start_polling(bot)
    finally:
        await api.close()


if __name__ == "__main__":
    asyncio.run(main())
