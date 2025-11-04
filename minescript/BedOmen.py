#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import math
import os
import minescript
from minescript import EventQueue, EventType

# --- Константы ---
SCRIPT_NAME = "BedOmen.py"
INTERNAL_COMMAND = "_event_loop"
LOG_STATUS_FILE = "bedomen_log_status.txt"
COOLDOWN_SECONDS = 5
TRIGGER_DISTANCE = 2.5
BOTTLE_ITEM_ID = "minecraft:ominous_bottle"

# --- Глобальные переменные для event_loop ---
last_activation_time = 0

# --- Функции логирования ---

def is_log_enabled():
    return os.path.exists(LOG_STATUS_FILE)

def log_message(message):
    if is_log_enabled():
        minescript.echo(f"§7[BedOmen Log] {message}§r")

def set_log_status(enable):
    if enable:
        if not is_log_enabled():
            try:
                with open(LOG_STATUS_FILE, 'w') as f: f.write('enabled')
                minescript.echo("§aBedOmen: Логирование включено.")
            except Exception as e:
                minescript.echo(f"§cBedOmen: Не удалось включить логирование: {e}")
        else:
            minescript.echo("§aBedOmen: Логирование уже было включено.")
    else:
        if is_log_enabled():
            try:
                os.remove(LOG_STATUS_FILE)
                minescript.echo("§eBedOmen: Логирование выключено.")
            except Exception as e:
                minescript.echo(f"§cBedOmen: Не удалось выключить логирование: {e}")
        else:
            minescript.echo("§eBedOmen: Логирование уже было выключено.")

# --- Функции управления скриптом ---

def is_already_running():
    my_job_id = -1
    for job in minescript.job_info():
        if job.self: my_job_id = job.job_id
    for job in minescript.job_info():
        if SCRIPT_NAME in job.command and INTERNAL_COMMAND in job.command and job.job_id != my_job_id: return True
    return False

def start_script():
    if is_already_running():
        minescript.echo("§eBedOmen: Скрипт уже запущен.")
        return
    minescript.execute(f"\\{SCRIPT_NAME.replace('.py', '')} {INTERNAL_COMMAND} > null 2> null")
    minescript.echo("§aBedOmen: Скрипт успешно активирован.")

def stop_script():
    my_job_id = -1
    for job in minescript.job_info():
        if job.self: my_job_id = job.job_id
    job_found = False
    for job in minescript.job_info():
        if SCRIPT_NAME in job.command and INTERNAL_COMMAND in job.command and job.job_id != my_job_id:
            minescript.execute(f"killjob {job.job_id}")
            job_found = True
    if job_found: minescript.echo("§eBedOmen: Скрипт успешно остановлен.")
    else: minescript.echo("§eBedOmen: Скрипт не был запущен.")

# --- Основная логика и обработка событий ---

def drink_bottle():
    log_message("Проверка зловещей бутылки в левой руке...")
    hand_items = minescript.player_hand_items()
    if hand_items and hand_items.off_hand and hand_items.off_hand.item == BOTTLE_ITEM_ID:
        log_message("Бутылка найдена. Начинаю пить...")
        minescript.player_press_use(True)
        start_wait_time, bottle_consumed = time.time(), False
        while time.time() - start_wait_time < 3:
            current_hand_items = minescript.player_hand_items()
            if not current_hand_items.off_hand or current_hand_items.off_hand.item != BOTTLE_ITEM_ID:
                log_message("Бутылка успешно выпита.")
                bottle_consumed = True
                break
            time.sleep(0.1)
        minescript.player_press_use(False)
        log_message("Отпустил ПКМ.")
        if not bottle_consumed: log_message("§cНе удалось подтвердить, что бутылка была выпита.")
    else:
        log_message("§cВ левой руке нет зловещей бутылки.")
        minescript.echo("§cBedOmen: В левой руке нет зловещей бутылки.")

def handle_block_update(event):
    global last_activation_time
    if not ("trapdoor" in event.new_state and "open=false" in event.old_state and "open=true" in event.new_state): return
    current_time = time.time()
    if current_time - last_activation_time < COOLDOWN_SECONDS:
        log_message("Открытие люка проигнорировано из-за кулдауна.")
        return
    player_pos, block_pos = minescript.player_position(), event.position
    distance = math.sqrt(sum([(pc - (bc + 0.5))**2 for pc, bc in zip(player_pos, block_pos)]))
    if distance <= TRIGGER_DISTANCE:
        log_message(f"Люк открыт в пределах дистанции ({distance:.2f} м). Запускаю питьё.")
        last_activation_time = current_time
        drink_bottle()
    else:
        log_message(f"Люк открыт, но слишком далеко ({distance:.2f} м).")

def event_loop():
    with EventQueue() as event_queue:
        event_queue.register_block_update_listener()
        log_message("Цикл событий запущен. Ожидание открытия люков...")
        while True:
            try:
                event = event_queue.get(block=True, timeout=1.0)
                if event and event.type == EventType.BLOCK_UPDATE: handle_block_update(event)
            except minescript.JobInterruptedException: break
            except Exception: pass
    log_message("Цикл событий завершен.")

# --- Обработка команд ---

def main():
    if len(sys.argv) < 2:
        minescript.echo("§cОшибка: Команда не указана. Используйте §e\\potion <on|off|log on|log off>§c.")
        return
    command = sys.argv[1].lower()
    if command == "on": start_script()
    elif command == "off": stop_script()
    elif command == INTERNAL_COMMAND: event_loop()
    elif command == "log":
        if len(sys.argv) > 2:
            log_command = sys.argv[2].lower()
            if log_command == "on": set_log_status(True)
            elif log_command == "off": set_log_status(False)
            else: minescript.echo(f"§cОшибка: Неизвестный аргумент для 'log': '{log_command}'. Используйте 'on' или 'off'.")
        else: minescript.echo("§cОшибка: Для команды 'log' необходимо указать 'on' или 'off'.")
    else:
        minescript.echo(f"§cОшибка: Неизвестная команда '{command}'. Используйте 'on' или 'off'.")

if __name__ == "__main__":
    main()
