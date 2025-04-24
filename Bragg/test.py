import numpy as np
import pyaudio

# Parametry sygnału
freq = 50  # częstotliwość w Hz
sample_rate = 44100  # liczba próbek na sekundę
duration = 20  # czas trwania sygnału w sekundach
volume = 0.2  # głośność (0.0 do 1.0)
CHUNK = 1024 * 4  # rozmiar bufora

# Generowanie sygnału sinusoidalnego
t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
y = np.sin(2 * np.pi * freq * t)

# Skalowanie sygnału
y = y * volume

# Konwersja do formatu 16-bitowego
y = (y * 32767).astype(np.int16)

# Inicjalizacja PyAudio
p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=sample_rate, output=True, frames_per_buffer=CHUNK)

# Odtwarzanie sygnału
stream.write(y.tobytes())

# Zamykanie strumienia
stream.stop_stream()
stream.close()
p.terminate()
