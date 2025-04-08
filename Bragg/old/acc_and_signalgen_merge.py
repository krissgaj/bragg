import time
import smbus2 as smbus
import numpy as np
import sounddevice as sd
import csv
from datetime import datetime

# --- KONFIGURACJA LIS3DH --- Akcelerometr

# Adres I2C czujnika LIS3DH
LIS3DH_ADDR = 0x18  # Adres czujnika LIS3DH na szynie I2C. Adres 0x18 jest używany do komunikacji z czujnikiem.

# Rejestr CTRL_REG1 - Konfiguracja trybu pracy i częstotliwości próbkowania
CTRL_REG1 = 0x20  # Adres rejestru, który kontroluje podstawowe ustawienia czujnika, takie jak tryb pracy i częstotliwość próbkowania.
# Możesz ustawić różne parametry w tym rejestrze, np. włączenie/wyłączenie osi, tryb ciągłego pomiaru itp.
# Wartość w tym rejestrze będzie zależała od tego, jakie ustawienia chcesz zastosować (np. 0x57 - włączenie wszystkich osi z częstotliwością próbkowania 100 Hz).
# CTRL_REG1, 0x57) 200 Hz CTRL_REG1, 0x58) 400 Hz

# Rejestr CTRL_REG4 - Konfiguracja zakresu pomiarowego i ustawień filtra
CTRL_REG4 = 0x98  # Adres rejestru, który kontroluje zakres pomiarowy oraz ustawienia filtrów. Wczescniej 0x23
# W tym rejestrze możesz ustawić zakres przyspieszenia (np. ±2g, ±4g, ±8g, ±16g), a także inne opcje, takie jak filtracja i ustawienia osi.
# Wartość 0x98 ustawia zakres pomiarowy na ±16g oraz włącza filtr.

# Rejestr OUT_Z_L - Dolna część odczytu danych osi Z (8 najmniej znaczących bitów)
OUT_Z_L = 0x2C  # Adres rejestru, który zawiera dolną część wartości osi Z. To jest 8 najmniej znaczących bitów wyniku.
# Odczytując ten rejestr, uzyskujemy część danych dotyczących przyspieszenia na osi Z (dolne 8 bitów).

# Rejestr OUT_Z_H - Górna część odczytu danych osi Z (8 najbardziej znaczących bitów)
OUT_Z_H = 0x2D  # Adres rejestru, który zawiera górną część wartości osi Z. To jest 8 najbardziej znaczących bitów wyniku.
# Odczytując ten rejestr, uzyskujemy kolejną część danych dotyczących przyspieszenia na osi Z (górne 8 bitów).

# --- PARAMETRY CZUJNIKA ---
odr_hz = 200              # Częstotliwość próbkowania (Hz)
dt = 1.0 / odr_hz         # Interwał próbkowania
mode = 'high_res'         # 'low_power', 'normal', 'high_res'
range_g = 16              # Pełna skala: 2, 4, 8, 16 [g]
scale_divisor = 1365      # dla 16g w high_res (odczyt 12-bit: 2^12/2 = 2048, 16g -> 2048/16 = 136.5 -> 1365 po podzieleniu przez 10)

czestotliwosc = 20        # Częstotliwość dźwięku [Hz]
czas_trwania = 2.0       # Czas trwania dźwięku [s]
probkowanie = 44100      # Częstotliwość próbkowania dźwięku [Hz]
amplituda = 0.1          # Amplituda dźwięku
window_size = 5          # Rozmiar okna dla filtracji

# --- INICJALIZACJA I2C ---
bus = smbus.SMBus(1)
bus.write_byte_data(LIS3DH_ADDR, CTRL_REG1, 0x57)
bus.write_byte_data(LIS3DH_ADDR, CTRL_REG4, 0x98)

def twos_complement(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

# --- KALIBRACJA ---
offset_samples = 100
offset_sum = 0
for _ in range(offset_samples):
    z_l = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_L)
    z_h = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_H)
    raw = twos_complement((z_h << 8) | z_l, 16)
    raw >>= 4
    offset_sum += raw / scale_divisor
    time.sleep(dt)
offset_z = offset_sum / offset_samples

# --- DŹWIĘK --- Zamiast generowania sygnału w zwykły sposób, użyj funkcji sweep z parametrami
def sweep_with_amplitude_and_duration(start_freq=5, end_freq=200, freq_duration=1, sample_rate=44100, smooth_transition=True, pause_duration=0.5, amplitude=0.0, freq_step=1, total_duration=None, gradual_amplitude_increase=False, amplitude_rise_time=1, amplitude_start=0.0, amplitude_end=1.0):
    """
    Funkcja do generowania sweepu z możliwością stopniowego zwiększania amplitudy, z parametrami kontroli narostu amplitudy.
    """
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
        if total_duration is None:
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
total_duration = 5  # 9. Całkowity czas trwania sweepu (sekundy)
gradual_amplitude_increase = False  # 10. Włącz stopniowe zwiększanie amplitudy
amplitude_rise_time = 0.5  # 11. Czas narostu amplitudy w sekundach
amplitude_start = 0.05    # 12. Początkowa amplituda
amplitude_end = 0.5      # 13. Końcowa amplituda

# Uruchomienie funkcji sweep
sweep_with_amplitude_and_duration(start_freq, end_freq, freq_duration, sample_rate, smooth_transition, pause_duration, amplitude, freq_step, total_duration, gradual_amplitude_increase, amplitude_rise_time, amplitude_start, amplitude_end)

# --- POMIAR --- Dodanie metody trapezów do obliczeń
a_buffer = [0.0] * window_size
sample_count = 0
start_time = time.time()
start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
pomiar_danych = []

previous_velocity = 0
previous_time = 0

while time.time() - start_time < czas_trwania:
    z_l = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_L)
    z_h = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_H)
    raw = twos_complement((z_h << 8) | z_l, 16)
    raw >>= 4
    az_g = raw / scale_divisor - offset_z

    a_buffer.append(az_g)
    a_buffer.pop(0)
    az_filtered = sum(a_buffer) / len(a_buffer)
    if abs(az_filtered) < 0.01:
        az_filtered = 0.0

    az_ms2 = az_filtered * 9.81
    
    # Obliczanie prędkości i drogi metodą trapezów
    if previous_time == 0:
        velocity = 0  # Początkowa prędkość
    else:
        velocity = previous_velocity + 0.5 * (az_ms2 + previous_velocity) * (time.time() - previous_time)
    
    distance = previous_velocity * (time.time() - previous_time) + 0.5 * az_ms2 * (time.time() - previous_time) ** 2
    previous_velocity = velocity
    previous_time = time.time()

    audio_value = amplituda * np.sin(2 * np.pi * czestotliwosc * (sample_count / probkowanie))
    pomiar_danych.append([datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                         sample_count,
                         distance * 1000,  # przekształcone na mm
                         audio_value])

    time.sleep(dt)
    sample_count += 1

sd.wait()

# --- OBLICZENIE MIN/MAX ---
drogi_mm = [row[2] for row in pomiar_danych]
min_dist = min(drogi_mm)
max_dist = max(drogi_mm)

# --- ZAPIS CSV ---
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
