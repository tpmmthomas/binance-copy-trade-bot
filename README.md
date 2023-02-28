# binance-copy-trade-bot 

This program uses web scraping to monitor the positions opened by traders sharing their positions on Binance Futures Leaderboard. We then mimic the trade in your account using the Bybit api. MongoDB is the database used in this software.

### Current Limitations of the program (Contributions are Welcome)
1. Supports Only Bybit for actual trading (This is because the author is based in Hong Kong where Binance usage are restricted.)
2. Telegram python program hangs from time to time (No idea why.)
3. THe code isn't exactly at its cleanest state (I'm sorry! This is a one person project and I have other jobs.)


### Environment setup (Recommended)

#### Using Conda
At your target directory, execute the following:   
```
conda create -n trading python=3.9 -y
conda activate trading
git clone https://github.com/tpmmthomas/binance-copy-trade-bot.git
cd binance-copy-trade-bot
pip install -r requirements.txt
```

### Database Setup
Follow the instructions in https://www.mongodb.com/docs/manual/tutorial/install-mongodb-on-ubuntu/ to set up MongoDB on the same host where the program is run.  
Follow https://www.digitalocean.com/community/tutorials/how-to-secure-mongodb-on-ubuntu-20-04 to set up username and password.  

### Software setup 
1. Setup a telegram bot using `Botfather` (details on telegram official site) and mark the access token.
2. Set commands of the bot in `Botfather` by copy and pasting the commands in `telegram-commands.txt`
3. Fill in the required fields in  `app/data/credentials.py ` () 
4. Run `python -m app.ct_main` and `python -m app.tgb_main`. It is suggested to set both up as a systemctl service, with restart=always and a MaxRunTime so that the program is automatically restarted from time to time. A template service file is located at `template.service`, that needs to be adjusted according to your runtime environment.

### Using the software
After the python programs are up and running, go to your telegram bot and type /start, then follow the instructions.  
It should be rather straightforward but if you encounter any uncertainties, please report it to me by raising an issue.  
Refer to the file telegram-commands.txt for a list of commands you can use.  
I personally suggest you go to the binance leaderboard, pick a longer timespan (e.g. monthly or all-time) and choose the top traders sharing their positions.  

### Warnings
No tests or code-review have been done. It is NOT bug-free. Unexpected scenarios may occur. Use it with extreme caution and check the status of the running programs often. You are welcome to report any errors to me by raising an issue.


### Disclaimer
This software is for non-commercial purposes only. Do not risk money which you are afraid to lose.  

USE THIS SOFTWARE AT YOUR OWN RISK. THE AUTHORS ASSUME NO RESPONSIBILITY FOR YOUR TRADING RESULTS.     

Start by running backtesting of the bot first. Do not engage money before you understand how it works and what profit/loss you should expect.  


### Buy Me A Coffee
You could support my developement by using my refferal code at Bybit Trading platform. I highly recommend it.
https://www.bybit.com/en-US/invite?ref=L9QLLJ  


Donations are also welcome at the following addresses:

BTC: bc1qx9sldvfqsggajdhc24pvflcyl5x4lrc75303xq
USDT (ERC20/BSC): 0xb5bb89624842E3De8FC9e5F6dC2b3951d91f7dBa
ATOM: cosmos132v3ud437dvelw79xhe3pnned7nrzkvy8cespd
