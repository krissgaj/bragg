import time
import smbus2 as smbus
import numpy as np
import sounddevice as sd
import csv
from datetime import datetime

# --- LIS3DH KONFIGURACJA ---
# Parametry LIS3DH
LIS3DH_ADDR = 0x18
I2C_ADRES = 0x18
CTRL_REG1 = 0x20
CTRL_REG4 = 0x23

OUT_Z_L = 0x2C
OUT_Z_H = 0x2D

REG_CTRL1 = 0x20
REG_CTRL4 = 0x23
REG_OUT_Z_L = 0x2C
REG_OUT_Z_H = 0x2D

# --- PARAMETRY CZUJNIKA ---
odr_hz = 400              # Częstotliwość próbkowania (Hz)
dt = 1.0 / odr_hz         # Interwał próbkowania
mode = 'high_res'        # 'low_power', 'normal', 'high_res'
range_g = 16             # Pełna skala: 2, 4, 8, 16 [g]
scale_divisor = 1365     # dla 16g w high_res (odczyt 12-bit: 2^12/2 = 2048, 16g -> 2048/16 = 136.5 -> 1365 po podzieleniu przez 10)

czestotliwosc = 20
czas_trwania = 2.0
probkowanie = 44100
amplituda = 0.5
window_size = 5

# --- INICJALIZACJA I2C ---
bus = smbus.SMBus(1)
bus.write_byte_data(LIS3DH_ADDR, CTRL_REG1, 0x58)
bus.write_byte_data(LIS3DH_ADDR, CTRL_REG4, 0x98)

def twos_complement(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

# --- KALIBRACJA OFFSETU W SPOCZYNKU ---
print("Kalibracja...")
offset_samples = 100
offset_sum = 0
for _ in range(offset_samples):
    z_l = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_L)
    z_h = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_H)
    raw = twos_complement((z_h << 8) | z_l, 16)
    raw >>= 4  # high_res
    offset_sum += raw / scale_divisor
    time.sleep(dt)
offset_z = offset_sum / offset_samples
print(f"Offset Z = {offset_z:.3f} g\n")

# --- START DŹWIĘKU ---
print("Start drgań audio...")
t = np.linspace(0, czas_trwania, int(probkowanie * czas_trwania), endpoint=False)
sygnal = amplituda * np.sin(2 * np.pi * czestotliwosc * t)
sd.play(sygnal, probkowanie)

# --- DŹWIĘK ---
t = np.linspace(0, czas_trwania, int(probkowanie * czas_trwania), endpoint=False)
sygnal = amplituda * np.sin(2 * np.pi * czestotliwosc * t)
sd.play(sygnal, probkowanie)

# --- POMIAR ---
a_buffer = [0.0] * window_size
sample_count = 0
start_time = time.time()
start_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
pomiar_danych = []

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
    velocity = az_ms2 * dt
    distance = velocity * dt

    audio_value = amplituda * np.sin(2 * np.pi * czestotliwosc * (sample_count / probkowanie))
    pomiar_danych.append([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
        sample_count,
        distance * 1000,
        audio_value
    ])

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
