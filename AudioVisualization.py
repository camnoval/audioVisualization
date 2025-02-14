import sys
import site
from moviepy import VideoFileClip, AudioFileClip
import math
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pytube import YouTube
import os
import subprocess

def download_youtube_audio(url, output_filename='audio.wav'):
    """
    Downloads audio from a YouTube video URL using yt-dlp and converts it to WAV.
    """
    # Use yt-dlp to download the audio stream
    command = [
        "yt-dlp", "-f", "bestaudio", "-o", "temp_audio.%(ext)s", url
    ]
    subprocess.run(command, check=True)
    
    # Find the downloaded file (assumes temp_audio.* exists)
    temp_filename = next((f for f in os.listdir('.') if f.startswith('temp_audio')), None)
    if not temp_filename:
        raise FileNotFoundError("Audio file not found after yt-dlp download.")

    # Convert to WAV using moviepy
    audio_clip = AudioFileClip(temp_filename)
    audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
    audio_clip.close()

    # Remove the temporary file
    os.remove(temp_filename)
    return output_filename

def wavelength_to_rgb(wavelength):
    """
    Convert a wavelength in nanometers (380-780 nm) to an RGB color.
    This approximate algorithm is adapted from common wavelength-to-RGB methods.
    """
    gamma = 0.8
    intensity_max = 255
    if 380 <= wavelength < 440:
        attenuation = 0.3 + 0.7 * (wavelength - 380) / (440 - 380)
        R = ((-(wavelength - 440) / (440 - 380)) * attenuation) ** gamma
        G = 0.0
        B = (1.0 * attenuation) ** gamma
    elif 440 <= wavelength < 490:
        R = 0.0
        G = ((wavelength - 440) / (490 - 440)) ** gamma
        B = 1.0 ** gamma
    elif 490 <= wavelength < 510:
        R = 0.0
        G = 1.0 ** gamma
        B = (-(wavelength - 510) / (510 - 490)) ** gamma
    elif 510 <= wavelength < 580:
        R = ((wavelength - 510) / (580 - 510)) ** gamma
        G = 1.0 ** gamma
        B = 0.0
    elif 580 <= wavelength < 645:
        R = 1.0 ** gamma
        G = (-(wavelength - 645) / (645 - 580)) ** gamma
        B = 0.0
    elif 645 <= wavelength <= 780:
        attenuation = 0.3 + 0.7 * (780 - wavelength) / (780 - 645)
        R = (1.0 * attenuation) ** gamma
        G = 0.0
        B = 0.0
    else:
        R = G = B = 0

    R = int(R * intensity_max)
    G = int(G * intensity_max)
    B = int(B * intensity_max)
    return (R, G, B)

def frequency_to_color(f, f_min=20, f_max=20000):
    """
    Maps a musical frequency (in Hz) to a value between 4 and 7 (log-scaled),
    converts that to a wavelength between 400 and 700 nm, and then returns the RGB color.
    """
    # Clamp frequency within f_min and f_max
    f = max(min(f, f_max), f_min)

    # Logarithmic scaling (because human pitch perception is logarithmic)
    x = math.log10(f)
    x_min = math.log10(f_min)
    x_max = math.log10(f_max)
    
    # Map log-frequency linearly to the range [4, 7]
    mapped_value = 4.00 + ((x - x_min) / (x_max - x_min)) * 3.00
    
    # Convert mapped value to wavelength (4 -> 400 nm, 7 -> 700 nm)
    wavelength = mapped_value * 100
    
    # Convert wavelength to RGB
    rgb = wavelength_to_rgb(wavelength)
    
    return mapped_value, wavelength, rgb

def process_audio(file_path, segment_duration=0.1):
    """
    Loads an audio file, splits it into segments (each segment_duration seconds),
    computes the FFT for each segment to extract a dominant frequency,
    maps that frequency to a color, and returns a list of RGB colors.
    """
    # Load the audio file; sr=None preserves the original sampling rate.
    y, sr = librosa.load(file_path, sr=None)
    segment_samples = int(segment_duration * sr)
    colors = []
    
    # Number of complete segments
    num_segments = len(y) // segment_samples
    
    for i in range(num_segments):
        # Extract the segment of audio
        segment = y[i * segment_samples:(i + 1) * segment_samples]
        
        # Compute the FFT for the segment and get magnitudes.
        fft_vals = np.fft.rfft(segment)
        magnitudes = np.abs(fft_vals)
        
        # Find the frequency bin with the maximum magnitude.
        max_index = np.argmax(magnitudes)
        
        # Calculate the corresponding frequency (bin index * frequency resolution)
        frequency = max_index * sr / segment_samples
        
        # Map the frequency to a color.
        _, _, rgb = frequency_to_color(frequency)
        colors.append(rgb)
    
    return colors

def create_gradient_image(colors, height=100):
    """
    Creates a numpy array representing an image with a horizontal gradient
    based on a list of RGB colors. Each color corresponds to one vertical column.
    """
    width = len(colors)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i, color in enumerate(colors):
        img[:, i, :] = color  # Set the entire column to the color
    return img

from yt_dlp import YoutubeDL

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
    """
    Downloads audio from a YouTube video URL and extracts the metadata (title and artist).
    """
    options = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True,  # Suppress yt-dlp output
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    
    # Extract title and artist (if available)
    title = info.get('title', 'Unknown Title')
    artist = info.get('artist', 'Unknown Artist')

    # Convert downloaded file to WAV
    temp_filename = f"temp_audio.{info['ext']}"
    audio_clip = AudioFileClip(temp_filename)
    audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
    audio_clip.close()
    
    # Remove the temporary file
    os.remove(temp_filename)
    os.remove("downloaded_audio.wav")
    
    return output_filename, title, artist

# Update the main block to use the title and artist
if __name__ == "__main__":
    # URL of the YouTube video
    youtube_url = "https://www.youtube.com/watch?v=ABlYBn7Jo38&pp=ygUgZGFyayBzaWRlIG9mIHRoZSBtb29uIHBpbmsgZmxveWQ%3D"
    
    # Download and extract audio and metadata
    audio_file, song_title, song_artist = download_youtube_audio_and_metadata(youtube_url)
    
    # Process the audio file to get a list of colors for each 0.05-second segment.
    colors = process_audio(audio_file, segment_duration=0.05)
    
    # Create a gradient image from the list of colors.
    gradient_img = create_gradient_image(colors, height=1000)
    
    # Display the gradient image with a dynamic title
    plt.figure(figsize=(10, 2))
    plt.imshow(gradient_img)
    plt.axis('off')
    plt.title(f"Dark Side of the Moon - Pink Floyd")
    #plt.title(f"'{song_title} - {song_artist}'", fontsize=14)
    plt.show()

