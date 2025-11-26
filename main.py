import socket
import tkinter as tk
from tkinter import messagebox
import threading
import random
import asyncio
import websockets
import json
import os

# ---------------------------
# Variables globales
# ---------------------------
USERNAME = f"justinfan{random.randint(10000, 99999)}"
CHANNEL = ""  # sera chargé depuis config.json

CONFIG_FILE = "config.json"

irc_socket = None
thread_twitch = None

messages = []
selected_message = None
clients = set()
central_active = False

# ---------------------------
# Charger / Sauvegarder config
# ---------------------------
def load_config():
    global CHANNEL
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                CHANNEL = data.get("channel", "")
        except:
            CHANNEL = ""

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"channel": CHANNEL}, f)

# ---------------------------
# Interface Tkinter
# ---------------------------
def start_ui():
    window = tk.Tk()
    window.title("Twitch Chat Manager")
    window.geometry("550x520")
    window.configure(bg="#1e1e1e")

    font_title = ("Segoe UI", 12, "bold")
    font_normal = ("Segoe UI", 10)

    # ---------- Zone choix chaîne ----------
    frame_top = tk.Frame(window, bg="#1e1e1e")
    frame_top.pack(pady=10)

    tk.Label(frame_top, text="Nom de la chaîne :", bg="#1e1e1e", fg="white", font=font_normal).grid(row=0, column=0, padx=5)

    entry_channel = tk.Entry(frame_top, width=20, font=font_normal)
    entry_channel.grid(row=0, column=1, padx=5)

    # pré-remplir avec la valeur sauvegardée
    if CHANNEL:
        entry_channel.insert(0, CHANNEL)

    def update_channel():
        global CHANNEL, thread_twitch, irc_socket

        new_channel = entry_channel.get().strip().lower()

        if not new_channel:
            messagebox.showerror("Erreur", "Veuillez entrer une chaîne Twitch.")
            return

        CHANNEL = new_channel
        save_config()   # 🔥 SAUVEGARDE AUTOMATIQUE

        # fermer connexion existante
        if irc_socket:
            try:
                irc_socket.close()
            except:
                pass

        # vider liste
        listbox.delete(0, tk.END)

        # relancer listener
        thread_t = threading.Thread(target=twitch_listener, args=(listbox,), daemon=True)
        thread_t.start()

        messagebox.showinfo("OK", f"Connexion au chat de : {CHANNEL}")

    tk.Button(frame_top, text="Mettre à jour", font=font_normal,
              bg="#3c3c3c", fg="white", relief="flat",
              command=update_channel).grid(row=0, column=2, padx=5)


    # ---------- Liste messages ----------
    tk.Label(window, text="Messages Twitch :", bg="#1e1e1e", fg="white", font=font_title).pack()

    listbox = tk.Listbox(window, width=70, height=20, font=font_normal, bg="#2a2a2a", fg="white",
                         selectbackground="#007acc", selectforeground="white")
    listbox.pack(pady=10)

    selected = {"name": None, "msg": None}

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


    # ---------- Bouton central message ----------
    def toggle_central():
        global central_active
        central_active = not central_active

        print("Central active:", central_active)


        data_to_send = {
            "central": central_active,
            "user": selected_message["user"] if selected_message else "",
            "msg": selected_message["msg"] if selected_message else ""
        }

        threading.Thread(target=lambda: asyncio.run(send_to_clients(json.dumps(data_to_send))), daemon=True).start()

    tk.Button(window, text="Afficher / Masquer Message Central",
              font=font_normal, bg="#007acc", fg="white", relief="flat",
              command=toggle_central).pack(pady=10)

    return window, listbox

# ---------------------------
# Listener Twitch IRC
# ---------------------------
def twitch_listener(listbox):
    global irc_socket, CHANNEL

    if not CHANNEL:
        return

    server = "irc.chat.twitch.tv"
    port = 6667

    sock = socket.socket()
    irc_socket = sock

    try:
        sock.connect((server, port))
        sock.send(f"PASS SCHMOOPIIE\r\n".encode("utf-8"))
        sock.send(f"NICK {USERNAME}\r\n".encode("utf-8"))
        sock.send(f"JOIN #{CHANNEL}\r\n".encode("utf-8"))
    except Exception as e:
        print("Erreur IRC :", e)
        return

    buffer = ""   # 🔥 buffer pour stocker les données partielles

    while True:
        try:
            buffer += sock.recv(2048).decode("utf-8", errors="ignore")
        except:
            break

        # Tant qu'un message complet est disponible
        while "\r\n" in buffer:
            line, buffer = buffer.split("\r\n", 1)

            # Réponse au ping
            if line.startswith("PING"):
                try:
                    sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                except:
                    pass
                continue

            # Traitement d'un PRIVMSG
            if "PRIVMSG" in line:
                try:
                    # Extraire auteur
                    author = line.split("!", 1)[0][1:]

                    # Extraire message
                    message = line.split("PRIVMSG", 1)[1].split(":", 1)[1]

                    data = {"user": author, "msg": message}
                    messages.append(data)

                    listbox.insert(tk.END, f"{author} : {message}")

                except Exception as e:
                    print("Erreur parsing IRC:", e)


# ---------------------------
# WebSocket serveur
# ---------------------------
async def handler(websocket):
    clients.add(websocket)
    try:
        await websocket.send(json.dumps({"central": central_active, "user": "", "msg": ""}))
        while True:
            await websocket.recv()
    except:
        pass
    finally:
        clients.remove(websocket)

async def send_to_clients(data):
    if clients:
        tasks = [asyncio.create_task(client.send(data)) for client in clients]
        print("Envoi de:", data)
        await asyncio.wait(tasks)


def start_websocket_server():
    async def main():
        async with websockets.serve(handler, "0.0.0.0", 6789):
            await asyncio.Future()
    asyncio.run(main())

# ---------------------------
# Lancement
# ---------------------------
load_config()   # 🔥 Charger dernière chaîne

window, listbox = start_ui()

thread_ws = threading.Thread(target=start_websocket_server, daemon=True)
thread_ws.start()

window.mainloop()
