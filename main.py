import os
import sys
import audio_processing
import visualization
import youtube_utils
from config import sanitize_filename
from visualization import get_dominant_color
from PIL import Image
import requests
from io import BytesIO

def main():
   # Get user input for album/song

    user_input = input("Enter YouTube URL or album/song name: ").strip()


 
    # Search for the album
    print(f"Searching for '{user_input}'...")
    try:
        if "youtube.com" in user_input or "youtu.be" in user_input:
            print(f"Loading YouTube link: {user_input}")
            result = youtube_utils.load_youtube_url(user_input)
        else:
            print(f"Searching for '{user_input}'...")
            result = youtube_utils.search_youtube_playlist(user_input)
    except Exception as e:
        print(f"❌ Error during YouTube search: {e}")
        sys.exit(1)

    if not result:
        print("No results found. Please try a different search.")
        sys.exit(1)

    # Create output folder based on sanitized album title
    album_title = result.get('title', user_input)
    output_folder = os.path.join(os.getcwd(), sanitize_filename(album_title))
    os.makedirs(output_folder, exist_ok=True)
    print(f"Saving to folder: {output_folder}")

    # Fetch thumbnail and compute background color
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
                    break
            except Exception as e:
                print(f"Thumbnail fetch failed for {url}: {e}")
        else:
            print("No usable thumbnail found, using fallback background color.")

    # Ask user if they want to override the background color
    user_bg = get_user_bg_color_choice()
    if user_bg is not None:
        bg_color = user_bg

    # Extract tracks based on whether it's a playlist or a single album video
    try:
        tracks = extract_tracks(result, output_folder)
    except Exception as e:
        print(f"❌ Error extracting tracks: {e}")
        sys.exit(1)

    if not tracks:
        print("No valid tracks found.")
        sys.exit(1)

    print(f"Processing {len(tracks)} tracks...")

    all_image_paths = []
    all_gradient_images = []

    # Process each track
    for idx, track in enumerate(tracks, start=1):
        print(f"Processing track {idx}/{len(tracks)}: {track['title']}")
        try:
            # Download if URL is provided, otherwise use existing file
            if 'url' in track:
                audio_file, song_title, _ = youtube_utils.download_youtube_audio_and_metadata(
                    track['url'],
                    output_filename=os.path.join(output_folder, f"track_{idx:02d}.wav")
                )
            else:
                audio_file = track['file']
                song_title = track['title']

            # Process the audio to generate colors
            colors = audio_processing.process_audio(audio_file, segment_duration=0.05)

            # Create the gradient image
            base_gradient = visualization.create_gradient_image(colors, height=200)
            all_gradient_images.append(base_gradient)

            # Create visualization and save
            output_filename = f"{idx:02d}_{sanitize_filename(song_title)}.png"
            full_output_path = os.path.join(output_folder, output_filename)

            visualization.create_track_visualization(
                base_gradient, song_title, full_output_path
            )
            all_image_paths.append(full_output_path)

            print(f"Saved visualization: {output_filename}")

        except Exception as e:
            print(f"Error processing track {idx}: {e}")

    # Stack all images with margins
    if all_image_paths:
        print("Creating combined image...")

        # Create the combined image with the album title
        try:
            combined_path = visualization.create_combined_image(
                all_image_paths,
                output_folder,
                album_title,
                bg_color
            )

            # Open the final image
            try:
                if sys.platform == 'win32':
                    os.startfile(combined_path)
                elif sys.platform == 'darwin':
                    import subprocess
                    subprocess.call(['open', combined_path])
                else:
                    import subprocess
                    subprocess.call(['xdg-open', combined_path])
            except Exception as e:
                print(f"Could not open image automatically: {e}")
                print(f"Combined image saved to: {combined_path}")
        except Exception as e:
            print(f"❌ Error creating combined image: {e}")

    print("Done!")

def get_user_bg_color_choice():
    use_custom_bg = input("Would you like to use a custom background color? (y/n): ").lower().startswith('y')

    if not use_custom_bg:
        return None

    color_options = {
        '1': (0, 0, 0),       # Black
        '2': (255, 255, 255), # White
        '3': (25, 25, 112),   # Midnight Blue
        '4': (139, 0, 0),     # Dark Red
        '5': (0, 100, 0)      # Dark Green
    }

    print("\nSelect a background color:")
    print("1. Black")
    print("2. White")
    print("3. Midnight Blue")
    print("4. Dark Red")
    print("5. Dark Green")
    print("6. Custom RGB")

    choice = input("Enter your choice (1-6): ")

    if choice in color_options:
        return color_options[choice]
    elif choice == '6':
        # Allow custom RGB input
        try:
            r = int(input("Enter Red value (0-255): "))
            g = int(input("Enter Green value (0-255): "))
            b = int(input("Enter Blue value (0-255): "))
            return (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
        except:
            print("Invalid RGB values, will use auto-detected color")
    else:
        print("Invalid choice, will use auto-detected color")

    return None

def extract_tracks(result, output_folder):
    if 'entries' in result:
        # It's a playlist
        print(f"Found playlist: {result.get('title')} with {len(result['entries'])} tracks")
        return youtube_utils.extract_tracks_from_playlist(result)
    else:
        # It's a single video - try to split if it has chapters
        print(f"Found video: {result.get('title')}")
        return youtube_utils.split_album_video(result, output_folder)

if __name__ == "__main__":
    main()
