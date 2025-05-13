import os
import re
import subprocess
import numpy as np
import io
import wave
from yt_dlp import YoutubeDL
from audio_processing import map_frequencies_to_colors
from visualization import create_gradient_image
from PIL import Image

def search_youtube_playlist(query):
    """Search for a YouTube playlist using yt-dlp instead of pytube"""
    search_query = f"{query} full album playlist"

    options = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True,
        'max_results': 5,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    }

    with YoutubeDL(options) as ydl:
        try:
            search_results = ydl.extract_info(f"ytsearch5:{search_query}", download=False)
            playlists = []
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if entry.get('_type') == 'playlist' or 'playlist' in entry.get('title', '').lower():
                        try:
                            playlist_info = ydl.extract_info(
                                f"https://www.youtube.com/playlist?list={entry.get('id')}",
                                download=False
                            )
                            if playlist_info and 'entries' in playlist_info and len(playlist_info['entries']) > 3:
                                playlists.append(playlist_info)
                        except:
                            continue

            if playlists:
                return max(playlists, key=lambda p: len(p['entries']))

            album_search = ydl.extract_info(f"ytsearch1:{query} full album", download=False)
            if album_search and 'entries' in album_search and album_search['entries']:
                return album_search['entries'][0]
        except Exception as e:
            print(f"Search error: {e}")
    return None

def split_album_video(video_info, output_folder):
    """Split a full album video into individual tracks using metadata chapters"""
    with YoutubeDL({'quiet': True, 'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}) as ydl:
        full_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_info['id']}", download=False)

    tracks = []

    if 'chapters' in full_info and full_info['chapters']:
        print(f"Found {len(full_info['chapters'])} chapters/tracks in the video")

        stream_url = get_stream_url(f"https://www.youtube.com/watch?v={video_info['id']}")
        dominant_freqs = extract_dominant_frequencies_from_stream(stream_url)
        colors = map_frequencies_to_colors(dominant_freqs)

        gradient_image = create_gradient_image(colors, height=100)
        Image.fromarray(gradient_image).save(os.path.join(output_folder, "full_album_gradient.png"))

        try:
            full_duration = full_info['chapters'][-1].get('end_time', 0) + 1.0
            print(f"Estimated full duration from chapters: {full_duration:.2f} seconds")
        except Exception as e:
            print(f"Error estimating duration from chapters: {e}")
            full_duration = 0

        for idx, chapter in enumerate(full_info['chapters'], start=1):
            try:
                chapter_title = chapter.get('title', f"Track {idx}")
                start_time = chapter.get('start_time', 0)

                if idx < len(full_info['chapters']):
                    end_time = full_info['chapters'][idx]['start_time']
                else:
                    end_time = min(chapter.get('end_time', full_duration), full_duration - 0.1)

                print(f"  Track {idx}: {chapter_title} ({start_time:.1f}s to {end_time:.1f}s)")

                tracks.append({
                    'id': f"{video_info['id']}_track{idx}",
                    'title': chapter_title,
                    'start_time': start_time,
                    'end_time': end_time,
                    'video_url': f"https://www.youtube.com/watch?v={video_info['id']}"
                })
            except Exception as e:
                print(f"  Error extracting metadata for track {idx}: {e}")

        return tracks

    return [{
        'id': video_info['id'],
        'title': video_info.get('title', 'Full Album'),
        'url': f"https://www.youtube.com/watch?v={video_info['id']}"
    }]

def extract_tracks_from_playlist(playlist_info):
    """Extract track information from a playlist result"""
    tracks = []
    if 'entries' in playlist_info:
        for entry in playlist_info['entries']:
            if entry and isinstance(entry, dict) and 'id' in entry:
                tracks.append({
                    'id': entry['id'],
                    'title': entry.get('title', 'Unknown Track'),
                    'url': f"https://www.youtube.com/watch?v={entry['id']}"
                })
    return tracks

def get_stream_url(youtube_url):
    """Get direct audio stream URL from a YouTube video"""
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestaudio',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(youtube_url, download=False)
        return info['url']

def extract_dominant_frequencies_from_stream(stream_url, segment_duration=0.1, sample_rate=44100):
    """Stream audio from YouTube and return dominant frequency per time segment"""
    ffmpeg_cmd = [
        'ffmpeg', '-i', stream_url,
        '-f', 'wav', '-acodec', 'pcm_s16le',
        '-ar', str(sample_rate), '-ac', '1',
        'pipe:1'
    ]

    proc = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    raw_audio = io.BytesIO(proc.stdout.read())

    raw_audio.seek(0)
    with wave.open(raw_audio, 'rb') as wav_file:
        n_frames = wav_file.getnframes()
        audio_data = np.frombuffer(wav_file.readframes(n_frames), dtype=np.int16)

    segment_samples = int(segment_duration * sample_rate)
    frequencies = []

    for i in range(0, len(audio_data), segment_samples):
        segment = audio_data[i:i + segment_samples]
        if len(segment) == 0:
            continue
        segment = segment * np.hanning(len(segment))  # smooth edges
        freqs = np.fft.rfft(segment)
        mags = np.abs(freqs)
        dominant_freq = np.argmax(mags) * sample_rate / segment_samples
        frequencies.append(dominant_freq)

    return frequencies
