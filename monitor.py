#!/usr/bin/env python3
"""
KYRONEX Monitor — Client tkinter + WebSocket temps réel.
Affiche les conversations en cours sur le serveur KYRONEX.

Lancement : venv/bin/python3 monitor.py
"""

import asyncio
import json
import ssl as _ssl
import threading
import tkinter as tk
from datetime import datetime

# URLs à tenter dans l'ordre (localhost d'abord, puis LAN)
WS_URLS = [
    "wss://127.0.0.1:3000/api/monitor/ws",
    "ws://127.0.0.1:3000/api/monitor/ws",
    "wss://192.168.1.32:3000/api/monitor/ws",
    "ws://192.168.1.32:3000/api/monitor/ws",
]
RECONNECT_DELAY = 5


class MonitorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("KYRONEX — Monitor")
        self.root.configure(bg="#0a0a0a")
        self.root.geometry("700x500")
        self.root.minsize(400, 300)

        # Header
        header = tk.Frame(self.root, bg="#0a0a0a")
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(
            header, text="KYRONEX MONITOR", font=("Courier", 16, "bold"),
            fg="#ff3333", bg="#0a0a0a"
        ).pack(side=tk.LEFT)

        self.status_label = tk.Label(
            header, text="DECONNECTE", font=("Courier", 10),
            fg="#aa0000", bg="#0a0a0a"
        )
        self.status_label.pack(side=tk.RIGHT)

        # Separator
        tk.Frame(self.root, height=1, bg="#333333").pack(fill=tk.X, padx=10)

        # Text area
        text_frame = tk.Frame(self.root, bg="#0a0a0a")
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.text = tk.Text(
            text_frame, bg="#0a0a0a", fg="#888888",
            font=("Courier", 11), wrap=tk.WORD,
            insertbackground="#ff3333", borderwidth=0,
            highlightthickness=0, state=tk.DISABLED,
            padx=8, pady=8
        )
        scrollbar = tk.Scrollbar(text_frame, command=self.text.yview, bg="#1a1a1a", troughcolor="#0a0a0a")
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Tags for colors
        self.text.tag_configure("timestamp", foreground="#555555", font=("Courier", 9))
        self.text.tag_configure("user_name", foreground="#44aa44", font=("Courier", 11, "bold"))
        self.text.tag_configure("user_msg", foreground="#88cc88")
        self.text.tag_configure("kyronex_name", foreground="#cc3333", font=("Courier", 11, "bold"))
        self.text.tag_configure("kyronex_msg", foreground="#ff8888")
        self.text.tag_configure("system", foreground="#666666", font=("Courier", 10, "italic"))
        self.text.tag_configure("error", foreground="#aa4444", font=("Courier", 9))

        # Footer
        footer = tk.Frame(self.root, bg="#0a0a0a")
        footer.pack(fill=tk.X, padx=10, pady=(0, 5))
        tk.Label(
            footer, text="Surveillance locale — conversations en temps reel",
            font=("Courier", 8), fg="#333333", bg="#0a0a0a"
        ).pack()

        self.connected = False

    def append_text(self, timestamp, name_tag, name, msg_tag, message):
        self.text.configure(state=tk.NORMAL)
        if timestamp:
            # Extract HH:MM:SS from ISO timestamp
            try:
                ts = timestamp.split("T")[1][:8]
            except (IndexError, AttributeError):
                ts = datetime.now().strftime("%H:%M:%S")
        else:
            ts = datetime.now().strftime("%H:%M:%S")

        self.text.insert(tk.END, f"[{ts}] ", "timestamp")
        self.text.insert(tk.END, f"{name}: ", name_tag)
        self.text.insert(tk.END, f"{message}\n", msg_tag)
        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)

    def append_system(self, message):
        self.text.configure(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.insert(tk.END, f"[{ts}] {message}\n", "system")
        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)

    def append_error(self, message):
        self.text.configure(state=tk.NORMAL)
        ts = datetime.now().strftime("%H:%M:%S")
        self.text.insert(tk.END, f"[{ts}] ERR: {message}\n", "error")
        self.text.configure(state=tk.DISABLED)
        self.text.see(tk.END)

    def set_status(self, text, color):
        self.status_label.configure(text=text, fg=color)

    def on_message(self, data):
        self.root.after(0, self._process_message, data)

    def _process_message(self, data):
        try:
            event = json.loads(data)
            msg_type = event.get("type", "")
            user = event.get("user", "???")
            message = event.get("message", "")
            timestamp = event.get("timestamp", "")

            if msg_type == "user_msg":
                self.append_text(timestamp, "user_name", user, "user_msg", message)
            elif msg_type == "assistant_msg":
                self.append_text(timestamp, "kyronex_name", "KYRONEX", "kyronex_msg", message)
            else:
                self.append_system(f"Event inconnu: {msg_type}")
        except Exception as e:
            self.append_error(f"Parsing: {e}")

    def on_connected(self, url):
        self.root.after(0, self._on_connected, url)

    def _on_connected(self, url):
        self.connected = True
        self.set_status("CONNECTE", "#44aa44")
        self.append_system(f"Connecte a {url}")

    def on_disconnected(self, reason=""):
        self.root.after(0, self._on_disconnected, reason)

    def _on_disconnected(self, reason):
        if self.connected:
            self.connected = False
            self.set_status("DECONNECTE", "#aa0000")
            msg = "Connexion perdue"
            if reason:
                msg += f" ({reason})"
            self.append_system(msg)

    def on_error(self, url, error):
        self.root.after(0, self._on_error, url, error)

    def _on_error(self, url, error):
        self.append_error(f"{url} — {error}")


async def ws_loop(app):
    """Boucle WebSocket avec reconnexion automatique."""
    import aiohttp

    ssl_ctx = _ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = _ssl.CERT_NONE

    while True:
        for url in WS_URLS:
            try:
                use_ssl = url.startswith("wss")
                connector = aiohttp.TCPConnector(ssl=False if not use_ssl else ssl_ctx)
                async with aiohttp.ClientSession(connector=connector) as session:
                    async with session.ws_connect(
                        url,
                        ssl=ssl_ctx if use_ssl else False,
                        timeout=aiohttp.ClientTimeout(total=10),
                    ) as ws:
                        app.on_connected(url)
                        async for msg in ws:
                            if msg.type == aiohttp.WSMsgType.TEXT:
                                app.on_message(msg.data)
                            elif msg.type == aiohttp.WSMsgType.ERROR:
                                app.on_disconnected(f"WS error: {ws.exception()}")
                                break
                            elif msg.type == aiohttp.WSMsgType.CLOSED:
                                app.on_disconnected("ferme par le serveur")
                                break
                        # If we were connected, don't try other URLs, just reconnect same one
                        app.on_disconnected("deconnecte")
                        break
            except Exception as e:
                app.on_error(url, str(e)[:80])
                continue
        await asyncio.sleep(RECONNECT_DELAY)


def run_async_loop(app):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_loop(app))


def main():
    app = MonitorApp()

    ws_thread = threading.Thread(target=run_async_loop, args=(app,), daemon=True)
    ws_thread.start()

    app.append_system("KYRONEX Monitor demarre")
    app.append_system("Tentative de connexion...")

    app.root.mainloop()


if __name__ == "__main__":
    main()
