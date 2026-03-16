import json
from pathlib import Path
import re
import sys

CONFIG_DIR = Path("./config")

def bot_number(path):
    return int(re.search(r'bot_(\d+)', path.name).group(1))


def load_bots():
    bots = []

    files = sorted(CONFIG_DIR.glob("bot_*.json"), key=bot_number)

    for file in files:
        with open(file) as f:
            data = json.load(f)
            bots.append((file, data))

    return bots


def save_bot(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


def show_bots(filter_mode=None):
    bots = load_bots()

    print("\nBots:")
    print("-" * 60)

    for i, (file, bot) in enumerate(bots, start=1):

        enabled = bot.get("is_enabled", False)

        if filter_mode == "enabled" and not enabled:
            continue

        if filter_mode == "disabled" and enabled:
            continue

        print(
            f"{i:>3}. "
            f"[Bot {bot['bot_id']:<3}] "
            f"{bot['symbol']:<10} | "
            f"{bot['timeframe']:<4} | "
            f"{bot['entry_strategy']:<25} -> {bot['exit_strategy']:<25} | "
            f"{bot['run_mode']:<8} | "
            f"Enabled: {enabled}"
        )


def choose_bot():
    bots = load_bots()

    print("\nChoose bot")
    print("  0. back")

    for i, (file, _) in enumerate(bots, start=1):
        print(
            f"{i:>3}. "
            f"{file.stem}"
        )

    choice = input("> ")

    if choice == "0":
        return None

    idx = int(choice) - 1
    return bots[idx]


def config_bot(file, data):

    while True:
        print("\nConfig fields")
        print("  0. back (save)")

        keys = list(data.keys())

        for i, k in enumerate(keys, start=1):
            print(f"{i:>3}. {k} = {data[k]}")

        choice = input("> ")

        if choice == "0":
            return

        key = keys[int(choice) - 1]

        current_value = data[key]

        print(f"Current value: {current_value}")
        new_value = input("New value > ")

        try:
            if isinstance(current_value, bool):
                new_value = new_value.lower() in ["true", "1", "yes"]

            elif isinstance(current_value, int):
                new_value = int(new_value)

            elif isinstance(current_value, float):
                new_value = float(new_value)

            else:
                new_value = str(new_value)

        except ValueError:
            print("Invalid value type.")
            continue

        data[key] = new_value
        save_bot(file, data)

        print("Saved.")


def show_menu():
    while True:

        print("\nShow Menu")
        print("0. back")
        print("1. all bots")
        print("2. enabled bots")
        print("3. disabled bots")

        choice = input("> ")

        if choice == "0":
            return
        elif choice == "1":
            show_bots()
        elif choice == "2":
            show_bots("enabled")
        elif choice == "3":
            show_bots("disabled")


def config_menu():

    while True:

        bot = choose_bot()

        if bot is None:
            return

        file, data = bot
        config_bot(file, data)


def set_bot_config(bot_number, field, value):
    file = CONFIG_DIR / f"bot_{bot_number}.json"

    if not file.exists():
        print(f"Bot config not found: {file}")
        return

    with open(file) as f:
        data = json.load(f)

    if field not in data:
        print(f"Field '{field}' not found")
        return

    old_value = data[field]
    new_value = value

    try:
        if isinstance(old_value, bool):
            new_value = value.lower() in ["true", "1", "yes"]

        elif isinstance(old_value, int):
            new_value = int(value)

        elif isinstance(old_value, float):
            new_value = float(value)

        else:
            new_value = str(value)

    except ValueError:
        print("Invalid value type")
        return

    data[field] = new_value

    with open(file, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Updated bot_{bot_number}: {field} {old_value} -> {new_value}")


def main():
    if len(sys.argv) > 1:

        command = sys.argv[1]

        if command == "show":

            if len(sys.argv) != 3:
                print(f"Usage: show <all | enabled | disabled>")
                return

            if len(sys.argv) == 2:
                show_bots()

            elif sys.argv[2] == "enabled":
                show_bots("enabled")

            elif sys.argv[2] == "disabled":
                show_bots("disabled")

            else:
                show_bots()

            return

        elif command == "config":

            if len(sys.argv) != 5:
                print("Usage: config <bot_number> <field> <value>")
                return

            bot_number = sys.argv[2]
            field = sys.argv[3]
            value = sys.argv[4]

            set_bot_config(bot_number, field, value)
            return

    while True:

        print("\nMain Menu")
        print("0. exit")
        print("1. show")
        print("2. config")

        choice = input("> ")

        if choice == "0":
            break
        elif choice == "1":
            show_menu()
        elif choice == "2":
            config_menu()


if __name__ == "__main__":
    main()