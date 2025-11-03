# -*- coding: utf-8 -*-
import time
import minescript
from minescript import EventQueue, echo, player_hand_items
from minescript import player_press_use

ITEM_ID = "minecraft:ominous_bottle"
MAX_TRAPDOOR_DISTANCE = 4.5
DRINK_HOLD_SECONDS = 1.9

active = False
last_trigger_time = 0.0
trigger_cooldown = 0.25

def toggle():
    global active
    active = not active
    echo(f"[potion] {'ON' if active else 'OFF'}")

def distance_to_player(pos):
    px, py, pz = minescript.player_position()
    x, y, z = pos
    return ((px - x) ** 2 + (py - y) ** 2 + (pz - z) ** 2) ** 0.5

def is_trapdoor_open_event(old_state, new_state):
    if "_trapdoor" not in new_state:
        return False
    return ("open=true" in new_state) and ("open=true" not in old_state)

def drink_offhand_bottle():
    hands = player_hand_items()
    off = hands.off_hand
    if not off or off.item != ITEM_ID or off.count <= 0:
        echo("[potion] В левой руке нет ominous bottle")
        return False

    # Пьём из offhand без смены рук и без изменения взгляда
    player_press_use(True)
    time.sleep(DRINK_HOLD_SECONDS)
    player_press_use(False)
    return True

def on_block_update(event):
    global last_trigger_time
    if not active:
        return
    if not is_trapdoor_open_event(event.old_state, event.new_state):
        return
    if distance_to_player(event.position) > MAX_TRAPDOOR_DISTANCE:
        return
    now = time.time()
    if now - last_trigger_time < trigger_cooldown:
        return
    last_trigger_time = now
    drink_offhand_bottle()

def main():
    echo("[potion] Запущено. Используйте /potion для переключения.")
    with EventQueue() as q:
        q.register_outgoing_chat_interceptor(pattern=r"^/potion\s*$")
        q.register_block_update_listener()
        q.register_world_listener()
        while True:
            ev = q.get()
            if ev.type == "outgoing_chat_intercept":
                toggle()
            elif ev.type == "block_update":
                on_block_update(ev)
            elif ev.type == "world":
                pass

if __name__ == "__main__":
    main()
