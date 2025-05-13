import os
import re
import subprocess
from yt_dlp import YoutubeDL

# Try different import methods for moviepy
try:
    # First try the direct import that worked in your local VSCode
    from moviepy import AudioFileClip
    print("Using direct AudioFileClip import")
except ImportError:
    try:
        # Try the more common import path
        from moviepy.editor import AudioFileClip
        print("Using moviepy.editor AudioFileClip import")
    except ImportError:
        # Fallback to a manual approach if moviepy is having issues
        print("Warning: Could not import AudioFileClip from moviepy. Using FFmpeg fallback.")
        AudioFileClip = None

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
    """Download audio from YouTube video and extract metadata"""
    options = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    temp_filename = f"temp_audio.{info['ext']}"

    if AudioFileClip is not None:
        audio_clip = AudioFileClip(temp_filename)
        audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
        audio_clip.close()
    else:
        try:
            subprocess.run([
                'ffmpeg', '-i', temp_filename,
                '-acodec', 'pcm_s16le', '-y', output_filename
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Converted {temp_filename} to {output_filename} using FFmpeg")
        except Exception as e:
            print(f"Error converting audio with FFmpeg: {e}")
            import shutil
            shutil.copy(temp_filename, output_filename)
            print(f"Copied original file instead")

    try:
        os.remove(temp_filename)
    except:
        pass

    return output_filename, title, artist

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
                best_playlist = max(playlists, key=lambda p: len(p['entries']))
                return best_playlist

            album_search = ydl.extract_info(f"ytsearch1:{query} full album", download=False)
            if album_search and 'entries' in album_search and album_search['entries']:
                return album_search['entries'][0]

        except Exception as e:
            print(f"Search error: {e}")

    return None

def split_album_video(video_info, output_folder):
    """Split a full album video into individual tracks using ffmpeg directly"""
    with YoutubeDL({'quiet': True, 'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}) as ydl:
        full_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_info['id']}", download=False)

    tracks = []

    if 'chapters' in full_info and full_info['chapters']:
        print(f"Found {len(full_info['chapters'])} chapters/tracks in the video")

        audio_file, _, _ = download_youtube_audio_and_metadata(
            f"https://www.youtube.com/watch?v={video_info['id']}",
            output_filename=os.path.join(output_folder, 'full_album.wav')
        )

        try:
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                 '-of', 'default=noprint_wrappers=1:nokey=1', audio_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            full_duration = float(result.stdout.strip())
            print(f"Full audio duration: {full_duration:.2f} seconds")
        except Exception as e:
            print(f"Error getting audio duration: {e}")
            full_duration = full_info['chapters'][-1]['end_time'] + 1

        for idx, chapter in enumerate(full_info['chapters'], start=1):
            try:
                chapter_title = chapter.get('title', f"Track {idx}")
                start_time = chapter.get('start_time', 0)

                if idx < len(full_info['chapters']):
                    end_time = full_info['chapters'][idx]['start_time']
                else:
                    end_time = min(chapter.get('end_time', full_duration), full_duration - 0.1)

                print(f"  Extracting track {idx}: {chapter_title} ({start_time:.1f}s to {end_time:.1f}s)")

                chapter_filename = os.path.join(output_folder, f"track_{idx:02d}.wav")
                subprocess.run([
                    'ffmpeg', '-i', audio_file,
                    '-ss', str(start_time), '-to', str(end_time),
                    '-acodec', 'pcm_s16le', '-y', chapter_filename
                ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if os.path.exists(chapter_filename):
                    tracks.append({
                        'id': f"{video_info['id']}_track{idx}",
                        'title': chapter_title,
                        'file': chapter_filename
                    })
                else:
                    print(f"  Error: Failed to create track file {chapter_filename}")
            except Exception as e:
                print(f"  Error extracting track {idx}: {e}")

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
