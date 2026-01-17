import json
import threading
from pathlib import Path
from tkinter import messagebox
from tkinter import ttk
import tkinter as tk

from PIL import Image, ImageDraw
import pystray


DATA_PATH = Path.home() / ".config" / "ccc_hub" / "models.json"
CLAUDE_SETTINGS_PATH = Path.home() / ".claude" / "settings.json"
DEFAULT_ENV = {
    "CLAUDE_CODE_ENABLE_TELEMETRY": "0",
    "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
    "HTTP_PROXY": "",
    "ANTHROPIC_AUTH_TOKEN": "",
    "ANTHROPIC_BASE_URL": "",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "glm-4.5-air",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "glm-4.7",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "glm-4.7",
}
DEFAULT_MODELS = [
    {
        "name": "Z.AI Claude Proxy",
        "endpoint": "https://api.z.ai/api/anthropic",
        "api_key": "your_zai_api_key",
        **DEFAULT_ENV,
    },
    {
        "name": "Local (Ollama)",
        "endpoint": "http://localhost:11434/v1",
        "api_key": "",
        **{**DEFAULT_ENV, "ANTHROPIC_BASE_URL": "http://localhost:11434/v1"},
    },
]


class ModelManager:
    def __init__(self, path: Path):
        self.path = path
        self.lock = threading.Lock()
        self.models = []
        self.active = None
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            self.models = DEFAULT_MODELS.copy()
            self.active = self.models[0]["name"] if self.models else None
            self._save()
            return
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        self.models = [
            self._normalize_model(m)
            for m in data.get("models", [])
            if isinstance(m, dict) and m.get("name") and m.get("endpoint")
        ]
        if not self.models:
            self.models = DEFAULT_MODELS.copy()
        self.active = data.get("active")
        if self.active and not any(m["name"] == self.active for m in self.models):
            self.active = self.models[0]["name"] if self.models else None
        if self.active is None and self.models:
            self.active = self.models[0]["name"]
        self._save()

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump({"models": self.models, "active": self.active}, f, indent=2)

    def list_models(self):
        with self.lock:
            return list(self.models)

    def add_model(self, model):
        with self.lock:
            model = self._normalize_model(model)
            if any(m["name"] == model["name"] for m in self.models):
                raise ValueError(f"Модель {model['name']} уже существует")
            self.models.append(model)
            if not self.active:
                self.active = model["name"]
            self._save()

    def remove_model(self, name: str):
        with self.lock:
            self.models = [m for m in self.models if m["name"] != name]
            if self.active == name:
                self.active = self.models[0]["name"] if self.models else None
            self._save()

    def set_active(self, name: str):
        with self.lock:
            model = next((m for m in self.models if m["name"] == name), None)
            if not model:
                raise ValueError("Модель не найдена")
            self.active = name
            self._save()
        self._write_claude_settings(model)

    def is_active(self, name: str) -> bool:
        with self.lock:
            return self.active == name

    def update_model(self, old_name: str, new_model: dict):
        with self.lock:
            new_model = self._normalize_model(new_model)
            found = False
            for idx, m in enumerate(self.models):
                if m["name"] == old_name:
                    self.models[idx] = new_model
                    found = True
                    break
            if not found:
                raise ValueError("Модель не найдена")
            # ensure unique names
            if sum(1 for m in self.models if m["name"] == new_model["name"]) > 1:
                raise ValueError(f"Модель {new_model['name']} уже существует")
            if self.active == old_name:
                self.active = new_model["name"]
            self._save()
        self._write_claude_settings(new_model)

    def _normalize_model(self, model: dict) -> dict:
        norm = {**DEFAULT_ENV}
        norm.update(model)
        return norm

    def _write_claude_settings(self, model: dict) -> Path:
        CLAUDE_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if CLAUDE_SETTINGS_PATH.exists():
            try:
                data = json.loads(CLAUDE_SETTINGS_PATH.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        env = data.get("env", {})
        env.update(
            {
                "CLAUDE_CODE_ENABLE_TELEMETRY": model.get("CLAUDE_CODE_ENABLE_TELEMETRY", ""),
                "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": model.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", ""),
                "HTTP_PROXY": model.get("HTTP_PROXY", ""),
                "ANTHROPIC_AUTH_TOKEN": model.get("api_key", ""),
                "ANTHROPIC_BASE_URL": model.get("endpoint", ""),
                "ANTHROPIC_DEFAULT_HAIKU_MODEL": model.get("ANTHROPIC_DEFAULT_HAIKU_MODEL", ""),
                "ANTHROPIC_DEFAULT_SONNET_MODEL": model.get("ANTHROPIC_DEFAULT_SONNET_MODEL", ""),
                "ANTHROPIC_DEFAULT_OPUS_MODEL": model.get("ANTHROPIC_DEFAULT_OPUS_MODEL", ""),
            }
        )
        data["env"] = env
        CLAUDE_SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return CLAUDE_SETTINGS_PATH


class ModelDialog:
    def __init__(self, master: tk.Tk, title: str, initial: dict | None = None):
        self.window = tk.Toplevel(master)
        self.window.title(title)
        self.window.grab_set()
        self.result = None

        frm = ttk.Frame(self.window, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frm, text="Название").grid(row=0, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Endpoint / базовый URL").grid(row=1, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="API ключ").grid(row=2, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="HTTP прокси").grid(row=3, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Телеметрия (0/1)").grid(row=4, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Необязательный трафик (0/1)").grid(row=5, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Модель Haiku").grid(row=6, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Модель Sonnet").grid(row=7, column=0, sticky=tk.W, pady=4, padx=(0, 8))
        ttk.Label(frm, text="Модель Opus").grid(row=8, column=0, sticky=tk.W, pady=4, padx=(0, 8))

        self.name_var = tk.StringVar(value=initial.get("name") if initial else "")
        self.endpoint_var = tk.StringVar(value=initial.get("endpoint") if initial else "")
        self.key_var = tk.StringVar(value=initial.get("api_key") if initial else "")
        self.proxy_var = tk.StringVar(value=initial.get("HTTP_PROXY") if initial else "")
        self.telemetry_var = tk.StringVar(
            value=initial.get("CLAUDE_CODE_ENABLE_TELEMETRY") if initial else DEFAULT_ENV["CLAUDE_CODE_ENABLE_TELEMETRY"]
        )
        self.traffic_var = tk.StringVar(
            value=initial.get("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC")
            if initial
            else DEFAULT_ENV["CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC"]
        )
        self.haiku_var = tk.StringVar(
            value=initial.get("ANTHROPIC_DEFAULT_HAIKU_MODEL") if initial else DEFAULT_ENV["ANTHROPIC_DEFAULT_HAIKU_MODEL"]
        )
        self.sonnet_var = tk.StringVar(
            value=initial.get("ANTHROPIC_DEFAULT_SONNET_MODEL")
            if initial
            else DEFAULT_ENV["ANTHROPIC_DEFAULT_SONNET_MODEL"]
        )
        self.opus_var = tk.StringVar(
            value=initial.get("ANTHROPIC_DEFAULT_OPUS_MODEL") if initial else DEFAULT_ENV["ANTHROPIC_DEFAULT_OPUS_MODEL"]
        )

        ttk.Entry(frm, textvariable=self.name_var, width=38).grid(row=0, column=1, sticky=tk.EW, pady=4)
        endpoint_entry = ttk.Entry(frm, textvariable=self.endpoint_var, width=38)
        endpoint_entry.grid(row=1, column=1, sticky=tk.EW, pady=4)
        key_entry = ttk.Entry(frm, textvariable=self.key_var, width=38, show="*")
        key_entry.grid(row=2, column=1, sticky=tk.EW, pady=4)
        proxy_entry = ttk.Entry(frm, textvariable=self.proxy_var, width=38)
        proxy_entry.grid(row=3, column=1, sticky=tk.EW, pady=4)
        telemetry_entry = ttk.Entry(frm, textvariable=self.telemetry_var, width=38)
        telemetry_entry.grid(row=4, column=1, sticky=tk.EW, pady=4)
        traffic_entry = ttk.Entry(frm, textvariable=self.traffic_var, width=38)
        traffic_entry.grid(row=5, column=1, sticky=tk.EW, pady=4)
        haiku_entry = ttk.Entry(frm, textvariable=self.haiku_var, width=38)
        haiku_entry.grid(row=6, column=1, sticky=tk.EW, pady=4)
        sonnet_entry = ttk.Entry(frm, textvariable=self.sonnet_var, width=38)
        sonnet_entry.grid(row=7, column=1, sticky=tk.EW, pady=4)
        opus_entry = ttk.Entry(frm, textvariable=self.opus_var, width=38)
        opus_entry.grid(row=8, column=1, sticky=tk.EW, pady=4)

        self._entries = [
            self.window.nametowidget(frm.grid_slaves(row=0, column=1)[0]),
            endpoint_entry,
            key_entry,
            proxy_entry,
            telemetry_entry,
            traffic_entry,
            haiku_entry,
            sonnet_entry,
            opus_entry,
        ]
        self._install_shortcuts_and_menu()

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=2, sticky=tk.E, pady=(10, 0))
        ttk.Button(btns, text="Отмена", command=self.window.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Button(btns, text="Сохранить", command=self._on_save).pack(side=tk.RIGHT)

        frm.columnconfigure(1, weight=1)
        self.window.bind("<Return>", lambda _: self._on_save())
        self.window.bind("<Escape>", lambda _: self.window.destroy())

    def _on_save(self):
        name = self.name_var.get().strip()
        endpoint = self.endpoint_var.get().strip()
        api_key = self.key_var.get().strip()
        proxy = self.proxy_var.get().strip()
        telemetry = self.telemetry_var.get().strip()
        traffic = self.traffic_var.get().strip()
        haiku = self.haiku_var.get().strip()
        sonnet = self.sonnet_var.get().strip()
        opus = self.opus_var.get().strip()
        if not name or not endpoint:
            messagebox.showerror("Ошибка", "Название и endpoint обязательны")
            return
        self.result = {
            "name": name,
            "endpoint": endpoint,
            "api_key": api_key,
            "HTTP_PROXY": proxy,
            "CLAUDE_CODE_ENABLE_TELEMETRY": telemetry,
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": traffic,
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": haiku,
            "ANTHROPIC_DEFAULT_SONNET_MODEL": sonnet,
            "ANTHROPIC_DEFAULT_OPUS_MODEL": opus,
        }
        self.window.destroy()

    def _install_shortcuts_and_menu(self):
        self._context_menu = tk.Menu(self.window, tearoff=0)
        self._context_menu.add_command(label="Вырезать", command=self._ctx_cut)
        self._context_menu.add_command(label="Копировать", command=self._ctx_copy)
        self._context_menu.add_command(label="Вставить", command=self._ctx_paste)

        for entry in self._entries:
            # cover right click on Windows/Linux and secondary click on macOS
            entry.bind("<Button-3>", self._show_context_menu, add="+")
            entry.bind("<Button-2>", self._show_context_menu, add="+")
            entry.bind("<ButtonRelease-3>", self._show_context_menu, add="+")
            entry.bind("<ButtonRelease-2>", self._show_context_menu, add="+")
            entry.bind("<Control-Button-1>", self._show_context_menu, add="+")  # macOS ctrl+click fallback

            # force paste to run once, overriding platform defaults that may double-trigger
            for seq in ("<Command-v>", "<Control-v>", "<Command-V>", "<Control-V>"):
                entry.bind(seq, self._on_paste_key)

    def _focused_entry(self):
        w = self.window.focus_get()
        return w if w in self._entries else None

    def _ctx_cut(self):
        if (w := self._focused_entry()):
            w.event_generate("<<Cut>>")

    def _ctx_copy(self):
        if (w := self._focused_entry()):
            w.event_generate("<<Copy>>")

    def _ctx_paste(self):
        if (w := self._focused_entry()):
            w.event_generate("<<Paste>>")

    def _show_context_menu(self, event):
        event.widget.focus_set()
        try:
            self._context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._context_menu.grab_release()
        return "break"

    def _on_paste_key(self, event):
        if event.widget in self._entries:
            event.widget.event_generate("<<Paste>>")
            return "break"  # stop default class binding to avoid double paste
        return None

class App:
    def __init__(self, root: tk.Tk, manager: ModelManager):
        self.root = root
        self.manager = manager
        self.tray_icon = None
        self._setup_ui()
        self._start_tray()

    def _setup_ui(self):
        self.root.title("Переключатель моделей")
        self.root.geometry("560x420")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=4)

        frm = ttk.Frame(self.root, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        header = ttk.Label(frm, text="Модели", font=("SF Pro Display", 12, "bold"))
        header.pack(anchor=tk.W, pady=(0, 6))

        columns = ("active", "name", "endpoint")
        self.tree = ttk.Treeview(frm, columns=columns, show="headings", height=10)
        self.tree.heading("active", text="")
        self.tree.heading("name", text="Модель")
        self.tree.heading("endpoint", text="Endpoint / базовый URL")
        self.tree.column("active", width=40, anchor=tk.CENTER)
        self.tree.column("name", width=150)
        self.tree.column("endpoint", width=320)
        self.tree.pack(fill=tk.BOTH, expand=True)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

        btns = ttk.Frame(frm)
        btns.pack(fill=tk.X, pady=(8, 0))
        ttk.Button(btns, text="Добавить", command=self._on_add_model).pack(side=tk.LEFT)
        ttk.Button(btns, text="Редактировать", command=self._on_edit_model).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns, text="Сделать активной", command=self._on_make_active).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns, text="Удалить", command=self._on_delete).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(btns, text="Экспорт в Claude Code", command=self._export_to_claude).pack(side=tk.RIGHT)

        self._refresh_tree()

    def _open_model_dialog(self, title: str, initial: dict | None = None):
        dialog = ModelDialog(self.root, title=title, initial=initial)
        self.root.wait_window(dialog.window)
        return dialog.result

    def _start_tray(self):
        icon_image = self._generate_icon()
        menu = self._build_menu()
        self.tray_icon = pystray.Icon("model_switcher", icon_image, "Переключатель моделей", menu)
        thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        thread.start()

    def _generate_icon(self):
        size = 64
        image = Image.new("RGBA", (size, size), (30, 30, 36, 255))
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, size - 8, size - 8), fill=(93, 188, 210), outline=(255, 255, 255))
        draw.rectangle((size // 2 - 6, size // 2 - 6, size // 2 + 6, size // 2 + 6), fill=(30, 30, 36))
        return image

    def _build_menu(self):
        items = []
        for model in self.manager.list_models():
            name = model["name"]
            # Create a closure that captures the name
            def make_callback(model_name):
                def callback(icon, item):
                    self._set_active_from_tray(model_name)
                return callback

            def make_checked(model_name):
                def checked_func(item):
                    return self.manager.is_active(model_name)
                return checked_func

            items.append(pystray.MenuItem(
                name,
                make_callback(name),
                checked=make_checked(name)
            ))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem("Открыть окно", lambda _: self._bring_to_front()))
        items.append(pystray.MenuItem("Выйти", lambda _: self._quit_all()))
        return pystray.Menu(*items)

    def _refresh_tray_menu(self):
        if self.tray_icon:
            self.tray_icon.menu = self._build_menu()
            self.tray_icon.update_menu()

    def _export_to_claude(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Экспорт", "Выберите модель")
            return
        values = self.tree.item(selected[0], "values")
        name = values[1] if len(values) > 1 else values[0]
        model = next((m for m in self.manager.list_models() if m["name"] == name), None)
        if not model:
            messagebox.showerror("Экспорт", "Модель не найдена")
            return
        if not model.get("api_key"):
            if not messagebox.askyesno("Нет API ключа", "API ключ пустой. Продолжить экспорт?"):
                return

        try:
            target = self.manager._write_claude_settings(model)
        except Exception as exc:
            messagebox.showerror("Экспорт", f"Не удалось записать настройки: {exc}")
            return
        messagebox.showinfo("Экспорт завершен", f"Настройки записаны в {target}. Перезапусти `claude` чтобы применить.")

    def _set_active_from_tray(self, name: str):
        try:
            self.manager.set_active(name)
            self._refresh_tree()
            self._refresh_tray_menu()
        except ValueError as exc:
            messagebox.showerror("Ошибка", str(exc))

    def _bring_to_front(self):
        self.root.deiconify()
        self.root.lift()
        self.root.attributes('-topmost', True)
        self.root.after_idle(lambda: self.root.attributes('-topmost', False))

    def _on_add_model(self):
        result = self._open_model_dialog("Добавить модель")
        if not result:
            return
        try:
            self.manager.add_model(result)
        except ValueError as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self._refresh_tree()
        self._refresh_tray_menu()

    def _on_edit_model(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор", "Выберите модель")
            return
        values = self.tree.item(selected[0], "values")
        name = values[1] if len(values) > 1 else values[0]
        model = next((m for m in self.manager.list_models() if m["name"] == name), None)
        if not model:
            messagebox.showerror("Ошибка", "Модель не найдена")
            return
        result = self._open_model_dialog("Редактировать модель", initial=model)
        if not result:
            return
        try:
            self.manager.update_model(name, result)
        except ValueError as exc:
            messagebox.showerror("Ошибка", str(exc))
            return
        self._refresh_tree()
        self._refresh_tray_menu()

    def _on_tree_double_click(self, event):
        row_id = self.tree.identify_row(event.y)
        if not row_id:
            return
        self.tree.selection_set(row_id)
        self._on_edit_model()

    def _on_make_active(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор", "Выберите модель")
            return
        values = self.tree.item(selected[0], "values")
        name = values[1] if len(values) > 1 else values[0]
        self.manager.set_active(name)
        self._refresh_tree()
        self._refresh_tray_menu()

    def _on_delete(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Выбор", "Выберите модель")
            return
        values = self.tree.item(selected[0], "values")
        name = values[1] if len(values) > 1 else values[0]
        self.manager.remove_model(name)
        self._refresh_tree()
        self._refresh_tray_menu()

    def _refresh_tree(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for model in self.manager.list_models():
            is_active = "✅" if self.manager.is_active(model["name"]) else ""
            values = (is_active, model["name"], model["endpoint"])
            row = self.tree.insert("", tk.END, values=values)
            if self.manager.is_active(model["name"]):
                self.tree.selection_set(row)

    def _on_close(self):
        self.root.withdraw()

    def _quit_all(self):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.quit()


if __name__ == "__main__":
    manager = ModelManager(DATA_PATH)
    root = tk.Tk()
    app = App(root, manager)
    root.mainloop()
