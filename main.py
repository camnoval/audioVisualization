import os
import sys
import audio_processing
import visualization
import youtube_utils
from config import sanitize_filename
from PIL import Image
import requests
from io import BytesIO
import numpy as np
from visualization import get_dominant_color

def main():
    direct_url = os.environ.get("AUDIOVISUALIZER_DIRECT_URL")
    if direct_url:
        print(f"[INFO] Loading direct URL: {direct_url}")
        result = youtube_utils.load_youtube_url(direct_url)
        user_input = direct_url
    else:
        user_input = os.environ.get("AUDIOVISUALIZER_INPUT")
        if not user_input:
            user_input = input("Enter YouTube URL or album/song name: ").strip()
        print(f"[INFO] Searching for '{user_input}'...")
        selection_index = os.environ.get("AUDIOVISUALIZER_SELECTION_INDEX")
        selection_index = int(selection_index) if selection_index and selection_index.isdigit() else None
        result = youtube_utils.search_youtube_playlist(user_input, selection_index=selection_index)

    if not result:
        print("[ERROR] No results found. Please try a different search.")
        sys.exit(1)

    album_title = result.get('title', user_input)
    output_folder = os.path.join(os.getcwd(), sanitize_filename(album_title))
    os.makedirs(output_folder, exist_ok=True)
    print(f"[INFO] Saving to folder: {output_folder}")

    bg_color = None
    video_id = result.get('id') or (result['entries'][0].get('id') if 'entries' in result else None)
    if video_id:
        thumb_urls = [
            f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
        ]
        for url in thumb_urls:
            try:
                response = requests.get(url)
                if response.status_code == 200:
                    cover_image = Image.open(BytesIO(response.content))
                    bg_color = get_dominant_color([cover_image])
                    print(f"[INFO] Auto-detected background color from album cover: RGB{bg_color}")
                    break
            except Exception as e:
                print(f"[WARN] Thumbnail fetch failed for {url}: {e}")
        else:
            print("[WARN] No usable thumbnail found, using fallback background color.")

    env_color = os.environ.get("AUDIOVISUALIZER_COLOR")
    if env_color and env_color.lower() != "auto":
        try:
            parts = tuple(int(x) for x in env_color.split(","))
            if len(parts) == 3:
                bg_color = parts
                print(f"[INFO] Custom background color from GUI: RGB{bg_color}")
        except Exception as e:
            print(f"[WARN] Invalid custom color input: {env_color}")

    if 'entries' in result:
        print(f"[INFO] Found playlist: {result.get('title')} with {len(result['entries'])} tracks")
        tracks = youtube_utils.extract_tracks_from_playlist(result)
    elif 'chapters' in result:
        print(f"[INFO] Found chaptered video: {result.get('title')}")
        tracks = youtube_utils.split_album_video(result, output_folder)
    else:
        print(f"[INFO] Found single video: {result.get('title')}")
        tracks = [{
            'id': result['id'],
            'title': result.get('title', 'Full Album'),
            'url': f"https://www.youtube.com/watch?v={result['id']}"
        }]

    if not tracks:
        print("[ERROR] No valid tracks found.")
        sys.exit(1)

    print(f"[INFO] Beginning to process {len(tracks)} tracks...")
    all_image_paths = []

    for idx, track in enumerate(tracks, start=1):
        percent = int((idx - 1) / len(tracks) * 100)
        print(f"[PROGRESS] {percent}% complete")
        print(f"[INFO] Processing track {idx}/{len(tracks)}: {track['title']}")
        try:
            if 'url' in track:
                print(f"[DEBUG] Downloading audio for: {track['url']}")
                audio_file, song_title, _ = youtube_utils.download_youtube_audio_and_metadata(
                    track['url'],
                    output_filename=os.path.join(output_folder, f"track_{idx:02d}.wav")
                )
            else:
                print(f"[DEBUG] Using local file: {track['file']}")
                audio_file = track['file']
                song_title = track['title']

            print("[DEBUG] Starting audio analysis...")
            colors = audio_processing.process_audio(audio_file, segment_duration=0.05)
            print(f"[DEBUG] Generated {len(colors)} colors")

            base_gradient = visualization.create_gradient_image(colors, height=200, target_width=1000)
            output_filename = f"{idx:02d}_{sanitize_filename(song_title)}.png"
            full_output_path = os.path.join(output_folder, output_filename)

            visualization.create_track_visualization(
                base_gradient, song_title, full_output_path
            )
            all_image_paths.append(full_output_path)

            print(f"[INFO] Saved visualization: {output_filename}")

        except Exception as e:
            print(f"[ERROR] Error processing track {idx}: {e}")

    print("[INFO] Creating combined image...")
    try:
        combined_path = visualization.create_combined_image(
            all_image_paths,
            output_folder,
            album_title,
            bg_color
        )
        print(f"[INFO] Combined image saved to: {combined_path}")
        print(f"[OUTPUT] {combined_path}", flush=True) 
    except Exception as e:
        print(f"[ERROR] Failed to create combined image: {e}")

    print("[INFO] Done!")

if __name__ == "__main__":
    main()
