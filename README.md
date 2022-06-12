# ЧАСТЬ 1

Классы:
* AuthPayloadNoPass -- Наследует BaseModel pydantic
    Описывает JSON авторизации без сохранения пароля
    Поля:
    * name: str -- Имя пользователя
    * digest: str = '' -- Дайджест сессии
    
* AuthPayload -- Наследует AuthPayloadNoPass
    Описывает то же, что и родительский класс, но содержит пароль
    Поля:
    * pwd: str -- Пароль пользователя
    
* UserAsJson -- Наследует BaseModel pydantic
    Описывает польователя в JSON формате
    Поля:
    * name: str -- Имя пользователя
    * pwd: str -- Пароль пользователя
    * rights: str = 'r' -- Права пользователя

    Методы:
    * valid_rights(cls, v) -> str -- Дополнительный валидатор для поля rights
        Проверяет вхождение права в перечень доступных

* DBUser
    Описывает пользователя
    Поля:
    * name: str = '' -- Имя пользователя
    * rights: str = '' -- Права пользователя

    Методы:
    * __init__ -- конструктор, ничего не делает, т.к. нужны awaitable методы
    * login(self, name: str, pwd: str) -> dict -- Метод авторизации
    * get_user(self, name: str) -> dict -- Метод поиска пользователя
    * create_user(self, new_user:UserAsJson) -> dict -- Метод создания пользователя
    * drop_user(self, name: str) -> dict -- Метод удаления пользователя
    * edit_user(self, new_user:UserAsJson) -> dict -- Метод редактирования пользователя


Глобальные переменные:
* session_keys -- Словарь, хранит данные в виде 
    **'Имя пользователя': ('ID сессии', <Объект DBUser>, float времени создания сессии)**
* MongoClient -- Клиент работы с БД, изначально None, создается при запуске
* app -- Приложение FastAPI


Внутренняя зависимость:

Файл **configs.py**

Переменные:
* DB_HOST -- Хост БД

* DB_USER -- Пользователь БД

* DB_PWD -- Пароль пользователя БД

* DB_NAME -- Имя БД

Раздел по 1 Части ТЗ:

* SALT -- Соль для хеширования

* AVAIBLE_RIGHTS -- Кортеж доступных прав пользователей

* MAX_SESSION_TIME -- Макисмальное время жизни сессии


События:
* Запуск приложения -- функция db_connect()


Роуты:
* /tz1/login -- функция log_in(auth_payload: AuthPayload) -> dict
    * Авторизация пользователя
* /tz1/get_user -- функция get_user(serch_name: str, auth_payload: AuthPayloadNoPass) -> dict
    * Поиск пользователя
* /tz1/create_user -- функция create_user(new_user: UserAsJson, auth_payload: AuthPayloadNoPass) -> dict
    * Создание пользователя
* /tz1/drop_user -- функция drop_user(serch_name: str, auth_payload: AuthPayloadNoPass) -> dict
    * Удаление пользователя
* /tz1/edit_user -- функция edit_user(new_user: UserAsJson, auth_payload: AuthPayloadNoPass) -> dict
    * Редактирование пользователя


Запуск:
Для запуска необходимо:
* БД sklv_test
* Коллекция sklv_test.users
* Форма документа коллекции: 
    * {  "_id": {"$oid": "..."},  "name": "Alex",  "pwd": "...",  "rights": "rw"}
* Пользователь БД с правами readWrite
* Тестовый сервер -- uvicorn



# ЧАСТЬ 2

Внутренняя зависимость:

Файл **configs.py**
Переменные:
* COLLECTION_NAMES -- Котреж коллекций с данными
* MAX_DB_TIMEOUT_MS -- Время в миллисекундах максимально допустимого ожидания ответа БД


Роуты:
* /tz2/get_data -- функция get_data()
    * Получение данных из 3-х коллекций


Запуск:
Для запуска необходимо:
* БД sklv_test
* Коллекции:
    * sklv_test.input_col_1
    * sklv_test.input_col_2
    * sklv_test.input_col_3
* Форма документа любой из коллекций: 
* {  "_id": {"$oid": "..."},  "id": 1,  "name": "Test 1"}
* Пользователь БД с правами readWrite
* Тестовый сервер -- uvicorn