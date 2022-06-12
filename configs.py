# Хост БД
DB_HOST = 'localhost:27017'

# Пользователь БД
DB_USER = "mongo-admin"

# Пароль пользователя БД
DB_PWD = "qwerty123"

# Имя БД
DB_NAME = "sklv_test"

"""Раздел по 1 Части ТЗ"""

# Соль для хеширования
SALT = b'qwerty!0'

# Кортеж доступных прав пользователей
AVAIBLE_RIGHTS = ('r', 'rw')

# Макисмальное время жизни сессии
MAX_SESSION_TIME = 86400


"""Раздел по 2 Части ТЗ"""
COLLECTION_NAMES = ('input_col_1', 'input_col_2', 'input_col_3')

MAX_DB_TIMEOUT_MS = 2000