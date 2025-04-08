import time
import smbus2 as smbus
import csv
import numpy as np
from datetime import datetime
import sounddevice as sd

# --- PARAMETRY ---
odr_hz = 400  # Częstotliwość próbkowania (400 Hz)
dt = 1.0 / odr_hz  # Krok czasowy
mode = 'high_res'  # Tryb wysokiej rozdzielczości
range_g = 16  # Zakres ±16g
scale_divisor = 1365  # Skala dla ±16g w trybie 12-bitowym z przesunięciem o 4 bity
filter_window = 10  # Okno dla filtru (średnia ruchoma)

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
    bus.write_byte_data(LIS3DH_ADDR, LIS3DH_CTRL_REG4, 0x98)  # 0x10: ±16g zakres
    time.sleep(0.1)

# Funkcja do odczytu przyspieszenia z osi Z
def read_z_acceleration():
    # Odczyt danych z rejestru dla osi Z
    z_l = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_L)
    z_h = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_H)
    raw = twos_complement((z_h << 8) | z_l, 16)  # Odczyt wartości Z
    raw >>= 4  # Przesunięcie w prawo o 4 bity (w zależności od ustawionego zakresu)
    z_accel = raw / scale_divisor  # Przemiana na jednostki g
    return z_accel

# Funkcja do obliczenia offsetu (średnia wartość przyspieszenia w stanie spoczynku)
def calculate_offset(samples=100):
    offset_sum = 0
    for _ in range(samples):
        z_accel = read_z_acceleration()
        offset_sum += z_accel
        time.sleep(dt)
    return offset_sum / samples

# Funkcja do zapisu danych do pliku CSV
def save_to_csv(pomiar_danych, raw_data):
    with open("pomiar_przyspieszenia.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["Czas [UTC]", "Numer próbki", "Surowe przyspieszenie Z [g]", "Przyspieszenie Z [g]"])
        for i in range(len(pomiar_danych)):
            writer.writerow([pomiar_danych[i][0],  # Czas
                             pomiar_danych[i][1],  # Numer próbki
                             raw_data[i],  # Surowe przyspieszenie Z
                             pomiar_danych[i][2]])  # Skorygowane i przefiltrowane przyspieszenie Z
    print("Zapisano dane do 'pomiar_przyspieszenia.csv'.")

# Funkcja do generowania sygnału sinusoida
def play_sine_wave(czestotliwosc=50, czas_trwania=10.0, probkowanie=96000, amplituda=0.3):
    t = np.linspace(0, czas_trwania, int(probkowanie * czas_trwania), endpoint=False)
    sygnal = amplituda * np.sin(2 * np.pi * czestotliwosc * t)
    sd.play(sygnal, probkowanie)
    sd.wait()

# Funkcja do generowania sweepu
def sweep_with_amplitude_and_duration(start_freq=10, end_freq=150, freq_duration=2.5, sample_rate=44100, smooth_transition=False, pause_duration=0.5, amplitude=0.1, freq_step=3, total_duration=10, gradual_amplitude_increase=False, amplitude_rise_time=0.5, amplitude_start=0.05, amplitude_end=0.5):
    freqs = np.arange(start_freq, end_freq, freq_step)

    def generate_signal(freq, duration, amplitude_start, amplitude_end, sample_rate):
        t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
        if gradual_amplitude_increase:
            rise_time_samples = int(sample_rate * amplitude_rise_time)
            amplitude_sweep = np.linspace(amplitude_start, amplitude_end, rise_time_samples) if len(t) >= rise_time_samples else np.ones(len(t)) * amplitude_end
            amplitude_sweep = np.concatenate([amplitude_sweep, np.ones(len(t) - len(amplitude_sweep)) * amplitude_end])
        else:
            amplitude_sweep = np.ones(len(t)) * amplitude_end
        return amplitude_sweep * np.sin(2 * np.pi * freq * t)

    if smooth_transition:
        total_duration = (end_freq - start_freq) / freq_step * freq_duration
        t = np.linspace(0, total_duration, int(sample_rate * total_duration), endpoint=False)
        freq_sweep = np.linspace(start_freq, end_freq, len(t))
        sweep_signal = generate_signal(freq_sweep, total_duration, amplitude_start, amplitude_end, sample_rate)
        sd.play(sweep_signal, samplerate=sample_rate)
        sd.wait()

    else:
        total_duration = len(freqs) * (freq_duration + pause_duration)
        for freq in freqs:
            t = np.linspace(0, freq_duration, int(sample_rate * freq_duration), endpoint=False)
            signal = generate_signal(freq, freq_duration, amplitude_start, amplitude_end, sample_rate)
            sd.play(signal, samplerate=sample_rate)
            sd.wait()
            time.sleep(pause_duration)

# Parametry sweepu
start_freq = 10        # 1. Początkowa częstotliwość (5 Hz)
end_freq = 50        # 2. Końcowa częstotliwość (200 Hz)
freq_duration = 2.5   # 3. Czas trwania każdej częstotliwości w sekundach
sample_rate = 44100   # 4. Częstotliwość próbkowania (Hz)
smooth_transition = True  # 5. Ustaw na True, aby uzyskać płynne przejście
pause_duration = 0.5  # 6. Czas pauzy pomiędzy częstotliwościami (jeśli smooth_transition=False)
amplitude = 0.1      # 7. Początkowa amplituda (0.0 do 1.0)
freq_step = 3        # 8. Krok zmiany częstotliwości (np. 1, 3, 15, etc.)
total_duration = 2  # 9. Całkowity czas trwania sweepu (sekundy)
gradual_amplitude_increase = False  # 10. Włącz stopniowe zwiększanie amplitudy
amplitude_rise_time = 0.5  # 11. Czas narostu amplitudy w sekundach
amplitude_start = 0.05    # 12. Początkowa amplituda
amplitude_end = 0.1      # 13. Końcowa amplituda

# Główna funkcja
def main():
    # Inicjalizacja akcelerometru LIS3DH
    print("Inicjalizacja akcelerometru LIS3DH...")
    init_lis3dh()

    # Obliczenie offsetu (średnia wartość przyspieszenia w stanie spoczynku)
    print("Obliczanie offsetu...")
    offset_z = calculate_offset()
    print(f"Obliczony offset Z: {offset_z:.4f} g")

    time_duration = total_duration  # Czas trwania pomiaru w sekundach
    num_samples = int((time_duration*freq_duration )/ dt)  # Liczba próbek
    pomiar_danych = []  # Lista do przechowywania wyników pomiarów
    raw_data = []  # Lista do przechowywania surowych danych przyspieszenia

    # Kolejka do filtracji (średnia ruchoma)
    filter_data = []

    # Pętla zbierająca dane przez określony czas
    for _ in range(num_samples):
        z_accel = read_z_acceleration() - offset_z  # Przemieszczenie w odniesieniu do offsetu
        filtered_data = z_accel  # Zastosowanie filtracji (jeśli potrzeba)
        pomiar_danych.append([datetime.utcnow(), _, filtered_data])
        raw_data.append(z_accel)
        time.sleep(dt)

    # Generowanie sweepu i zbieranie danych w tle
    print("Generowanie sweepu i zbieranie danych...")
    sweep_with_amplitude_and_duration(start_freq, end_freq, freq_duration, sample_rate, smooth_transition, pause_duration, amplitude, freq_step, total_duration, gradual_amplitude_increase, amplitude_rise_time, amplitude_start, amplitude_end)

    # Zapisanie danych po zakończeniu sweepu
    save_to_csv(pomiar_danych, raw_data)

# Uruchomienie programu
if __name__ == "__main__":
    main()
