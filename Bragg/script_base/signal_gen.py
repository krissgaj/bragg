
"""
import numpy as np
import sounddevice as sd

# Parametry sygnału
czestotliwosc = 50      # Hz (np. A4)
czas_trwania = 10.0       # sekundy
probkowanie = 96000      # standard audio
amplituda = 0.3          # max 1.0

# Generowanie próbek
t = np.linspace(0, czas_trwania, int(probkowanie * czas_trwania), endpoint=False)
sygnal = amplituda * np.sin(2 * np.pi * czestotliwosc * t)

# Odtwarzanie przez wyjście audio
sd.play(sygnal, probkowanie)
sd.wait()
"""

import numpy as np
import sounddevice as sd
import time
import csv
from datetime import datetime, timedelta

def generate_signal(freq, duration, amplitude, sample_rate):
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    
    if isinstance(freq, (int, float)):
        freq_array = np.ones_like(t) * freq
    else:
        freq_array = freq

    return amplitude * np.sin(2 * np.pi * freq_array * t), t

def sweep_with_amplitude_and_duration(start_freq=10, end_freq=100, freq_duration=1, sample_rate=96000, smooth_transition=False,
                                      pause_duration=0.5, amplitude=0.1, freq_step=10, total_duration=10,
                                      gradual_amplitude_increase=False, amplitude_rise_time=0.5,
                                      amplitude_start=0.05, amplitude_end=0.5, csv_filename="sweep_output.csv"):
    
    print("Starting the sweep generation...")
    print(f"Smooth Transition: {smooth_transition}")
    print(f"Frequency Step: {freq_step}")
    print(f"Total Duration: {total_duration}")
    
    freqs = np.arange(start_freq, end_freq + freq_step, freq_step)  # Include end_freq in the range
    all_samples = []

    start_datetime = datetime.now()
    sample_counter = 0
    step_size = int(sample_rate * 0.005)  # co 5 ms

    if smooth_transition:
        t = np.linspace(0, total_duration, int(sample_rate * total_duration), endpoint=False)
        freq_sweep = np.linspace(start_freq, end_freq, len(t))

        sweep_signal, _ = generate_signal(freq_sweep, total_duration, amplitude, sample_rate)

        sd.play(sweep_signal, samplerate=sample_rate)
        sd.wait()

        for i in range(0, len(sweep_signal), step_size):
            current_time = start_datetime + timedelta(seconds=i / sample_rate)
            timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
            all_samples.append((i + 1, timestamp_str, round(sweep_signal[i], 5), round(freq_sweep[i], 2)))

    else:
        for freq in freqs:
            signal, t = generate_signal(freq, freq_duration, amplitude, sample_rate)

            sd.play(signal, samplerate=sample_rate)
            sd.wait()

            for i in range(0, len(signal), step_size):
                current_time = start_datetime + timedelta(seconds=sample_counter / sample_rate)
                timestamp_str = current_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                all_samples.append((sample_counter + 1, timestamp_str, round(signal[i], 5), round(freq, 2)))
                sample_counter += step_size

            time.sleep(pause_duration)

    with open(csv_filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Parameter", "Value"])
        writer.writerow(["Start Frequency", start_freq])
        writer.writerow(["End Frequency", end_freq])
        writer.writerow(["Frequency Duration", freq_duration])
        writer.writerow(["Smooth Transition", smooth_transition])
        writer.writerow(["Pause Duration", pause_duration])
        writer.writerow(["Amplitude", amplitude])
        writer.writerow(["Frequency Step", freq_step])
        writer.writerow(["Total Duration", total_duration])
        writer.writerow(["Gradual Amplitude Increase", gradual_amplitude_increase])
        writer.writerow(["Amplitude Rise Time", amplitude_rise_time])
        writer.writerow(["Amplitude Start", amplitude_start])
        writer.writerow(["Amplitude End", amplitude_end])
        writer.writerow(["Sample Rate", sample_rate])
        
        writer.writerow([])
        
        writer.writerow(["Sample Number", "Timestamp", "Sine value", "Frequency (Hz)"])
        writer.writerows(all_samples)

    print("Sweep signal has been generated and saved to 'sweep_output.csv'.")

# ---------------------------------------------------- Parametry sweepu ----------------------------------------------------

start_freq = 10                     # 1. Początkowa częstotliwość (np.:5 Hz)
end_freq = 150                      # 2. Końcowa częstotliwość (np.: 200 Hz)
freq_duration = 1                   # 3. Czas trwania każdej częstotliwości w sekundach

smooth_transition = False           # 4. Ustaw na True aby uzyskać płynne przejście
pause_duration = 0.5                # 5. Czas pauzy pomiędzy częstotliwościami (jeśli smooth_transition=False)

amplitude = 0.2                     # 6. Początkowa amplituda (0.0 do 1.0)
freq_step = 5                      # 7. Krok zmiany częstotliwości (np. 1 ,3 ,15 etc.)

total_duration = 10                 # 8. Całkowity czas trwania sweepu (sekundy) dla płynnej zmiany czestotliwości: smooth_transition=True

gradual_amplitude_increase = False  # 9. Włącz stopniowe zwiększanie amplitudy (próba eliminacji szumu)

amplitude_rise_time = 0.5           # 10. Czas narostu amplitudy w sekundach
amplitude_start = 0.05              # 11. Początkowa amplituda
amplitude_end = 0.5                 # 12. Końcowa amplituda

sample_rate = 96000                 # 13. Częstotliwość próbkowania (Hz)

# Uruchomienie sweepu
sweep_with_amplitude_and_duration(start_freq, end_freq, freq_duration, sample_rate, smooth_transition,
                                  pause_duration, amplitude, freq_step, total_duration,
                                  gradual_amplitude_increase, amplitude_rise_time,
                                  amplitude_start, amplitude_end,
                                  csv_filename="sweep_output.csv")

print("Sweep signal has been generated and saved to 'sweep_output.csv'.")






