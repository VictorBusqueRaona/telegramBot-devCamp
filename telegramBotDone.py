#-- 3rd party imports --#
from telegram import ChatAction
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
						  ConversationHandler)

import json
import random
import warnings
import requests
import datetime
import unidecode


# States of the ConversationHandler (single-state machine)
MESSAGE_INCOME, DATACOLLECTION = 1,2

TOKEN = "858696338:AAEMPf6WqFLZ0MRMhROcIy2FnMfnyt_R9VI" # Change it for your own bot token

chatId_2_patient = { }
MANDATORY_FIELDS = ["Name", "Gender", "DateOfBirth", "CigarretesDailyConsumption"]
ENT2FIELD = { "Date": "DateOfBirth", "Number": "CigarretesDailyConsumption" }

"""
	Helper class to interact with Telegram's API
"""
class Message_handler(object):
	def __init__(self):
		self.bot_token = TOKEN
		with open("responseMessages.json", "r", encoding="utf8") as f: self.intentMessages = json.load(f)
		

	def send_chat_action(self, chat_id, action = ChatAction.TYPING):
		params = {
			'chat_id': chat_id,
			'action': action
		}
		base_url = 'https://api.telegram.org/bot{}/sendChatAction'.format(self.bot_token)
		response = requests.get(base_url, params = params)


	def send_message(self, chat_id, message, typing = False, reply_to = None, parse_mode = 'Markdown'):
		print("sending messsage...")
		if isinstance(message, list):
			for item in message:
				self.send_message(chat_id, item, typing, reply_to, parse_mode)
		else:
			if typing: self.send_chat_action(chat_id)
			params = {
				'chat_id': chat_id,
				'text': message
			}
			if parse_mode: params['parse_mode'] = parse_mode
			if reply_to: params['reply_to_message_id'] = reply_to
			base_url = 'https://api.telegram.org/bot{}/sendMessage'.format(self.bot_token)
			response = requests.get(base_url, params = params)

	def send_intent_message(self, intent, chat_id, message_id=None):
		selectedMsg = random.choice(self.intentMessages[intent])
		print("Selected response is: {}".format(selectedMsg))
		self.send_message(chat_id, selectedMsg, reply_to=message_id, typing=True)

"""
	Helper class to interact with LUIS's API
"""
class LUIS_handler(object):
	def __init__(self, appId="fabd7d06-9bcf-4ec0-8f66-7841fe4f944b", authKey="e704bf3d2d214dcda7d4821d614bfd57"):
		self.appId = appId
		self.authKey = authKey
		self.url = "https://westeurope.api.cognitive.microsoft.com/luis/v2.0/apps/{}?staging=true&subscription-key={}&q=".format(appId, authKey)

	def query(self, msg):
		response = requests.get(self.url + msg)
		if response.status_code == 200:
			intent = response.json()['topScoringIntent']['intent']
			luisEntities = [ {'type': e['type'], 'value': e['entity']} for e in response.json()['entities']]   
			
			for e in luisEntities:
				if e['type'] == "Date": e['value'] = str(Date(e['value']))
			return intent, luisEntities
		
"""
	Helper class to handle LUIS "date" entities
"""
class Date(object):
    def __init__(self, strDate):
        self.strDate = strDate
        self.m2n = {
            "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
            "mayo": "05", "junio": "06", "julio": "07", "agosto": "08", 
            "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
        }
        self.stdFormat = "{0}/{1}/{2}"

    def toDatetime(self):
        aux = self.strDate.replace('del', '').replace('de','')
        splitment = aux.split()
        try:
            try: 
                day, month, year = splitment
                try: month = self.m2n[month]
                except: month = month if int(month) >= 10 else "0"+month
            except:
                try:
                    month, year, day = splitment + [1]
                    try: month = self.m2n[month]
                    except: month = month if int(month) >= 10 else "0"+month
                except:
                    day, month = splitment
                    try: month = self.m2n[month]
                    except: month = month if int(month) >= 10 else "0"+month
                    year = str(datetime.datetime.now().year)
            if len(year) == 2: year = "{}{}".format("19", year)
            return datetime.datetime(int(year), int(month), int(day))
        except: None

    def __repr__(self):
        date = self.toDatetime()
        if not date: return ""
        date = str(date).split()[0]
        year, month, day = [item.zfill(2) for item in date.split('-')]
        return self.stdFormat.format(day, month, year)



# Global handlers
MH = Message_handler()
LH = LUIS_handler()


"""
	Function that responds to the /start command
"""
def start(bot, update, args):
	print("STARTED")
	chat_id = update.message.chat_id
	text = update.message.text[1:]
	message_id = update.message.message_id

	user_name = update.message.from_user.first_name
	last_name = update.message.from_user.last_name
	chatId_2_patient[chat_id] = {
		"Name": user_name,
		"Surname": last_name,
		"Name": None,
		"Gender": None,
		"DateOfBirth": None,
		"CigarretesDailyConsumption": None
	}
	MH.send_message(chat_id, "¡Hola {}, encantado! ¡Soy Respibot!".format(user_name), typing=True, reply_to=message_id)

	return collectData(bot, update)


"""
	Function that ends a conversation
"""
def done(bot, update):
	return ConversationHandler.END


def collectData(bot, update):
	chat_id = update.message.chat_id
	print("Collecting data from {}".format(chat_id))
	message = update.message.text
	message_id = update.message.message_id

	intent, entities = LH.query(message)
	print("intent -> {}".format(intent))
	print("entities -> {}".format(entities))

	for e in entities:
		type = e['type']
		value = e['value']
		if not type in MANDATORY_FIELDS: type = ENT2FIELD[type]
		chatId_2_patient[chat_id][type] = value

	for field, value in chatId_2_patient[chat_id]:
		if not value: 
			MH.send_message(chat_id, "Proporcióname el {}".format(field), typing=True, reply_to=message_id)
			return DATACOLLECTION
	return MESSAGE_INCOME



"""
	Function that gets triggered every time a regular message is received
"""
def processMessage(bot, update):
	chat_id = update.message.chat_id
	message = update.message.text
	message_id = update.message.message_id

	print("New message from {} -> {}...".format(chat_id, message[:100]))
	intent, _ = LH.query(message)
	print("Message's intent: {}".format(intent))
	MH.send_intent_message(intent, chat_id, message_id)

	return MESSAGE_INCOME


"""
	Main function, polls waiting for messages
"""
def main():

		# Create the Updater and pass it your bot's token.
		warnings.filterwarnings("ignore")
		updater = Updater(TOKEN)

		dp = updater.dispatcher

		conv_handler = ConversationHandler(
			entry_points=[CommandHandler('start', start, pass_args = True)],
						# MessageHandler(filters = Filters.text, callback = processMessage)],
			states = {
				DATACOLLECTION: [MessageHandler(filters = Filters.text, callback = collectData)],
				MESSAGE_INCOME: [MessageHandler(filters = Filters.text, callback = processMessage)]
			},
			fallbacks=[RegexHandler('^Done$', done)],
			allow_reentry = True #So users can use /login
		)
		dp.add_handler(conv_handler)

		# Start the Bot
		updater.start_polling()

		# Run the bot until you press Ctrl-C or the process receives SIGINT,
		# SIGTERM or SIGABRT. This should be used most of the time, since
		# start_polling() is non-blocking and will stop the bot gracefully.
		updater.idle()


if __name__ == '__main__':
	main()