import os
import re
import sys
import math
import numpy as np
import librosa
import matplotlib.pyplot as plt
import subprocess
from moviepy import AudioFileClip
from yt_dlp import YoutubeDL
from pytube import YouTube  # (if still needed elsewhere)

# Define helper functions
def sanitize_filename(filename):
    # Remove characters not allowed in Windows filenames
    return re.sub(r'[<>:"/\\|?*]', '', filename)

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
    return (int(R * intensity_max), int(G * intensity_max), int(B * intensity_max))

def frequency_to_color(f, f_min=20, f_max=20000):
    f = max(min(f, f_max), f_min)
    x = math.log10(f)
    x_min = math.log10(f_min)
    x_max = math.log10(f_max)
    mapped_value = 4.0 + ((x - x_min) / (x_max - x_min)) * 3.0
    wavelength = mapped_value * 100
    rgb = wavelength_to_rgb(wavelength)
    return mapped_value, wavelength, rgb

def process_audio(file_path, segment_duration=0.1):
    y, sr = librosa.load(file_path, sr=None)
    segment_samples = int(segment_duration * sr)
    colors = []
    num_segments = len(y) // segment_samples
    for i in range(num_segments):
        segment = y[i * segment_samples:(i + 1) * segment_samples]
        fft_vals = np.fft.rfft(segment)
        magnitudes = np.abs(fft_vals)
        max_index = np.argmax(magnitudes)
        frequency = max_index * sr / segment_samples
        _, _, rgb = frequency_to_color(frequency)
        colors.append(rgb)
    return colors

def create_gradient_image(colors, height=100):
    width = len(colors)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i, color in enumerate(colors):
        img[:, i, :] = color
    return img

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
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
#                                Main Script                                  #
###############################################################################

if __name__ == "__main__":
    # Define a list of YouTube URLs (in the desired order)
    youtube_urls = [
        "https://youtu.be/_ZditPOzJnM?si=n9K6jABaGJ_ZYbuB", #1
        "https://youtu.be/rm9UDrEq3vs?si=ydOoxwLSCih07xNz",
        "https://youtu.be/-DY5fqecP5c?si=oJhEV0io7Vty7fIJ", #3
        "https://youtu.be/xUI95wXggB4?si=Q3CU8gONnonHGC6_",
        "https://youtu.be/EnNgASBdCeo?si=LR9w-9m2CowIzNhE", #5
        "https://youtu.be/c7IYSAUj78g?si=Gs4K_qWK9L7IlzDS",
        "https://youtu.be/3CB0_YU4G6Y?si=dOgCFik1WL7OVHOz", #7
        "https://youtu.be/1TLFnokO1Oo?si=ZIlwLgob3mjuRBP-",
        "https://youtu.be/mD96b2xOraM?si=JFQHgXk2trNWdgmu", #9
        "https://youtu.be/WXgY6NZ429I?si=GZIRVUM8JzbZPjon",
        "https://youtu.be/7YGc6RMOYF8?si=4t4bT4b28aPHpdim", #11
        "https://youtu.be/kXBaySil6YY?si=9o7HxinTGnN8wnDs",
        "https://youtu.be/XCX2o7zOzg8?si=_Sun-nEkSadOePMJ", #13
        "https://youtu.be/Fj4ZnTRmfrg?si=WPO0oKuZQ5xN8VnJ", 
        "https://youtu.be/gU-DfjTWemQ?si=UOXqG1UwkJpBG8de", #15
        "https://youtu.be/eLbmdG8U60E?si=HtLfGL1CwfZIhr5z",
        "https://youtu.be/TJU_HGZFjgo?si=r1PnLtQMTInWjl7P", #17
        "https://youtu.be/-FvzpOF0nDQ?si=VDEC0fYAy_sge1Nw",
        "https://youtu.be/PSDIX5GIicE?si=JgQr_VDoKrR_KEsj", #19
        "https://youtu.be/ZwspyQxIPeM?si=BPuXfo32vAemn33-", 
        "https://youtu.be/dQWt2o08qh8?si=kQle3sHcmqKcTDmC" #21
    ]
    
    # Set the output folder (make sure it exists)
    output_folder = r"C:\Users\camer\Documents\Coding\audioVisualization\SongsInKeyOfLife"
    os.makedirs(output_folder, exist_ok=True)
    
    # Fixed output dimensions (all images will be 1000x100)
    final_width = 1000
    final_height = 100
    dpi = 100
    fig_w = final_width / dpi
    fig_h = final_height / dpi
    
    # Loop through each YouTube URL
    for idx, url in enumerate(youtube_urls, start=1):
        # Download audio and metadata
        audio_file, song_title, song_artist = download_youtube_audio_and_metadata(url)
        
        # Process the audio to generate a list of colors
        colors = process_audio(audio_file, segment_duration=0.05)
        
        # Create the gradient image (stretch it to 1000x100)
        base_gradient = create_gradient_image(colors, height=200)
        
        plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
        plt.imshow(base_gradient, aspect='auto')
        plt.axis('off')
        
        # Place white text in bottom-left corner
        # Scale font size to final height (e.g., 10% of height)
        font_size = int(final_height * 0.10)
        text_label = f"{song_title}"
        plt.text(
            0.01, 0.01,
            text_label,
            color='white',
            fontsize=font_size,
            fontname='Forte',
            transform=plt.gca().transAxes,
            va='bottom',
            ha='left'
        )
        
        # Combine output folder, sequential number, and sanitized song title for file name
        output_filename = f"{idx}{sanitize_filename(song_title)}.png"
        full_output_path = os.path.join(output_folder, output_filename)
        
        # Save the figure
        plt.savefig(
            full_output_path,
            dpi=dpi,
            bbox_inches='tight',
            pad_inches=0,
            transparent=True
        )
        plt.close()  # Close the figure to free memory
        
        print(f"Saved: {full_output_path}")
