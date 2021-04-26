import datetime

import schedule

import time
from multiprocessing.context import Process
import sqlite3

from perfectmoney import PerfectMoney
from telebot import TeleBot, types
from config import token, admin_link, db_name, information
from config import admin_id, admin_password, admin_token, admin_account, admin_chat_id

bot = TeleBot(admin_token)

withdraw_lst = []

bot = TeleBot(token)
ref_link = 'https://telegram.me/{}?start={}'

kb = types.ReplyKeyboardMarkup(True)
kb.row('💠 Чат', '🖥 Кабинет')
kb.row('🏛 Фонд', 'ℹ️Информация')


@bot.message_handler(commands=['start'])
def start(message):
    if message.chat.id == admin_chat_id:
        bot.send_message(message.chat.id, 'Для получения статистики о запросах на снятие средств /get_requests')
    user_id = int(message.chat.id)
    name = message.from_user.first_name
    second_name = message.from_user.last_name
    try:
        parent_id = int(message.text.split()[1])
    except IndexError as e:
        parent_id = 0

    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    sql = """SELECT * from users"""
    cursor.execute(sql)
    records = cursor.fetchall()
    users_ids = [row[1] for row in records]
    if parent_id in users_ids:
        if not user_id in users_ids:
            sql = """INSERT INTO users (user_id, parent_id, name, second_name, balance, gain, for_withdrawal) 
            VALUES ({user_id}, {parent_id}, '{name}', '{second_name}', 0, 0, 0)""" \
                .format(id=len(users_ids) + 1, user_id=user_id, parent_id=parent_id, name=name, second_name=second_name)
            cursor.execute(sql)
            sqlite_connection.commit()
    else:
        sql = """INSERT INTO users (user_id, parent_id, name, second_name, balance, gain, for_withdrawal) 
        VALUES ({user_id}, {parent_id}, '{name}', '{second_name}', 0, 0, 0)""" \
            .format(id=len(users_ids) + 1, user_id=user_id, parent_id=0, name=name, second_name=second_name)

        cursor.execute(sql)
        sqlite_connection.commit()
    bot.send_message(message.from_user.id, information, reply_markup=kb)


@bot.message_handler(commands=['get_requests'])
def get_requests(message):
    user_id = message.chat.id
    print(user_id)
    if user_id == admin_chat_id:
        global withdraw_lst
        sqlite_connection = sqlite3.connect(db_name)
        cursor = sqlite_connection.cursor()
        sql = """SELECT for_withdrawal, user_id FROM users"""
        data = cursor.execute(sql).fetchall()
        for_withdrawal = [float(i[0]) for i in data]
        users_ids = [i[1] for i in data]
        pm_ids = []
        s = 0

        for i in range(len(users_ids)):
            if for_withdrawal[i] == 0:
                pm_ids.append('void')
            else:
                pm_id = cursor.execute(f"""SELECT pm_id FROM pm_ids where user_id is {users_ids[i]}""").fetchall()[0][0]
                bot.send_message(message.chat.id, 'Вывод запросил пользователь №' + str(users_ids[i])
                                       + ' на сумму ' + str(for_withdrawal[i]) + '\n' + 'Его PerfectMoney ID ' + pm_id)
                pm_ids.append(pm_id)
                s += for_withdrawal[i]
        kb_inline = types.InlineKeyboardMarkup()
        kb_inline.row(types.InlineKeyboardButton(text='Да', callback_data='confirm'),
                      types.InlineKeyboardButton(text='Отмена', callback_data='cancel'))
        bot.send_message(message.chat.id, 'Итого: ' + str(s) + '\n' + 'Оплатить?', reply_markup=kb_inline)
        withdraw_lst = [(pm_ids[i], for_withdrawal[i]) for i in range(len(for_withdrawal)) if pm_ids[i] != 'void']


@bot.message_handler(commands=['invest'])
def choose_sum_to_fund(message):
    user_id = message.chat.id
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                 {user_id}"""
                             .format(user_id=user_id)).fetchall()[0][0]
    try:
        sum_to_fund = int(message.text.split()[1])
        if sum_to_fund < 0:
            raise Exception
    except Exception as e:
        bot.send_message(user_id, 'Введите натуральное число')
        return
    if sum_to_fund >= balance:

        kb_inline = types.InlineKeyboardMarkup()
        kb_inline.row(types.InlineKeyboardButton(text='Да', callback_data='confirmed'),
                      types.InlineKeyboardButton(text='Отмена', callback_data='cancel'))
        bot.send_message(user_id, 'Сумма инвестиции превышает или равна вашем балансу. Вы уверены, что хотите '
                                  'инвестировать все средства?' + '\n' +
                         'Вернуть их на баланс можно будет только через месяц', reply_markup=kb_inline)

    else:
        sql = """SELECT * from funds"""
        cursor.execute(sql)
        data = cursor.fetchall()
        sql = """INSERT INTO funds (owner_id, size, date) 
                                            VALUES ({owner_id}, {size}, '{date}')""" \
            .format(id=len(data) + 1, owner_id=user_id, size=sum_to_fund, date=datetime.datetime.now())

        cursor.execute(sql)
        sqlite_connection.commit()
        sql = """UPDATE users SET balance={balance} WHERE user_id is {user_id}""" \
            .format(balance=balance - sum_to_fund, user_id=user_id)

        cursor.execute(sql)
        sqlite_connection.commit()
        bot.send_message(user_id, 'Создан новый вклад на ' + str(sum_to_fund))


@bot.message_handler(commands=['new_pm_id'])
def new_pm_id(message):
    user_id = message.chat.id
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    try:
        text = message.text.split()
        pm_id = text[1]
    except Exception as e:
        bot.send_message(user_id, 'Введите корректный id')
        return
    sql = """SELECT pm_id FROM pm_ids WHERE user_id is {user_id}""".format(user_id=user_id)
    current_pm_id = cursor.execute(sql).fetchall()
    if len(current_pm_id) == 0:
        sql = """SELECT * from pm_ids"""
        cursor.execute(sql)
        records = cursor.fetchall()
        sql = """INSERT INTO pm_ids (user_id, pm_id) 
                    VALUES ({user_id}, '{pm_id}')""" \
            .format(user_id=user_id, pm_id=pm_id)
        cursor.execute(sql)
        sqlite_connection.commit()

        bot.send_message(user_id, 'Ваш PerfectMoney счёт успешно сохранён')
    else:
        sql = """UPDATE pm_ids SET pm_id = '{pm_id}' where user_id is {user_id}""" \
            .format(pm_id=pm_id, user_id=user_id)
        cursor.execute(sql)
        sqlite_connection.commit()
        bot.send_message(user_id, 'Ваш PerfectMoney счёт успешно изменён')


@bot.message_handler(commands=['withdraw'])
def choose_sum_to_withdraw(message):
    user_id = message.chat.id
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    try:
        sql = """SELECT pm_id FROM pm_ids WHERE user_id is 
                                         {user_id}""".format(user_id=user_id)
        pm_id = cursor.execute(sql).fetchall()[0][0]


    except Exception as e:
        bot.send_message(user_id, 'Введите название своего Perfect Money командой /new_pm_id' + '\n'
                         +
                         'Например, /new_pm_id U14228880')
        return
    balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                     {user_id}"""
                             .format(user_id=user_id)).fetchall()[0][0]
    try:
        sum_to_withdraw = float(message.text.split()[1])

        if sum_to_withdraw < 0:
            raise Exception
    except Exception as e:
        bot.send_message(user_id, 'Введите натуральное число')
        return
    if sum_to_withdraw >= balance:

        kb_inline = types.InlineKeyboardMarkup()
        kb_inline.row(types.InlineKeyboardButton(text='Да', callback_data='confirm_withdraw'),
                      types.InlineKeyboardButton(text='Отмена', callback_data='cancel'))
        bot.send_message(user_id, 'Сумма запрошенных средств на снятие превышает или равна вашем балансу. '
                                  'Вы уверены, что хотите '
                                  'снять все средства?', reply_markup=kb_inline)

    else:
        sql = """UPDATE users SET balance={balance} WHERE user_id is {user_id}""" \
            .format(balance=balance - sum_to_withdraw, user_id=user_id)
        cursor.execute(sql)
        current_withdraw = int(cursor.execute(
            """SELECT for_withdrawal FROM users WHERE user_id is {user_id}""".format(user_id=user_id)).fetchall()[0][0])
        sql = """UPDATE users SET for_withdrawal = (SELECT for_withdrawal 
        FROM users WHERE user_id is {user_id}) + {withdraw} WHERE user_id is {user_id}""".format(
            withdraw=current_withdraw + sum_to_withdraw * 0.98, user_id=user_id)
        cursor.execute(sql)
        sqlite_connection.commit()
        bot.send_message(user_id, 'Запрошен перевод на ' + str(sum_to_withdraw))


@bot.message_handler(content_types=['text'])
def messages_works(message):
    if message.text == '🖥 Кабинет':
        cabinet(message)
    if message.text == '💠 Чат':
        chat(message)
    if message.text == '🏛 Фонд':
        fund(message)
    if message.text == 'ℹ️Информация':
        info(message)


@bot.callback_query_handler(func=lambda call: True)
def callback_worker(call):
    if call.data == 'confirmed':
        user_id = call.message.chat.id
        sqlite_connection = sqlite3.connect(db_name)
        cursor = sqlite_connection.cursor()
        sql = """SELECT * from funds"""
        cursor.execute(sql)
        data = cursor.fetchall()
        balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                     {user_id}"""
                                 .format(user_id=user_id)).fetchall()[0][0]
        sql = """UPDATE users SET balance={balance} WHERE user_id is {user_id}""" \
            .format(balance=balance - balance, user_id=user_id)
        cursor.execute(sql)
        sqlite_connection.commit()
        sql = """INSERT INTO funds ( owner_id, size, date) 
                                                    VALUES ({owner_id}, {size}, '{date}')""" \
            .format(owner_id=user_id, size=balance, date=datetime.datetime.now())

        cursor.execute(sql)
        sqlite_connection.commit()
        bot.send_message(user_id, 'Создан новый вклад на ' + str(balance))
    elif call.data == 'canceled':
        pass
    if call.data == 'confirm_withdraw':
        user_id = call.message.chat.id
        sqlite_connection = sqlite3.connect(db_name)
        cursor = sqlite_connection.cursor()
        balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                             {user_id}"""
                                 .format(user_id=user_id)).fetchall()[0][0]
        sql = """UPDATE users SET balance={balance} WHERE user_id is {user_id}""" \
            .format(balance=balance - balance, user_id=user_id)
        cursor.execute(sql)
        sqlite_connection.commit()
        current_withdraw = int(cursor.execute(
            """SELECT for_withdrawal FROM users WHERE user_id is {user_id}""".format(user_id=user_id)).fetchall()[0][0])
        sql = """UPDATE users SET for_withdrawal={withdraw} where user_id is {user_id}""".format(
            withdraw=current_withdraw + balance * 0.98, user_id=user_id)
        cursor.execute(sql)
        sqlite_connection.commit()
        bot.send_message(user_id, 'Запрошен перевод на ' + str(balance))
    elif call.data == 'canceled':
        pass
    if call.data == 'deposit':
        deposit(call.message)
    if call.data == 'ref_link':
        get_my_ref(call.message)
    if call.data == 'invest':
        invest(call.message)
    if call.data == 'new_fund':
        new_fund(call.message)
    if call.data == 'withdraw':
        withdraw(call.message)
    if call.data == 'to_ballance':
        user_id = call.message.chat.id
        sqlite_connection = sqlite3.connect(db_name)
        cursor = sqlite_connection.cursor()
        data = cursor.execute("""SELECT size, date, id FROM funds WHERE owner_id is {owner_id}"""
                              .format(owner_id=user_id)).fetchall()
        dates = [datetime.datetime.strptime(i[1].split()[0], '%Y-%m-%d').date() for i in data]
        funds = [i[0] for i in data]
        ids = [i[2] for i in data]
        today = datetime.datetime.now()
        s = 0
        for i in range(len(funds)):
            if (dates[i] - today).days >= 30:
                s += int(funds[i])
                sql = """DELETE from funds WHERE id is {id}""".format(
                    id=ids[i])
                cursor.execute(sql)
                sqlite_connection.commit()
        bot.send_message(user_id, 'Выведено на баланс ' + str(s))
    if call.message.chat.id == admin_chat_id:
        global withdraw_lst
        if call.data == 'confirm':
            for i in withdraw_lst:
                pm = PerfectMoney(str(admin_account), admin_password)
                print(admin_id)
                res = pm.spend(admin_id, i[0], i[1])
                if pm.error:
                    print(pm.error)
                    bot.send_message(call.message.chat.id, 'Произошла ошибка при оплате' + '\n' + pm.error)

                    continue
                user_id = call.message.chat.id
                sqlite_connection = sqlite3.connect(db_name)
                cursor = sqlite_connection.cursor()
                sql = f"""UPDATE users SET for_withdrawal = 0 WHERE user_id is {user_id}"""
                cursor.execute(sql)
                sqlite_connection.commit()
            withdraw_lst = []

        else:
            pass


def cabinet(message):
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    user_id = int(message.chat.id)
    data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                          .format(parent_id=user_id)).fetchall()

    kb_inline = types.InlineKeyboardMarkup()
    kb_inline.row(types.InlineKeyboardButton(text='📥 Пополнить', callback_data='deposit'),
                  types.InlineKeyboardButton(text='📤 Вывести', callback_data='withdraw'))
    kb_inline.row(types.InlineKeyboardButton(text='➡️ Инвестировать', callback_data='invest'))
    kb_inline.row(types.InlineKeyboardButton(text='🔗 Партнёрская ссылка', callback_data='ref_link'))
    if len(data) > 0:
        level1 = [i[0] for i in data]
        level1 = [j[0][0] + ' ' + j[0][1] for j in
                  [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                                  .format(user_id=i)).fetchall() for i in level1]]
    else:
        level1 = []
    funds = [i[0] for i in cursor.execute("""SELECT size FROM funds WHERE owner_id is {user_id}"""
                                          .format(user_id=user_id)).fetchall()]

    if len(cursor.execute("""SELECT name FROM users WHERE user_id is 
                         (SELECT parent_id FROM users WHERE user_id is {user_id})"""
                                  .format(user_id=user_id)).fetchall()) > 0:
        bot.send_message(message.from_user.id,
                         '🖥 Кабинет' + '\n' + '🆔 Ваш ID: ' + str(user_id) + '\n' +
                         '🙎‍♂️Пригласитель: ' +
                         cursor.execute("""SELECT name FROM users WHERE user_id is 
                             (SELECT parent_id FROM users WHERE user_id is {user_id})"""
                                        .format(user_id=user_id)).fetchall()[0][0] + '\n' +
                         '👬 Лично приглашённые: ' + str(len(level1)) + '\n' +
                         '📈 Заработано: ' + str(cursor.execute("""SELECT gain FROM users WHERE user_id is 
                                     {user_id}"""
                                                                .format(user_id=user_id)).fetchall()[0][0]) + '\n' +
                         'Инвестировано ' + str(sum(funds)) + '\n' +
                         '💵 Баланс: ' + str(cursor.execute("""SELECT balance FROM users WHERE user_id is 
                             {user_id}"""
                                                            .format(user_id=user_id)).fetchall()[0][0]),
                         reply_markup=kb_inline

                         )
    else:
        bot.send_message(message.from_user.id,
                         '🖥 Кабинет' + '\n' + '🆔 Ваш ID: ' + str(user_id) + '\n' +
                         '🙎‍♂️Пригласитель: ' +
                         'Отсутсвует' + '\n' +
                         '👬 Лично приглашённые: ' + str(len(level1)) + '\n' +
                         '📈 Заработано: ' + str(cursor.execute("""SELECT gain FROM users WHERE user_id is 
                                     {user_id}"""
                                                                .format(user_id=user_id)).fetchall()[0][0]) + '\n' +
                         'Инвестировано: ' + str(sum(funds)) + '\n' +
                         '💵 Баланс: ' + str(cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                     {user_id}"""
                                                            .format(user_id=user_id)).fetchall()[0][0]),
                         reply_markup=kb_inline
                         )


def chat(message):
    bot.send_message(message.from_user.id, 'По вопросам технической поддержки:' + '\n' + 'Admin: ' + admin_link)


def fund(message):
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    bot.send_message(message.from_user.id, '📈 Уже '
                     + str(sum([i[0] for i in cursor.execute("""SELECT gain FROM users""").fetchall()]))
                     + ' рублей было заработано пользователями проекта')


def info(message):
    bot.send_message(message.from_user.id, information)


def invest(message):
    user_id = message.chat.id
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    data = cursor.execute("""SELECT size, date FROM funds WHERE owner_id is {owner_id}"""
                          .format(owner_id=user_id)).fetchall()

    if len(data) == 0:
        kb_inline = types.InlineKeyboardMarkup()
        kb_inline.row(types.InlineKeyboardButton(text='📥 Создать вклад', callback_data='new_fund'))
        bot.send_message(user_id, 'Нет текущих вкладов', reply_markup=kb_inline)
    else:

        kb_inline = types.InlineKeyboardMarkup()
        kb_inline.row(types.InlineKeyboardButton(text='📥 Создать вклад', callback_data='new_fund'))
        bot.send_message(user_id, 'Текущие вклады: ', reply_markup=kb_inline)

        dates = [datetime.datetime.strptime(i[1].split()[0], '%Y-%m-%d').date() for i in data]
        funds = [i[0] for i in data]
        today = datetime.datetime.now()
        s = 0
        for i in range(len(funds)):
            delta = today.day + today.month * 30 + today.year * 365 - \
                    dates[i].day - dates[i].month * 30 - dates[i].year * 365
            if delta >= 30:
                s += int(funds[i])
        if s:
            kb_inline2 = types.InlineKeyboardMarkup()
            kb_inline2.row(types.InlineKeyboardButton(text='Вернуть на баланс', callback_data='to_balance'))
            bot.send_message(user_id, 'Вы можете вернуть на баланс ' + str(s), reply_markup=kb_inline2)


def new_fund(message):
    user_id = message.chat.id
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                             {user_id}"""
                             .format(user_id=user_id)).fetchall()[0][0]
    bot.send_message(user_id, 'Напишите команду /invest и введите сумму, которую хотите положить' + '\n' +
                     'Например, /invest 50' + '\n'
                                              '💵 Баланс: ' + str(balance))


def get_my_ref(message):
    bot_name = bot.get_me().username
    user_id = int(message.chat.id)
    bot.send_message(user_id, 'Ваша партнёрская ссылка: ' + ref_link.format(bot_name, message.chat.id))
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                          .format(parent_id=user_id)).fetchall()

    if len(data) > 0:
        level1 = [i[0] for i in data]
    else:
        bot.send_message(user_id, 'Партнёры отсутствуют')
        return
    level2 = list()
    level3 = list()
    level4 = list()
    level5 = list()
    for i2 in level1:
        data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                              .format(parent_id=i2)).fetchall()
        if len(data) > 0:
            level2 += [i[0] for i in data]
        for i3 in level2:
            data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                                  .format(parent_id=i3)).fetchall()
            if len(data) > 0:
                level3 += [i[0] for i in data]
            for i4 in level3:
                data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                                      .format(parent_id=i4)).fetchall()
                if len(data) > 0:
                    level4 += [i[0] for i in data]
                for i5 in level5:
                    data = cursor.execute("""SELECT user_id FROM users WHERE parent_id is {parent_id}"""
                                          .format(parent_id=i5)).fetchall()
                    if len(data) > 0:
                        level5 += [i[0] for i in data]
    level1 = [j[0][0] + ' ' + j[0][1] for j in
              [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                              .format(user_id=i)).fetchall() for i in level1]]
    level2 = [j[0][0] + ' ' + j[0][1] for j in
              [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                              .format(user_id=i)).fetchall() for i in level2]]
    level3 = [j[0][0] + ' ' + j[0][1] for j in
              [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                              .format(user_id=i)).fetchall() for i in level3]]
    level4 = [j[0][0] + ' ' + j[0][1] for j in
              [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                              .format(user_id=i)).fetchall() for i in level4]]
    level5 = [j[0][0] + ' ' + j[0][1] for j in
              [cursor.execute("""SELECT name, second_name FROM users WHERE user_id is {user_id}"""
                              .format(user_id=i)).fetchall() for i in level5]]
    bot.send_message(user_id, 'Ваши партнёры:' + '\n' +
                     'Уровень 1 - ' + ', '.join(level1) + '\n' +
                     'Уровень 2 - ' + ', '.join(level2) + '\n' +
                     'Уровень 3 - ' + ', '.join(level3) + '\n' +
                     'Уровень 4 - ' + ', '.join(level4) + '\n' +
                     'Уровень 5 - ' + ', '.join(level5))


def withdraw(message):
    user_id = message.chat.id

    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    balance = cursor.execute("""SELECT balance FROM users WHERE user_id is 
                                 {user_id}"""
                             .format(user_id=user_id)).fetchall()[0][0]
    bot.send_message(user_id, 'Напишите команду /withdraw и введите сумму, которую хотите снять' + '\n' +
                     'Например, /withdraw 50' + '\n'
                                                '💵 Баланс: ' + str(balance) + '\n' + 'Комиссия 2%')


def update_balances():
    import holidays
    holidays = holidays.Russia()
    today = datetime.datetime.now()
    if today.strftime('%Y-%m-%d') in holidays or today.weekday() >= 5:
        return
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    sql = """SELECT * from users"""
    cursor.execute(sql)
    records = cursor.fetchall()
    users_ids = [row[1] for row in records]
    users_balances = [row[5] for row in records]
    users_gains = [row[6] for row in records]
    for i in range(len(users_ids)):
        funds = [j[0] for j in cursor.execute("""SELECT size FROM funds WHERE owner_id is {user_id}"""
                                              .format(user_id=users_ids[i])).fetchall()]
        sql = """UPDATE users SET balance={balance} WHERE user_id is {user_id}""" \
            .format(balance=round(users_balances[i] + sum(funds) * 0.01, 4), user_id=users_ids[i])
        cursor.execute(sql)
        sqlite_connection.commit()
        sql = """UPDATE users SET gain={gain} WHERE user_id is {user_id}""" \
            .format(gain=round(users_gains[i] + sum(funds) * 0.01, 4), user_id=users_ids[i])
        cursor.execute(sql)
        sqlite_connection.commit()



def check():
    from history import history
    from config import start_month, start_day, start_year,\
        end_month, end_day, end_year
    sqlite_connection = sqlite3.connect(db_name)
    cursor = sqlite_connection.cursor()
    login = str(admin_account)
    password = admin_password
    pm = PerfectMoney(login, password)
    data = pm.history(start_month, start_day, start_year, end_month, end_day, end_year)
    if pm.error:
        print(pm.error)
        return
    res = []
    for i in [j for j in data]:
        try:
            memo = i['Memo'].split(': ')[1]
            user_id = cursor.execute("""SELECT user_id FROM users WHERE user_id is {user_id}"""
                                     .format(user_id=memo)).fetchall()[0][0]
            amount = float(i['Amount'])
            amount = int(amount)
            res.append([user_id, amount])
        except:
            continue

    print(res)
    f = open('history.py', 'w')
    if len(res) > 0:
        f.write('history = [[' + '], ['.join([', '.join([f'{i[0]}', f"{i[1]}"]) for i in res]) + ']]')
    else:
        f.write('history = []')
    f.close()
    for i in [j for j in res[len(history):]]:
        try:
            user_id = i[0]
            amount = i[1]


        except:
            continue

        data = cursor.execute(
            f"""SELECT parent_id FROM users WHERE user_id is {user_id}""").fetchall()
        if len(data) > 0:
            level1 = data[0][0]
            sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                WHERE user_id is {level1}) + {amount * 0.05} WHERE user_id is {level1}"""
            cursor.execute(sql)
            sqlite_connection.commit()
            data = cursor.execute(
                f"""SELECT parent_id FROM users WHERE user_id is {level1}""").fetchall()
            if len(data) > 0:
                level2 = data[0][0]
                sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                            WHERE user_id is {level2}) + {amount * 0.04} WHERE user_id is {level2}"""
                cursor.execute(sql)
                sqlite_connection.commit()
                data = cursor.execute(
                    f"""SELECT parent_id FROM users WHERE user_id is {level2}""").fetchall()
                if len(data) > 0:
                    level3 = data[0][0]
                    sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                                            WHERE user_id is {level3}) + {amount * 0.03} WHERE user_id is {level3}"""
                    cursor.execute(sql)
                    sqlite_connection.commit()
                    data = cursor.execute(
                        f"""SELECT parent_id FROM users WHERE user_id is {level3}""").fetchall()
                    if len(data) > 0:
                        level4 = data[0][0]
                        sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                                                WHERE user_id is {level4}) + {amount * 0.02} WHERE user_id is {level4}"""
                        cursor.execute(sql)
                        sqlite_connection.commit()
                        data = cursor.execute(
                            f"""SELECT parent_id FROM users WHERE user_id is {level4}""").fetchall()
                        if len(data) > 0:
                            level5 = data[0][0]
                            sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                                                    WHERE user_id is {level5}) + {amount * 0.01} WHERE user_id is {level5}"""
                            cursor.execute(sql)
                            sqlite_connection.commit()
        sql = f"""UPDATE users SET balance = (SELECT balance FROM users 
                                                WHERE user_id is {user_id}) + {amount} WHERE user_id is {user_id}"""
        cursor.execute(sql)
        sqlite_connection.commit()


schedule.every().day.at('00:00').do(lambda: update_balances())
schedule.every(10).minutes.do(check)


def deposit(message):
    user_id = message.chat.id
    bot.send_message(user_id, '📥 Пополнение баланса' + '\n' +

                     '▫ Способ: Perfect Money' + '\n' +

                     '👉 Для пополнения баланса бота выполните перевод по следующим реквизитам:' + '\n' +
                     '▫ Кошелёк: ' + admin_id + '\n' +
                     '▫ Описание: ' + str(message.chat.id) + ''
                     + '\n' +
                     '❗ Не забудьте оставить описание к переводу, иначе средства не придут. '
                     'Зачислены на баланс будут только цифры до запятой')


class ScheduleMessage():
    def try_send_schedule(self):
        while True:
            schedule.run_pending()
            time.sleep(1)

    def start_process(self):
        p1 = Process(target=ScheduleMessage.try_send_schedule, args=(self,))
        p1.start()


if __name__ == '__main__':
    check()
    c = ScheduleMessage()
    c.start_process()
    bot.polling(none_stop=True)
