# binance-copy-trade-bot  

> [!IMPORTANT]  
> The bot is now rebranded to TraderCloneX, and is available as a service so that you do not need to run the server on your own!!! You could make use our hosted telegram server and make trades directly without worrying about technical details. Please make a registration here: <https://forms.gle/98SpxWP7BgjCbxe47>. We will provide you with detailed instructions on how to onboard the service soon.

## Running the bot on your own

This program uses web scraping to monitor the positions opened by traders sharing their positions on Binance Futures Leaderboard. We then mimic the trade in your account using the Bybit api. MongoDB is the database used in this software.

### Environment setup (Recommended)

#### Using Conda

At your target directory, execute the following:

```bash
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
2. Fill in the required fields in  `app/data/credentials.py`
3. Run `python copy_trade_backend/ct_main.py` and `python telegram_frontend/tgb_main.py`. It is suggested to set both up as a systemctl service, with restart=always and a MaxRunTime so that the program is automatically restarted from time to time.
4. Call `/addcookie` to add credentials required for api end-points every 2-3 days. I will not teach you how to do so here, but you can find the information on the internet.

### Using the software

After the python programs are up and running, go to your telegram bot and type /start, then follow the instructions.  
It should be rather straightforward but if you encounter any uncertainties, please report it to me by raising an issue.  
Refer to the file telegram-commands.txt for a list of commands you can use.  
I personally suggest you go to the binance leaderboard, pick a longer timespan (e.g. monthly or all-time) and choose the top traders sharing their positions.  

### Disclaimer

- Users are solely responsible for their own trading decisions and the management of their accounts. TraderCloneX is not a financial advisor, and any information provided by the bot should not be taken as financial advice. Users should conduct their own due diligence and consider seeking advice from an independent financial advisor.
- TraderCloneX does not accept any liability for loss or damage as a result of reliance on the information contained within this bot. Please be fully informed regarding the risks and costs associated with trading the financial markets. While we strive to ensure our service is both fast and reliable, TraderCloneX cannot guarantee the uptime or data accuracy of the service. Access to the bot during the launch phase is limited to users who sign up using our Bybit referral link, and this condition may be subject to change in the future.
- By using TraderCloneX, you acknowledge and agree that you have read, understood, and accept the full terms of this disclaimer. You agree that all use of the TraderCloneX service is at your own risk, and you are fully responsible for any resulting profits or losses.
- Remember that trading can lead to losses that exceed initial investments. Therefore, you should not trade with capital that you cannot afford to lose. If you have any doubts, it is advisable to seek advice from an independent financial advisor.


### Buy Me A Coffee

Donations are welcome at the following addresses (updated Feb 2024):  
BTC: bc1qyacynkmdctszja7zjzw2da50jv8wcltcxxz995  
ETH / ERC20 tokens in general: 0xcF7D346C0A139DDaE79aed9e9a09bef0D61d1509
