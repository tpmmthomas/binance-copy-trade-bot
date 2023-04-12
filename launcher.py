import os
import sys

def add_directories_to_path():
    current_directory = os.path.dirname(os.path.abspath(__file__))
    binance_directory = os.path.join(current_directory, "Binance")
    bybit_directory = os.path.join(current_directory, "Bybit")

    sys.path.append(binance_directory)
    sys.path.append(bybit_directory)

def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")

def main_menu():
    print("Hello, welcome to the Bybit/Binance bot! \n")
    print("Which exchange do you want to use?")
    print("1. Bybit - Currently working with Telegram")
    print("2. Binance - Currently working with Discord")
    print("3. Exit\n")
    return input(">> ")

def main():
    add_directories_to_path()

    import Binance.assist as binance_assist
    import Bybit.assist as bybit_assist

    while True:
        choice = main_menu()

        if choice == "1":
            clear_screen()
            bybit_assist.start()
        elif choice == "2":
            clear_screen()
            binance_assist.start()
        elif choice == "3":
            print("Exiting...")
            break
        else:
            clear_screen()
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    main()

    
    
