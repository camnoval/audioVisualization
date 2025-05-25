import os
import re
import subprocess
from yt_dlp import YoutubeDL

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
    options = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True,
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    temp_filename = f"temp_audio.{info['ext']}"

    try:
        subprocess.run([
            'ffmpeg', '-i', temp_filename, '-acodec', 'pcm_s16le', '-y', output_filename
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

def search_youtube_playlist(query, selection_index=None, return_entries_only=False):
    if query.startswith("http") and ("list=" in query or "playlist" in query):
        return load_youtube_url(query)

    search_query = f"{query}"
    options = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True,
        'max_results': 8,
    }

    with YoutubeDL(options) as ydl_flat:
        try:
            results = ydl_flat.extract_info(f"ytsearch8:{search_query}", download=False)
            entries = results.get('entries', [])
            if not entries:
                return None

            if return_entries_only:
                return entries

            if selection_index is None:
                env_index = os.environ.get("AUDIOVISUALIZER_SELECTION_INDEX")
                if env_index is not None and env_index.isdigit():
                    selection_index = int(env_index)

            selected = entries[selection_index] if selection_index is not None else entries[0]

            eid = selected.get('id')
            if selected.get('_type') == 'playlist' or 'playlist' in (selected.get('title', '').lower()) or 'list=' in query:
                real_url = f"https://www.youtube.com/playlist?list={eid}"
            else:
                real_url = f"https://www.youtube.com/watch?v={eid}"

        except Exception as e:
            print(f"Search error: {e}")
            return None

    return load_youtube_url(real_url)

def load_youtube_url(link):
    try:
        with YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
            info = ydl.extract_info(link, download=False)

            if 'entries' in info and len(info['entries']) > 1:
                print(f"✅ Loaded playlist: {info.get('title')} ({len(info['entries'])} tracks)")
                info['id'] = info.get('id') or info['entries'][0].get('id')
                return info

            elif 'chapters' in info and len(info['chapters']) > 1:
                print(f"✅ Loaded chaptered video: {info.get('title')}")
                info['id'] = info.get('id') or info.get('webpage_url', '').split('=')[-1]
                return info

            print("❌ Link must be a playlist or a video with chapters.")
            return None
    except Exception as e:
        print(f"Error loading YouTube URL: {e}")
        return None

def split_album_video(video_info, output_folder):
    with YoutubeDL({'quiet': True}) as ydl:
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
