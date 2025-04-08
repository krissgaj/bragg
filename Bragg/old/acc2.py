import time
import smbus2 as smbus
import numpy as np
import sounddevice as sd
from datetime import datetime
import csv

# --- PARAMETRY ---
odr_hz = 200  # Częstotliwość próbkowania (200 Hz)
dt = 1.0 / odr_hz  # Krok czasowy
mode = 'high_res'  # Tryb wysokiej rozdzielczości
range_g = 16  # Zakres ±16g
scale_divisor = 1365  # Skala dla ±16g w trybie 12-bitowym z przesunięciem o 4 bity

# Parametry dźwięku
czestotliwosc = 50  # Częstotliwość dźwięku (50 Hz)
amplituda = 0.1  # Amplituda dźwięku
czas_trwania = 10  # Czas trwania dźwięku (sekundy)
probkowanie = 44100  # Częstotliwość próbkowania dźwięku (44100 Hz dla wysokiej jakości)

# Inicjalizacja magistrali I2C (zakładając, że akcelerometr jest podłączony do Raspberry Pi lub STM32)
I2C_BUS = 1  # dla Raspberry Pi (dla STM32 numer magistrali może być inny)
LIS3DH_ADDR = 0x18  # Adres LIS3DH (domyślny)

# Rejestry konfiguracji LIS3DH
LIS3DH_OUT_X_L = 0x28  # Początek danych (X, Y, Z) na wyjściu akcelerometru
LIS3DH_OUT_Z_L = 0x2C  # Rejestr danych Z (niski bajt)
LIS3DH_OUT_Z_H = 0x2D  # Rejestr danych Z (wysoki bajt)
LIS3DH_CTRL_REG1 = 0x20
LIS3DH_CTRL_REG4 = 0x23

# Inicjalizacja magistrali I2C
bus = smbus.SMBus(I2C_BUS)

# Funkcja do obliczania liczby w formacie uzupełnienia do dwóch
def twos_complement(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

# Funkcja do inicjalizacji LIS3DH
def init_lis3dh():
    # Ustawienie sensora na tryb aktywny, 400 Hz, ±16g
    bus.write_byte_data(LIS3DH_ADDR, LIS3DH_CTRL_REG1, 0x57)  # 0x57: 400 Hz, włączony, normalny tryb
    bus.write_byte_data(LIS3DH_ADDR, LIS3DH_CTRL_REG4, 0x10)  # 0x10: ±16g zakres
    time.sleep(0.1)

# Funkcja do kalibracji osi Z
def calibrate_offset():
    offset_sum = 0
    offset_samples = 100  # Liczba próbek do kalibracji
    print("Rozpoczynanie kalibracji... Zbieranie próbek...")
    for _ in range(offset_samples):
        z_l = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_L)
        z_h = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_H)
        
        # Odczyt surowych danych z osi Z
        raw = twos_complement((z_h << 8) | z_l, 16)  # Złączenie niskiego i wysokiego bajtu
        raw >>= 4  # Przesunięcie w prawo o 4 bity (w zależności od ustawionego zakresu)
        
        # Dodanie odczytu do sumy
        offset_sum += raw / scale_divisor
        time.sleep(dt)  # Opóźnienie między próbkami
        
    offset_z = offset_sum / offset_samples  # Oblicz średnią wartość offsetu
    print(f"Offset Z: {offset_z:.4f} g")
    return offset_z

# Funkcja do odczytu przyspieszenia z osi Z
def read_z_acceleration():
    # Odczyt danych z rejestru dla osi Z
    z_l = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_L)
    z_h = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_H)
    raw = twos_complement((z_h << 8) | z_l, 16)  # Odczyt wartości Z
    raw >>= 4  # Przesunięcie w prawo o 4 bity (w zależności od ustawionego zakresu)
    z_accel = raw / scale_divisor  # Przemiana na jednostki g
    return z_accel

# Funkcja do filtrowania szumu (ustawienie wartości poniżej 0.01g na 0)
def filter_noise(accel_value, threshold=0.01):
    if abs(accel_value) < threshold:
        return 0.0
    return accel_value

# Funkcja generująca sygnał dźwiękowy w najwyższej jakości
def generate_audio_signal(czas_trwania, probkowanie, czestotliwosc, amplituda):
    # Wysoka jakość z float32, próbki w sinusoidalnym kształcie
    t = np.linspace(0, czas_trwania, int(probkowanie * czas_trwania), endpoint=False)
    sygnal = amplituda * np.sin(2 * np.pi * czestotliwosc * t)
    
    print("Odtwarzanie dźwięku...")
    sd.play(sygnal, probkowanie, blocking=True)  # blocking=True, żeby poczekać aż dźwięk się zakończy
    print("Dźwięk zakończony.")

# Implementacja metody Rungego-Kutty 4. rzędu
def runge_kutta(acceleration, time_step):
    velocity = 0.0  # Początkowa prędkość
    displacement = 0.0  # Początkowe przemieszczenie

    # Obliczenia RK4 dla prędkości i przemieszczenia
    for i in range(len(acceleration) - 1):
        t = i * time_step
        a1 = acceleration[i]
        v1 = velocity
        x1 = displacement

        a2 = acceleration[i] + 0.5 * time_step * a1
        v2 = velocity + 0.5 * time_step * a1
        x2 = displacement + 0.5 * time_step * v1

        a3 = acceleration[i] + 0.5 * time_step * a2
        v3 = velocity + 0.5 * time_step * a2
        x3 = displacement + 0.5 * time_step * v2

        a4 = acceleration[i] + time_step * a3
        v4 = velocity + time_step * a3
        x4 = displacement + time_step * v3

        velocity += (time_step / 6.0) * (a1 + 2*a2 + 2*a3 + a4)
        displacement += (time_step / 6.0) * (v1 + 2*v2 + 2*v3 + v4)

    return velocity, displacement

# --- ZAPIS CSV ---
def save_to_csv(pomiar_danych, min_dist, max_dist, start_timestamp, czestotliwosc, czas_trwania, range_g, scale_divisor, dt):
    with open("pomiar_drogi.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([
            "Czas startu pomiaru", "Częstotliwość [Hz]", "Czas trwania [s]",
            "Zakres [g]", "Skala divisor", "Czas próbkowania [s]"
        ])
        writer.writerow([
            start_timestamp, czestotliwosc, czas_trwania, range_g, scale_divisor, dt
        ])
        writer.writerow([
            "Minimalne przemieszczenie [mm]", "Maksymalne przemieszczenie [mm]"
        ])
        writer.writerow([min_dist, max_dist])
        writer.writerow([
            "Czas [UTC]", "Numer próbki", "Droga [mm]", "Wartość sygnału audio"
        ])
        for row in pomiar_danych:
            writer.writerow(row)

    print(f"Zapisano dane do 'pomiar_drogi.csv'. Min: {min_dist:.5f} mm, Max: {max_dist:.5f} mm")

# Główna funkcja
def main():
    start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    print("Inicjalizacja akcelerometru LIS3DH...")
    init_lis3dh()
    
    # Kalibracja i obliczenie offsetu Z
    offset_z = calibrate_offset()
    
    time_step = dt  # Krok czasowy
    time_duration = 10  # Czas trwania w sekundach
    num_samples = int(time_duration / time_step)
    
    # Przechowywanie danych
    accelerations = []
    pomiar_danych = []  # Lista do przechowywania wyników pomiarów
    min_dist = float('inf')
    max_dist = float('-inf')

    # Odtwarzanie dźwięku po obliczeniu offsetu
    print("Odtwarzanie dźwięku...")
    generate_audio_signal(czas_trwania, probkowanie, czestotliwosc, amplituda)

    # Odczyt przyspieszenia z osi Z
    for sample_count in range(num_samples):
        z_accel = read_z_acceleration()  # Odczyt przyspieszenia Z
        z_accel -= offset_z  # Korekcja odczytu o offset
        
        # Filtrowanie szumu poniżej 0.01g
        z_accel = filter_noise(z_accel)
        
        accelerations.append(z_accel)
        
        # Generowanie wartości audio na podstawie czasu
        audio_value = amplituda * np.sin(2 * np.pi * czestotliwosc * (sample_count / probkowanie))
        
        # Obliczanie przemieszczenia w mm
        displacement = z_accel * 1000  # Zakładając przemieszczenie w mm
        
        min_dist = min(min_dist, displacement)
        max_dist = max(max_dist, displacement)

        # Zapis danych pomiarowych
        pomiar_danych.append([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),  # Czas w milisekundach
            sample_count,
            displacement,  # Droga w mm
            audio_value
        ])
        
        time.sleep(time_step)

    accelerations = np.array(accelerations)
    
    # Całkowanie przyspieszenia (RK4)
    velocity, displacement = runge_kutta(accelerations, time_step)

    # Zapis danych do CSV
    save_to_csv(pomiar_danych, min_dist, max_dist, start_timestamp, czestotliwosc, czas_trwania, range_g, scale_divisor, dt)

    # Wyniki
    print(f"Prędkość końcowa: {velocity} m/s")
    print(f"Przemieszczenie: {displacement} m")

if __name__ == "__main__":
    main()
