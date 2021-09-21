# pyinstaller -F -n Registrator ./registrator/main.py

import re
import threading
from time import sleep
import PySimpleGUI as sg
import serial
from PySimpleGUI import Tab, TabGroup
from tabulate import tabulate

from config import config
from request import select_request
from tools import convert
from query import get_card_info, update_phone
from widgets import display_notification

import log
logger = log.set_logger('registrator')


img_error = b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAA3NCSVQICAjb4U/gAAAACXBIWXMAAADlAAAA5QGP5Zs8AAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAIpQTFRF////20lt30Bg30pg4FJc409g4FBe4E9f4U9f4U9g4U9f4E9g31Bf4E9f4E9f4E9f4E9f4E9f4FFh4Vdm4lhn42Bv5GNx5W575nJ/6HqH6HyI6YCM6YGM6YGN6oaR8Kev9MPI9cbM9snO9s3R+Nfb+dzg+d/i++vt/O7v/fb3/vj5//z8//7+////KofnuQAAABF0Uk5TAAcIGBktSYSXmMHI2uPy8/XVqDFbAAAA8UlEQVQ4y4VT15LCMBBTQkgPYem9d9D//x4P2I7vILN68kj2WtsAhyDO8rKuyzyLA3wjSnvi0Eujf3KY9OUP+kno651CvlB0Gr1byQ9UXff+py5SmRhhIS0oPj4SaUUCAJHxP9+tLb/ezU0uEYDUsCc+l5/T8smTIVMgsPXZkvepiMj0Tm5txQLENu7gSF7HIuMreRxYNkbmHI0u5Hk4PJOXkSMz5I3nyY08HMjbpOFylF5WswdJPmYeVaL28968yNfGZ2r9gvqFalJNUy2UWmq1Wa7di/3Kxl3tF1671YHRR04dWn3s9cXRV09f3vb1fwPD7z9j1WgeRgAAAABJRU5ErkJggg=='
img_success = b'iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAAAA3NCSVQICAjb4U/gAAAACXBIWXMAAAEKAAABCgEWpLzLAAAAGXRFWHRTb2Z0d2FyZQB3d3cuaW5rc2NhcGUub3Jnm+48GgAAAHJQTFRF////ZsxmbbZJYL9gZrtVar9VZsJcbMRYaMZVasFYaL9XbMFbasRZaMFZacRXa8NYasFaasJaasFZasJaasNZasNYasJYasJZasJZasJZasJZasJZasJYasJZasJZasJZasJZasJaasJZasJZasJZasJZ2IAizQAAACV0Uk5TAAUHCA8YGRobHSwtPEJJUVtghJeYrbDByNjZ2tvj6vLz9fb3/CyrN0oAAADnSURBVDjLjZPbWoUgFIQnbNPBIgNKiwwo5v1fsQvMvUXI5oqPf4DFOgCrhLKjC8GNVgnsJY3nKm9kgTsduVHU3SU/TdxpOp15P7OiuV/PVzk5L3d0ExuachyaTWkAkLFtiBKAqZHPh/yuAYSv8R7XE0l6AVXnwBNJUsE2+GMOzWL8k3OEW7a/q5wOIS9e7t5qnGExvF5Bvlc4w/LEM4Abt+d0S5BpAHD7seMcf7+ZHfclp10TlYZc2y2nOqc6OwruxUWx0rDjNJtyp6HkUW4bJn0VWdf/a7nDpj1u++PBOR694+Ftj/8PKNdnDLn/V8YAAAAASUVORK5CYII='

sp = {
    "idaccount": 0,
    "idvip": 0,
    "idrvip": 0,
    "waiting_visit": False,
    "info": ''
}


def thread_check_current_visit(window):
    """
    The thread that communicates with the application through the window's events.

    Once a second wakes and sends a new event and associated value to the window
    """
    global sp
    while True:
        if sp.get("waiting_visit"):
            logger.info(f'idrvip: {sp.get("idrvip")}')
            sql = f"""
                SELECT FIRST 1 udf_formatdatetime('dd.mm.yy hh:mm:ss', v.DATEDOC) 
                FROM FITNESS_VVISITS v 
                    JOIN FITNESS_VSTICKETS st ON st.ID = v.IDVSTICKET
                    JOIN RESTAURANT_SHIFTS s ON s.ID = v.IDSHIFT 
                WHERE s.DATEEND IS NULL AND st.IDVIPCUSTOMER = {sp.get("idrvip")}
                order by v.id desc
            """
            if current_visit := select_request(sql):
                logger.info(f'current_visit: {current_visit}')
                sp.update({"waiting_visit": False})
                sp.update({"waiting_card": True})
                info = f'\nТекущее посещение: {current_visit[0][0]}'
                logger.info(info)
                window.write_event_value('-THREAD_CHECK_CURRENT_VISIT-', info)  # Data sent is a tuple of thread name and counter
        sleep(3)


def thread_serial(window):
    """
    The thread that communicates with the application through the window's events.

    Once a second wakes and sends a new event and associated value to the window
    """
    port = config()['port']
    with serial.Serial(port) as ser:
        while True:
            data = ser.readline().decode()
            # data = data.replace("\n", "")
            data = convert(data)
            logger.info(f'Card Data: {data}')
            logger.info(f"waiting_card: {sp.get('waiting_card')}")

            if data:
                card_info = get_card_info(data)
                logger.info(card_info)
                if card_info:
                    if exctact_cabinet_state(card_info) == 1 and sp.get("waiting_card"):
                        sql = f"SELECT idaccount, msg FROM UD_NEW_ACCOUNT({sp.get('idrvip')}, '{data}')"
                        new_account = select_request(sql)
                        logger.info(sql)
                        logger.info(new_account)
                        if new_account:
                            if new_account[0][0] > 0:
                                logger.info(new_account[0][0])
                                sp.update({"waiting_card": False})
                                card_info = get_card_info(data)
                                logger.info(card_info)
                                if card_info:
                                    window.write_event_value('-THREAD_SERIAL-', card_info)

                    else:
                        window.write_event_value('-THREAD_SERIAL-', card_info)

                # else:
                #     window.write_event_value('-THREAD_SERIAL-', None)


def size(font_size):
    scale = int(config()['scale'])
    return round(font_size*scale/100)


def main():
    """
    The demo will display in the multiline info about the event and values dictionary as it is being
    returned from window.read()
    Every time "Start" is clicked a new thread is started
    Try clicking "Dummy" to see that the window is active while the thread stuff is happening in the background
    """

    sg.theme('DarkBlue4')
    global sp

    layout = [
        [sg.Text('Жду браслеты...', font=('Lucida Console', size(12)))],
    ]
    tab = Tab("...", layout, key='-TAB-')

    # Tab Phone
    layout = [
        [sg.Text('', font=('Lucida Console', 12), key='-INFO-')],
        [sg.Text('Телефон:', font=('Lucida Console', 15)), sg.Text(font=('Lucida Console', size(20)), key='-PHONE-')],
        [sg.T('Введите номер телефона:', size=(30, 1), font=('Lucida Console', size(15)), key='-MSG-')],
        [
            sg.Text('+7', size=(2, 1), font=('Lucida Console', size(30)), key='-PREFIX-'),
            sg.Input(size=(11, 1), font=('Lucida Console', size(30)), enable_events=True, key='-INPUT_PHONE-'),
            sg.Button('->', font=('Lucida Console', size(20)), bind_return_key=True, key='-SAVE-')
        ],
    ]
    tab_phone = Tab("Телефон", layout, visible=False, key='-TAB_PHONE-')

    # Tab Fitness
    layout = [
        [sg.Text('', font=('Lucida Console', size(12)), key='-FIT_INFO-')],
        [sg.T('Поднесите браслет для шкафчика...', size=(33, 1), font=('Lucida Console', size(15)), text_color='#Ebcc5f',
              key='-FIT_MSG-')],
    ]
    tab_fit = Tab("Фитнес", layout, visible=False, key='-TAB_FIT-')

    # Tab Cabinet
    layout = [
        [sg.Text('', font=('Lucida Console', size(12)), key='-CAB_INFO-')],
    ]
    tab_cab = Tab("Шкафчик", layout, visible=False, key='-TAB_CAB-')

    tg_main = TabGroup([[tab, tab_phone, tab_fit, tab_cab]], font=('Lucida Console', size(15)))

    layout = [
        # [sg.Text('Жду браслеты...', key='-INFO-', font=('Lucida Console', 12))],
        [tg_main]
    ]

    window = sg.Window('Аквапарк 🐬 "Дельфин"', layout, keep_on_top=True)
    threading.Thread(target=thread_serial, args=(window,), daemon=True).start()
    threading.Thread(target=thread_check_current_visit, args=(window,), daemon=True).start()

    while True:  # Event Loop
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Exit':
            break

        if event == '-THREAD_SERIAL-':
            card_info = values['-THREAD_SERIAL-']
            if card_info:
                tab, info, phone = extract(card_info)

                if tab == '-TAB_FIT-':
                    # info = f"{values['-INFO-']}\n{info}"
                    window['-FIT_INFO-'].update(value=info)
                    show_tab(window, '-TAB_FIT-')

                elif tab == '-TAB_PHONE-':
                    font_size = size(12) if sp.get("idaccount") > 0 else size(15)
                    window['-INFO-'].update(value=info, font=('Lucida Console', font_size))
                    if phone:
                        window['-PHONE-'].update(f"+{phone}", text_color='#Ebcc5f')
                    else:
                        window['-PHONE-'].update("не зарегистрирован", text_color='#Cc3e41')

                    # window['-INPUT_PHONE-'].update('', disabled=False)
                    # window['-SAVE-'].update(disabled=False)
                    show_tab(window, '-TAB_PHONE-')

                elif tab == '-TAB_CAB-':
                    window['-CAB_INFO-'].update(value=info)
                    show_tab(window, tab)

            else:
                show_tab(window, '-TAB-')

        if event == '-THREAD_CHECK_CURRENT_VISIT-':
            info = values['-THREAD_CHECK_CURRENT_VISIT-']
            info = f"{sp.get('info')}\n{info}"
            window['-FIT_INFO-'].update(value=info)
            show_tab(window, '-TAB_FIT-')

        if event == '-INPUT_PHONE-':
            window['-INPUT_PHONE-'].update(re.sub("[^0-9]", "", values['-INPUT_PHONE-']))

            if len(values['-INPUT_PHONE-']) > 10:
                window['-INPUT_PHONE-'].update(values['-INPUT_PHONE-'][0:-1])

        if event == '-SAVE-':
            phone = values['-INPUT_PHONE-']
            if update_phone(sp.get('idaccount'), sp.get('idvip'), phone) != -1:
                title = 'Все на букву "З"'
                window['-PHONE-'].update(phone, text_color='#3ecc49')
                display_notification(title, f"Записал: {phone}", img_success, 500, True)
            else:
                title = 'Все на букву "З"'
                display_notification(title, f"Не удалось записать: {phone}", img_success, 500, True)

    window.close()


def show_tab(window, selected_tab):
    tabs = ['-TAB-', '-TAB_FIT-', '-TAB_PHONE-', '-TAB_CAB-']
    for tab in tabs:
        window[tab].update(visible=tab == selected_tab)

    window[selected_tab].select()


def exctact_cabinet_state(card_info):
    entity = card_info.get('entity')
    if entity == 'cabinet':
        idstate = card_info.get("idstate")
        print(f"state: {idstate}")
        return idstate
    return None


def extract(card_info):
    global sp
    entity = card_info.get('entity')
    sp.update({"waiting_visit": False})
    sp.update({"waiting_card": False})

    if entity == 'account':
        tab = '-TAB_PHONE-'
        sp.update({"idaccount": card_info.get("account")[0]})
        sp.update({"idvip": 0})

        idaccount, phone, date_begin, cabinet, owner = card_info.get("account")
        cabinet = cabinet.replace(' Аквапарк "Дельфин"', '')
        owner = owner.replace(' Аквапарк "Дельфин"', '')
        orders = card_info.get("orders")
        payment = card_info.get("payment")
        orders.extend([['Оплачено', ' ', payment]])

        info = tabulate([['Время входа', date_begin], ['Браслет', cabinet], ['Владелец счета', owner]],
                                tablefmt="plain", colalign=("right",))
        info += '\n\n'
        info += tabulate(orders, tablefmt="grid", colalign=("right",))
        return tab, info, phone

    elif entity == 'vipcustomer':
        sp.update({"idaccount": 0})

        if vipcustomer := card_info.get("vipcustomer"):
            print(f"vipcustomer: {vipcustomer}")
            tab = '-TAB_PHONE-'
            idvip, info, phone, idrvip = vipcustomer
            sp.update({"idvip": idvip})
            sp.update({"idrvip": idrvip})

            if fitness_ticket := card_info.get('fitness_ticket'):
                terms, name, total_visits, remaining_visits, used_visits = fitness_ticket
                name = name.replace("Абонемент", "")
                info += f'\nАбонемент: {name}\n'
                info += f'Срок действия: {terms}\n'
                info += f'Посещения: {total_visits}-всего, {used_visits}-освоено, {remaining_visits}-осталось\n'

                if current_visit := card_info.get('current_visit'):
                    print(f"current_visit: {current_visit}")
                    visit_time, idaccount, cabinet = current_visit
                    info += f'\nТекущее посещение: {visit_time}\n'
                    if idaccount > 0:
                        info += f"""Выдан шкафчик: {cabinet.replace(' Аквапарк "Дельфин"', '')}"""
                    else:
                        sp.update({"waiting_card": True})
                        tab = '-TAB_FIT-'
                else:
                    info += f'\nЖду регистрации посещения ...\n'
                    sp.update({"waiting_visit": True})

            sp.update({"info": info})
            return tab, info, phone

    elif entity == 'cabinet':
        tab = '-TAB_CAB-'
        cabinet = card_info.get("cabinet")
        state = card_info.get("state")
        info = f'Шкафчик: {cabinet}\n'
        info += f'Состояник: {state}'
        return tab, info, None

    else:
        return None


if __name__ == '__main__':
    main()