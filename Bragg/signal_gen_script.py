import sys
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

def sweep_with_amplitude_and_duration(start_freq, end_freq, freq_duration, sample_rate, smooth_transition,
                                      pause_duration, amplitude, freq_step, total_duration,
                                      gradual_amplitude_increase, amplitude_rise_time,
                                      amplitude_start, amplitude_end, csv_filename="sweep_output.csv"):
    
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

if __name__ == "__main__":
    print("Script started")
    if len(sys.argv) != 14:
        print("Usage: python signal_gen_script.py <start_freq> <end_freq> <freq_duration> <sample_rate> <smooth_transition> <pause_duration> <amplitude> <freq_step> <total_duration> <gradual_amplitude_increase> <amplitude_rise_time> <amplitude_start> <amplitude_end>")
        sys.exit(1)
    
    try:
        print("Parsing arguments")
        start_freq = float(sys.argv[1])
        end_freq = float(sys.argv[2])
        freq_duration = float(sys.argv[3])
        sample_rate = int(sys.argv[4])
        smooth_transition = sys.argv[5].lower() == 'true'
        pause_duration = float(sys.argv[6])
        amplitude = float(sys.argv[7])
        freq_step = float(sys.argv[8])
        total_duration = float(sys.argv[9])
        gradual_amplitude_increase = sys.argv[10].lower() == 'true'
        amplitude_rise_time = float(sys.argv[11])
        amplitude_start = float(sys.argv[12])
        amplitude_end = float(sys.argv[13])
        
        print("Starting sweep_with_amplitude_and_duration function")
        sweep_with_amplitude_and_duration(start_freq, end_freq, freq_duration, sample_rate, smooth_transition,
                                          pause_duration, amplitude, freq_step, total_duration,
                                          gradual_amplitude_increase, amplitude_rise_time,
                                          amplitude_start, amplitude_end)
    except ValueError:
        print("Invalid parameter. Please provide valid numbers.")
        sys.exit(1)