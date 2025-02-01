import os
import json
import time
import random
import asyncio
from typing import Dict, List, Optional
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from telegram.error import TelegramError

# Configuration
TOKEN = os.environ['BOT_TOKEN']

class KageoBot:
    def __init__(self):
        self.load_data()
        self.speed_wpm = 70  # Vitesse par défaut
        
    def load_data(self):
        """Charge ou initialise les données persistantes"""
        try:
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.moderators = set(data.get('moderators', []))
                self.saved_tables = data.get('saved_tables', {})
                self.challengers = data.get('challengers', {})  # Ajout des challengers
        except FileNotFoundError:
            self.moderators = set()
            self.saved_tables = {}
            self.challengers = {}
            self.save_data()

        try:
            with open('LPdatabase.json', 'r', encoding='utf-8') as f:
                self.lp_database = json.load(f)
        except FileNotFoundError:
            print("Erreur: LPdatabase.json non trouvé!")
            self.lp_database = {}
        except json.JSONDecodeError:
            print("Erreur: LPdatabase.json mal formaté!")
            self.lp_database = {}

        # État du jeu par chat
        self.games = {}

    def save_data(self):
        """Sauvegarde les données persistantes"""
        data = {
            'moderators': list(self.moderators),
            'saved_tables': self.saved_tables,
            'challengers': self.challengers  # Ajout des challengers dans la sauvegarde
        }
        with open('bot_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_game_state(self, chat_id: int) -> dict:
        """Récupère l'état du jeu pour un chat spécifique"""
        if chat_id not in self.games:
            self.games[chat_id] = {
                'active': False,
                'opponent': None,
                'last_question_time': None,
                'waiting_confirmation': False  # Ajout pour la confirmation du duel
            }
        return self.games[chat_id]

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        welcome_message = """
Je suis 𝗞𝗔𝗚𝗘𝗢 2.0 , Aka 𝗧𝗛𝗔𝗗𝗗𝗘𝗨𝗦, the god of Kowloon.

Je suis un bot d'entraînement conçu par Izumi Heathcliff, exclusivement pour les Quiz de type LP. Mon but sera de te challenger au maximum. Mais avant de commencer, je veux que tu sache que :

« 𝙏𝙃𝙀 𝙊𝙉𝙇𝙔 𝙒𝙃𝙊 𝘾𝘼𝙉 𝘽𝙀𝘼𝙏 𝙈𝙀 𝙄𝙎 𝙈𝙀 »

Commandes disponibles:
/start - Afficher ce message
/duel_lp - Lancer un défi
/speed [wpm] - Définir ma vitesse d'écriture (20-200)
/add_modo - S'enregistrer comme modérateur
/modo_list - Voir la liste des modérateurs
/save_tab - Sauvegarder un tableau
/show_tab - Afficher un tableau sauvegardé
/end_game - Terminer la partie en cours
"""
        try:
            await update.message.reply_text(welcome_message)
        except TelegramError as e:
            print(f"Erreur Telegram dans start: {e}")

    def calculate_typing_time(self, text: str) -> float:
        """Calcule précisément le temps d'écriture"""
        if not text:
            return 0.5  # Temps minimum par défaut
            
        chars_per_minute = self.speed_wpm * 5
        chars_per_second = chars_per_minute / 60
        
        char_count = len(text)
        space_count = text.count(' ')
        
        char_time = char_count / chars_per_second
        space_time = space_count * 0.1
        send_time = 0.2
        
        total_time = char_time + space_time + send_time
        return min(round(total_time, 2), 10.0)

    async def set_speed(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            if not context.args:
                await update.message.reply_text("Usage: /speed [20-200]")
                return
                
            speed = int(context.args[0])
            if not 20 <= speed <= 200:
                await update.message.reply_text("La vitesse doit être entre 20 et 200 WPM.")
                return
            
            self.speed_wpm = speed
            if speed == 200:
                await update.message.reply_text("Es-tu sûr de réussir a take fils ?🌛 ")
            else:
                await update.message.reply_text(f"✅ Ma vitesse actuelle vient d'être définie sur {speed} WPM")
        except ValueError:
            await update.message.reply_text("La vitesse doit être un nombre entier.")
        except TelegramError as e:
            print(f"Erreur Telegram dans set_speed: {e}")

    async def handle_lp_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return

        chat_id = update.message.chat_id
        game_state = self.get_game_state(chat_id)
        
        if not game_state['active']:
            return
        
        if update.effective_user.id not in self.moderators:
            return
            
        message = update.message.text
        if not (message.startswith('Q/') or message.startswith('Q)')):
            return

        current_time = time.time()
        if game_state['last_question_time'] and \
           current_time - game_state['last_question_time'] < 1:
            return

        game_state['last_question_time'] = current_time
            
        try:
            letters = message[2:].strip().split()
            if not letters:
                await update.message.reply_text("❌ Format incorrect. Exemple: Q/ A B")
                return

            response = []
            for letter in letters:
                if letter.upper() in self.lp_database:
                    possible_answers = self.lp_database[letter.upper()]
                    if possible_answers:
                        response.append(random.choice(possible_answers))
            
            if response:
                full_response = " ".join(response)
                typing_time = self.calculate_typing_time(full_response)
                
                await asyncio.sleep(typing_time)
                await update.message.reply_text(full_response)
                
                await asyncio.sleep(1)
                await update.message.reply_text(f"⌛ Temps d'écriture : {typing_time}s")
            else:
                await update.message.reply_text("❌ Aucune réponse trouvée pour ces lettres.")
        except TelegramError as e:
            print(f"Erreur Telegram dans handle_lp_question: {e}")

    async def duel_lp(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return

        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        game_state = self.get_game_state(chat_id)
        
        if game_state['active']:
            await update.message.reply_text("❌ Une partie est déjà en cours. Utilisez /end_game pour la terminer.")
            return

        game_state['active'] = True
        game_state['opponent'] = user_id
        game_state['waiting_confirmation'] = True
        
        try:
            await update.message.reply_text("Thaddeus accepte ton défi. Confirmes-tu le duel ? (Réponds par 'oui' pour confirmer)")
        except TelegramError as e:
            print(f"Erreur Telegram dans duel_lp: {e}")
            game_state['active'] = False
            game_state['opponent'] = None
            game_state['waiting_confirmation'] = False

    async def add_modo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return

        try:
            user_id = update.effective_user.id
            if user_id in self.moderators:
                await update.message.reply_text("Vous êtes déjà modérateur.")
                return

            self.moderators.add(user_id)
            self.save_data()
            await update.message.reply_text(f"✅ {update.effective_user.first_name} a été ajouté comme modérateur.")
        except TelegramError as e:
            print(f"Erreur Telegram dans add_modo: {e}")

    async def modo_list(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            if not self.moderators:
                await update.message.reply_text("Aucun modérateur enregistré.")
                return
                
            modo_text = "Liste des modérateurs:\n"
            for modo_id in self.moderators:
                try:
                    chat = await context.bot.get_chat(modo_id)
                    modo_text += f"• {chat.first_name}\n"
                except TelegramError:
                    modo_text += f"• ID: {modo_id} (non trouvé)\n"
                    
            await update.message.reply_text(modo_text)
        except TelegramError as e:
            print(f"Erreur Telegram dans modo_list: {e}")

    async def save_tab(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            if not update.message.reply_to_message:
                await update.message.reply_text("❌ Vous devez répondre au tableau que vous souhaitez sauvegarder.")
                return
                
            context.user_data['waiting_for_table_name'] = True
            context.user_data['table_content'] = update.message.reply_to_message.text
            await update.message.reply_text("Donnez un nom à ce tableau:")
        except TelegramError as e:
            print(f"Erreur Telegram dans save_tab: {e}")

    async def show_tab(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            # Charger les tableaux depuis le fichier
            with open('bot_data.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.saved_tables = data.get('saved_tables', {})

            if not self.saved_tables:
                await update.message.reply_text("Aucun tableau sauvegardé.")
                return
                
            table_list = "\n".join(f"• {name}" for name in self.saved_tables.keys())
            await update.message.reply_text(
                f"Tableaux disponibles:\n{table_list}\n\n"
                "Répondez avec le nom du tableau à afficher."
            )
            context.user_data['waiting_for_table_choice'] = True
        except TelegramError as e:
            print(f"Erreur Telegram dans show_tab: {e}")
        except FileNotFoundError:
            await update.message.reply_text("❌ Erreur: Aucun tableau n'a été sauvegardé.")

    async def handle_table_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        try:
            table_name = update.message.text.strip()
            if not table_name:
                await update.message.reply_text("❌ Le nom du tableau ne peut pas être vide.")
                return
                
            table_content = context.user_data.get('table_content')
            if table_content:
                self.saved_tables[table_name] = table_content
                self.save_data()  # Sauvegarde dans bot_data.json
                await update.message.reply_text(f"✅ Tableau '{table_name}' sauvegardé.")
            
            context.user_data['waiting_for_table_name'] = False
            context.user_data['table_content'] = None
        except TelegramError as e:
            print(f"Erreur Telegram dans handle_table_name: {e}")

    async def end_game(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message:
            return

        chat_id = update.message.chat_id
        game_state = self.get_game_state(chat_id)
        
        try:
            if not game_state['active']:
                await update.message.reply_text("❌ Aucune partie n'est en cours.")
                return
                
            game_state['active'] = False
            game_state['opponent'] = None
            game_state['last_question_time'] = None
            game_state['waiting_confirmation'] = False
            await update.message.reply_text("Partie terminée. Ja ne 🌛⚡")
        except TelegramError as e:
            print(f"Erreur Telegram dans end_game: {e}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.effective_user:
            return

        message = update.message.text.lower() if update.message.text else ""
        chat_id = update.message.chat_id
        user_id = update.effective_user.id
        game_state = self.get_game_state(chat_id)
        
        try:
            # Gestion des noms de tableaux
            if context.user_data.get('waiting_for_table_name'):
                await self.handle_table_name(update, context)
                return
                
            # Gestion du choix de tableau
            if context.user_data.get('waiting_for_table_choice'):
                if message in self.saved_tables: await update.message.reply_text(self.saved_tables[message])
                else:
                    await update.message.reply_text("❌ Tableau non trouvé.")
                context.user_data['waiting_for_table_choice'] = False
                return
            
            # Gestion de la confirmation du duel
            if game_state['waiting_confirmation'] and game_state['opponent'] == user_id:
                if message.lower() in ['oui', 'wep', 'ouais', '.']:
                    # Enregistrer le challenger dans la base de données
                    if str(user_id) not in self.challengers:
                        self.challengers[str(user_id)] = {
                            'name': update.effective_user.first_name,
                            'duels_count': 0,
                            'join_date': time.strftime('%Y-%m-%d')
                        }
                    self.challengers[str(user_id)]['duels_count'] += 1
                    self.save_data()
                    
                    game_state['waiting_confirmation'] = False
                    await update.message.reply_text(f"Duel confirmé! Bienvenue challenger {update.effective_user.first_name}! 🌛⚡")
                    return
                elif message.lower() in ['non', 'nop', 'non.']:
                    game_state['active'] = False
                    game_state['opponent'] = None
                    game_state['waiting_confirmation'] = False
                    await update.message.reply_text("Duel annulé.")
                    return
            
            # Gestion des appels au bot
            if message in ['ai', 'kageo']:
                await update.message.reply_text("tu m'as appelé ? 🌛⚡")
                return

            # Gestion des questions LP
            await self.handle_lp_question(update, context)
            
        except TelegramError as e:
            print(f"Erreur Telegram dans handle_message: {e}")

def main():
    try:
        print("Démarrage de Kageo 2.0...")
        bot = KageoBot()
        application = Application.builder().token(TOKEN).build()
        
        # Ajout des handlers avec gestion d'erreurs
        handlers = [
            CommandHandler("start", bot.start),
            CommandHandler("speed", bot.set_speed),
            CommandHandler("duel_lp", bot.duel_lp),
            CommandHandler("add_modo", bot.add_modo),
            CommandHandler("modo_list", bot.modo_list),
            CommandHandler("save_tab", bot.save_tab),
            CommandHandler("show_tab", bot.show_tab),
            CommandHandler("end_game", bot.end_game),
            MessageHandler(filters.TEXT & ~filters.COMMAND, bot.handle_message)
        ]
        
        for handler in handlers:
            application.add_handler(handler)
        
        # Handler pour les erreurs non gérées
        async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
            print(f'Erreur non gérée: {context.error}')
            try:
                if update and update.message:
                    await update.message.reply_text(
                        "Une erreur s'est produite. Veuillez réessayer."
                    )
            except:
                pass

        application.add_error_handler(error_handler)
        
        # Démarrage du bot
        print("Kageo 2.0 est prêt!")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        print(f"Erreur critique au démarrage: {e}")

if __name__ == '__main__':
    main()