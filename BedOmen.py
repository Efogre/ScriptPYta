"""Automation script for drinking Ominous Bottles when trapdoors open nearby.

This script is designed for use with the Minescript mod. It listens for trapdoor
open events, checks the player's off-hand for an ominous bottle, and triggers
the use action while ensuring the bottle is actually consumed.
"""

import math
import time
from typing import Dict, Tuple

import minescript
from minescript import EventQueue, EventType

COOLDOWN_SECONDS = 5.0
TRIGGER_DISTANCE = 2.5
OMINOUS_BOTTLE_ID = "minecraft:ominous_bottle"
CHECK_INTERVAL = 0.1
MAX_USE_TIME = 15.0


def _distance_to_block(player_pos: Tuple[float, float, float], block_pos: Tuple[int, int, int]) -> float:
    """Return Euclidean distance between player and the center of a block."""
    px, py, pz = player_pos
    bx, by, bz = block_pos
    # Compare using block center to better approximate in-game distance checks.
    dx = px - (bx + 0.5)
    dy = py - (by + 0.5)
    dz = pz - (bz + 0.5)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _is_trapdoor_state_open(state: str) -> bool:
    """Return True if the block state string represents an open trapdoor."""
    if not state:
        return False
    if "trapdoor" not in state:
        return False
    return "open=true" in state


def _is_trapdoor_state_closed(state: str) -> bool:
    """Return True if the block state string represents a closed trapdoor."""
    if not state:
        return False
    if "trapdoor" not in state:
        return False
    return "open=false" in state


def _get_offhand_item():
    """Return the item stack held in the off-hand."""
    hand_items = minescript.player_hand_items()
    return getattr(hand_items, "off_hand", None)


def _attempt_drink(log_callback) -> bool:
    """Attempt to drink the ominous bottle from the off-hand.

    Returns True if a bottle was successfully consumed, False otherwise.
    """
    off_hand = _get_offhand_item()
    if off_hand is None or off_hand.item != OMINOUS_BOTTLE_ID or off_hand.count <= 0:
        log_callback("В левой руке нет зловещей бутылки.")
        return False

    initial_count = off_hand.count
    minescript.player_press_use(True)
    start_time = time.monotonic()
    consumed = False
    try:
        while True:
            time.sleep(CHECK_INTERVAL)
            current = _get_offhand_item()
            if current is None or current.item != OMINOUS_BOTTLE_ID or current.count < initial_count:
                consumed = True
                break
            if time.monotonic() - start_time > MAX_USE_TIME:
                break
    finally:
        minescript.player_press_use(False)

    if consumed:
        log_callback("Зловещая бутылка выпита.")
    else:
        log_callback("Не удалось завершить питьё зловещей бутылки.")
    return consumed


def main():
    automation_enabled = False
    logging_enabled = True
    cooldown_ready_time = 0.0
    last_states: Dict[Tuple[int, int, int], bool] = {}

    def notify(message: str) -> None:
        minescript.echo(message)

    def log_message(message: str) -> None:
        if logging_enabled:
            notify(message)

    def handle_command(message: str) -> None:
        nonlocal automation_enabled, logging_enabled, cooldown_ready_time
        text = message.strip()
        parts = text.split()
        if not parts:
            return
        command = parts[0].lower()
        args = [part.lower() for part in parts[1:]]

        if command != "\\potion":
            return

        if not args:
            notify("Использование: \\potion <on|off|log> [on|off].")
            return

        if args[0] == "on":
            if automation_enabled:
                notify("Авто-питьё уже включено.")
            else:
                automation_enabled = True
                cooldown_ready_time = 0.0
                notify("Авто-питьё зловещих бутылок включено.")
            return

        if args[0] == "off":
            if automation_enabled:
                automation_enabled = False
                notify("Авто-питьё зловещих бутылок выключено.")
            else:
                notify("Авто-питьё уже выключено.")
            return

        if args[0] == "log":
            if len(args) < 2 or args[1] not in {"on", "off"}:
                notify("Использование: \\potion log <on|off>.")
                return
            logging_enabled = args[1] == "on"
            status = "включён" if logging_enabled else "выключен"
            notify(f"Лог действий {status}.")
            return

        notify("Неизвестная подкоманда для \\potion.")

    def handle_block_update(event) -> None:
        nonlocal cooldown_ready_time
        if not automation_enabled:
            return
        if time.monotonic() < cooldown_ready_time:
            return

        position = tuple(event.position)
        was_open = last_states.get(position)
        is_now_open = _is_trapdoor_state_open(event.new_state)

        if not is_now_open:
            if _is_trapdoor_state_closed(event.new_state):
                last_states[position] = False
            return

        if not _is_trapdoor_state_closed(event.old_state) and was_open:
            return

        last_states[position] = True

        player_pos = tuple(minescript.player_position())
        if _distance_to_block(player_pos, position) > TRIGGER_DISTANCE:
            return

        cooldown_ready_time = time.monotonic() + COOLDOWN_SECONDS
        _attempt_drink(log_message)

    with EventQueue() as event_queue:
        event_queue.register_block_update_listener()
        event_queue.register_outgoing_chat_interceptor(prefix="\\potion")

        while True:
            event = event_queue.get()
            if event.type == EventType.OUTGOING_CHAT_INTERCEPT:
                handle_command(event.message)
            elif event.type == EventType.BLOCK_UPDATE:
                handle_block_update(event)


if __name__ == "__main__":
    main()
