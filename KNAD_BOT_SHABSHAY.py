import sqlite3
import openai
import telegram 
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import MessageHandler, CommandHandler, Filters, Updater, CallbackQueryHandler, Job, JobQueue
from datetime import datetime
from dateutil import parser
import pytz
import random
import time
import os
import speech_recognition as sr


def save_message(update, context):
    global chats

    chat_id = update.effective_chat.id
    name = update.message.from_user.first_name
    text = update.message.text
    name_and_text = f'{name}: {text}'

    if chat_id not in chats:
        chats[chat_id] = {'messages': []}


    messages = chats[chat_id]['messages']
    messages.append({'name_and_text': name_and_text})


    if len(messages) > 1000:
        messages = messages[-1000:]

    chats[chat_id]['messages'] = messages

    print(chats)




def save_voice_message(update, context):

    audio = update.message.voice

    if audio is not None:
        f = context.bot.get_file(audio.file_id)
        f.download('voice.ogg')

        text = voice_translator('voice.ogg', context.bot, update)

        update.message.reply_text(text)
    else:
        print('файла нет')

def voice_translator(audio_path, bot, update):
    if os.path.isfile(audio_path):  # Проверяем, существует ли файл
        r = sr.Recognizer()
        audio_f = open(audio_path, 'rb')
        audio = r.record(audio_f)

        text_from_voice = r.recognize_google(audio, language='ru-RU')
        bot.send_message(chat_id = update.effective_chat.id, text = text_from_voice)
    else:
        bot.send_message(chat_id = update.effective_chat.id, text = "Не удалось распознать рчеь")




def summary_command(update, context):

    if len(context.args) == 0 or not context.args[0].isdigit():
        context.bot.send_message(chat_id = update.effective_chat.id, text = 'Пожалуйста, укажите количество сообщений после команды /summary в виде цифры.')
        pass

    num = int(context.args[0])
    chat_id = update.effective_chat.id

    print(num)
    print(chat_id)

    if chat_id in chats:
        messages = chats[chat_id]['messages']
        num = min(num, len(messages))
        message_texts = [message['name_and_text'] for message in messages[-num:]]

        model_response = openai.Completion.create(
            engine = 'gpt-3.5-turbo-instruct',
            prompt = '\n'.join(message_texts) + '\n\nНапишите кратко, кто о чем был разговор?',
            max_tokens = 1800,
            n = 1,
            stop = None,
            temperature = 0.5,
        )
        summary = model_response.choices[0].text
        bot.send_message(chat_id = update.effective_chat.id, text = f'{summary} \n\nИногда бот может выдавать неточную информацию. МЫ приносим свои извинения и сообщаем, что уже работаем над данной проблемой')




def assistent_command(update, context):

    message = context.args
    request = ' '.join(message)
    print(request)

    model_response = openai.Completion.create(
        engine='gpt-3.5-turbo-instruct',
        prompt=request,
        max_tokens=1800,
        n=1,
        stop=None,
        temperature=0.5,
    )
    answer = model_response.choices[0].text
    bot.send_message(chat_id = update.effective_chat.id, text = f'{answer} \n\nИногда бот выдает неправильный или неполный ответ. Если вы столкнулись с такой проблемой - задайте вопрос повторно. Мы уже работаем над проблемой (нет)')




def paint_command(update, context):

    message = context.args
    request = ' '.join(message)
    print(request)

    response = openai.Completion.create(
        engine="davinci",
        prompt=f'Сгенерируйте изображение: {request}',
        max_tokens=100,
    )
    image_url = response.choices[0].text.strip()
    bot.send_message(chat_id=update.effective_chat.id,
                     text=image_url)

def remind_command(update, context):
    global reminds

    chat_id = update.effective_chat.id
    args = context.args

    if len(args) < 2:
        bot.send_message(chat_id=chat_id, text='Введите напоминание в таком формате: дд.мм.гггг чч:мм')
        return

    date_time = f'{args[0]} {args[1]}'
    date_format = '%d.%m.%Y %H:%M'

    remind_time = datetime.strptime(date_time, date_format)

    message = ' '.join(args[2:])
    if chat_id not in reminds:
        reminds[chat_id] = {'reminders': []}

    reminds[chat_id]['reminders'].append({'time': remind_time, 'message': message})
    bot.send_message(chat_id = chat_id, text = f'Напоминание установлено: {message} в {remind_time} по МСК')

    print(reminds)




def remind_checker(context):
    global reminds

    moscow_time = pytz.timezone('Europe/Moscow')
    chat_id = context.job.context['chat_id']

    if chat_id in reminds:
        time_now = datetime.now(moscow_time)
        reminders = reminds[chat_id]['reminders']
        reminders_to_remove = []

        for reminder in reminders:
            remind_time = reminder['remind_time']
            message = reminder['message']

            if time_now >= remind_time:
                bot.send_message(chat_id=chat_id, text=f'НАПОМИНАНИЕ: {message}')
                reminders_to_remove.append(reminder)

        for reminder in reminders_to_remove:
            reminders.remove(reminder)




def choose_kitty(update, context):
    global kitties_of_the_day

    chat = update.effective_chat
    chat_id = chat.id

    chat = context.bot.get_chat(chat_id)
    members_count = chat.get_members_count()
    usernames = [member.user.username for member in members if member.user.username]

    chosen_kitty = random.choice(usernames)
    kitties_of_the_day[chat_id] = chosen_kitty

    context.bot.send_message(chat_id=chat_id, text=f"{chosen_kitty} - Котик дня!")


    

def get_kitty(update, context):
    global kitties_of_the_day

    chat = update.effective_chat
    chat_id = chat.id

    moscow_time = pytz.timezone('Europe/Moscow')
    now = datetime.now(moscow_time)
    midnight = now.replace(hour = 0, minute = 0, second = 0, microsecond = 0)

    if chat_id in kitties_of_the_day:
        chosen_kitty = kitties_of_the_day[chat_id]
        context.bot.send_message(chat_id = chat_id, text  =f"Сегодняшний Котик дня: {chosen_kitty}")
    else:
        context.bot.send_message(chat_id = chat_id, text = "Котик дня еще не выбран. Попробуйте позже.")








def reset_command(update, context):
    chat_id = update.effective_chat.id

    keyboard = [
        [InlineKeyboardButton('Очистить историю чата', callback_data = 'clear_chat')],
        [InlineKeyboardButton('Очистить историю бота', callback_data = 'clear_bot')],
        [InlineKeyboardButton('Отмена', callback_data = 'cancel')]
    ]

    bot.send_message(chat_id = chat_id, text = 'Выберите вариант очистки истории. После удаления вы уже не сможете востановить историю', reply_markup = InlineKeyboardMarkup(keyboard))


def button_callback(update, context):
    global chats

    query = update.callback_query
    chat_id = query.message.chat_id
    message_id = query.message.message_id

    if query.data == 'clear_chat':
        if chat_id in chats:
            chats[chat_id]['messages'] = []
            bot.send_message(chat_id = chat_id, text = 'История чата очищена')
            bot.delete_message(chat_id = chat_id, message_id = message_id)

    elif query.data == 'clear_bot':
        chats = {}
        bot.send_message(chat_id = chat_id, text = 'История бота очищена')
        bot.delete_message(chat_id=chat_id, message_id = message_id)

    elif query.data == 'cancel':
        bot.delete_message(chat_id = chat_id, message_id = message_id)




def start_command(update, context):
    bot.send_message(chat_id = update.effective_chat.id, text = 'Првет! Я многофункциональный (нет) бот для телеграм чатов.  \nЧтобы узнать весь функционале - используйте комманду /commands. \nПриятного пользования 😁 ')
    chat_id = update.effective_chat.id
    remind_queue = updater.job_queue
    context.job_queue.run_repeating(remind_checker, interval=60, first=0, context={'chat_id': chat_id})




def help_command(update, context):
    bot.send_message(chat_id = update.effective_chat.id, text = 'Вот команды, которые можно использовать:' \
                              '\n/summary n вывод краткого пересказа последних n сообщений' \
                              '\n/assist  вирутальный помошник, готовый ответить на любой вопрос'
                              '\n/reset  очистить истоию разговора'
                              '\n/remind  создать напоминание'
                              '\n/paint text  создать арт с помощью нейросети'
                              '\n/remind  создать напоминание'                            
                              '\n/kotik_of_a_day  ищет котика дня')



telegram_token = '6862454013:AAFyftc7Ax3jeAFDA2MkiOdMhPdeT5_IXOE'
openai_api_key = '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'

chats = {}
reminds = {}
kitties_of_the_day = {}


bot = telegram.Bot(token = telegram_token)
openai.api_key = openai_api_key
updater = Updater(telegram_token, use_context = True)
dispatcher = updater.dispatcher

dispatcher.add_handler(CommandHandler('start', start_command))
dispatcher.add_handler(CommandHandler('commands', help_command))
dispatcher.add_handler(CommandHandler('reset', reset_command))


dispatcher.add_handler(CommandHandler('summary', summary_command))
dispatcher.add_handler(CommandHandler('assist', assistent_command))
dispatcher.add_handler(CommandHandler('remind', remind_command))
dispatcher.add_handler(CommandHandler("kotik_dnya", choose_kitty))
dispatcher.add_handler(CommandHandler("get_kotik", get_kitty))
dispatcher.add_handler(CommandHandler("paint", paint_command))


dispatcher.add_handler(CallbackQueryHandler(button_callback))


dispatcher.add_handler(MessageHandler(Filters.voice & Filters.audio, save_voice_message))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, save_message))


updater.start_polling()