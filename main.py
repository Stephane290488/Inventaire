import time
import requests
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from flask import Flask
from threading import Thread

# 🔐 Config
TOKEN = "7525702867:AAGyZWPH1cdI8aLXxc8ml_BQDg3nWOA-1As"
URL = f"https://api.telegram.org/bot{TOKEN}"
SHEET_ID = "1IJIaLsvU-O-68wlwqisp5B6NyryvLUUiQ7xasN4Jidk"

# 📋 Feuilles Google Sheets
FEUILLE_INVENTAIRE = "Inventaire actuel"
FEUILLE_REPONSES = "Réponses au formulaire 1"
FEUILLE_SORTIES = "Entrées et Sorties"

# 🧩 Auth Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)

# 🌐 Serveur Flask pour keep-alive Replit
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot Telegram Proxy en ligne."

def keep_alive():
    app.run(host="0.0.0.0", port=8080)

LAST_UPDATE_ID = 0

def send_message(chat_id, text):
    requests.post(f"{URL}/sendMessage", json={"chat_id": chat_id, "text": text})

def handle_command(text, chat_id):
    text = text.strip()

    if text.lower().startswith("/aide"):
        help_msg = """📋 Commandes disponibles :

🔍 /recherche NomDuProduit
📦 /inventaire
🚨 /rupture
🕒 /derniers
📊 /etat
📦 /stock NomProduit
🧹 /viderreponse CONFIRMER
ℹ️ /aide"""
        send_message(chat_id, help_msg)

    elif text.lower().startswith("/inventaire"):
        try:
            send_message(chat_id, "🕓 Veuillez patienter...")
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_INVENTAIRE)
            rows = sheet.get_all_records()
            lignes = [f"{r['Nom']} : {r['Quantité'] if r.get('Quantité') else '0'}" for r in rows]
            send_message(chat_id, "\n".join(lignes))
        except Exception as e:
            send_message(chat_id, f"❌ Erreur inventaire : {e}")

    elif text.lower().startswith("/rupture"):
        try:
            send_message(chat_id, "🕓 Veuillez patienter...")
            seuil = 3
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_INVENTAIRE)
            rows = sheet.get_all_records()
            low = [f"{r['Nom']} : {r['Quantité']}" for r in rows if str(r.get("Quantité", "")).isdigit() and int(r["Quantité"]) <= seuil]
            if low:
                send_message(chat_id, "🚨 Produits sous le seuil :\n" + "\n".join(low))
            else:
                send_message(chat_id, "✅ Aucun produit sous le seuil.")
        except Exception as e:
            send_message(chat_id, f"❌ Erreur rupture : {e}")

    elif text.lower().startswith("/recherche"):
        try:
            terme = text.replace("/recherche", "").strip()
            if not terme or len(terme) < 2:
                send_message(chat_id, "❌ Veuillez entrer un mot-clé d'au moins 2 lettres.")
                return
            send_message(chat_id, "🕓 Veuillez patienter...")
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_INVENTAIRE)
            rows = sheet.get_all_records()
            resultats = [f"{r['Nom']} : {r['Quantité']}" for r in rows if terme.lower() in r['Nom'].lower()]
            if resultats:
                send_message(chat_id, "🔍 Résultats :\n" + "\n".join(resultats))
            else:
                send_message(chat_id, "❌ Aucun produit trouvé.")
        except Exception as e:
            send_message(chat_id, f"❌ Erreur recherche : {e}")

    elif text.lower().startswith("/derniers"):
        try:
            send_message(chat_id, "🕓 Veuillez patienter...")
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_SORTIES)
            rows = sheet.get_all_values()
            last = rows[-5:]
            lignes = []
            for row in last:
                propre = [cell if cell != "#NUM!" else "-" for cell in row]
                lignes.append(" | ".join(propre))
            send_message(chat_id, "🕒 Derniers mouvements :\n" + "\n".join(lignes))
        except Exception as e:
            send_message(chat_id, f"❌ Erreur mouvements : {e}")

    elif text.startswith("/viderreponse"):
        if "CONFIRMER" not in text:
            send_message(chat_id, "⚠️ Cette action supprimera toutes les réponses du formulaire.\nTapez : /viderreponse CONFIRMER")
            return
        try:
            send_message(chat_id, "🕓 Veuillez patienter...")
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_REPONSES)
            data = sheet.get_all_values()
            if len(data) <= 1:
                send_message(chat_id, "📭 Aucune réponse à supprimer.")
            else:
                sheet.batch_clear(["A2:Z1000"])
                send_message(chat_id, "🧹 Réponses du formulaire effacées.")
        except Exception as e:
            send_message(chat_id, f"❌ Erreur formulaire : {e}")

    elif text.lower().startswith("/etat"):
        try:
            send_message(chat_id, "🕓 Veuillez patienter...")
            seuil = 3
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_INVENTAIRE)
            rows = sheet.get_all_records()
            total = len(rows)
            sous_seuil = sum(1 for r in rows if str(r.get("Quantité", "")).isdigit() and int(r["Quantité"]) <= seuil)
            heure = datetime.now().strftime("%d/%m/%Y %H:%M")
            send_message(chat_id,
                f"📊 État de l’inventaire :\n"
                f"🔢 Produits total : {total}\n"
                f"🚨 Sous le seuil (≤{seuil}) : {sous_seuil}\n"
                f"🕓 Mise à jour : {heure}"
            )
        except Exception as e:
            send_message(chat_id, f"❌ Erreur état : {e}")

    elif text.lower().startswith("/stock"):
        try:
            terme = text.replace("/stock", "").strip().lower()
            if not terme:
                send_message(chat_id, "❌ Veuillez préciser un nom de produit.")
                return
            send_message(chat_id, "🕓 Veuillez patienter...")
            sheet = client.open_by_key(SHEET_ID).worksheet(FEUILLE_INVENTAIRE)
            rows = sheet.get_all_records()
            resultats = [f"📦 {r['Nom']} : {r['Quantité']} unités"
                         for r in rows if terme in r['Nom'].lower()]
            if resultats:
                send_message(chat_id, "\n".join(resultats))
            else:
                send_message(chat_id, "❌ Produit non trouvé.")
        except Exception as e:
            send_message(chat_id, f"❌ Erreur stock : {e}")

    else:
        send_message(chat_id, "❓ Commande inconnue. Tapez /aide")

def main_loop():
    global LAST_UPDATE_ID
    print("🤖 Bot Telegram actif (mode polling)...")
    while True:
        try:
            response = requests.get(f"{URL}/getUpdates", params={"offset": LAST_UPDATE_ID + 1, "timeout": 10})
            data = response.json()

            for update in data.get("result", []):
                LAST_UPDATE_ID = update["update_id"]
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = message.get("t")  # Correct

