import aiohttp
from . import config as c

class Api:
    def __init__(self):
        headers = {"X-API-Token": c.API_TOKEN} if c.API_TOKEN else {}
        self.session = aiohttp.ClientSession(
            c.API_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=10)
        )

    async def _req(self, method: str, path: str, **kw):
        async with self.session.request(method, path, **kw) as r:
            if r.status == 404:
                return None
            r.raise_for_status()
            return await r.json()

    async def criar(self, dados: dict):
        return await self._req("POST", "/pessoas", json=dados)

    async def buscar(self, codigo: str):
        return await self._req("GET", f"/codigos/{codigo}")

    async def confirmar(self, codigo: str):
        return await self._req("POST", f"/codigos/{codigo}/presenca")

    async def inscritos(self):
        return await self._req("GET", "/pessoas")

    async def presentes(self):
        return await self._req("GET", "/presentes")

    async def instagrams(self):
        return await self._req("GET", "/presentes/instagrams")

    async def close(self):
        await self.session.close()