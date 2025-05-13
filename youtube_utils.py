import os
import re
import subprocess
from yt_dlp import YoutubeDL

def download_youtube_audio_and_metadata(url, output_filename='audio.wav'):
    """Download audio from YouTube video and extract metadata using FFmpeg directly"""
    # Configure yt-dlp options
    options = {
        'format': 'bestaudio/best',
        'outtmpl': 'temp_audio.%(ext)s',
        'quiet': True,
    }
    
    # Download the audio file
    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=True)
    
    # Extract metadata
    title = info.get('title', 'Unknown Title')
    artist = info.get('uploader', 'Unknown Artist')
    temp_filename = f"temp_audio.{info['ext']}"
    
    # Convert to WAV using FFmpeg directly
    try:
        print(f"Converting {temp_filename} to WAV format...")
        subprocess.run([
            'ffmpeg', '-i', temp_filename, 
            '-acodec', 'pcm_s16le', '-ar', '44100', '-y', output_filename
        ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Successfully converted to: {output_filename}")
    except Exception as e:
        print(f"Error converting audio with FFmpeg: {e}")
        # If conversion fails, try to copy the file if it's compatible
        if temp_filename.lower().endswith(('.wav', '.mp3', '.ogg')):
            import shutil
            shutil.copy(temp_filename, output_filename)
            print(f"Copied original audio file as fallback")
        else:
            print(f"Could not convert audio file. Processing may fail.")
    
    # Clean up temporary file
    try:
        os.remove(temp_filename)
        print(f"Removed temporary file: {temp_filename}")
    except Exception as e:
        print(f"Warning: Could not remove temporary file: {e}")
        
    return output_filename, title, artist

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

def search_youtube_playlist(query):
    """Search for a YouTube playlist using yt-dlp instead of pytube"""
    search_query = f"{query} full album playlist"
    
    # Search options
    options = {
        'quiet': True,
        'extract_flat': True,
        'skip_download': True,
        'no_warnings': True,
        'max_results': 5  # Limit results to avoid excessive API calls
    }
    
    with YoutubeDL(options) as ydl:
        # First try to find a playlist
        try:
            # Search for playlists
            search_results = ydl.extract_info(f"ytsearch5:{search_query}", download=False)
            
            # Filter for playlists with reasonable track counts
            playlists = []
            if search_results and 'entries' in search_results:
                for entry in search_results['entries']:
                    if entry.get('_type') == 'playlist' or 'playlist' in entry.get('title', '').lower():
                        try:
                            playlist_info = ydl.extract_info(f"https://www.youtube.com/playlist?list={entry.get('id')}", 
                                                         download=False)
                            if playlist_info and 'entries' in playlist_info and len(playlist_info['entries']) > 3:
                                playlists.append(playlist_info)
                        except:
                            continue
            
            # If playlists found, return the one with the most tracks
            if playlists:
                best_playlist = max(playlists, key=lambda p: len(p['entries']))
                return best_playlist
                
            # If no playlists found, try searching for a full album video
            album_search = ydl.extract_info(f"ytsearch1:{query} full album", download=False)
            if album_search and 'entries' in album_search and album_search['entries']:
                # Return info about the first result
                return album_search['entries'][0]
                
        except Exception as e:
            print(f"Search error: {e}")
            
    return None

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