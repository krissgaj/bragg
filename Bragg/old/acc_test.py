from smbus2 import SMBus
import time

LIS3DH_ADDR = 0x18  # Może być też 0x19

# === KONFIGURACJA ===
# Wybierz zakres pomiarowy:
# '2g', '4g', '8g', '16g'
scale = '16g'

# Wybierz tryb pracy:
# 'normal', 'high_res', 'low_power'
mode = 'high_res'
# =====================

# Mapowanie zakresu na ustawienia i przelicznik
scale_settings = {
    '2g':  (0b000 << 4, 1000.0),
    '4g':  (0b001 << 4, 500.0),
    '8g':  (0b010 << 4, 250.0),
    '16g': (0b011 << 4, 136.0),
}

# Mapowanie trybu na bity konfiguracyjne
mode_settings = {
    'normal':    0b00000000,
    'high_res':  0b10001000,  # HR on, BDU on
    'low_power': 0b00001000,  # LP on, BDU on
}

# Wybór ustawień
fs_bits, scale_divisor = scale_settings[scale]
ctrl_reg4 = mode_settings[mode] | fs_bits

# Rejestry
CTRL_REG1 = 0x20
CTRL_REG4 = 0x23
OUT_Z_L = 0x2C
OUT_Z_H = 0x2D

def twos_complement(val, bits):
    if val & (1 << (bits - 1)):
        val -= 1 << bits
    return val

with SMBus(1) as bus:
    # Aktywuj LIS3DH: 100 Hz, wszystkie osie włączone
    bus.write_byte_data(LIS3DH_ADDR, CTRL_REG1, 0x57)  # 0b01010111

    # Ustaw zakres i tryb pracy
    bus.write_byte_data(LIS3DH_ADDR, CTRL_REG4, ctrl_reg4)

    time.sleep(0.1)

    while True:
        z_l = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_L)
        z_h = bus.read_byte_data(LIS3DH_ADDR, OUT_Z_H)

        # Połącz bajty i dostosuj do trybu
        raw = twos_complement((z_h << 8) | z_l, 16)

        if mode == 'high_res':
            raw >>= 4  # 12-bit
        elif mode == 'normal':
            raw >>= 6  # 10-bit
        elif mode == 'low_power':
            raw >>= 8  # 8-bit

        z_g = raw / scale_divisor
        print(f"Przyspieszenie Z: {z_g:.3f} g")
        time.sleep(0.5)

