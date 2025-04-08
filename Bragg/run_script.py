import subprocess
import logging
import os
import shutil

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the time duration here
time_duration = 10  # Change this value to your desired duration

# Parameters for folder naming
material = "PLA"  # Replace with actual material name
wypelnienie = 50  # Replace with actual fill percentage

# Amplitude range and step (for auto mode)
amplitude_start = 0.1 # Starting amplitude
amplitude_end = 0.2  # Ending amplitude
amplitude_step = 0.1  # Step for amplitude

# Manual amplitude option
use_manual_amplitude = True  # Set to True to use manual amplitude
manual_amplitude = 0.15  # Manual amplitude value

# Folder to store CSV files
csv_folder_base = f"csv_files_{material}_infill{wypelnienie}_%_amp"

# ---------------------------------------------------- Parametry sweepu ----------------------------------------------------
start_freq = 10  # 1. Początkowa częstotliwość (np.:5 Hz)
end_freq = 100  # 2. Końcowa częstotliwość (np.: 200 Hz)
freq_duration = 1  # 3. Czas trwania każdej częstotliwości w sekundach
smooth_transition = True  # 4. Ustaw na True aby uzyskać płynne przejście
pause_duration = 1  # 5. Czas pauzy pomiędzy częstotliwościami (jeśli smooth_transition=False)
freq_step = 10  # 7. Krok zmiany częstotliwości (np. 1 ,3 ,15 etc.)
total_duration = 10  # 8. Całkowity czas trwania sweepu (sekundy) dla płynnej zmiany czestotliwości: smooth_transition=True
gradual_amplitude_increase = False  # 9. Włącz stopniowe zwiększanie amplitudy (próba eliminacji szumu)
amplitude_rise_time = 0.5  # 10. Czas narostu amplitudy w sekundach
sample_rate = 96000  # 13. Częstotliwość próbkowania (Hz)

def validate_parameters():
    """Validate the sweep parameters."""
    if not (0 <= amplitude_start <= 1 and 0 <= amplitude_end <= 1):
        raise ValueError("Amplitude must be between 0.0 and 1.0")
    if not (start_freq > 0 and end_freq > start_freq):
        raise ValueError("End frequency must be greater than start frequency and both must be positive")
    if not (freq_duration > 0 and total_duration > 0):
        raise ValueError("Duration values must be positive")

def run_main_script(time_duration):
    """Run the main script with the given time duration."""
    try:
        logging.info(f"Running acc_collect_only_script.py with time_duration={time_duration}")
        acc_process = subprocess.Popen(["python", "acc_collect_only_script.py", str(time_duration)])
        logging.info(f"Running temperatura_script.py with time_duration={time_duration}")
        temp_process = subprocess.Popen(["python", "temperatura_script.py", str(time_duration)])
        return acc_process, temp_process
    except Exception as e:
        logging.error(f"Error running main scripts: {e}")
        return None, None

def run_sweep_signal(amplitude):
    """Run the sweep signal generation script with the given amplitude."""
    try:
        validate_parameters()
        logging.info("Running signal_gen_script.py with sweep parameters")
        logging.info(f"Parameters: start_freq={start_freq}, end_freq={end_freq}, freq_duration={freq_duration}, sample_rate={sample_rate}, smooth_transition={smooth_transition}, pause_duration={pause_duration}, amplitude={amplitude}, freq_step={freq_step}, total_duration={total_duration}, gradual_amplitude_increase={gradual_amplitude_increase}, amplitude_rise_time={amplitude_rise_time}, amplitude_start={amplitude_start}, amplitude_end={amplitude_end}")
        sweep_process = subprocess.Popen([
            "python", "signal_gen_script.py",
            str(start_freq), str(end_freq), str(freq_duration), str(sample_rate),
            str(smooth_transition), str(pause_duration), str(amplitude), str(freq_step),
            str(total_duration), str(gradual_amplitude_increase), str(amplitude_rise_time),
            str(amplitude_start), str(amplitude_end)
        ])
        return sweep_process
    except Exception as e:
        logging.error(f"Error running sweep signal script: {e}")
        return None

def move_csv_files(amplitude):
    """Move CSV files to the specified folder."""
    csv_folder = f"csv_files_{material}_infill{wypelnienie}_%_amp_{amplitude}"
    os.makedirs(csv_folder, exist_ok=True)
    for file_name in os.listdir():
        if file_name.endswith(".csv"):
            shutil.move(file_name, os.path.join(csv_folder, file_name))
            logging.info(f"Moved {file_name} to {csv_folder}")

if __name__ == "__main__":
    if use_manual_amplitude:
        amplitude = manual_amplitude
        sweep_process = run_sweep_signal(amplitude)
        acc_process, temp_process = run_main_script(time_duration)

        if sweep_process:
            logging.info("Waiting for sweep_process to complete")
            sweep_process.wait()
        if acc_process:
            logging.info("Waiting for acc_process to complete")
            acc_process.wait()
        if temp_process:
            logging.info("Waiting for temp_process to complete")
            temp_process.wait()

        logging.info("All subprocesses have completed.")
        move_csv_files(amplitude)
    else:
        for amplitude in range(int(amplitude_start * 100), int(amplitude_end * 100) + 1, int(amplitude_step * 100)):
            amplitude /= 100.0
            sweep_process = run_sweep_signal(amplitude)
            acc_process, temp_process = run_main_script(time_duration)

            if sweep_process:
                logging.info("Waiting for sweep_process to complete")
                sweep_process.wait()
            if acc_process:
                logging.info("Waiting for acc_process to complete")
                acc_process.wait()
            if temp_process:
                logging.info("Waiting for temp_process to complete")
                temp_process.wait()

            logging.info("All subprocesses have completed.")
            move_csv_files(amplitude)