import os
import re
import subprocess
from yt_dlp import YoutubeDL

# Try different import methods for moviepy
try:
    # First try the direct import that worked in your local VSCode
    from moviepy import AudioFileClip
    #print("Using direct AudioFileClip import")
except ImportError:
    try:
        # Try the more common import path
        from moviepy.editor import AudioFileClip # type: ignore
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
    }
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    temp_filename = f"temp_audio.{info['ext']}"
    
    # Choose between AudioFileClip and direct FFmpeg approach
    if AudioFileClip is not None:
        # Use moviepy if available
        audio_clip = AudioFileClip(temp_filename)
        audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
        audio_clip.close()
    else:
        # Fallback to direct FFmpeg call
        try:
            subprocess.run([
                'ffmpeg', '-i', temp_filename, 
                '-acodec', 'pcm_s16le', '-y', output_filename
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            print(f"Converted {temp_filename} to {output_filename} using FFmpeg")
        except Exception as e:
            print(f"Error converting audio with FFmpeg: {e}")
            # If FFmpeg fails, just use the original file
            import shutil
            shutil.copy(temp_filename, output_filename)
            print(f"Copied original file instead")
    
    # Clean up temporary file
    try:
        os.remove(temp_filename)
    except:
        pass
        
    return output_filename, title, artist

def search_youtube_playlist(query):
    """Search for a playlist or chaptered album video, let the user pick one."""
    search_query = f"{query} full album"

    options = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True,
        'max_results': 8,
    }

    with YoutubeDL(options) as ydl_flat:
        try:
            # 1) Get flat search results
            results = ydl_flat.extract_info(f"ytsearch8:{search_query}", download=False)
            entries = results.get('entries', [])
            if not entries:
                print("No matching items found.")
                return None

            # 2) Show the entries to the user
            print("\nFound the following options:")
            for i, e in enumerate(entries, 1):
                title = e.get('title') or e.get('id')
                print(f"{i}. {title}")

            # 3) Prompt for selection
            while True:
                try:
                    choice = int(input(f"Select a result (1–{len(entries)}): "))
                    if not 1 <= choice <= len(entries):
                        raise ValueError("Out of range")
                    selected = entries[choice - 1]
                    break
                except Exception as err:
                    print(f"Invalid selection. Try again. ({err})")

            # 4) Build the real URL
            eid = selected.get('id')
            if selected.get('_type') == 'playlist' or 'playlist' in (selected.get('title','').lower()):
                real_url = f"https://www.youtube.com/playlist?list={eid}"
            else:
                real_url = f"https://www.youtube.com/watch?v={eid}"

        except Exception as e:
            print(f"Search error: {e}")
            return None

    # 5) Fetch full info (with chapters or entries)
    with YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
        try:
            info = ydl.extract_info(real_url, download=False)
            # If it's a playlist with entries, return that
            if 'entries' in info and len(info['entries']) > 1:
                print(f"✅ Loaded playlist: {info.get('title')} ({len(info['entries'])} tracks)")
                return info
            # If it's a video with chapters, return that
            if 'chapters' in info and len(info['chapters']) > 1:
                print(f"✅ Loaded chaptered video: {info.get('title')}")
                return info

            print("❌ Selected item has neither multiple entries nor chapters.")
        except Exception as e:
            print(f"Error loading selected item: {e}")

    return None

def split_album_video(video_info, output_folder):
    """Split a full album video into individual tracks using ffmpeg directly"""
    # Download the full video info to get chapters/timestamps
    with YoutubeDL({'quiet': True}) as ydl:
        full_info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_info['id']}", download=False)
    
    tracks = []
    
    # Check if video has chapters
    if 'chapters' in full_info and full_info['chapters']:
        print(f"Found {len(full_info['chapters'])} chapters/tracks in the video")
        
        # Download the full audio once
        audio_file, _, _ = download_youtube_audio_and_metadata(
            f"https://www.youtube.com/watch?v={video_info['id']}",
            output_filename=os.path.join(output_folder, 'full_album.wav')
        )
        
        # Get full audio duration using ffprobe
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
            # Estimate from the last chapter end time
            full_duration = full_info['chapters'][-1]['end_time'] + 1
        
        # Split the audio based on chapters using ffmpeg directly
        for idx, chapter in enumerate(full_info['chapters'], start=1):
            try:
                chapter_title = chapter.get('title', f"Track {idx}")
                start_time = chapter.get('start_time', 0)
                
                # Ensure end time doesn't exceed duration
                if idx < len(full_info['chapters']):
                    # Use next chapter's start as this chapter's end
                    end_time = full_info['chapters'][idx]['start_time']
                else:
                    # For last track, use duration with small margin
                    end_time = min(chapter.get('end_time', full_duration), full_duration - 0.1)
                
                print(f"  Extracting track {idx}: {chapter_title} ({start_time:.1f}s to {end_time:.1f}s)")
                
                # Use ffmpeg directly
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
    
    # If no chapters, return the whole video as one track
    return [{
        'id': video_info['id'],
        'title': video_info.get('title', 'Full Album'),
        'url': f"https://www.youtube.com/watch?v={video_info['id']}"
    }]

def extract_tracks_from_playlist(playlist_info):
    """Extract track information from a playlist result"""
    tracks = []
    
    if 'entries' in playlist_info:
        # This is a proper playlist
        for entry in playlist_info['entries']:
            if entry and isinstance(entry, dict) and 'id' in entry:
                tracks.append({
                    'id': entry['id'],
                    'title': entry.get('title', 'Unknown Track'),
                    'url': f"https://www.youtube.com/watch?v={entry['id']}"
                })
    
    return tracks