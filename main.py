import os
import sys
import audio_processing
import visualization
import youtube_utils
from config import sanitize_filename

def main():
    query = input("Enter album or song name: ")
    
    print(f"Searching for '{query}'...")
    result = youtube_utils.search_youtube_playlist(query)
    
    if not result:
        print("No results found. Please try a different search.")
        sys.exit(1)
    
    album_title = result.get('title', query)
    output_folder = os.path.join(os.getcwd(), sanitize_filename(album_title))
    os.makedirs(output_folder, exist_ok=True)
    print(f"Saving to folder: {output_folder}")
    
    bg_color = get_user_bg_color_choice()
    
    tracks = extract_tracks(result, output_folder)
    
    if not tracks:
        print("No valid tracks found.")
        sys.exit(1)
    
    print(f"Processing {len(tracks)} tracks...")
    all_image_paths = []
    all_gradient_images = []
    
    for idx, track in enumerate(tracks, start=1):
        print(f"Processing track {idx}/{len(tracks)}: {track['title']}")
        try:
            if 'url' in track:
                stream_url = youtube_utils.get_stream_url(track['url'])
                dominant_freqs = youtube_utils.extract_dominant_frequencies_from_stream(stream_url)
                
                # You must define this in audio_processing.py
                colors = audio_processing.map_frequencies_to_colors(dominant_freqs)
                base_gradient = visualization.create_gradient_image(colors, height=200)
                all_gradient_images.append(base_gradient)

                output_filename = f"{idx:02d}_{sanitize_filename(track['title'])}.png"
                full_output_path = os.path.join(output_folder, output_filename)
                
                visualization.create_track_visualization(base_gradient, track['title'], full_output_path)
                all_image_paths.append(full_output_path)
                print(f"Saved visualization: {output_filename}")
            else:
                print(f"No URL found for track {idx}, skipping.")

        except Exception as e:
            print(f"Error processing track {idx}: {e}")
    
    if all_image_paths:
        print("Creating combined image...")
        combined_path = visualization.create_combined_image(
            all_image_paths, output_folder, album_title, bg_color
        )
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
    
    print("Done!")

def get_user_bg_color_choice():
    use_custom_bg = input("Use a custom background color? (y/n): ").lower().startswith('y')
    if not use_custom_bg:
        return None
    color_options = {
        '1': (0, 0, 0),
        '2': (255, 255, 255),
        '3': (25, 25, 112),
        '4': (139, 0, 0),
        '5': (0, 100, 0)
    }
    print("\nSelect a background color:")
    print("1. Black\n2. White\n3. Midnight Blue\n4. Dark Red\n5. Dark Green\n6. Custom RGB")
    choice = input("Choice (1-6): ")
    if choice in color_options:
        return color_options[choice]
    elif choice == '6':
        try:
            r = int(input("Red (0-255): "))
            g = int(input("Green (0-255): "))
            b = int(input("Blue (0-255): "))
            return (r, g, b)
        except:
            print("Invalid values.")
    return None

def extract_tracks(result, output_folder):
    if 'entries' in result:
        print(f"Found playlist: {result.get('title')} with {len(result['entries'])} tracks")
        return youtube_utils.extract_tracks_from_playlist(result)
    else:
        print(f"Found video: {result.get('title')}")
        return youtube_utils.split_album_video(result, output_folder)

if __name__ == "__main__":
    main()
