from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from . import config as c

def kb(*linhas: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t, callback_data=d) for t, d in linha] for linha in linhas
    ])


def chunks(linhas: list[str], sep: str):
    """Divide em mensagens que cabem no limite do Telegram."""
    atual = ""
    for linha in linhas:
        if atual and len(atual) + len(sep) + len(linha) > c.TG_LIMIT:
            yield atual
            atual = linha
        else:
            atual = f"{atual}{sep}{linha}" if atual else linha
    if atual:
        yield atual


MENU = kb([("📝 Inscribirme", "novo")])

