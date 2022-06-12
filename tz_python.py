import time

from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ValidationError, validator
from typing import Union
from fastapi import FastAPI
from pymongo import errors
from hashlib import md5

from configs import DB_HOST, DB_NAME, DB_PWD, DB_USER, SALT, AVAIBLE_RIGHTS, MAX_SESSION_TIME, COLLECTION_NAMES, MAX_DB_TIMEOUT_MS




# Словарь хранения сессий (Вместо Redis), 
# Данные хранит в формате: 'Имя пользователя': ('ID сессии', <Объект DBUser>, float времени создания сессии)
session_keys = dict()

# Клиент работы с БД, изначально None, создастся при запуске
MongoClient = None


app = FastAPI()






class AuthPayloadNoPass(BaseModel):
    """Авторизационный JSON без пароля"""

    # Имя
    name: str

    # Дайджест сессии
    digest: str = ''


class AuthPayload(AuthPayloadNoPass):
    """Авторизационный JSON с паролем"""

    # Пароль
    pwd: str


class UserAsJson(BaseModel):
    """Описание польователя в JSON формате"""

    # Имя (логин)
    name: str

    # Пароль
    pwd: str

    # Права
    rights: str = 'r'

    # Дополнительная валидация прав на их вхождение в AVAIBLE_RIGHTS
    @validator('rights')
    def valid_rights(cls, v) -> str:
        if v not in AVAIBLE_RIGHTS: raise ValueError('Not avaible rights.')
        else: return v


class DBUser():
    """Класс описания пользователя"""

    # Имя (логин)
    name: str = ''

    # Права
    rights: str = ''

    def __init__(self):
        """Инициализация пустая, т.к. нужны асинхронные методы"""
        pass


    async def login(self, name: str, pwd: str) -> dict:
        """Метод авторизации

            _____________________________________
            name: Имя пользователя, str
            pwd: пароль пользователя, str
        
        """
        try:

            user_doc = await MongoClient['users'].find_one({'name': name})

            # Проверка нахождения по имени
            if user_doc:

                # Проверка совпадения хешей паролей
                if get_pwd_hash(pwd) == user_doc['pwd']:

                    # Валидация прав
                    if user_doc['rights'] in AVAIBLE_RIGHTS: self.rights = user_doc['rights']
                    else: return {'status': 'error', 'result': [], 'errmsg': 'Invalid rights.'}

                    # По-сути конструктор объекта
                    self.name = name
                    sess_id = get_sess_id_by_login(name)
                    session_keys[name] = (sess_id, self, time.time())
                    print(session_keys)
                    return {'status': 'success', 'result': [sess_id], 'errmsg': ''}

                else: return {'status': 'error', 'result': [], 'errmsg': 'Authentication failed.'}

            else: return {'status': 'error', 'result': [], 'errmsg': 'User is not exist.'}

        # Ошибка операции с БД
        except errors.OperationFailure as e:
            return {'status': 'error', 'result': [], 'errmsg': e.details['errmsg']}


    async def get_user(self, name: str) -> dict:
        """Метод поиска пользователя по имени"""

        
        # Проверка наличия прав на метод
        if self.rights.count('r'): 
            try:
                user_doc = await MongoClient['users'].find_one({'name': name})

            # Ошибка операции с БД
            except errors.OperationFailure as e:
                return {'status': 'error', 'result': [], 'errmsg': e.details['errmsg']}

            # Проверка нахождения по имени
            if user_doc:

                # Фильтрация ответа от _id и пароля
                filtered_user_doc = {key:user_doc[key] for key in user_doc.keys() if key != '_id' and key != 'pwd'}
                return {'status': 'success', 'result': [filtered_user_doc], 'errmsg': ''}

            else: return {'status': 'error', 'result': [], 'errmsg': 'User is not exist.'}
        
        else: return {'status': 'error', 'result': [], 'errmsg': 'You have not enough rights for operation'}


    async def create_user(self, new_user:UserAsJson) -> dict:
        """Метод создания нового пользователя"""

        try:

            # Проверка наличия прав на метод
            if self.rights.count('rw'):
                new_user_doc = {'name': new_user.name, 'pwd': get_pwd_hash(new_user.pwd), 'rights': new_user.rights}

                try:
                    await MongoClient['users'].insert_one(new_user_doc)
                    return {'status': 'success', 'result': [new_user.name], 'errmsg': ''}

                # Ошибка операции с БД
                except errors.OperationFailure as e:
                    return {'status': 'error', 'result': [], 'errmsg': e.details['errmsg']}

            else: return {'status': 'error', 'result': [], 'errmsg': 'You have not enough rights for operation'}

        # Ошибка валидации формы
        except ValidationError as e:
            return {'status': 'error', 'result': [], 'errmsg': e}


    async def drop_user(self, name: str) -> dict:
        """Метод удаления пользователя"""

        # Проверка наличия прав на метод
        if self.rights.count('rw'):
            try:
                await MongoClient['users'].delete_one(filter={'name': name})

                # Случай удаления себя
                if name == self.name:
                    session_keys.pop(self.name)

                return {'status': 'success', 'result': [name], 'errmsg': ''}

            # Ошибка операции с БД
            except errors.OperationFailure as e:
                return {'status': 'error', 'result': [], 'errmsg': e.details['errmsg']}

        else: return {'status': 'error', 'result': [], 'errmsg': 'You have not enough rights for operation'}


    async def edit_user(self, new_user:UserAsJson) -> dict:
        """Метод редактирования пользователя"""

        try:
            # Проверка наличия прав на метод
            if self.rights.count('rw'):
                old_user_doc = await MongoClient['users'].find_one(filter={'name': new_user.name})

                if old_user_doc:
                    try:
                        await MongoClient['users'].replace_one( {'_id': old_user_doc['_id']}, 
                                                                {'name': new_user.name, 'pwd': get_pwd_hash(new_user.pwd), 'rights': new_user.rights})
                        
                        # Случай редактирования себя
                        if new_user.name == self.name:
                            session_keys.pop(self.name)
                            self.login(name=new_user.name, pwd=new_user.pwd)

                        return {'status': 'success', 'result': [new_user.name], 'errmsg': ''}

                    # Ошибка операции с БД
                    except errors.OperationFailure as e:
                        return {'status': 'error', 'result': [], 'errmsg': e.details['errmsg']}

                else: return {'status': 'error', 'result': [], 'errmsg': 'User is not exist.'}


            else: return {'status': 'error', 'result': [], 'errmsg': 'You have not enough rights for operation'}

        # Ошибка валидации формы
        except ValidationError as e:
            return {'status': 'error', 'result': [], 'errmsg': e}



def get_sess_id_by_login(login:str) -> str:
    """Генерация ID сессии"""

    to_hach = SALT
    to_hach += login.encode('utf8')
    to_hach += str(time.time()).encode('utf8')
    return md5(to_hach).hexdigest()


def get_pwd_hash(pwd: str) -> str:
    """Хэширование пароля"""

    to_hach = SALT
    to_hach += pwd.encode('utf8')
    return md5(to_hach).hexdigest()


def check_auth(auth_payload: AuthPayloadNoPass) -> Union[DBUser, bool]:
    """Проверка авторизации"""

    # Проверка вхождения логина пользователя в ключи сесиий и совпадения ключа
    if auth_payload.name in session_keys.keys() and auth_payload.digest == session_keys[auth_payload.name][0]:

        # Проверка валидности сессии во времени
        if session_keys[auth_payload.name][2] < MAX_SESSION_TIME: return session_keys[auth_payload.name][1]

        # Рефреш сессии
        else: session_keys.pop(auth_payload.name); session_keys[auth_payload.name][1].login(name=auth_payload.name, pwd=auth_payload.pwd)
    
    else: return False



@app.on_event('startup')
async def db_connect():
    """Создание клинта БД при включении приложения"""

    global MongoClient

    URI = f"mongodb://{DB_USER}:{DB_PWD}@{DB_HOST}/{DB_NAME}"
    MongoClient = AsyncIOMotorClient(URI)[DB_NAME]
    

"""Раздел по 1 Части ТЗ"""


@app.post('/tz1/login')
async def log_in(auth_payload: AuthPayload) -> dict:
    """ Авторизация и создание объекта пользователя
        При успешной авторизации возвращает ID сессии, которая необходима для последующих запросов
    """

    try:
        user_object = DBUser()
        return await user_object.login(name=auth_payload.name, pwd=auth_payload.pwd)
    except ValidationError as e:
        return {'status': 'error', 'result': [], 'errmsg': e}


@app.post('/tz1/get_user')
async def get_user(serch_name: str, auth_payload: AuthPayloadNoPass) -> dict:
    """Поиск пользователя по имени"""

    try:
        user_object = check_auth(auth_payload)
        if user_object: return await user_object.get_user(name=serch_name)
        else: return {'status': 'error', 'result': [], 'errmsg': 'Authentication failed.'}
        
    except ValidationError as e:
        return {'status': 'error', 'result': [], 'errmsg': e}


@app.post('/tz1/create_user')
async def create_user(new_user: UserAsJson, auth_payload: AuthPayloadNoPass) -> dict:
    """Создание нового пользователя"""

    try:
        user_object = check_auth(auth_payload)
        if user_object.name: return await user_object.create_user(new_user=new_user)
        else: return {'status': 'error', 'result': [], 'errmsg': 'Authentication failed.'}
        
    except ValidationError as e:
        return {'status': 'error', 'result': [], 'errmsg': e}


@app.post('/tz1/drop_user')
async def drop_user(serch_name: str, auth_payload: AuthPayloadNoPass) -> dict:
    """Удаления пользователя"""

    try:
        user_object = check_auth(auth_payload)
        if user_object.name: return await user_object.drop_user(name=serch_name)
        else: return {'status': 'error', 'result': [], 'errmsg': 'Authentication failed.'}
        
    except ValidationError as e:
        return {'status': 'error', 'result': [], 'errmsg': e}


@app.post('/tz1/edit_user')
async def edit_user(new_user: UserAsJson, auth_payload: AuthPayloadNoPass) -> dict:
    """Редактирование пользователя"""

    try:
        user_object = check_auth(auth_payload)
        if user_object.name: return await user_object.edit_user(new_user=new_user)
        else: return {'status': 'error', 'result': [], 'errmsg': 'Authentication failed.'}
        
    except ValidationError as e:
        return {'status': 'error', 'result': [], 'errmsg': e}



"""Раздел по 2 Части ТЗ"""


@app.get('/tz2/get_data')
async def get_data():
    """Функция получения данных из 3-х коллекций"""

    item_list = []
    try:
        # Перебор курсора каждой коллекции идет асинхронно, но перебор по коллекции идет все же синхронно
        for collection in COLLECTION_NAMES:
            try:
                item_list.extend([{key:item[key] for key in item.keys() if key != '_id'} async for item in MongoClient[collection].find(max_time_ms=MAX_DB_TIMEOUT_MS)])

            # Ошибка операции с БД
            except errors.OperationFailure:
                return {'status': 'error', 'result': [], 'errmsg': 'Try request later.'}

    # Ошибка по таймауту
    except errors.ExecutionTimeout:
        return {'status': 'error', 'result': [], 'errmsg': 'Try request later.'}

    item_list.sort(key=lambda item:item['id'], reverse=False)
    return item_list






