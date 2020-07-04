import telebot
from tinydb import TinyDB, Query
import xlsxwriter
import config
import os
import re
from telebot_calendar import create_calendar
import datetime

current_shown_dates={}

users = TinyDB('users.json')
requests = TinyDB('requests.json')

bot = telebot.TeleBot(config.token)

@bot.message_handler(commands=['admin'])
def admin(message):
	if message.chat.id in config.admin:
		markup = telebot.types.InlineKeyboardMarkup()
		kb1 = telebot.types.InlineKeyboardButton(text="Добавить новое фото в галерею ", callback_data="add_requests")
		kb2 = telebot.types.InlineKeyboardButton(text="Получить таблицу с данными пользователей", callback_data="get_users")
		markup.add(kb1)
		markup.add(kb2)
		bot.send_message(chat_id=message.chat.id, text="Добро пожаловать в меню Администратора!", reply_markup = markup)

@bot.message_handler(commands=['start'])
def start(message):
	user = users.search(Query().chatId == message.chat.id)
	if not user:
		users.insert({
			'chatId': message.chat.id,
			'username': message.chat.username,
			'stage': 0,
			'temp': 0,
			'country': 0,
			'start_date': 0,
			'yacht_type': 0,
			'beds': 0,
			'budget': 0,
			'name': 0,
			'phone': 0,
			'email': 0,
			'licence': 0
		})
	users.update({'temp': 0}, Query().chatId == message.chat.id)
	pre_markup = telebot.types.InlineKeyboardMarkup()
	kb = telebot.types.InlineKeyboardButton(text="Интересные предложения", callback_data="requests:")
	pre_markup.add(kb)
	bot.send_message(message.chat.id, config.messages['pre_start'], reply_markup=pre_markup)

	markup = telebot.types.InlineKeyboardMarkup()
	kb1 = telebot.types.InlineKeyboardButton(text="Да", callback_data="start_yes")
	kb2 = telebot.types.InlineKeyboardButton(text="Нет", callback_data="start_no")
	markup.add(kb1,kb2)
	bot.send_message(message.chat.id, config.messages['start'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: 'DAY' in call.data[0:13])
def handle_day_query(call):
	chat_id = call.message.chat.id
	saved_date = current_shown_dates.get(chat_id)
	last_sep = call.data.rfind(';') + 1

	if saved_date is not None:

		day = call.data[last_sep:]
		date = datetime.datetime(int(saved_date[0]), int(saved_date[1]), int(day), 0, 0, 0).strftime('%d/%m/%Y')

		users.update({'start_date': str(date)}, Query().chatId == call.message.chat.id)
		users.update({'stage': 'beds'}, Query().chatId == call.message.chat.id)
		bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text=config.messages['reply_send_beds'])

		bot.answer_callback_query(call.id, text="Вы выбрали "+ str(date))

	else:
		# add your reaction for shown an error
		pass


@bot.callback_query_handler(func=lambda call: 'MONTH' in call.data)
def handle_month_query(call):

    info = call.data.split(';')
    month_opt = info[0].split('-')[0]
    year, month = int(info[1]), int(info[2])
    chat_id = call.message.chat.id

    if month_opt == 'PREV':
        month -= 1

    elif month_opt == 'NEXT':
        month += 1

    if month < 1:
        month = 12
        year -= 1

    if month > 12:
        month = 1
        year += 1

    date = (year, month)
    current_shown_dates[chat_id] = date
    markup = create_calendar(year, month)
    bot.edit_message_text(config.messages['reply_send_start_date'], call.from_user.id, call.message.message_id, reply_markup=markup)


@bot.callback_query_handler(func=lambda call: "IGNORE" in call.data)
def ignore(call):
    bot.answer_callback_query(call.id, text="OOPS... something went wrong")

@bot.callback_query_handler(func=lambda call:True)
def call_handler(call):

	if call.data == 'get_users':
		workbook = xlsxwriter.Workbook('result.xlsx')
		worksheet = workbook.add_worksheet()
		worksheet.write(0, 0, 'Имя Telegram')
		worksheet.write(0, 1, 'Страна плавания')
		worksheet.write(0, 2, 'Дата начала')
		worksheet.write(0, 3, 'Тип яхты')
		worksheet.write(0, 4, 'Кол-во кроватей')
		worksheet.write(0, 5, 'Бюджет')
		worksheet.write(0, 6, 'Имя')
		worksheet.write(0, 7, 'Телефон')
		worksheet.write(0, 8, 'E-mail')
		worksheet.write(0, 9, 'Лицензия')
		list_user = users.search(Query().chatId > 1)
		for i,user in enumerate(list_user):

			worksheet.write(i+1, 0, user['username'])
			worksheet.write(i+1, 1, user['country'])
			worksheet.write(i+1, 2, user['start_date'])
			worksheet.write(i+1, 3, user['yacht_type'])
			worksheet.write(i+1, 4, user['beds'])
			worksheet.write(i+1, 5, user['budget'])
			worksheet.write(i+1, 6, user['name'])
			worksheet.write(i+1, 7, user['phone'])
			worksheet.write(i+1, 8, user['email'])
			worksheet.write(i+1, 9, user['licence'])

		workbook.close()

		doc = open('result.xlsx', 'rb')
		bot.send_document(call.message.chat.id, doc)

	if call.data == 'send_message_no':
		users.update({'temp': 0}, Query().chatId == call.message.chat.id)
		users.update({'stage': 0}, Query().chatId == call.message.chat.id)
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Отменено')

	if call.data == 'add_requests':
		users.update({'stage': 'add_request_photo'}, Query().chatId == call.message.chat.id)
		markup = telebot.types.InlineKeyboardMarkup()
		kb1 = telebot.types.InlineKeyboardButton(text="Отмена", callback_data="send_message_no")
		markup.add(kb1)
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Отправьте фото для отчета', reply_markup=markup)

	if call.data == 'menu':
		users.update({'temp': 0}, Query().chatId == call.message.chat.id)
		markup = telebot.types.InlineKeyboardMarkup()
		kb1 = telebot.types.InlineKeyboardButton(text="Да", callback_data="start_yes")
		kb2 = telebot.types.InlineKeyboardButton(text="Нет", callback_data="start_no")
		markup.add(kb1,kb2)
		bot.send_message(call.message.chat.id, config.messages['start'], reply_markup=markup)

	if call.data == 'start_no':
		users.update({'stage': 0}, Query().chatId == call.message.chat.id)
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=config.messages['start_reply_no'])

	if call.data == 'start_yes':
		users.update({'stage': 'name_input'}, Query().chatId == call.message.chat.id)
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=config.messages['reply_send_name'])

	if call.data in config.yacht_types:
		users.update({'yacht_type': call.data}, Query().chatId == call.message.chat.id)
		users.update({'stage': 'licence'}, Query().chatId == call.message.chat.id)

		markup = telebot.types.InlineKeyboardMarkup()
		kb1 = telebot.types.InlineKeyboardButton(text="Да", callback_data="lic_yes")
		kb2 = telebot.types.InlineKeyboardButton(text="Нет", callback_data="lic_no")
		markup.add(kb1,kb2)
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=config.messages['reply_send_licence'], reply_markup=markup)

	if call.data == 'lic_no':
		users.update({'stage': 'final'}, Query().chatId == call.message.chat.id)
		users.update({'licence': 'Нет'}, Query().chatId == call.message.chat.id)

		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=config.messages['reply_send_final'])

	if call.data == 'lic_yes':
		users.update({'stage': 'final'}, Query().chatId == call.message.chat.id)
		users.update({'licence': 'Да'}, Query().chatId == call.message.chat.id)
		
		bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=config.messages['reply_send_final'])

	if 'requests:' in call.data:
		try:
			side = call.data[call.data.index(':')+1:]
		except:
			side = ''
	
		try:
			index = int(users.search(Query().chatId == call.message.chat.id)[0]['temp'])
		except:
			index = 0

		before = index
		if side == 'next':
			index += 1
		elif side == 'prev':
			index -= 1

		req = requests.all()
		msg = ''
		try:
			if index < len(req) and index >= 0:
				addr = req[index]['img']
			else:
				index = before
				addr = req[index]['img']
		except:
			return bot.answer_callback_query(call.id, text="Пока что тут пусто")

		users.update({'temp': index}, Query().chatId == call.message.chat.id)

		markup = telebot.types.InlineKeyboardMarkup()
		prev = telebot.types.InlineKeyboardButton(text="<<<", callback_data="requests:prev")
		next = telebot.types.InlineKeyboardButton(text=">>>", callback_data="requests:next")
		kb1 = telebot.types.InlineKeyboardButton(text="Назад", callback_data="menu")
		markup.add(prev, next)
		markup.add(kb1)
		if call.message.chat.id in config.admin:
			rem_btn = telebot.types.InlineKeyboardButton(text="Удалить", callback_data="delete:"+str(req[index].doc_id))
			markup.add(rem_btn)
		if msg == '':
			msg = 'Пока что тут пусто'

		if call.message.content_type != 'photo':
			with open(addr, 'rb') as photo:
					bot.send_photo(chat_id=call.message.chat.id, photo = photo, reply_markup=markup)
		else:
			try:
				with open(addr, 'rb') as photo:
					bot.edit_message_media(chat_id=call.message.chat.id, message_id=call.message.message_id, media=telebot.types.InputMedia(type='photo', media=photo), reply_markup=markup)
			except:
				bot.answer_callback_query(call.id, text="Больше ничего нет")

	if 'delete:' in call.data:
		index = int(call.data[call.data.index(':')+1:])
		print(index)
		print(requests.get(doc_id=index))
		if requests.get(doc_id=index):
			addr = requests.get(doc_id=index)['img']
			os.remove(addr)
			requests.remove(doc_ids=[index])

@bot.message_handler(content_types=["text"])
def text_handler(message):
	user = users.search(Query().chatId == message.chat.id)
	if user:
		user = user[0]

		if user['stage'] == 'name_input':
			if len(message.text) > 2 and message.text.isalpha():
				users.update({'name': message.text}, Query().chatId == message.chat.id)

				users.update({'stage': 'phone_input'}, Query().chatId == message.chat.id)
				bot.send_message(message.chat.id, config.messages['reply_send_phone'])
			else:
				bot.send_message(message.chat.id, config.messages['reply_send_name_wrong'])

		if user['stage'] == 'phone_input':
			if len(message.text) >= 7:
				users.update({'phone': message.text}, Query().chatId == message.chat.id)

				for admin in config.admin:
					try:
						bot.send_message(admin, 'Новый пользователь в базе')
					except:
						pass

				users.update({'stage': 'email_input'}, Query().chatId == message.chat.id)
				bot.send_message(message.chat.id, config.messages['reply_send_email'])
			else:
				bot.send_message(message.chat.id, config.messages['reply_send_phone_wrong'])

		if user['stage'] == 'email_input':
			if re.match('^(?!.*@.*@.*$)(?!.*@.*\-\-.*\..*$)(?!.*@.*\-\..*$)(?!.*@.*\-$)(.*@.+(\..{1,11})?)$', message.text):
				users.update({'email': message.text}, Query().chatId == message.chat.id)

				users.update({'stage': 'country_input'}, Query().chatId == message.chat.id)
				bot.send_message(message.chat.id, config.messages['reply_send_country'])
			else:
				bot.send_message(message.chat.id, config.messages['reply_send_email_wrong'])

		if user['stage'] == 'country_input':
			users.update({'country': message.text}, Query().chatId == message.chat.id)
			if len(message.text) >= 4:
				users.update({'stage': 'start_date_input'}, Query().chatId == message.chat.id)
				now = datetime.datetime.now()
				chat_id = message.chat.id

				date = (now.year, now.month)
				current_shown_dates[chat_id] = date

				markup = create_calendar(now.year, now.month)

				bot.send_message(message.chat.id, config.messages['reply_send_start_date'], reply_markup=markup)
				#bot.send_message(message.chat.id, config.messages['reply_send_start_date'])
			else:
				bot.send_message(message.chat.id, config.messages['reply_send_country_short'])

		if user['stage'] == 'beds':
			try:
				users.update({'beds': int(message.text)}, Query().chatId == message.chat.id)
				users.update({'stage': 'budget'}, Query().chatId == message.chat.id)
				bot.send_message(message.chat.id, config.messages['reply_send_budget'])
			except ValueError:
				bot.send_message(message.chat.id, config.messages['reply_send_number_error'])

		if user['stage'] == 'budget':
			try:
				users.update({'budget': int(message.text)}, Query().chatId == message.chat.id)
				
				users.update({'stage': 'yacht_type'}, Query().chatId == message.chat.id)
				markup = telebot.types.InlineKeyboardMarkup()
				for y_type in config.yacht_types:
					kb = telebot.types.InlineKeyboardButton(text=y_type, callback_data=y_type)
					markup.add(kb)
				bot.send_message(message.chat.id, config.messages['reply_send_yacht_type'], reply_markup=markup)
			except ValueError:
				bot.send_message(message.chat.id, config.messages['reply_send_number_error'])

		

		

		

@bot.message_handler(content_types=["photo"])
def photo_handler(message):
	user = users.search(Query().chatId == message.chat.id)
	if user:
		user = user[0]

		if user['stage'] == 'add_request_photo':
			file_info = bot.get_file(message.photo[-1].file_id)
			downloaded_file = bot.download_file(file_info.file_path)
			src = 'img/' + message.photo[-1].file_id[20:-20:2] + '.jpg'
			try:
				with open(src, 'wb') as new_file:
					new_file.write(downloaded_file)
			except:
				pass
			requests.insert({'img': src})
			bot.send_message(message.chat.id, 'Материал успешно добавлен')

if __name__ == '__main__':
	bot.polling(none_stop=True)