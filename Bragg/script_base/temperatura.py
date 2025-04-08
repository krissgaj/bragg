
# bragg@raspberrypi:~/Desktop/Bragg $ source .Bragg/bin/activate

import time
import board
import busio
from adafruit_bmp280 import Adafruit_BMP280_I2C
from adafruit_ahtx0 import AHTx0
from datetime import datetime
import csv

# Inicjalizacja I2C
i2c = busio.I2C(board.SCL, board.SDA)
bmp280 = Adafruit_BMP280_I2C(i2c)
aht20 = AHTx0(i2c)

# Nazwa pliku CSV
csv_file = 'temp_pressure_hum.csv'

# Nagłówki kolumn
headers = ['Sample Number', 'Timestamp', 'Temperature (°C)', 'Pressure (hPa)', 'Humidity (%)']

# Tworzenie pliku CSV i zapisywanie nagłówków
with open(csv_file, mode='w', newline='') as file:
    writer = csv.writer(file)
    writer.writerow(headers)

# Funkcja do odczytu i zapisu danych przez określony czas
def read_and_save_data(measurement_interval, duration):
    start_time = time.time()
    sample_number = 1
    while time.time() - start_time < duration:
        iteration_start_time = time.time()
        
        # Odczyt danych z czujnika BMP280
        temperature = round(bmp280.temperature, 3)  # Odczyt temperatury i zaokrąglenie do tysięcznych
        pressure = round(bmp280.pressure, 2)  # Odczyt ciśnienia i zaokrąglenie do dwóch miejsc po przecinku

        # Odczyt danych z czujnika AHT20
        humidity = round(aht20.relative_humidity, 2)  # Odczyt wilgotności i zaokrąglenie do dwóch miejsc po przecinku

        # Pobranie bieżącej pieczątki czasowej z milisekundami
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # Wyświetlenie wyników
        print(f'Sample Number: {sample_number}')
        print(f'Temperature: {temperature} °C')
        print(f'Pressure: {pressure} hPa')
        print(f'Humidity: {humidity} %')
        print(f'Timestamp: {timestamp}')  # Wyświetlenie pieczątki czasowej

        # Zapis danych do pliku CSV
        with open(csv_file, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow([sample_number, timestamp, temperature, pressure, humidity])

        # Zwiększenie numeru próbki
        sample_number += 1

        # Czekaj określoną liczbę sekund przed kolejnym odczytem
        time.sleep(max(0, measurement_interval - (time.time() - iteration_start_time)))

# Ustawienie czasu pomiaru i całkowitego czasu trwania w sekundach
measurement_interval = 0.2  # Pomiar co 0.2 sekundy
duration = 20  # Całkowity czas trwania pomiaru 5 sekund
read_and_save_data(measurement_interval, duration)