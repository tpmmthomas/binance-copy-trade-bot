import telebot

def start():
    print("Welcome to the Bybit Telegram bot! \n")
    print("First, we will need some details about your Telegram bot. Can you please copy/paste your BotFather bot token?")
    token_check()
    print("\nIt's time to setup the bot. Please fill the file credentials.py with your data. Then press Enter here.")
    input(">>")
    print("\nNow, you can start the bot with python -m app.ct_main and python -m app.tgb_main ! \n")
    input("Press any key to continue...")
    exit()



def token_check():
    token = input(">> ")
    try:
        check_token = telebot.TeleBot(token)
        print("Good, your token is valid! Bot name : " + check_token.get_me().first_name + "\n")
        print("\nNow, you can setup the commands. Please send /setcommands to your botFhater and copy/paste the commands in telegram-commands.txt file. Then press Enter here.")
        input(">> ")
    except:
        print("Your token is not valid, please try again.")
        token_check()
