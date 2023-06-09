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
from aiogram.handlers import CallbackQueryHandler

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

#подключение к AD
AD_SERVER = config.AD_SERVER.get_secret_value()
AD_DOMEN= config.AD_DOMEN.get_secret_value()
AD_USER = config.AD_USER.get_secret_value()
AD_PASSWORD = config.AD_PASSWORD.get_secret_value()
AD_SEARCH_TREE = config.AD_SEARCH_TREE.get_secret_value()
server = Server(AD_SERVER)
authad=f"{AD_DOMEN}\\{AD_USER}"
conn = Connection(server,user=authad,password=AD_PASSWORD)
conn.bind()

#подключение к JIRA
jira = config.JIRA.get_secret_value()
print(f"{jira} jira")
session = requests.Session()
session.auth = (AD_USER,AD_PASSWORD)
auth = session.post(jira)
print (auth.status_code)

logging.basicConfig(level=logging.INFO)
builder = InlineKeyboardBuilder()
router = Router()
dp.include_routers(router)

#issuetypes
#10201 запрос на обслуживание
#10200 инцидент
def newReq(message,issuetype,issuetextfield):
    cursor.execute(f"SELECT * FROM users WHERE chatid={str(message.from_user.id)} AND adusr NOT NULL")
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
            "id": issuetype
        },
        "customfield_10208": issuetextfield
        }
    },indent=4)
    print(body)
    headers= {'Content-type':'application/json;charset=UTF-8', 'Accept': '*/*'}
    response = session.post(f'{jira}/rest/api/2/issue',data=body,headers=headers)
    json_response = response.json()
    return response

@dp.callback_query()
async def mycallback(callback: types.CallbackQuery):
    await callback.message.answer('sdasdasd')

def checkReq(idReq,session):
    headers= {'Content-type':'application/json;charset=UTF-8', 'Accept': '*/*'}
    response = session.get(f'{jira}/rest/servicedeskapi/request/{idReq}?expand=issueType',headers=headers)
    print(response)
    return response


reqResponse = checkReq("DEV-28439",session).json()
print(type(reqResponse))
print(reqResponse['issueKey'])
print(reqResponse['requestFieldValues'][0]['value'])
print(reqResponse['requestFieldValues'][1]['value'])
print(reqResponse['currentStatus']['status'])
#print(reqResponse.issueKey)
#newReq(message.text,10201,"Не знаю что выбрать")

def add_user(chat_id, tg_name, usrtype, phone, ad_usr, domain):
    cursor.execute("INSERT INTO users (chatid, tgname, usertype, phone, adusr, domain) VALUES (?, ?, ?, ?, ?, ?)", (chat_id, tg_name, usrtype, phone, ad_usr, domain))
    conndb.commit()

# Включаем логирование, чтобы не пропустить важные сообщения

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

contactbtn = [[types.KeyboardButton(text='Отправить контакт',request_contact=True)]]
contactkb = types.ReplyKeyboardMarkup(keyboard=contactbtn, resize_keyboard=True)

@dp.message(Command("start"))
async def contact_request(message: types.Message):
    await message.answer("Нажмите на кнопку, чтобы отправить номер телефона:",reply_markup=contactkb
    )

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
                reqbld.button(text=key["key"],callback_data="www")
                #url=f"{jira}/servicedesk/customer/portal/1/{key['key']}" ,
            await message.reply("Ваши заявки:", reply_markup=reqbld.as_markup())
        else: await message.reply("Очередь заявок пуста")
    else: await message.reply("номер не синхронизирован с AD")

reqList=["Проблема с ПО","Проблема с ПК","Проблема с сетью","Запрос картриджа","Замена периферии","Смена пароля","Не знаю что выбрать"]
reqtypes = ["1","2","3","4","5","6","7"]
incidentReq={
    "reqKey":10200,
    "req":[
        "Проблема с ПО",
        "Проблема с ПК",
        "Проблема с сетью"
        ],
    "jiraKey":[
        "Устранение известных проблем программ из списка стандартного набора ПО.",
        "Устранение неисправностей ОС (без переустановки ОС), например, решение вопросов торможения ПК, неудачный вход в систему, освобождение свободного места на локальных дисках.",
        "Устранение проблем доступа к сети интернет и/или локальной сети с одного компьютера"
        ]
}
serviceReq={
    "reqKey":10201,
    "req":[
        "Запрос картриджа",
        "Замена периферии",
        "Смена пароля",
        "Не знаю что выбрать"
        ],
    "jiraKey":[
        "Замена картриджей в принтерах/мфу.",
        "Замена периферии (мыши, клавиатуры, наушники).",
        "Изменение пароля для входа в УЗ Windows.",
        "Не знаю что выбрать"
        ]
}

"""
count=0
i=0
while True:
    try:
        #print(f"{str(count+1)}. {incidentReq['req'][i]}")
        reqtypes.append(str(count+1))
    except IndexError:
        break
    count+=1
    i+=1
i=0
while True:
    try:
        #print(f"{str(count+1)}. {serviceReq['req'][i]}")
        reqtypes.append(str(count+1))
    except IndexError:
        break
    count+=1
    i+=1
"""
print (len(serviceReq['req']))

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
        text=f"Выберите тип заявки:\n\n1. Проблема с ПО\n2. Проблема с ПК\n3. Проблема с сетью\n4. Запрос картриджа\n5. Замена периферии\n6. Смена пароля\n7. Не знаю что выбрать\n\n/cancel - отмена текущего действия",
        reply_markup=make_row_keyboard(reqtypes)
    )
    # Устанавливаем пользователю состояние "выбирает название"
    await state.set_state(NewRequest.choosing_request_type)

@router.message(NewRequest.choosing_request_type, F.text.in_(reqtypes))
async def request_chosen(message: Message, state: FSMContext):
    await state.update_data(reqNum=message.text)
    await message.answer(
        text="Пожалуйста, опишите проблему\n\n/cancel - отмена текущего действия",
        reply_markup=make_row_keyboard(reqtypes)
    )
    await state.set_state(NewRequest.entering_text)

@router.message(NewRequest.choosing_request_type)
async def norequsttype(message: Message):
    await message.answer(
        text="Нет такого варианта ответа.\nПожалуйста, выберите одно из списка ниже:\n\n1. Проблема с ПО\n2. Проблема с ПК\n3. Проблема с сетью\n4. Запрос картриджа\n5. Замена периферии\n6. Смена пароля\n7. Не знаю что выбрать\n\n/cancel - отмена текущего действия",
        reply_markup=make_row_keyboard(reqtypes)
    )

@router.message(NewRequest.entering_text, F.text)
async def text_entered(message: Message, state: FSMContext):
    user_data = await state.get_data()
    """
    
    """
    if int(user_data['reqNum'])==1:
        reqJson=newReq(message,10200,"Устранение известных проблем программ из списка стандартного набора ПО.")
    elif int(user_data['reqNum'])==2:
        reqJson=newReq(message,10200,"Устранение неисправностей ОС (без переустановки ОС), например, решение вопросов торможения ПК, неудачный вход в систему, освобождение свободного места на локальных дисках.")
    elif int(user_data['reqNum'])==3:
        reqJson=newReq(message,10200,"Устранение проблем доступа к сети интернет и/или локальной сети с одного компьютера")
    elif int(user_data['reqNum'])==4:
        reqJson=newReq(message,10201,'Замена картриджей в принтерах/мфу.')
    elif int(user_data['reqNum'])==5:
        reqJson=newReq(message,10201,"Замена периферии (мыши, клавиатуры, наушники).")
    elif int(user_data['reqNum'])==6:
        reqJson=newReq(message,10201,"Изменение пароля для входа в УЗ Windows.")
    elif int(user_data['reqNum'])==7:
        reqJson=newReq(message,10201,"Не знаю что выбрать")
    reqResponse=reqJson.json()
    if reqJson.status_code==201: await message.answer(
        text=f"Создана заявка типа \"{reqList[int(user_data['reqNum'])-1]}\".\nТекст заявки {message.text}.\nНомер заявки {reqResponse['key']}",
        reply_markup=types.ReplyKeyboardRemove()
    )
    else: 
        print(reqJson)
        print(reqJson.status_code)
        await message.answer(
        text=f"Заявка не была создана.\nКод ошибки \"{reqJson.status_code}\"",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.clear()

@dp.message(F.contact)
async def handle_contact(message: types.Message):
        if message.contact.user_id != message.from_user.id:
            #await bot.delete_message(message.chat.id,message.message_id)
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

if __name__ == "__main__":
    asyncio.run(main())