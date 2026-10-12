import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import log  # noqa: F401
import init_db as db
import function as f

COMUNS = [
    ("nome", "Nome"),
    ("localizacao", "Localização"),
    ("data_nascimento", "Nascimento (AAAA-MM-DD)"),
]
ADULTO = [
    ("telefone", "Telefone"),
    ("instagram", "Instagram"),
    ("email", "Email"),
]
CRIANCA = [
    ("nome_resp", "Nome do responsável"),
    ("telefone_resp", "Telefone do responsável"),
    ("instagram_resp", "Instagram do responsável"),
    ("email_resp", "Email do responsável"),
]
OBRIGATORIOS = {
    "adulto": ["nome", "localizacao", "data_nascimento", "telefone", "instagram", "email"],
    "crianca": ["nome", "localizacao", "data_nascimento", "nome_resp", "telefone_resp"],
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Cadastro - Evento Lleida")
        self.resizable(False, False)

        self.tipo = tk.StringVar(value="adulto")
        self.genero = tk.StringVar(value="masculino")
        self.entries: dict[str, ttk.Entry] = {}

        frm = ttk.Frame(self, padding=16)
        frm.grid()

        ttk.Label(frm, text="Tipo").grid(row=0, column=0, sticky="w")
        tipo_box = ttk.Frame(frm)
        tipo_box.grid(row=0, column=1, sticky="w")
        for t in ("adulto", "crianca"):
            ttk.Radiobutton(tipo_box, text=t.capitalize(), value=t,
                            variable=self.tipo, command=self.trocar_tipo).pack(side="left")

        ttk.Label(frm, text="Gênero").grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(frm, textvariable=self.genero, state="readonly", width=28,
                     values=["masculino", "feminino", "outros"]).grid(row=1, column=1, sticky="w")

        row = 2
        for key, label in COMUNS:
            self._campo(frm, row, key, label)
            row += 1

        self.box_adulto = ttk.LabelFrame(frm, text="Adulto", padding=8)
        self.box_crianca = ttk.LabelFrame(frm, text="Responsável", padding=8)
        for i, (key, label) in enumerate(ADULTO):
            self._campo(self.box_adulto, i, key, label)
        for i, (key, label) in enumerate(CRIANCA):
            self._campo(self.box_crianca, i, key, label)
        self.box_row = row

        self.btn = ttk.Button(frm, text="Cadastrar e marcar presença", command=self.salvar)
        self.btn.grid(row=row + 1, column=0, columnspan=2, pady=(12, 4), sticky="ew")

        self.resultado = ttk.Label(frm, text="", font=("TkDefaultFont", 20, "bold"))
        self.resultado.grid(row=row + 2, column=0, columnspan=2)

        self.trocar_tipo()
        self.bind("<Return>", lambda _e: self.salvar())
        self.entries["nome"].focus()

    def _campo(self, parent, row, key, label):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2)
        e = ttk.Entry(parent, width=32)
        e.grid(row=row, column=1, pady=2, padx=(8, 0))
        self.entries[key] = e

    def trocar_tipo(self):
        mostrar, esconder = (
            (self.box_adulto, self.box_crianca) if self.tipo.get() == "adulto"
            else (self.box_crianca, self.box_adulto)
        )
        esconder.grid_remove()
        mostrar.grid(row=self.box_row, column=0, columnspan=2, sticky="ew", pady=(8, 0))

    def dados(self) -> dict:
        tipo = self.tipo.get()
        campos = COMUNS + (ADULTO if tipo == "adulto" else CRIANCA)
        info = {k: (self.entries[k].get().strip() or None) for k, _ in campos}
        info["tipo"] = tipo
        info["genero"] = self.genero.get()
        return info

    def salvar(self):
        info = self.dados()
        faltando = [k for k in OBRIGATORIOS[info["tipo"]] if not info.get(k)]
        if faltando:
            messagebox.showwarning("Faltam campos", "Preencha: " + ", ".join(faltando))
            return

        try:
            _, _, codigo = f.create_person(info)
            f.confirm_presence(codigo)  # cadastrou no evento = está presente
        except (sqlite3.Error, ValueError, KeyError) as e:
            messagebox.showerror("Erro", f"Não foi possível cadastrar:\n{e}")
            return

        self.resultado.config(text=f"Código: {codigo}")
        for e in self.entries.values():
            e.delete(0, tk.END)
        self.entries["nome"].focus()


if __name__ == "__main__":
    db.open_db()
    App().mainloop()
