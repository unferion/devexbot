import asyncio
import logging
from config_reader import config
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters.command import Command
from aiogram.filters.text import Text
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder
import requests
from requests.auth import HTTPDigestAuth
from aiogram import F
from aiogram.methods import DeleteMessage
import sqlite3
import pathlib
import sys
import json
from ldap3 import Server, Connection, SIMPLE, SYNC, ASYNC, SUBTREE, ALL
from aiogram.fsm.storage.memory import MemoryStorage

async def main():
    # Объект бота
    bot = Bot(token=config.bot_token.get_secret_value())
    # Диспетчер
    
    await dp.start_polling(bot)

dp = Dispatcher()
script_path = pathlib.Path(sys.argv[0]).parent
conndb = sqlite3.connect(script_path / "bot.db")
# создание курсора для работы с базой данных
cursor = conndb.cursor()
# домен - example.com
# DNS имя сервера Active Directory
AD_SERVER = config.AD_SERVER.get_secret_value()
# Пользователь (логин) в Active Directory - нужно указать логин в AD 
# в формате 'EXAMPLE\aduser' или 'aduser@example.com'
AD_DOMEN= config.AD_DOMEN.get_secret_value()
AD_USER = config.AD_USER.get_secret_value()
AD_PASSWORD = config.AD_PASSWORD.get_secret_value()
AD_SEARCH_TREE = config.AD_SEARCH_TREE.get_secret_value()
server = Server(AD_SERVER)
conn = Connection(server,user=f"{AD_USER}/{AD_DOMEN}",password=AD_PASSWORD)
conn.bind()

def add_user(chat_id, tg_name, usrtype, phone, ad_usr, domain):
    cursor.execute("INSERT INTO users (chatid, tgname, usertype, phone, adusr, domain) VALUES (?, ?, ?, ?, ?, ?)", (chat_id, tg_name, usrtype, phone, ad_usr, domain))
    conndb.commit()

# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
builder = InlineKeyboardBuilder()
router = Router()
dp.include_routers(router)

'''@dp.message(Command("start"))
async def start_handler(message: types.Message):
    # get the user's Telegram ID
    user_id = message.from_user.id

    # get the user's phone number (if available)
    phone_number = message.from_user.phone_number

    # get the user's username (if available)
    username = message.from_user.username

    # print the user's information to the console
    print(f"User ID: {user_id}")
    print(f"Phone number: {phone_number}")
    print(f"Username: {username}")

    # send a greeting message to the user
    await message.reply("Hello, world!")'''
# Создаем кнопку "Отправить номер телефона"
#request_contact_button = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)

# Создаем клавиатуру, содержащую только одну кнопку
#keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True).add(request_contact_button)

contactbtn = [[types.KeyboardButton(text='Отправить контакт',request_contact=True, resize_keyboard=True)]]
contactkb=types.ReplyKeyboardMarkup(keyboard=contactbtn)

@dp.message(Command("start"))
async def contact_request(message: types.Message):
    await message.answer("Нажмите на кнопку, чтобы отправить номер телефона:",reply_markup=contactkb
    )

jira ='https://jira.peopleandpeople.io'
print(f"{jira} jira")
session = requests.Session()
session.auth = (AD_USER,AD_PASSWORD)
auth = session.post(jira)
print (auth.status_code)

#print(json_response.keys())
#for key in json_response:
#    print(key, json_response[key])
#for key, value in json_response.items():
#  print("{0}: {1}".format(key,value))

#print (json_response['issues'])
#print(json_response['issues'][0])
#iss=json_response['issues'][0]
#print (json_response['issues'][0].keys())
#for key in json_response['issues']:
#    print(key["key"])
#print (json_response['issues'][0]['key'])
#print (type(json_response))
#print(json.dumps(json_response, indent=4))

@router.message(Command(commands=["cancel"]))
@router.message(Text(text="отмена",ignore_case=True))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        text="Действие отменено",
        reply_markup=types.ReplyKeyboardRemove()
    )

@dp.message(Command("queue"))
async def get_queue(message: types.Message):
    cursor.execute(f"SELECT * FROM users WHERE chatid="+str(message.from_user.id)+" AND adusr NOT NULL")
    result=cursor.fetchall()
    if result!=[]:
        req = f'{jira}/rest/api/2/search?jql=project=DEV AND reporter={result[0][4]} AND status in ("Открытa","В ожидании","В процессе","Передано на рассмотрение","На подтверждении СБ")&fields=key,status,reporter,assignee,requestFieldValues,requestType'
        response = session.get(req)
        json_response = response.json()
        if json_response['total']!=0:
            reqbld = InlineKeyboardBuilder()
            for key in json_response['issues']:
                print(key["key"])
                reqbld.button(text=key["key"], url=f"{jira}/servicedesk/customer/portal/1/{key['key']}")
            await message.reply("Ваши заявки:", reply_markup=reqbld.as_markup())
        else: await message.reply("Очередь заявок пуста")
    else: await message.reply("номер не синхронизирован с AD")

def make_row_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

reqtypes = ["Запрос на обслуживание","Инцидент","Сброс пароля"]

class NewRequest(StatesGroup):
    choosing_request_type = State()
    entering_text = State()

def make_row_keyboard(items: list[str]) -> ReplyKeyboardMarkup:
    """
    Создаёт реплай-клавиатуру с кнопками в один ряд
    :param items: список текстов для кнопок
    :return: объект реплай-клавиатуры
    """
    row = [KeyboardButton(text=item) for item in items]
    return ReplyKeyboardMarkup(keyboard=[row], resize_keyboard=True)

@dp.message(Command("request"))
async def cmd_request(message: Message, state: FSMContext):
    await message.answer(
        text=f"К инцидентам относится то\nК запросам на обслуживание сё\nСброс пароля сбрасывает пароль\n\nВыберите тип заявки:",
        reply_markup=make_row_keyboard(reqtypes)
    )
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(NewRequest.choosing_request_type)

@router.message(NewRequest.choosing_request_type, F.text.in_(reqtypes))
async def request_chosen(message: Message, state: FSMContext):
    await state.update_data(req_text=message.text)
    await message.answer(
        text="Теперь, пожалуйста, введите текст запроса:",
        reply_markup=make_row_keyboard(reqtypes)
    )
    await state.set_state(NewRequest.entering_text)

@router.message(NewRequest.choosing_request_type)
async def norequsttype(message: Message):
    await message.answer(
        text="Тип заявки указан неверно.\n\n"
             "Пожалуйста, выберите одно из списка ниже:",
        reply_markup=make_row_keyboard(reqtypes)
    )

@router.message(NewRequest.entering_text, F.text)
async def text_entered(message: Message, state: FSMContext):
    user_data = await state.get_data()
    cursor.execute(f"SELECT * FROM users WHERE chatid="+str(message.from_user.id)+" AND adusr NOT NULL")
    result=cursor.fetchall()
    body=json.dumps({
    "fields": {
        "project": {
            "key": "DEV"
        },
        "summary": "Заявка от бота",
        "description": message.text,
        "reporter": {
            "name": result[0][4]
        },
        "issuetype": {
            "id": "10201"
        },
        "customfield_10208": "Не знаю что выбрать"
        }
    },indent=4)
    print(body)
    headers= {'Content-type':'application/json;charset=UTF-8', 'Accept': '*/*'}
    response = session.post(f'{jira}/rest/api/2/issue',data=body,headers=headers)
    json_response = response.json()
    print(response.status_code)
    await message.answer(
        text=f"Создана заявка типа {user_data['req_text']}. Текст заявки {message.text}.\nНомер заявки {json_response['key']}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()

@dp.message(F.contact)
async def handle_contact(message: types.Message):
        if message.contact.user_id != message.from_user.id:
            await bot.delete_message(message.chat.id,message.message_id)
            await message.reply("Нельзя отправлять чужой контакт!")
        else:
            print(f"Received contact: {message.contact.first_name} {message.contact.last_name} {message.contact.phone_number}")
            cursor.execute("SELECT * FROM users WHERE chatid="+str(message.from_user.id)+" AND adusr NOT NULL")
            result=cursor.fetchall()
            if result==[]:
                conn.search(AD_SEARCH_TREE,'(telephoneNumber='+str(message.contact.phone_number).replace("+","")+')',SUBTREE,
                attributes =['sAMAccountName', 'telephoneNumber']
                )
                print(conn.response)
                if conn.response!=[]: 
                    add_user(message.from_user.id,message.from_user.username,0,int(message.contact.phone_number),str(conn.entries[0].sAMAccountname.value),"GRUZF")
                    await message.reply("ok",reply_markup=types.ReplyKeyboardRemove())
                else:
                    await message.reply("номер не найден")
            else: 
                await message.reply("номер уже синхронизирован",reply_markup=types.ReplyKeyboardRemove())

"""
    if message.contact.user_id != telegram_id:
        await message.answer("Нельзя отправлять контакты других пользователей!")
        print(f"Received contact: {message.contact.first_name} {message.contact.last_name}")
        return
"""

#def close_db():
#conndb.close()

if __name__ == "__main__":
    asyncio.run(main())