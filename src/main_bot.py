import os
from collections import defaultdict
from datetime import datetime
import threading
from time import sleep

import telebot
import ipaddress

from node_layout import NodeList
from node_database import Node

bot = telebot.TeleBot(os.environ.get('API_KEY'))
node = Node.initiate(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY'))

update_time = 5
help_items = {
    '/start - Start bot'
    '/help - Get bot commands',
    '/add <ip-address> <API port> <Met port> <SEED port> - Add your node to list',
    '/del <ip-address> - Delete node from list',
    '/nodes - Get node status',
}


@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, 'Aptos bot ready to monitor your node!')
    bot.send_message(message.chat.id,
                     '\n'.join(f'{items}' for items in help_items))


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.chat.id,
                     '\n'.join(f'{items}' for items in help_items))


# todo Add way to check for duplicates
@bot.message_handler(commands=['add'])
def add(message):
    input = message.text.split()
    if len(input) != 5:
        bot.send_message(message.chat.id, '❌ Valid input: <ip-address> <API port> <Met port> <SEED port>')
        return
    try:
        ipaddress.ip_address(input[1])
        node.update_nodelist(node_list=NodeList(
            tg_chat_id=message.chat.id,
            ip=input[1],
            api_port=input[2],
            metrics_port=input[3],
            seed_port=input[4]))
        bot.send_message(message.chat.id, '✅ Node added successfully')
    except ValueError:
        bot.send_message(message.chat.id, "❌ IP address '{}' is not valid".format(input[1]))


# Add way to delete nodes based on ports -> weird cases
@bot.message_handler(commands=['del'])
def delete(message):
    input = message.text.split()
    node.delete_node(NodeList(tg_chat_id=message.chat.id, ip=input[1]))
    bot.send_message(
        chat_id=message.chat.id,
        text=f"✅ Successfully deleted node: {input[1]}"
    )


# Add ports to nodes list
@bot.message_handler(commands=['nodes'])
def get_nodes(message):
    available_nodes = node.get_available_nodes(message.chat.id)
    if available_nodes:
        bot.send_message(
            chat_id=message.chat.id,
            text='\n'.join(str(a.ip) for a in available_nodes)
        )
    else:
        bot.send_message(
            chat_id=message.chat.id,
            text='❌ No nodes available'
        )


def send_alerts():
    while True:
        alarm_nodes = node.get_alarm_node()
        # # CHECK IF WORK?
        # if len(alarm_nodes) == 0:
        #     bot.send_message(my_chat_id, 'I checked')
        #     return
        grouped_alarms = defaultdict(list)
        for a in alarm_nodes:
            grouped_alarms[a.tg_chat_id].append(a)

        for chat_id, alarms in grouped_alarms.items():
            message_out = f'🔴 Node alert'
            for a in alarms:
                message_out += '\n'
                message_out += ''.join(str(a.ip)) + '\n'
                message_out += ''.join(a.errors) + '\n'
            bot.send_message(chat_id=chat_id, text=message_out)

            for alarm in alarms:
                alarm.alarm_sent = int(datetime.utcnow().timestamp())
                node.update_nodelist(alarm)
        sleep(update_time)


t = threading.Thread(target=send_alerts)
t.start()

while True:
    try:
        bot.polling(none_stop=True, interval=0)
    except:
        sleep(10)
