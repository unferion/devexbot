from pydantic import BaseSettings, SecretStr


class Settings(BaseSettings):
    # Желательно вместо str использовать SecretStr 
    # для конфиденциальных данных, например, токена бота
    bot_token: SecretStr
    AD_SERVER: SecretStr
    # Пользователь (логин) в Active Directory - нужно указать логин в AD 
    # в формате 'EXAMPLE\aduser' или 'aduser@example.com'
    AD_DOMEN: SecretStr
    AD_USER: SecretStr
    AD_PASSWORD: SecretStr
    AD_SEARCH_TREE: SecretStr
    JIRA: SecretStr
    
    # Вложенный класс с дополнительными указаниями для настроек
    class Config:
        # Имя файла, откуда будут прочитаны данные 
        # (относительно текущей рабочей директории)
        env_file = '.env'
        # Кодировка читаемого файла
        env_file_encoding = 'utf-8'


# При импорте файла сразу создастся 
# и провалидируется объект конфига, 
# который можно далее импортировать из разных мест
config = Settings()