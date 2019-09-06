#-- 3rd party imports --#
# from telegram import ChatAction
from telegram.ext import (Updater, CommandHandler, MessageHandler, Filters, RegexHandler,
						  ConversationHandler)

import json
import warnings
import requests
from pprint import pprint


# States of the ConversationHandler
MESSAGE_INCOME = 1
TOKEN = "858696338:AAEMPf6WqFLZ0MRMhROcIy2FnMfnyt_R9VI"



class Message_handler(object):
	def __init__(self):
		self.bot_token = TOKEN
		

	def send_chat_action(self, chat_id, action = "typing"):
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


class LUIS_handler(object):
	def __init__(self, appId="bc3ff1e2-70a8-4d2b-a7b8-15ba16b0321c", authKey="e704bf3d2d214dcda7d4821d614bfd57"):
		self.appId = appId
		self.authKey = authKey
		self.url = "https://westeurope.api.cognitive.microsoft.com/luis/v2.0/apps/{}?subscription-key={}&q=".format(appId, authKey)

	def query(self, msg):
		response = requests.get(self.url + msg)
		if response.status_code == 200:
			return response.json()

	def getResponse(self, msg):
		msgData = self.query(msg)
		intent = msgData['topScoringIntent']['intent']
		if intent == "welcome": return "¡Hola!"
		elif intent == "help": return "No te puedo ayudar, soy muy inútil ahora."
		elif intent == "bye": return "¡Chao pescao!"


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
	MH.send_message(chat_id, "¡Bienvenido al bot!", typing=True, reply_to=message_id)
	return MESSAGE_INCOME


"""
	Function that ends a conversation
"""
def done(bot, update):
	return ConversationHandler.END


"""
	Function that manages the state machine
"""
def processMessage(bot, update):
	chat_id = update.message.chat_id
	message = update.message.text
	message_id = update.message.message_id

	response = LH.getResponse(message)
	MH.send_message(chat_id, response, typing=True, reply_to=message_id)

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
			entry_points=[CommandHandler('start', start, pass_args = True),
						MessageHandler(filters = Filters.text, callback = processMessage)],
			states = {
				MESSAGE_INCOME: [MessageHandler(filters = Filters.text, callback = processMessage)],
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
