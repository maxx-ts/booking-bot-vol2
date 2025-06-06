import telebot
from telebot import types
import calendar
from datetime import datetime

bot = telebot.TeleBot('8017118025:AAHb_hxP6N0ffLELWMj0riXGIlpMAZ7erz4')

calen = {}  # date -> list of (start, end, user)
user_state = {}  # Stores user's selected date and times

def create_calendar(year, month):
    markup = types.InlineKeyboardMarkup(row_width=7)
    markup.add(types.InlineKeyboardButton(f'{calendar.month_name[month]} {year}', callback_data='ignore'))

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(types.InlineKeyboardButton(' ', callback_data='ignore'))
            else:
                date_str = f'{year}-{month:02d}-{day:02d}'
                label = f'{day}'
                if date_str in calen:
                    label += " ✅"
                row.append(types.InlineKeyboardButton(label, callback_data=f'day_{date_str}'))
        markup.row(*row)

    markup.row(
        types.InlineKeyboardButton('⬅️', callback_data='prev_month'),
        types.InlineKeyboardButton('🔙 Назад', callback_data='back'),
        types.InlineKeyboardButton('➡️', callback_data='next_month')
    )
    return markup

def time_markup(date_str, step, selected_time=None):
    markup = types.InlineKeyboardMarkup(row_width=4)
    available_hours = range(8, 22)
    booked_slots = calen.get(date_str, [])

    for h in available_hours:
        t = f"{h}:00"
        label = t
        if step == "end" and selected_time:
            if h <= int(selected_time.split(':')[0]):
                continue

        is_booked = any(
            int(start.split(':')[0]) <= h < int(end.split(':')[0])
            for start, end, _ in booked_slots
        )

        if is_booked:
            label += " ❌"
            markup.add(types.InlineKeyboardButton(label, callback_data='ignore'))
        else:
            callback = f"time_{step}_{date_str}_{t}"
            markup.add(types.InlineKeyboardButton(label, callback_data=callback))

    markup.add(types.InlineKeyboardButton('🔙 Назад до календаря', callback_data='show_calendar'))
    return markup

def main_menu():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Забронювати дату ⚙️', callback_data='show_calendar'))
    markup.row(
        types.InlineKeyboardButton('Переглянути броні 📅', callback_data='show_booked'),
        types.InlineKeyboardButton('Відмінити дату ❌', callback_data='cancel_date')
    )
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_state[message.from_user.id] = {'year': datetime.now().year, 'month': datetime.now().month}
    bot.send_message(
        message.chat.id,
        f'<b>Привіт, {message.from_user.first_name}! Я бот для бронювання</b>',
        parse_mode='html',
        reply_markup=main_menu()
    )

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = call.from_user.id
    state = user_state.setdefault(user_id, {'year': datetime.now().year, 'month': datetime.now().month})

    if call.data == 'show_calendar':
        markup = create_calendar(state['year'], state['month'])
        bot.edit_message_text("Оберіть дату:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('day_'):
        date_str = call.data.split('_')[1]
        state['selected_date'] = date_str
        state['step'] = 'start'
        markup = time_markup(date_str, 'start')
        bot.edit_message_text(
            f"Дата: {date_str}\nОберіть <b>початковий</b> час:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='html',
            reply_markup=markup
        )

    elif call.data.startswith('time_start_'):
        _, _, date_str, start_time = call.data.split('_')
        state['selected_start'] = start_time
        state['step'] = 'end'
        markup = time_markup(date_str, 'end', selected_time=start_time)
        bot.edit_message_text(
            f"Дата: {date_str}\nПочаток: {start_time}\nОберіть <b>кінець</b> часу:",
            call.message.chat.id,
            call.message.message_id,
            parse_mode='html',
            reply_markup=markup
        )

    elif call.data.startswith('time_end_'):
        _, _, date_str, end_time = call.data.split('_')
        start_time = state.get('selected_start')

        if not start_time:
            bot.answer_callback_query(call.id, "Спочатку оберіть початковий час.")
            return

        state['selected_end'] = end_time
        bot.send_message(call.message.chat.id, "Для чого це бронювання? Введіть мету:")
        state['step'] = 'ask_reason'

    elif call.data == 'show_booked':
        if not calen:
            bot.edit_message_text("Немає жодних бронювань.", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
            return
        text = "<b>Бронювання:</b>\n"
        for date, slots in sorted(calen.items()):
            text += f"{date}:\n"
            for s, e, who in sorted(slots):
                text += f"  — {s} до {e} | {who}\n"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode='html', reply_markup=main_menu())

    elif call.data == 'cancel_date':
        if not calen:
            bot.answer_callback_query(call.id, "Немає активних бронювань для скасування.")
            return
        markup = types.InlineKeyboardMarkup()
        for date in calen:
            markup.add(types.InlineKeyboardButton(date, callback_data=f'cancel_{date}'))
        markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back'))
        bot.edit_message_text("Оберіть дату для скасування:", call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data.startswith('cancel_'):
        date_str = call.data.split('_')[1]
        if date_str in calen:
            del calen[date_str]
            bot.edit_message_text(f"Бронювання на {date_str} було скасовано.", call.message.chat.id, call.message.message_id, reply_markup=main_menu())
        else:
            bot.answer_callback_query(call.id, "На цю дату немає бронювань.")

    elif call.data == 'back':
        bot.edit_message_text('<b>Оберіть дію:</b>', call.message.chat.id, call.message.message_id, parse_mode='html', reply_markup=main_menu())

    elif call.data == 'prev_month':
        year, month = state['year'], state['month']
        month = 12 if month == 1 else month - 1
        year = year - 1 if month == 12 else year
        state.update({'year': year, 'month': month})
        markup = create_calendar(year, month)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

    elif call.data == 'next_month':
        year, month = state['year'], state['month']
        month = 1 if month == 12 else month + 1
        year = year + 1 if month == 1 else year
        state.update({'year': year, 'month': month})
        markup = create_calendar(year, month)
        bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user_id = message.from_user.id
    state = user_state.get(user_id, {})

    if state.get('step') == 'ask_reason':
        reason = message.text
        date_str = state.get('selected_date')
        start_time = state.get('selected_start')
        end_time = state.get('selected_end')
        user_full_name = f"{message.from_user.first_name} {message.from_user.last_name or ''}".strip()

        if not all([date_str, start_time, end_time]):
            bot.send_message(message.chat.id, "Помилка: недостатньо даних для збереження бронювання.")
            return

        calen.setdefault(date_str, []).append((start_time, end_time, f"{user_full_name}: {reason}"))

        bot.send_message(
            message.chat.id,
            f"Успішно заброньовано:\n<b>{date_str} з {start_time} до {end_time}</b>\nМета: {reason}",
            parse_mode='html',
            reply_markup=main_menu()
        )

        for key in ['selected_date', 'selected_start', 'selected_end', 'step']:
            state.pop(key, None)

bot.polling(none_stop=True)
