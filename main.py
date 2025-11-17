import socket
import tkinter as tk
from tkinter import messagebox
import threading
import random
import asyncio
import websockets
import json

# ---------------------------
# Variables globales
# ---------------------------
USERNAME = f"justinfan{random.randint(10000, 99999)}"
CHANNEL = "gotaga"

messages = []  # liste de tous les messages
selected_message = None  # message sélectionné
clients = set()  # clients WebSocket
central_active = False  # flag message central

# ---------------------------
# Interface Tkinter
# ---------------------------
def start_ui():
    window = tk.Tk()
    window.title("Messages Twitch")
    window.geometry("500x450")

    listbox = tk.Listbox(window, width=60, height=20)
    listbox.pack(pady=10)

    selected = {"name": None, "msg": None}

    # sélection dans la liste
    def on_select(event):
        selection = listbox.curselection()
        if selection:
            line = listbox.get(selection[0])
            parts = line.split(" : ", 1)
            if len(parts) == 2:
                selected["name"], selected["msg"] = parts
                global selected_message
                selected_message = {"user": selected["name"], "msg": selected["msg"]}

    listbox.bind("<<ListboxSelect>>", on_select)


    # bouton toggle message central
    def toggle_central():
        global central_active
        central_active = not central_active
        data_to_send = {
            "central": central_active,
            "user": selected_message["user"] if selected_message else "",
            "msg": selected_message["msg"] if selected_message else ""
        }
        # envoyer dans un thread séparé pour éviter conflits avec Tkinter
        threading.Thread(target=lambda: asyncio.run(send_to_clients(json.dumps(data_to_send))), daemon=True).start()

    tk.Button(window, text="Afficher/Masquer message central", command=toggle_central).pack(pady=5)

    return window, listbox

# ---------------------------
# Listener Twitch IRC
# ---------------------------
def twitch_listener(listbox):
    server = "irc.chat.twitch.tv"
    port = 6667

    sock = socket.socket()
    sock.connect((server, port))
    sock.send(f"PASS SCHMOOPIIE\r\n".encode("utf-8"))
    sock.send(f"NICK {USERNAME}\r\n".encode("utf-8"))
    sock.send(f"JOIN #{CHANNEL}\r\n".encode("utf-8"))

    while True:
        resp = sock.recv(2048).decode("utf-8", errors="ignore")
        if resp.startswith("PING"):
            sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
            continue
        if "PRIVMSG" in resp:
            try:
                author = resp.split("!",1)[0][1:]
                message = resp.split("PRIVMSG",1)[1].split(":",1)[1]
                data = {"user": author, "msg": message}
                messages.append(data)
                listbox.insert(tk.END, f"{author} : {message}")
            except:
                pass

# ---------------------------
# WebSocket serveur
# ---------------------------
async def handler(websocket):
    clients.add(websocket)
    try:
        # envoyer l’état initial
        await websocket.send(json.dumps({"central": central_active, "user": "", "msg": ""}))
        while True:
            await websocket.recv()  # gérer messages du client si nécessaire
    except:
        pass
    finally:
        clients.remove(websocket)

async def send_to_clients(data):
    if clients:
        tasks = [asyncio.create_task(client.send(data)) for client in clients]
        await asyncio.wait(tasks)

def start_websocket_server():
    async def main():
        async with websockets.serve(handler, "0.0.0.0", 6789):
            await asyncio.Future()  # run forever
    asyncio.run(main())

# ---------------------------
# Lancement
# ---------------------------
window, listbox = start_ui()

thread_twitch = threading.Thread(target=twitch_listener, args=(listbox,), daemon=True)
thread_twitch.start()

thread_ws = threading.Thread(target=start_websocket_server, daemon=True)
thread_ws.start()

window.mainloop()
