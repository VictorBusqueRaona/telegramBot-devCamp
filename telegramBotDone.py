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
MESSAGE_INCOME, DATACOLLECTION, RESET = 1, 2, 3

TOKEN = "858696338:AAEMPf6WqFLZ0MRMhROcIy2FnMfnyt_R9VI" # Change it for your own bot token
LUIS_APPID = "fabd7d06-9bcf-4ec0-8f66-7841fe4f944b"
LUIS_AUTHKEY = ""


chatId_2_patientId = { }
patients = { }


#----------------------------------------- HELPER CLASSES ------------------------------------------


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
	def __init__(self, appId=LUIS_APPID, authKey=LUIS_AUTHKEY):
		self.appId = appId
		self.authKey = authKey
		self.url = "https://westeurope.api.cognitive.microsoft.com/luis/v2.0/apps/{}?staging=true&subscription-key={}&q=".format(appId, authKey)

	def query(self, msg):
		response = requests.get(self.url + msg)
		if response.status_code == 200:
			intent = response.json()['topScoringIntent']['intent']
			entities = response.json()['entities']

			luisEntities = [ {'type': e['type'], 'value': e['entity'] if not 'resolution' in e.keys() else e['resolution']['values'][0]} for e in response.json()['entities']]   
			
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
        self.stdFormat = "{0}-{1}-{2}T00:00:00"

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
        return self.stdFormat.format(year, month, day)


#----------------------------------------- RESPITRON CLASSES/FUNCTIONS ------------------------------------------


class Patient(object):
	def __init__(self, name, surname, chat_id):
		self.chat_id = None
		self.Id = None
		self.Name = name
		self.Surname = surname
		self.GenderId = None
		self.DateOfBirth = None
		self.DateOfDecease = None
		self.Smoker = None
		self.CigarrettesDailyConsumption = None
		self.CityId = 8

	def getMissingField(self):
		if not self.GenderId: return "GenderId", "Por favor, dime tu género."
		if not self.DateOfBirth: return "DateOfBirth", "¿Cuándo naciste?"
		if self.CigarrettesDailyConsumption == None: return "CigarretesDailyConsumption", "¿Cuántos cigarrillos fumas diariamente?"
		return None, None

	def postToAPI(self):
		data = {
			"Name": self.Name,
			"Surname": self.Surname,
			"GenderId": self.GenderId,
			"DateOfBirth": self.DateOfBirth,
			"DateOfDecease": self.DateOfDecease,
			"Smoker": self.Smoker,
			"CigarrettesDailyConsumption": self.CigarrettesDailyConsumption,
			"CityId": self.CityId
		}
		response = requests.post(
			"https://respitronday220190915060001.azurewebsites.net/api/Patients",
			json=data)
		return response.json()['Id']

	def setField(self, field, value):
		if field == "Gender":
			gender2id = {
				"Female": 1,
				"Male": 2,
				"Undefined": 3
			}
			if value in gender2id.keys(): self.GenderId = gender2id[value]
		if field == "Date":
			self.DateOfBirth = value
		if field == "Number":
			value = int(value)
			if value > 0: self.Smoker = True
			else: self.Smoker = False
			self.CigarrettesDailyConsumption = value


def getPatients():
	response = requests.get("https://respitronday220190915060001.azurewebsites.net/api/Patients")
	if response.status_code == 200: return response.json()


def deletePatient(chat_id):
	pId = chatId_2_patientId[chat_id]
	response = requests.delete("https://respitronday220190915060001.azurewebsites.net/api/Patients/{}".format(pId))
	return bool(response)


def addConsumption(chat_id, liters, date):
	data = {
		"PatientId": chatId_2_patientId[chat_id],
		"ConsumptionDate": date,
		"O2LitersConsumption": liters
	}
	response = requests.post("https://respitronday220190915060001.azurewebsites.net/api/ConsumptionHistories", json=data)
	return bool(response)


#----------------------------------------- DIALOG HANDLING FUNCTIONS ------------------------------------------


# Global handlers
MH = Message_handler()
LH = LUIS_handler()


"""
	Function that responds to the /start command
"""
def start(bot, update, args):
	global chatId_2_patientId, patients
	print("STARTED")
	chat_id = update.message.chat_id
	message_id = update.message.message_id

	user_name = update.message.from_user.first_name
	last_name = update.message.from_user.last_name

	patientsData = getPatients()
	for patient in patientsData:
		pName, pSurname, pId = patient["Name"], patient["Surname"], patient["Id"]
		if unidecode.unidecode(pName.lower()) == unidecode.unidecode(user_name.lower()):
			chatId_2_patientId[chat_id] = pId
			print("User {} with Id {} started conversation".format(user_name, pId))
			MH.send_message(chat_id, "Hola de nuevo, {}.".format(user_name), typing=True, reply_to=message_id)
			return MESSAGE_INCOME
	print("No matches...")
	patients[chat_id] = Patient(name=user_name, surname=last_name, chat_id=chat_id)
	MH.send_message(chat_id, "¡Hola {}, encantado! ¡Soy Respibot! Te voy a hacer unas cuantas preguntas para generar tu perfil.".format(user_name), typing=True, reply_to=message_id)
	return collectData(bot, update)

"""
	Function that collects patient data (conversational form)
"""
def collectData(bot, update):
	global patients, chatId_2_patientId
	chat_id = update.message.chat_id
	text = update.message.text

	patient = patients[chat_id]

	intent, entities = LH.query(text)

	if intent != "informarPatient": return DATACOLLECTION
	else:
		for entity in entities:
			type, value = entity['type'], entity['value']
			patient.setField(type, value)
		missingField, question = patient.getMissingField()
		if not missingField: 
			pId = patient.postToAPI()
			del(patients[chat_id])
			chatId_2_patientId[chat_id] = pId
			MH.send_message(chat_id, "¡Genial! Ya te he registrado en RespiTron.", typing=True)
			return MESSAGE_INCOME
		else:
			MH.send_message(chat_id, question, typing=True)
			return DATACOLLECTION


"""
	Function that gets triggered every time a regular message is received
"""
def processMessage(bot, update):
	chat_id = update.message.chat_id
	message = update.message.text
	message_id = update.message.message_id

	print("New message from {} -> {}...".format(chat_id, message[:100]))
	intent, entities = LH.query(message)
	print("Message's intent: {}".format(intent))
	if intent == "eliminarPatient": 
		deleted = deletePatient(chat_id)
		if deleted: 
			MH.send_message(chat_id, "Oh... Está bien, ya te he dado de baja.", typing=True)
			return RESET
		else: 
			MH.send_message(chat_id, "¡Uy! No he podido eliminarte, tal vez no estabas registrado.", typing=True)
			return MESSAGE_INCOME
	if intent == "informarConsumption":
		if not [e for e in entities if e['type'] == 'Number']: 
			MH.send_message(chat_id, "No he detectado la cantidad de litros!", message_id)
			return MESSAGE_INCOME
		else: liters = [e['value'] for e in entities if e['type'] == 'Number'][0]
		if not [e for e in entities if e['type'] == 'Date']: date = "2019-09-20T00:00:00"
		else: date = [e['value'] for e in entities if e['type'] == 'Date'][0]
		added = addConsumption(chat_id, liters, date)
		if added: MH.send_message(chat_id, "¡Estupendo! He anotado el consumo.", message_id)
		else: MH.send_message(chat_id, "Ha habido un problema al anotar el consumo.", message_id)

	MH.send_intent_message(intent, chat_id, message_id)

	return MESSAGE_INCOME


#----------------------------------------- MAIN ------------------------------------------


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
				MESSAGE_INCOME: [MessageHandler(filters = Filters.text, callback = processMessage)],
				RESET: [MessageHandler(filters = Filters.text, callback = start)]
			},
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
