import datetime
import time
from random import randint
import discord
from discord.ext import commands
import sqlite3
from settings import settings

client = commands.Bot(command_prefix = settings['PREFIX'],intents=discord.Intents.all())
client.remove_command("help")

connection = sqlite3.connect("server.db")
cursor = connection.cursor()

bad_words = []

@client.event
async def on_ready():
    cursor.execute("""CREATE TABLE IF NOT EXISTS users(
        name TEXT,
        id INT,
        cash BIGINT,
        rep INT,
        lvl INT,
        server_id INT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS shop(
        role_id INT,
        id INT,
        cost BIGINT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS badwords(
        bad_word TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS daily(
        user_id INT,
        dat BIGINT
    )""")

    connection.commit()
    for guild in client.guilds:
        for member in guild.members:
            if cursor.execute(f"SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
                cursor.execute(f"INSERT INTO users VALUES ('{member}', {member.id},{0},0,1,{guild.id})")
            else:
                pass
    connection.commit()

    for i in cursor.execute("SELECT * FROM badwords"):
        bad_words.append(i[0])
    print("Bot connected")
    await client.change_presence(status = discord.Status.online, activity=discord.Game('монополию'))

@client.event
async def on_member_join(member):
    if cursor.execute("SELECT id FROM users WHERE id = {member.id}").fetchone() is None:
        cursor.execute("INSERT INTO users VALUES ('{member}', {member.id},{0},0,1,{member.guild.id})")
        connection.commit()
        log("new user: "+member.name)
    else:
        pass

@client.command(aliases=['balance','cash'])
async def __balance(ctx, member: discord.Member = None):
    if member is None:
        await ctx.send(
            embed = discord.Embed(
                description=f"""Баланс пользователя **{ctx.author}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0]} :dollar:**"""
            ))
        await log(ctx.author.name+" узнал свой баланс")
    else:
        await ctx.send(
            embed = discord.Embed(
                description=f"""Баланс пользователя **{member}** составляет **{cursor.execute("SELECT cash FROM users WHERE id = {}".format(member.id)).fetchone()[0]} :dollar:**"""
            ))
        await log(ctx.author.name+" узнал баланс "+member.name)

@client.command(aliases = ['award'])
@commands.has_role("🚔 Police")
async def __award(ctx,member:discord.Member = None, amount: int = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите имя пользователя которому желаете выдать сумму")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму которую вы хотите выдать пользователю")
        elif amount < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 0 :dollar:")
        else:
            cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
            connection.commit()

            await ctx.message.add_reaction("✅")
            await log(ctx.author.name+" начислил "+str(amount)+" долларов пользователю "+member.name)

@client.command(aliases = ['take'])
@commands.has_role("🚔 Police")
async def __take(ctx,member:discord.Member = None, amount: int = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите имя пользователя у которого вы ржелаете забрать сумму")
    else:
        if amount is None:
            await ctx.send(f"**{ctx.author}**, укажите сумму которую вы хотите забрать пользователю")
        elif amount < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 0 :dollar:")
        else:
            cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(amount, member.id))
            connection.commit()

            await ctx.message.add_reaction("✅")
            await log(ctx.author.name+" забрал "+str(amount)+" долларов у пользователя "+member.name)

@client.command(aliases=['add-shop'])
@commands.has_role("zxcmaster")
async def __ad_shop(ctx, role: discord.Role = None, cost: int = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль которую вы желаете внести в магазин")
    else:
        if cost is None:
            await ctx.send(f"**{ctx.author}**, укажите стоимость данной роли")
        elif cost<1:
            await ctx.send(f"**{ctx.author}**, стоимость не может быть меньше 1")
        else:
            cursor.execute("INSERT INTO shop VALUES ({},{},{})".format(role.id,ctx.guild.id,cost))
            connection.commit()

            await ctx.message.add_reaction('✅')
            await log(ctx.author.name+" добавил в магазин роль "+role.name)

@client.command(aliases=['delete-shop'])
@commands.has_role("zxcmaster")
async def __del_shop(ctx, role: discord.Role = None, cost: int = None):
    if role is None:
        await ctx.send(f"**{ctx.author}**, укажите роль которую вы желаете удалить из магазина")
    else:
            cursor.execute("DELETE FROM shop WHERE role_id = {}".format(role.id))
            connection.commit()

            await ctx.message.add_reaction('✅')
            await log(ctx.author.name+" убрал из магазина роль "+role.name)

@client.command(aliases=['shop'])
async def __shop(ctx):
    embed = discord.Embed(title = 'Магазин ролей')

    for row in cursor.execute("SELECT role_id, cost FROM shop WHERE id = {}".format(ctx.guild.id)):
        if ctx.guild.get_role(row[0]) != None:
            embed.add_field(
                name = f'Стоимость {row[1]} :dollar:',
                value = f"Вы приобретете роль {ctx.guild.get_role(row[0]).mention}",
                inline = False
            )
            await log(ctx.author.name+" просмотрел список товаров")
        else:
            pass
    
    await ctx.send(embed = embed)

@client.command(aliases = ['buy','buy-role'])
async def __buy(ctx,role:discord.Role = None):
        if role is None:
            await ctx.send(f"**{ctx.author}**, укажите роль которую вы желаете приобрести")
        else:
            if role in ctx.author.roles:
                await ctx.send(f"**{ctx.author}**, вы уже приобрели данную роль")
            elif cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0] > cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0]:
                await ctx.send(f"**{ctx.author}**, у вас недостаточно средств")
            else:
                await ctx.author.add_roles(role)
                cursor.execute("UPDATE users SET cash = cash - {0} WHERE id = {1}".format(cursor.execute("SELECT cost FROM shop WHERE role_id = {}".format(role.id)).fetchone()[0],ctx.autor.id))
                connection.commit()
                await ctx.message.add_reaction('✅')
                await log(ctx.author.name+" купил роль "+role.name)


@client.command(aliases=['rep','+rep'])
async def __rep(ctx,member: discord.Member = None):
    if member is None:
        await ctx.send(f"**{ctx.author}**, укажите участника сервера")
    else:
        if member.id == ctx.author.id:
            await ctx.send(f"**{ctx.author}**, вы не можете указать самого себя")
        else:
            cursor.execute("UPDATE users SET rep = rep + {} WHERE id = {}".format(1, member.id))
            connection.commit()

            await ctx.message.add_reaction('✅')
            await log(ctx.author.name+" добавил репутацию пользователю "+member.name)

@client.command(aliases=['leader','top'])
async def __leaderboard(ctx):
    embed = discord.Embed(title = 'Топ 10 сервера')
    counter = 0

    for row in cursor.execute("SELECT name, cash FROM users WHERE server_id = {} ORDER BY cash DESC LIMIT 10".format(ctx.guild.id)):
        counter+=1
        embed.add_field(
            name = f'#{counter} | `{row[0]}`',
            value = f'Баланс: {row[1]}',
            inline = False
        )

    await ctx.send(embed = embed)
    await log(ctx.author.name+" вывел таблицу лидеров")

@client.command(aliases=['clear'])
@commands.has_role("🚔 Police")
async def __clear(ctx, amount: int = None):
    if amount == None:
        await ctx.message.channel.purge(limit=101)
        await log(ctx.author.name+" очистил чат на 100")
    else:
        await ctx.message.channel.purge(limit=amount+1)
        await log(ctx.author.name+" очистил чат на "+str(amount))

@client.command(aliases=['kick'])
@commands.has_role("🚔 Police")
async def __kick(ctx, member: discord.Member = None,*, reason = None): 
    await ctx.channel.purge(limit=1)
    if member == None:
        pass
    else:
        await member.kick(reason = reason)
        await ctx.send(f"{member.mention} был кикнут человеком {ctx.author.mention}")
        await member.send(f"Вы были выгнаны с сервера {ctx.guild.name}, пользователем {ctx.author.mention}")
        await log(member.name+" был выгнан пользователем "+ctx.author.name)

@client.command(aliases=['ban'])
@commands.has_role("🚔 Police")
async def __ban(ctx, member: discord.Member = None,*, reason = None): 
    await ctx.channel.purge(limit=1)
    if member == None:
        pass
    else:
        await member.kick(reason = reason)
        await ctx.send(f"{member.mention} был забанен человеком {ctx.author.mention}")
        await member.send(f"Вы были забанены на сервере {ctx.guild.name}, пользователем {ctx.author.mention}")
        await log(member.name+" был забанен пользователем "+ctx.author.name)

@client.command(aliases=['mute'])
@commands.has_role("🚔 Police")
async def __mute(ctx,member: discord.Member = None,minutes: int = 60):
    await ctx.channel.purge(limit = 1)
    if member == None:
        await ctx.send(f"**{ctx.author.mention}**, укажите пользователя котрого хотите замутить")
    else:
        mute_role = discord.utils.get(ctx.message.guild.roles, name="MUTED")
        await member.add_roles(mute_role)
        seconds = minutes*60
        await ctx.send(f"**{member.mention}**, получил ограничение чата за нарушение правил на {minutes} минут. Замутил - **{ctx.author.mention}**")
        await member.send(f"Вы были лишены способности писать и говорить на сервере {ctx.guild.name}, пользователем {ctx.author.mention}")
        await log(member.name+" был замучен пользователем "+ctx.author.name+" на "+minutes+" минут")
        time.sleep(seconds)
        await member.remove_roles(mute_role)

@client.command(aliases = ['help'])
async def __help(ctx):
    embed =  discord.Embed(title = "Список команд")

    embed.add_field(
        name = "{}clear".format(settings['PREFIX']),
        value = "Очищает чат. Внимание! Если не написать число сообщений для удаления - будут удалены 100 сообщений (Только @Police)",
        inline=False
        )
    embed.add_field(
        name = "{}balance/{}cash".format(settings['PREFIX'],settings['PREFIX']),
        value = "Показывает текущий баланс пользователя",
        inline=False
        )
    embed.add_field(
        name = "{}award".format(settings['PREFIX']),
        value = "Дает пользователю монеты (Только @zxcmaster)",
        inline=False
        )
    embed.add_field(
        name = "{}take".format(settings['PREFIX']),
        value = "Забирает у пользователя монеты, штраф (Только @zxcmaster)",
        inline=False
        )
    embed.add_field(
        name = "{}rep/{}+rep".format(settings['PREFIX'],settings['PREFIX']),
        value = "Добавляет одну репутацию пользователю()всем кроме себя",
        inline=False
        )
    embed.add_field(
        name = "{}leader/{}top".format(settings['PREFIX'],settings['PREFIX']),
        value = "Показывает топ самых богатых пользователей сервера",
        inline=False
        )
    embed.add_field(
        name = "{}kick".format(settings['PREFIX']),
        value = "Кикает пользователя(Только @Police)",
        inline=False
        )
    embed.add_field(
        name = "{}ban".format(settings['PREFIX']),
        value = "Банит пользователя(Только @Police)",
        inline=False
        )
    embed.add_field(
        name = "{}shop".format(settings['PREFIX']),
        value = "Показывает все товары в магазине",
        inline=False
        )
    embed.add_field(
        name = "{}add-shop".format(settings['PREFIX']),
        value = "Добавляет роль в магазин(Только @zxcmaster)",
        inline=False
        )
    embed.add_field(
        name = "{}delete-shop".format(settings['PREFIX']),
        value = "Удаляет роль из магазина(Только @zxcmaster)",
        inline=False
        )
    embed.add_field(
        name = "{}buy/{}buy-role".format(settings['PREFIX'],settings['PREFIX']),
        value = "Покупает выбранную роль",
        inline=False
        )
    embed.add_field(
        name = "{}mute".format(settings['PREFIX']),
        value = "Запрещает пользователю писать и говорить на время в минутах(Только @Police)",
        inline=False
        )
    embed.add_field(
        name = "{}help".format(settings['PREFIX']),
        value = "Показывает это сообщение",
        inline=False
        )

    await ctx.send(embed=embed)
    await log(ctx.author.name + " вывел список команд")

@client.command(aliases = ['give','give-money'])
async def __givemoney(ctx,member:discord.Member = None, amount: int = None):
    if member == None:
        await ctx.send(f"**{ctx.author}**, укажите имя пользователя которому хотите перевести деньги")
    else:
        if amount == None:
            await ctx.send(f"**{ctx.author}**, укажите сумму которую вы хотите перевести пользователю")
        elif amount < 1:
            await ctx.send(f"**{ctx.author}**, укажите сумму больше 0 :dollar:")
        else:
            if cursor.execute("SELECT cash FROM users WHERE id = {}".format(ctx.author.id)).fetchone()[0] >= amount:
                cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(amount, member.id))
                cursor.execute("UPDATE users SET cash = cash - {} WHERE id = {}".format(amount, ctx.author.id))
                connection.commit()
                await ctx.message.add_reaction("✅")
                await log(ctx.author.name+" перевел "+str(amount)+" долларов на счет пользователя "+member.name)
            else:
                await ctx.send(f"**{ctx.author}**, у вас нету такой суммы на балансе")


@client.command(aliases = ['daily','everyday'])
async def __daily(ctx):
    datee = datetime.datetime.now()
    datee = int(datee.strftime("%Y%m%d"))
    if cursor.execute("SELECT user_id FROM daily WHERE dat = {}".format(datee)).fetchone() != None:
        await ctx.send(f"**{ctx.author}**, вы уже получили ежедневный бонус сегодня")
    else:
        cursor.execute("INSERT INTO daily VALUES ({},{})".format(ctx.author.id, datee))
        rnd = randint(10,18)
        cursor.execute("UPDATE users SET cash = cash + {} WHERE id = {}".format(rnd,ctx.author.id))
        connection.commit()
        await ctx.send(f"**{ctx.author}**, вы получили {str(rnd)} :dollar:")
        await log(ctx.author.name + " получил ежедневную награду")

@client.command(aliases = ['add-badword'])
@commands.has_role("zxcmaster")
async def __addword(ctx,wordd: str = ""):
    if wordd == None:
        pass
    else:
        for i in cursor.execute("SELECT * FROM badwords").fetchall():
            if wordd == i[0]:
                await ctx.message.add_reaction("❌")
                return
        cursor.execute(f"INSERT INTO badwords VALUES ('{wordd}')")
        connection.commit()
        await ctx.message.add_reaction("✅")
        await log(ctx.author.name+" добавил запрещенное слово: "+wordd)
        bad_words.append(wordd)

@client.command(aliases = ['badwords'])
async def __badwords(ctx):
    embed =  discord.Embed(title = "Список запрещенных слов")
    for i in bad_words:
        embed.add_field(
            name = i,
            value = "#"*len(i)
            )
    await ctx.send(embed = embed)

@client.command(aliases = ['delete-badword'])
@commands.has_role("zxcmaster")
async def __deleteword(ctx,wordd: str = ""):
    if wordd == None:
        pass
    else:
        for i in cursor.execute("SELECT * FROM badwords").fetchall():
            if wordd == i[0]:
                cursor.execute(f"DELETE FROM badwords WHERE bad_word = '{wordd}'")
                connection.commit()
                await ctx.message.add_reaction("✅")
                await log(ctx.author.name+" удалил запрещенное слово: "+wordd)
                bad_words = []
                for i in cursor.execute("SELECT * FROM badwords"):
                    bad_words.append(i[0])
                return
        await ctx.message.add_reaction("❌")
        


@client.command(aliases=['logs'])
#@commands.has_role("zxcmaster")
async def __logs(ctx):
    await log(ctx.author.name+" скачал логи")
    await ctx.channel.purge(limit = 1)
    await ctx.author.send(file = discord.File("logs.txt"))

@client.command(aliases=['db'])
@commands.has_role("zxcmaster")
async def __db(ctx):
    await log(ctx.author.name+" скачал базу данных")
    await ctx.channel.purge(limit = 1)
    await ctx.author.send(file = discord.File("server.db"))

async def log(text: str = "Error"):
    now = datetime.datetime.now()
    now = now.strftime("%Y-%m-%d %H:%M:%S")
    string = "[log]["+now+"]: "+str(text)
    print(string)
    logs = open("logs.txt","a")
    logs.write(string+"\n")
    logs.close()


@client.event
async def on_message(message):
    await client.process_commands(message)
    msg = message.content.lower()
    if not msg.startswith("add-badword") or not msg.startswith("delete-badword"):
        for word in bad_words:
            if word in msg:
                await message.delete()
                await log("deleted message for bad words from user "+str(message.author.name)+" //сообщение: "+message.content)



client.run(settings["TOKEN"])

