import numpy as np
from scipy.io import wavfile
from scipy import signal
from config import frequency_to_color

def process_audio(file_path, segment_duration=0.05):
    """Process audio using scipy instead of librosa to avoid Numba dependency"""
    try:
        # Read audio file using scipy.io.wavfile
        print(f"Reading audio file: {file_path}")
        sample_rate, audio_data = wavfile.read(file_path)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Normalize data
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            max_val = np.iinfo(np.int16).max if audio_data.max() > 1.0 else 1.0
            audio_data = audio_data / max_val
        
        # Calculate segment size
        segment_samples = int(segment_duration * sample_rate)
        num_segments = min(1000, len(audio_data) // segment_samples)  # Limit segments
        
        print(f"Analyzing {num_segments} segments...")
        
        # Process each segment
        colors = []
        for i in range(num_segments):
            segment = audio_data[i * segment_samples:(i + 1) * segment_samples]
            
            # Apply window function to reduce edge effects
            segment = segment * signal.windows.hann(len(segment))
            
            # Compute FFT
            fft_data = np.abs(np.fft.rfft(segment))
            
            # Find frequency with maximum magnitude
            freq_bins = np.fft.rfftfreq(len(segment), 1/sample_rate)
            max_idx = np.argmax(fft_data)
            max_freq = freq_bins[max_idx]
            
            # Convert to color
            _, _, rgb = frequency_to_color(max_freq)
            colors.append(rgb)
        
        print(f"Generated {len(colors)} colors")
        return colors
    
    except Exception as e:
        print(f"Audio processing error: {e}")
        # Generate fallback colors if processing fails
        print("Using fallback color pattern")
        return [(int(127 + 127*np.sin(i/20)), 
                 int(127 + 127*np.sin((i+100)/20)), 
                 int(127 + 127*np.sin((i+200)/20))) 
                for i in range(1000)]