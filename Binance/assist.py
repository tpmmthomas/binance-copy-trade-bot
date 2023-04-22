import base64
import configparser
import os
import requests
import subprocess
import pymongo
import certifi
from getpass import getpass


from binance.client import Client
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from time import sleep

ca = certifi.where()
config = configparser.ConfigParser()
config.read('config.ini')


def encrypt_decrypt_helper(password, data, salt, mode='encrypt'):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256,
        length=32,
        salt=salt,
        iterations=100000,
        backend=default_backend()
    )
    key = base64.urlsafe_b64encode(kdf.derive(password))
    f = Fernet(key)
    if mode == 'encrypt':
        return f.encrypt(data.encode())
    else:
        return f.decrypt(data).decode()


def save_to_file(password: str, data: str):
    salt = os.urandom(16)
    encrypted_data = encrypt_decrypt_helper(password.encode(), data, salt)
    return encrypted_data, salt


def password_input(prompt):
    return input(prompt)


def api_input(prompt):
    return input(prompt)


def check_token(token):
    headers = {'Authorization': 'Bot ' + token}
    response = requests.get(
        'https://discord.com/api/v6/users/@me', headers=headers)
    return response.status_code == 200


def check_config(config):
    required_options = {
        'mongo-server': ['url'],
        'binance-settings': ['api-key', 'api-secret', 'mode', 'testnet'],
        'chanel-setting': ['chanel-id'],
    }

    for section, options in required_options.items():
        if not config.has_section(section):
            return False
        for option in options:
            if not config.has_option(section, option) or config.get(section, option) == '':
                return False

    return True


def config_setup():
    config = configparser.ConfigParser()
    config['mongo-server'] = {
        'url': '',
    }
    config['binance-settings'] = {
        'api-key': '',
        'api-key-salt': '',
        'api-secret': '',
        'api-secret-salt': '',
    }
    config['discord-token'] = {
        'token': '',
    }
    config['other-settings'] = {
        'webhook': '',
        'percent': '',
        'testnet': '',
        'mode': '',
        'default-leverage': '',
        'SL': '',
        'TP': '',
        'TPSL': '',
        'maxtrades': -1,
    }
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def settings(config):
    if check_config(config):
        print("Good, all settings are now saved in the file!")
    else:
        print("Some settings are missing, please check the config.ini file and try again.")
        input("Press any key to continue...")
        settings(config)


def api_setup(config):
    url = api_input("Please copy/paste your MongoDB URL from MongoDB.\n>> ")
    cluster = pymongo.MongoClient(url, tlsCAFile=ca)
    api_key = api_input("Please copy/paste your API key from Binance.\n>> ")
    api_secret = api_input(
        "Please copy/paste your API secret from Binance.\n>> ")

    client = Client(api_key, api_secret, testnet=True)

    passwd = password_input(
        "You need to provide a password to encrypt your API data.\n>> ")
    encrypted_data, salt = save_to_file(passwd, api_key)
    encrypted_secret, salt_secret = save_to_file(passwd, api_secret)

    with open("config.ini", "w") as configfile:
        config["binance-settings"] = {"api-key-salt": salt, "api-key": encrypted_data,
                                     "api-secret-salt": salt_secret, "api-secret": encrypted_secret}
        config["mongo-server"] = {"url": str(url)}
        config.write(configfile)

    print("Saved. Don't forget it or you will lose access to your bot.")
    webhook_setup(config)
    print("\nThe bot will now exit, please restart it.")
    sleep(5)
    exit()


def webhook_setup(config):
    webhook = api_input(
        "Please copy/paste your webhook URL from Discord.\n>> ")
    with open("config.ini", "w") as configfile:
        config["other-settings"] = {"webhook": str(webhook)}
        config.write(configfile)


def start():
    print("Welcome to the Binance Futures Discord bot!")
    print("First, we will need some details about your Discord bot. Can you please copy/paste your bot token?")

    token = api_input(">> ")

    if check_token(token):
        config_setup()
        print("Great, your token is valid!")
    else:
        print("Token is invalid, please try again.")
        start()

    config = configparser.ConfigParser()
    config.read('config.ini')
    settings(config)
    api_setup(config)
    unlock(config)


def unlock():
    print("Please enter your password to unlock the bot.")
    passwd = getpass(">> ")

    try:
        api_key = encrypt_decrypt_helper(passwd.encode(), eval(
            config['binance-settings']['api-key']), eval(config['binance-settings']['api-key-salt']), mode='decrypt')
        api_secret = encrypt_decrypt_helper(passwd.encode(), eval(
            config['binance-settings']['api-secret']), eval(config['binance-settings']['api-secret-salt']), mode='decrypt')
        global client
        client = Client(api_key, api_secret)
        print("Bot unlocked!")

    except Exception as e:
        print("Wrong password, please try again!\n")
        unlock()


if __name__ == '__main__':
    start()
