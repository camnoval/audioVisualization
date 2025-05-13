import numpy as np
from scipy.io import wavfile
from scipy import signal

def process_audio(file_path, segment_duration=0.05):
    """
    Process audio from a local .wav file and convert dominant frequencies to RGB colors
    """
    try:
        print(f"Reading audio file: {file_path}")
        sample_rate, audio_data = wavfile.read(file_path)

        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)

        # Normalize
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            max_val = np.iinfo(np.int16).max if audio_data.max() > 1.0 else 1.0
            audio_data = audio_data / max_val

        segment_samples = int(segment_duration * sample_rate)
        num_segments = min(1000, len(audio_data) // segment_samples)

        print(f"Analyzing {num_segments} segments...")
        colors = []

        for i in range(num_segments):
            segment = audio_data[i * segment_samples:(i + 1) * segment_samples]
            segment = segment * signal.windows.hann(len(segment))
            fft_data = np.abs(np.fft.rfft(segment))
            freq_bins = np.fft.rfftfreq(len(segment), 1 / sample_rate)
            max_idx = np.argmax(fft_data)
            max_freq = freq_bins[max_idx]

            rgb = map_frequency_to_rgb(max_freq)
            colors.append(rgb)

        print(f"Generated {len(colors)} colors")
        return colors

    except Exception as e:
        print(f"Audio processing error: {e}")


def map_frequencies_to_colors(frequencies):
    """
    Map a list of audio frequencies to RGB colors using a logarithmic scale and wavelength-based color mapping
    """
    return [map_frequency_to_rgb(freq) for freq in frequencies]

def map_frequency_to_rgb(freq):
    """
    Map a single frequency (Hz) to an RGB color via a logarithmic scale mapped to wavelength (400–700nm)
    """
    def wavelength_to_rgb(wavelength):
        if wavelength < 380 or wavelength > 780:
            return (0, 0, 0)
        if wavelength < 440:
            R = -(wavelength - 440) / (440 - 380)
            G = 0.0
            B = 1.0
        elif wavelength < 490:
            R = 0.0
            G = (wavelength - 440) / (490 - 440)
            B = 1.0
        elif wavelength < 510:
            R = 0.0
            G = 1.0
            B = -(wavelength - 510) / (510 - 490)
        elif wavelength < 580:
            R = (wavelength - 510) / (580 - 510)
            G = 1.0
            B = 0.0
        elif wavelength < 645:
            R = 1.0
            G = -(wavelength - 645) / (645 - 580)
            B = 0.0
        else:
            R = 1.0
            G = 0.0
            B = 0.0

        if wavelength < 420:
            factor = 0.3 + 0.7 * (wavelength - 380) / (420 - 380)
        elif wavelength > 700:
            factor = 0.3 + 0.7 * (780 - wavelength) / (780 - 700)
        else:
            factor = 1.0

        R = int(max(0, min(255, R * factor * 255)))
        G = int(max(0, min(255, G * factor * 255)))
        B = int(max(0, min(255, B * factor * 255)))
        return (R, G, B)

    log_min = np.log10(20)
    log_max = np.log10(20000)
    log_f = np.log10(max(freq, 1))
    t = (log_f - log_min) / (log_max - log_min)
    t = np.clip(t, 0, 1)
    wavelength = 700 - t * (700 - 400)
    return wavelength_to_rgb(wavelength)
