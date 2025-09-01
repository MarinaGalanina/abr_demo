import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Define wave detection time windows in ms
WAVE_WINDOWS = {
    'wave_1': (1.0, 1.8),
    'wave_2': (1.8, 2.5),
    'wave_3': (2.5, 3.5),
    'wave_4': (3.5, 4.7),
    'wave_5': (5.6, 10.2)  # shifted later to avoid premature detection
}

def detect_wave(signal, time_ms, start_ms, end_ms, threshold, window=3):
    segment_mask = (time_ms >= start_ms) & (time_ms <= end_ms)
    segment = signal[segment_mask]
    if segment.size == 0:
        return None, None, None, None

    start_idx = np.where(segment_mask)[0][0]

    for i in range(window, len(segment) - window):
        bin_val = segment[i]
        if all(bin_val > segment[i - j] for j in range(1, window + 1)) and \
           all(bin_val > segment[i + j] for j in range(1, window + 1)) and \
           bin_val > threshold:
            peak_idx = start_idx + i
            peak_val = signal[peak_idx]
            search_range = int(0.5 / (time_ms[1] - time_ms[0]))
            trough_segment = signal[peak_idx:peak_idx + search_range]
            if len(trough_segment) < 2:
                continue
            trough_idx_rel = np.argmin(trough_segment)
            trough_val = trough_segment[trough_idx_rel]
            trough_idx = peak_idx + trough_idx_rel
            latency = time_ms[peak_idx]
            amplitude = peak_val - trough_val
            return latency, amplitude, peak_idx, trough_idx
    return None, None, None, None

def process_trace(signal, time_ms):
    threshold = 0.05
    for _ in range(11):
        results = {}
        for wave, (start, end) in WAVE_WINDOWS.items():
            lat, amp, pk, tr = detect_wave(signal, time_ms, start, end, threshold)
            results[wave] = {
                'latency_ms': lat,
                'amplitude_nV': amp,
                'peak_bin': pk,
                'trough_bin': tr
            }
        if any(results[w]['latency_ms'] is not None for w in results):
            if results['wave_1']['latency_ms'] is not None and results['wave_5']['latency_ms'] is not None:
                results['interpeak_1_5'] = results['wave_5']['latency_ms'] - results['wave_1']['latency_ms']
            else:
                results['interpeak_1_5'] = None
            return results
        threshold *= 0.95
    results['interpeak_1_5'] = None
    return results

def plot_waveform(signal, wave_data, title, time_ms, output_dir="Results_for_waves"):
    os.makedirs(output_dir, exist_ok=True)

    min_index = np.argmax(time_ms >= 0.5)
    plot_signal = signal[min_index:]
    plot_time = time_ms[min_index:]

    # 1️⃣ raw plot
    plt.figure(figsize=(10, 4))
    plt.plot(plot_time, plot_signal, color='black', label="Average ABR waveform")
    plt.title(f"{title} (raw)")
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude")
    plt.grid(True)
    plt.tight_layout()
    raw_path = os.path.join(output_dir, f"{title}_raw.png")
    plt.savefig(raw_path, dpi=300)
    plt.close()

    # 2️⃣ with waves
    plt.figure(figsize=(10, 4))
    plt.plot(plot_time, plot_signal, color='black', label="Average ABR waveform")

    colors = ['b', 'm', 'g', 'purple', 'cyan']
    for i, wave in enumerate(WAVE_WINDOWS.keys()):
        pk = wave_data[wave]['peak_bin']
        tr = wave_data[wave]['trough_bin']
        if pk is not None and tr is not None and pk >= min_index and tr >= min_index:
            plt.plot(time_ms[pk], signal[pk], marker='^', color=colors[i], label=f'{wave} peak')
            plt.plot(time_ms[tr], signal[tr], marker='v', color=colors[i], label=f'{wave} trough')

    plt.title(f"{title} (with waves)")
    plt.xlabel("Time (ms)")
    plt.ylabel("Amplitude")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    wave_path = os.path.join(output_dir, f"{title}_with_waves.png")
    plt.savefig(wave_path, dpi=300)
    plt.close()

    return os.path.basename(raw_path), os.path.basename(wave_path)

def process_file(signal_path, time_path):
    df_time = pd.read_csv(time_path)
    time_ms = df_time.iloc[:, 0].to_numpy(dtype=np.float32)
    time_ms = time_ms - time_ms[0]

    df_signal = pd.read_csv(signal_path)
    max_len = min(len(time_ms), len(df_signal))
    time_ms = time_ms[:max_len]
    df_signal = df_signal.iloc[:max_len, :]

    mouse_id = os.path.basename(signal_path).split('.')[0]
    average_signal = df_signal.mean(axis=1).to_numpy(dtype=np.float32)
    wave_data = process_trace(average_signal, time_ms)

    wave = 'wave_5'
    d = wave_data[wave]
    row_out = {
        'PersonID': mouse_id,
        'Electrode': 'Average',
        'wave_5_latency': d['latency_ms'],
        'wave_5_amplitude': d['amplitude_nV'],
        'wave_5_peak_bin': d['peak_bin'],
        'wave_5_trough_bin': d['trough_bin']
    }

    # ✅ capture filenames
    raw_img, wave_img = plot_waveform(average_signal, wave_data, f"Patient_{mouse_id}_average", time_ms)
    row_out["raw_plot_filename"] = raw_img
    row_out["plot_filename"] = wave_img

    return pd.DataFrame([row_out])

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--signal", required=True, help="Path to signal CSV file (e.g. 215.csv)")
    parser.add_argument("--time", required=True, help="Path to time CSV file (e.g. time_data.csv)")
    parser.add_argument("--output", required=True, help="Output CSV file for results")
    args = parser.parse_args()

    df = process_file(args.signal, args.time)
    df.to_csv(args.output, index=False)
    print(f"Saved wave detection results to {args.output}")

if __name__ == "__main__":
    main()

