import asyncio
import websockets

async def listen():
    uri = "ws://localhost:6789"   # 🔥 Ton serveur WebSocket local

    print(f"Connexion à {uri} ...")

    async with websockets.connect(uri) as websocket:
        print("Connecté !")

        while True:
            try:
                msg = await websocket.recv()
                print("📩 Message brut reçu :", msg)
            except websockets.ConnectionClosed:
                print("❌ Connexion fermée.")
                break
            except Exception as e:
                print("⚠️ Erreur :", e)
                break

asyncio.run(listen())
