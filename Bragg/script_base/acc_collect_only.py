import time
import smbus2 as smbus
import csv
import numpy as np
from datetime import datetime

# --- PARAMETRY ---
odr_hz = 400  # Częstotliwość próbkowania (200 Hz)
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

def twos_complement(val, bits):
    """Convert raw data to signed integer."""
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

def init_lis3dh():
    """Initialize LIS3DH accelerometer."""
    try:
        bus.write_byte_data(LIS3DH_ADDR, LIS3DH_CTRL_REG1, 0x57)  # 400 Hz, enabled, normal mode
        bus.write_byte_data(LIS3DH_ADDR, LIS3DH_CTRL_REG4, 0x98)  # ±16g range
        time.sleep(0.1)
    except Exception as e:
        print(f"Error initializing LIS3DH: {e}")

def read_z_acceleration():
    """Read Z-axis acceleration."""
    try:
        z_l = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_L)
        z_h = bus.read_byte_data(LIS3DH_ADDR, LIS3DH_OUT_Z_H)
        raw = twos_complement((z_h << 8) | z_l, 16)
        raw >>= 4  # Right shift by 4 bits
        return raw / scale_divisor
    except Exception as e:
        print(f"Error reading Z acceleration: {e}")
        return 0.0

def calculate_offset(samples=100):
    """Calculate offset for Z-axis."""
    offset_sum = 0
    for _ in range(samples):
        offset_sum += read_z_acceleration()
        time.sleep(dt)
    return offset_sum / samples

def low_pass_filter(data, window_size):
    """Apply low-pass filter."""
    return np.mean(data[-window_size:])

def filter_noise(accel_value, threshold=0.02):
    """Filter out noise."""
    return 0.0 if abs(accel_value) < threshold else accel_value

def save_to_csv(pomiar_danych, raw_data):
    """Save data to CSV file."""
    try:
        with open("pomiar_przyspieszenia.csv", mode="w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Czas [UTC]", "Numer próbki", "Surowe przyspieszenie Z [g]", "Przyspieszenie Z [g]"])
            for i in range(len(pomiar_danych)):
                writer.writerow([pomiar_danych[i][0], pomiar_danych[i][1], raw_data[i], pomiar_danych[i][2]])
        print("Zapisano dane do 'pomiar_przyspieszenia.csv'.")
    except Exception as e:
        print(f"Error saving to CSV: {e}")

def main():
    """Main function."""
    print("Inicjalizacja akcelerometru LIS3DH...")
    init_lis3dh()

    print("Obliczanie offsetu...")
    offset_z = calculate_offset()
    print(f"Obliczony offset Z: {offset_z:.4f} g")

    time_duration = 2  # Duration of measurement in seconds
    num_samples = int(time_duration / dt)  # Number of samples
    pomiar_danych = []  # List to store measurement results
    raw_data = []  # List to store raw acceleration data
    filter_data = []  # Queue for filtering

    print("Rozpoczynamy pomiar...")
    for sample_count in range(num_samples):
        z_accel = read_z_acceleration()
        raw_data.append(z_accel)
        z_accel_corrected = filter_noise(z_accel - offset_z)
        filter_data.append(z_accel_corrected)
        filtered_z_accel = low_pass_filter(filter_data, filter_window)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
        pomiar_danych.append([current_time, sample_count, filtered_z_accel])
        time.sleep(dt)

    save_to_csv(pomiar_danych, raw_data)

if __name__ == "__main__":
    main()