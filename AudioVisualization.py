import sys
import site
from moviepy import VideoFileClip, AudioFileClip
import math
import numpy as np
import librosa
import matplotlib.pyplot as plt
from pytube import YouTube
import os
import re
import subprocess
from yt_dlp import YoutubeDL

###############################################################################
#                               Core Functions                                #
###############################################################################

def wavelength_to_rgb(wavelength):
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
    """Map a frequency to a color via a log-scale to 400–700 nm, then to RGB."""
    f = max(min(f, f_max), f_min)
    x = math.log10(f)
    x_min = math.log10(f_min)
    x_max = math.log10(f_max)
    mapped_value = 4.0 + ((x - x_min) / (x_max - x_min)) * 3.0
    wavelength = mapped_value * 100
    rgb = wavelength_to_rgb(wavelength)
    return mapped_value, wavelength, rgb

def process_audio(file_path, segment_duration=0.1):
    """
    Splits an audio file into segments of 'segment_duration' seconds,
    finds each segment's dominant frequency, and maps it to an RGB color.
    """
    y, sr = librosa.load(file_path, sr=None)
    segment_samples = int(segment_duration * sr)
    colors = []
    num_segments = len(y) // segment_samples

    for i in range(num_segments):
        segment = y[i * segment_samples : (i + 1) * segment_samples]
        fft_vals = np.fft.rfft(segment)
        magnitudes = np.abs(fft_vals)
        max_index = np.argmax(magnitudes)
        frequency = max_index * sr / segment_samples
        _, _, rgb = frequency_to_color(frequency)
        colors.append(rgb)

    return colors

def create_gradient_image(colors, height=100):
    """
    Creates a numpy array (height x len(colors) x 3) for the gradient.
    Each column is one color from 'colors'.
    """
    width = len(colors)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i, color in enumerate(colors):
        img[:, i, :] = color
    return img

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
    """
    Downloads audio from YouTube via yt-dlp, extracts title/artist metadata,
    and converts the file to WAV.
    """
    options = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)

    title = info.get('title', 'Unknown Title')
    artist = info.get('artist', 'Unknown Artist')

    temp_filename = f"temp_audio.{info['ext']}"
    audio_clip = AudioFileClip(temp_filename)
    audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
    audio_clip.close()

    os.remove(temp_filename)
    return output_filename, title, artist


###############################################################################
# Main Script - change youtube URL + outpath path to match song/album proj.   #
###############################################################################

if __name__ == "__main__":
    ## THINGS TO CHANGE BETWEEN PROJECTS ##
    youtube_url = "https://www.youtube.com/watch?v=XrLe6MSjBzg&pp=ygUiaGF2ZSBhIHRhbGsgd2l0aCBnb2Qgc3RldmllIHdvbmRlcg%3D%3D"
    output_path = "C:/Users/camer/Documents/Coding/audioVisualization/SongsInKeyOfLife"
    ######################################

    # Download audio & metadata
    audio_file, song_title, song_artist = download_youtube_audio_and_metadata(youtube_url)

    # Generate list of colors from the audio
    colors = process_audio(audio_file, segment_duration=0.05)

    # Create the gradient image
    base_gradient = create_gradient_image(colors, height=100)

    # -------------------------------------------------------------------------
    # FIXED OUTPUT DIMENSIONS
    # We'll produce a 1000x300 image for consistency across all songs
    # -------------------------------------------------------------------------
    final_width = 1000
    final_height = 300
    dpi = 100

    # Convert pixel size to figure size in inches
    fig_w = final_width / dpi
    fig_h = final_height / dpi

    plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    # aspect='auto' ensures the image stretches or shrinks to fill the figure
    plt.imshow(base_gradient, aspect='auto')
    plt.axis('off')

    # -------------------------------------------------------------------------
    # Text in bottom-left corner (white, scaled to final_height)
    # We'll pick a font size that looks consistent at 300 px tall
    # For example, 8% of final_height -> 24 px
    # -------------------------------------------------------------------------
    font_size = int(final_height * 0.08)
    text_label = f"{song_title}"
    plt.text(
        0.01, 0.01,  # near bottom-left
        text_label,
        color='white',
        fontsize=font_size,
        fontname='Forte',
        transform=plt.gca().transAxes,
        va='bottom',
        ha='left'
    )

    def sanitize_filename(filename): #had to add to stop errors, thanks chat lol
        # Remove characters not allowed in Windows filenames
        return re.sub(r'[<>:"/\\|?*]', '', filename)

    # In your main script, after extracting song_title, then combine with path:
    output_filename = sanitize_filename(song_title) + ".png"
    full_output_path = os.path.join(output_path, output_filename)

    plt.savefig(
        full_output_path,
        dpi=dpi,
        bbox_inches='tight',
        pad_inches=0,
        transparent=True
    )
    plt.show()
