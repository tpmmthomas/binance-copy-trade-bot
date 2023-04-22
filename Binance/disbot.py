import datetime
import certifi
import discord
import configparser
import os
from discord.ext import commands
import assist
import bparser
from discord_webhook import DiscordWebhook, DiscordEmbed
from discord.ui import Select, View

locked = True
ca = certifi.where()
client = commands.Bot(command_prefix='.', intents=discord.Intents.all())


def config_get(section, key):
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config[section][key]


def config_set(section, key, value):
    config = configparser.ConfigParser()
    config.read('config.ini')
    config[section][key] = value
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def create_embed(description, color):
    return discord.Embed(description=description, color=color)


@client.event
async def on_ready():
    print("Bot is running.")
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Binance Leaderboard"))
    global db
    import db
    db.freeDB()
    bparser.login()


@client.command()
async def settings(ctx):
    config = configparser.ConfigParser()
    config.read('config.ini')
    fields = [
        ("MongoDB", "mongo-server", "url",
         "You need to set your MongoDB server url first !  `.mongourl [url]`"),
        ("API KEY", "binance-settings", "api-key",
         "You need to set your Binance API key first !  `.apikey [key]`"),
        ("API SECRET", "binance-settings", "api-secret",
         "You need to set your Binance API secret first !  `.apisecret [secret]`"),
        ("Trading Mode", "other-settings", "mode",
         "You need to set your trading mode first !  `.mode [mode]`"),
        ("Webhook", "other-settings", "webhook",
         "You need to set your webhook !  `.webhook [id]`"),
        ("Testnet", "other-settings", "testnet",
         "You need to set your testnet mode first !  `.testnet [true or false]`"),
    ]
    embed = create_embed("Settings 🛠️", 0x4eb120)
    for field in fields:
        value = "✅" if config[field[1]][field[2]] else "❌"
        embed.add_field(
            name=field[0], value=f"{value} {field[3]}", inline=False)
    await ctx.send(embed=embed)


@client.command()
async def setup(ctx):
    embed = discord.Embed(description="Commands 🧪", color=0x34eb8f)
    commands = [("🔹 Add a new trader", "`.add [trader_id]`"),
                ("🔹 Delete trader(s)",
                 "`.delete [choose trader(s) in the list]`"),
                ("🔹 Set leverage for a symbol",
                 "`.leverage [symbol] [leverage]`"),
                ("🔹 Set percent of your balance to trade",
                 "`.setPercent [percent] `"),
                ("🔹 Set default leverage", "`.dLeverage [leverage] `"),
                ("🔹 Set your SL", "`.sl [percent]`"),
                ("🔹 Set your TP", "`.tp [percent]`"),
                ("🔹 Break Even", "`.breakeven [symbol]`"),
                ("🔹 Enable/Disable TP/SL", "`.tpsl [True or False]`"),
                ("🔹 See your FUTURES balance", "`.balance`"),
                ("🔹 See your performances", "`.stats`"),
                ("🔹 See your current trades", "`.current`"),
                ("🔹 Set maximum simultaneous trades ",
                 "`.maxtrades [number]`"),
                ("🔹 Modify settings", "`.settings`"),
                ("🔹 Stop the bot", "`.stop`")]

    for name, value in commands:
        embed.add_field(name=name, value=value, inline=False)

    embed.timestamp = datetime.datetime.utcnow()

    await ctx.send(embed=embed)


async def delete_traders_callback(interaction, traders_to_remove, ctx):
    await interaction.response.defer()
    new_embed = discord.Embed(description=db.deleteTraders(traders_to_remove))
    await ctx.send(embed=new_embed)


class TradersRemoveMenu(Select):
    def __init__(self, options, ctx):
        super().__init__(
            placeholder="Trader(s) to remove",
            options=options,
            max_values=len(options),
            min_values=1
        )
        self.ctx = ctx

    async def callback(self, interaction):
        await delete_traders_callback(interaction, self.values, self.ctx)


@client.command()
async def maxtrades(ctx, *, arg):
    if not arg.isnumeric():
        await ctx.send("❌ Oops, please enter a good value !")
        return
    update_config("other-settings", "maxtrades", arg)
    await ctx.send(f"✅ Maximum simultaneous trades is now {arg} !")


@client.command()
async def tpsl(ctx, *, arg):
    tp_percent = config_get("other-settings", "TP")
    sl_percent = config_get("other-settings", "SL")
    if not tp_percent or not sl_percent:
        await ctx.send("❌ Oops, you need to set your TP and SL first !")
        return
    if arg not in ["True", "False"]:
        await ctx.send("❌ Oops, please enter a good value 'True' or 'False' !")
        return
    update_config("other-settings", "TPSL", arg)
    await ctx.send("✅ TP/SL is now activated !" if arg == "True" else "✅ TP/SL is now deactivated !")


@client.command()
async def delete(ctx):
    traders = db.getTraders()
    if not traders:
        await ctx.send("❌ Oops, you don't have any traders yet !")
        return
    remove_menu = TradersRemoveMenu(
        options=[discord.SelectOption(
            value=trader, label=f"{trader}") for trader in traders[1]],
        ctx=ctx
    )
    view = View()
    view.add_item(remove_menu)
    await ctx.send(view=view)


@client.command()
async def stop(ctx):
    await ctx.send("❌ Bot is stopping, you will need to restart it manually.")
    await client.close()


@client.command()
async def current(ctx):
    trades = bparser.getCurrentTrade()
    if not trades:
        await ctx.send("❌ Oops, you don't have any current trade !")
        return

    embed = create_embed("💤 Current Trades", 0x6fa8dc)

    if isinstance(trades, dict) and len(trades) == 15:
        profit = round(float(trades['unRealizedProfit']), 3)
        embed.add_field(name=trades["symbol"],
                        value=f"Profit: {profit}", inline=False)
    elif isinstance(trades, list):
        for trade in trades:
            profit = round(float(trade['unRealizedProfit']), 3)
            embed.add_field(name=trade["symbol"],
                            value=f"Profit: {profit}", inline=False)
    await ctx.send(embed=embed)


def update_config(section, key, value):
    config = configparser.ConfigParser()
    config.read('config.ini')
    config[section][key] = value
    with open('config.ini', 'w') as configfile:
        config.write(configfile)


def is_valid_number(arg):
    if not arg.isdigit():
        return False
    return True


@client.command()
async def breakeven(ctx, *, arg):
    if not bparser.isSymbolValid(arg):
        await ctx.send("❌ Oops, symbol is not valid! Please use the format: BTCUSDT, ETHUSDT, etc...")
        return
    else:
        be = bparser.setBreakEven(arg)
        if be == True:
            await ctx.send(f"✅ SL moved to break even for {arg} pair !")
        else:
            await ctx.send(f"❌ Oops, something went wrong !")


@client.command()
async def leverage(ctx, *, arg):
    arg = arg.split()
    if len(arg) != 2:
        await ctx.send("❌ Oops, you need to specify a symbol and a leverage!")
        return
    symbol, leverage = arg
    if await is_valid_number(leverage):
        if not bparser.isSymbolValid(symbol):
            await ctx.send("❌ Oops, symbol is not valid! Please use the format: BTCUSDT, ETHUSDT, etc...")
            return
        if not bparser.isLeverageValid(symbol, leverage):
            await ctx.send(f"❌ Oops, leverage is not valid for {symbol}!")
            return
        db.setLeverage(symbol, leverage)
        await ctx.send(f"✅ Leverage for {symbol} set to {leverage}x!")


@client.command()
async def stats(ctx):
    incomes = bparser.stats()
    embed = discord.Embed(description="Stats 📊", color=0x34eb8f)
    timeframes = ["1 day", "7 days", "30 days"]

    for timeframe, income in zip(timeframes, incomes):
        embed.add_field(name=timeframe, value=f"`{income} USDT`", inline=True)

    await ctx.send(embed=embed)


@client.command()
async def balance(ctx):
    values = bparser.aBalance()
    embed = discord.Embed(title="Balances 💰", color=0xebb734)
    for symbol, balance in values.items():
        embed.add_field(
            name=symbol, value=f"{round(float(balance), 2)}", inline=False)
    embed.timestamp = datetime.datetime.utcnow()
    await ctx.send(embed=embed)


@client.command()
async def dLeverage(ctx, *, arg):
    if is_valid_number(arg):
        update_config('other-settings', 'default-leverage', arg)
        await ctx.send(f" ✅ Default leverage set to {arg}!")
    else:
        await ctx.send("❌ Oops, please enter a good value !")


@client.command()
async def tp(ctx, *, arg):
    if is_valid_number(arg):
        update_config('other-settings', 'tp', arg)
        await ctx.send(f"✅ TP set to {arg}%!")
    else:
        await ctx.send("❌ Oops, please enter a good value !")


@client.command()
async def sl(ctx, *, arg):
    if is_valid_number(arg):
        update_config('other-settings', 'sl', arg)
        await ctx.send(f"✅ SL set to {arg}%!")
    else:
        await ctx.send("❌ Oops, please enter a good value !")


@client.command()
async def mongourl(ctx, *, arg):
    update_config('other-settings', 'mongo-url', arg)
    await ctx.send("✅ MongoDB server url set !")


@client.command()
async def setPercent(ctx, *, arg):
    if is_valid_number(arg) and 1 <= int(arg) <= 100:
        update_config('other-settings', 'percent', arg)
        await ctx.send(f"✅ Percent set to {arg}%!")
    else:
        await ctx.send("❌ Oops, please enter a good value !")


async def send_embed(ctx, description):
    new_embed = discord.Embed(description=description)
    await ctx.send(embed=new_embed)


@client.command()
async def add(ctx, *, arg):
    followTraderQuery = db.followTrader(arg)
    await send_embed(ctx, followTraderQuery)


async def update_setting(ctx, key, value):
    update_config('binance-settings', key, value)
    await ctx.send(f"✅ Binance {key.replace('-', ' ')} set!")


@client.command()
async def apikey(ctx, *, arg):
    await update_setting(ctx, 'api-key', arg)


@client.command()
async def apisecret(ctx, *, arg):
    await update_setting(ctx, 'api-secret', arg)


@client.command()
async def mode(ctx, *, arg):
    update_config('other-settings', 'mode', arg)
    await ctx.send(f"✅ Trading mode set to: {arg}!")


@client.command()
async def testnet(ctx, *, arg):
    update_config('other-settings', 'testnet', arg)
    await ctx.send("✅ Testnet mode set!")


def webhook_start(title, side, symbol, orderid, quantity, leverage, entryPrice, color):
    webhook_url = config_get('other-settings', 'webhook')
    webhook = DiscordWebhook(url=webhook_url)
    embed = DiscordEmbed(title=title, color=color)
    embed.set_footer(text='Binance Trade Bot',
                     icon_url="https://imgur.com/hLBQTYI.png")
    embed.set_timestamp()
    fields = [('Side', side), ('Symbol', symbol), ('Quantity', quantity), ('Leverage',
                                                                           leverage), ('Entry Price', entryPrice), ('Order ID', (str(orderid)))]
    for name, value in fields:
        embed.add_embed_field(name=name, value=f'`{value}`')
    webhook.add_embed(embed)
    response = webhook.execute()


def webhook_end(title, symbol, leverage, entryPrice, exitPrice, data, color):
    webhook_url = config_get('other-settings', 'webhook')
    entryPrice = round(float(entryPrice), 2)
    exitPrice = round(float(exitPrice), 2)
    webhook = DiscordWebhook(url=webhook_url)
    embed = DiscordEmbed(title=title, color=color)
    embed.set_footer(text='Binance Trade Bot',
                     icon_url="https://imgur.com/hLBQTYI.png")
    embed.set_timestamp()
    fields = [('Symbol', symbol), ('Leverage', leverage), ('Entry Price', entryPrice),
              ('Exit Price', exitPrice), ('PnL', f'{data[0]} {symbol[-4:]}'), ('ROE %', f'{data[1]}%')]
    for name, value in fields:
        embed.add_embed_field(name=name, value=f'`{value}`')
    webhook.add_embed(embed)
    response = webhook.execute()


def get_webhook_url():
    config = configparser.ConfigParser()
    config.read('config.ini')
    return config['other-settings']['webhook']


def webhook_infos(title, side, symbol, orderid, quantity, leverage, percent, color):
    webhook = DiscordWebhook(url=get_webhook_url())
    embed = DiscordEmbed(title=title, color=color)
    embed.set_footer(text='Binance Trade Bot',
                     icon_url="https://imgur.com/hLBQTYI.png")
    embed.set_timestamp()
    fields = [
        ('Side', side),
        ('Symbol', symbol),
        ('Quantity', quantity),
        ('Leverage', leverage),
        ('Percent', f"{percent}%"),
        ('Order ID', f"||{orderid}||")
    ]
    for name, value in fields:
        embed.add_embed_field(name=name, value=f"`{value}`")
    webhook.add_embed(embed)
    response = webhook.execute()


def webhook_error(reason, symbol):
    webhook = DiscordWebhook(url=get_webhook_url())
    embed = DiscordEmbed(
        title="⚠️ Error, please verify your trades !", color='fc9d03')
    embed.set_footer(text='Binance Trade Bot',
                     icon_url="https://imgur.com/hLBQTYI.png")
    embed.set_timestamp()
    embed.set_description(f"{reason} for: {symbol}")
    webhook.add_embed(embed)
    response = webhook.execute()


def starter():
    if os.path.exists('config.ini'):
        assist.unlock()
        token = config_get('discord-token', 'token')
        client.run(token, log_handler=None)
    else:
        assist.start()


if __name__ == "__main__":
    starter()
