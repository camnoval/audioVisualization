import os
import re
import sys
import math
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
import subprocess
from moviepy import AudioFileClip
from yt_dlp import YoutubeDL
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
from io import BytesIO
from scipy.io import wavfile
from scipy import signal

# Define helper functions
def sanitize_filename(filename):
    """Remove characters not allowed in Windows filenames"""
    return re.sub(r'[<>:"/\\|?*]', '', filename)

def wavelength_to_rgb(wavelength):
    """Convert a wavelength to an RGB color value"""
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
    """Convert audio frequency to color via wavelength mapping"""
    f = max(min(f, f_max), f_min)
    x = math.log10(f)
    x_min = math.log10(f_min)
    x_max = math.log10(f_max)
    mapped_value = 4.0 + ((x - x_min) / (x_max - x_min)) * 3.0
    wavelength = mapped_value * 100
    rgb = wavelength_to_rgb(wavelength)
    return mapped_value, wavelength, rgb

def get_text_color(bg_color):
    """Determine the best text color (black or white) based on background brightness"""
    # Calculate perceived brightness using the formula: 0.299*R + 0.587*G + 0.114*B
    r, g, b = bg_color
    brightness = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    
    # Return white for dark backgrounds, black for light backgrounds
    return (0, 0, 0) if brightness > 0.5 else (255, 255, 255)

def get_font_path_from_matplotlib(font_name):
    """Use matplotlib's font manager to find a font path"""
    try:
        import matplotlib.font_manager as fm
        # Get a list of all fonts matplotlib can find
        font_files = fm.findSystemFonts(fontpaths=None)
        
        # Look for our desired font
        for font_file in font_files:
            try:
                if font_name.lower() in os.path.basename(font_file).lower():
                    print(f"Found font at: {font_file}")
                    return font_file
            except:
                continue
                
        # If we didn't find an exact match, get the default font that matplotlib would use
        font_path = fm.findfont(fm.FontProperties(family=font_name))
        if os.path.exists(font_path):
            print(f"Using matplotlib's suggested font: {font_path}")
            return font_path
    except Exception as e:
        print(f"Error finding font with matplotlib: {e}")
    
    return None
def process_audio(file_path, segment_duration=0.05):
    """Process audio using scipy instead of librosa to avoid Numba dependency"""
    try:
        # Read audio file using scipy.io.wavfile
        print(f"Reading audio file: {file_path}")
        sample_rate, audio_data = wavfile.read(file_path)
        
        # Convert to mono if stereo
        if len(audio_data.shape) > 1:
            audio_data = np.mean(audio_data, axis=1)
        
        # Normalize data
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
            max_val = np.iinfo(np.int16).max if audio_data.max() > 1.0 else 1.0
            audio_data = audio_data / max_val
        
        # Calculate segment size
        segment_samples = int(segment_duration * sample_rate)
        num_segments = min(1000, len(audio_data) // segment_samples)  # Limit segments
        
        print(f"Analyzing {num_segments} segments...")
        
        # Process each segment
        colors = []
        for i in range(num_segments):
            segment = audio_data[i * segment_samples:(i + 1) * segment_samples]
            
            # Apply window function to reduce edge effects
            segment = segment * signal.windows.hann(len(segment))
            
            # Compute FFT
            fft_data = np.abs(np.fft.rfft(segment))
            
            # Find frequency with maximum magnitude
            freq_bins = np.fft.rfftfreq(len(segment), 1/sample_rate)
            max_idx = np.argmax(fft_data)
            max_freq = freq_bins[max_idx]
            
            # Convert to color
            _, _, rgb = frequency_to_color(max_freq)
            colors.append(rgb)
        
        print(f"Generated {len(colors)} colors")
        return colors
    
    except Exception as e:
        print(f"Audio processing error: {e}")
        # Generate fallback colors if processing fails
        print("Using fallback color pattern")
        return [(int(127 + 127*np.sin(i/20)), 
                 int(127 + 127*np.sin((i+100)/20)), 
                 int(127 + 127*np.sin((i+200)/20))) 
                for i in range(1000)]

def create_gradient_image(colors, height=100):
    """Create a gradient image from a list of colors"""
    width = len(colors)
    img = np.zeros((height, width, 3), dtype=np.uint8)
    for i, color in enumerate(colors):
        img[:, i, :] = color
    return img

def get_dominant_color(images):
    """Extract dominant color from the visualization images with debugging"""
    # Flatten all gradients into one list of colors
    all_colors = []
    for img in images:
        # Convert to PIL Image if numpy array
        if isinstance(img, np.ndarray):
            pil_img = Image.fromarray(img)
        else:
            pil_img = img
            
        # Sample colors more evenly from across the image
        pil_img = pil_img.resize((50, 50))
        pixels = list(pil_img.getdata())
        
        # Take a smaller sample for efficiency
        sample = pixels[::10]  # Take every 10th pixel
        
        for color in sample:
            if isinstance(color, int):  # Skip grayscale
                continue
            if len(color) >= 3:  # RGB or RGBA
                all_colors.append(color[:3])  # Just take RGB values
    
    # Count colors and find most common
    color_counter = Counter(all_colors)
    
    # Print top 5 colors for debugging
    print("\nTop 5 most common colors:")
    for color, count in color_counter.most_common(5):
        print(f"RGB{color}: {count} occurrences")
    
    # Simply use the most common color
    if color_counter:
        return color_counter.most_common(1)[0][0]
    
    return (100, 100, 150)  # Default fallback

def stack_images_with_margin(image_files, margin=10, border=30, bg_color=None, album_title=None):
    """Stack multiple images with margin between them and border around"""
    if not image_files:
        return None
    
    # Load images
    images = []
    for img_file in image_files:
        if isinstance(img_file, str):
            img = Image.open(img_file)
        else:
            img = Image.fromarray(img_file)
        images.append(img)
    
    # If no background color specified, determine from images
    if bg_color is None:
        bg_color = get_dominant_color(images)
        print(f"Using detected background color: RGB{bg_color}")
    else:
        print(f"Using user-specified background color: RGB{bg_color}")
    
    # Determine text color for best contrast
    text_color = get_text_color(bg_color)
    
    # Determine dimensions
    width = max(img.width for img in images)
    total_height = sum(img.height for img in images) + margin * (len(images) - 1)
    
    # Add extra height for title - significantly increased
    title_height = 100 if album_title else 0  # Taller space for title
    
    # Create new image with margin for border
    combined = Image.new('RGB', 
                        (width + 2*border, total_height + 2*border + title_height),
                        color=bg_color)
    
    # Add album title if provided
    if album_title:
        try:
            # First try to get Forte path from matplotlib
            forte_path = get_font_path_from_matplotlib('Forte')
            
            if forte_path:
                font = ImageFont.truetype(forte_path, 72)
                print(f"Using Forte font at: {forte_path}")
            else:
                # Fall back to other options
                try:
                    font = ImageFont.truetype("Arial Bold", 70)
                    print("Using Arial Bold font")
                except:
                    print("Using default font")
                    font = ImageFont.load_default()
                    
            draw = ImageDraw.Draw(combined)
            
            # Calculate text position (centered)
            title_position = (width + 2*border) // 2
            
            # Simplified title - remove parts in brackets for cleaner display
            if " [" in album_title:
                display_title = album_title.split(" [")[0]
            elif " {" in album_title:
                display_title = album_title.split(" {")[0]
            else:
                display_title = album_title
            
            # Get opposite color for outline
            outline_color = (0, 0, 0) if text_color == (255, 255, 255) else (255, 255, 255)
            
            # Draw text outline/shadow for better visibility
            for offset in [(3,3), (-3,-3), (3,-3), (-3,3)]:  # Larger offsets for bigger font
                draw.text((title_position + offset[0], title_height//2), 
                        display_title, fill=outline_color, font=font, anchor="mm")  # Center vertically too
            
            # Draw the main text
            draw.text((title_position, title_height//2), display_title, 
                    fill=text_color, font=font, anchor="mm")  # Centered in title area
            
            print(f"Added title: {display_title}")
            
        except Exception as e:
            print(f"Title rendering error: {e}")
    
    # Paste images with margins
    y_offset = border + title_height
    for img in images:
        # Center horizontally if narrower than max width
        x_offset = border + (width - img.width) // 2
        combined.paste(img, (x_offset, y_offset))
        y_offset += img.height + margin
    
    return combined

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
    audio_clip = AudioFileClip(temp_filename)
    audio_clip.write_audiofile(output_filename, codec='pcm_s16le')
    audio_clip.close()
    os.remove(temp_filename)
    return output_filename, title, artist

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
            import subprocess
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
###############################################################################
#                                Main Script                                  #
###############################################################################

if __name__ == "__main__":
    # Get user input for album/song
    query = input("Enter album or song name: ")
    
    # Search for the album
    print(f"Searching for '{query}'...")
    result = search_youtube_playlist(query)
    
    if not result:
        print("No results found. Please try a different search.")
        sys.exit(1)
    
    # Create output folder based on sanitized album title
    album_title = result.get('title', query)
    output_folder = os.path.join(os.getcwd(), sanitize_filename(album_title))
    os.makedirs(output_folder, exist_ok=True)
    print(f"Saving to folder: {output_folder}")
    
    # Ask user if they want to set a specific background color
    use_custom_bg = input("Would you like to use a custom background color? (y/n): ").lower().startswith('y')
    bg_color = None
    
    if use_custom_bg:
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
            bg_color = color_options[choice]
        elif choice == '6':
            # Allow custom RGB input
            try:
                r = int(input("Enter Red value (0-255): "))
                g = int(input("Enter Green value (0-255): "))
                b = int(input("Enter Blue value (0-255): "))
                bg_color = (min(255, max(0, r)), min(255, max(0, g)), min(255, max(0, b)))
            except:
                print("Invalid RGB values, will use auto-detected color")
        else:
            print("Invalid choice, will use auto-detected color")
    
    # Extract tracks based on whether it's a playlist or a single album video
    if 'entries' in result:
        # It's a playlist
        print(f"Found playlist: {result.get('title')} with {len(result['entries'])} tracks")
        tracks = extract_tracks_from_playlist(result)
    else:
        # It's a single video - try to split if it has chapters
        print(f"Found video: {result.get('title')}")
        tracks = split_album_video(result, output_folder)
    
    if not tracks:
        print("No valid tracks found.")
        sys.exit(1)
    
    print(f"Processing {len(tracks)} tracks...")
    
    # Fixed output dimensions
    final_width = 1000
    final_height = 100
    dpi = 100
    fig_w = final_width / dpi
    fig_h = final_height / dpi
    
    all_image_paths = []
    all_gradient_images = []
        # Process each track
    for idx, track in enumerate(tracks, start=1):
        print(f"Processing track {idx}/{len(tracks)}: {track['title']}")
        try:
            # Download if URL is provided, otherwise use existing file
            if 'url' in track:
                audio_file, song_title, _ = download_youtube_audio_and_metadata(
                    track['url'], 
                    output_filename=os.path.join(output_folder, f"track_{idx:02d}.wav")
                )
            else:
                audio_file = track['file']
                song_title = track['title']
            
            # Process the audio to generate colors
            colors = process_audio(audio_file, segment_duration=0.05)
            
            # Create the gradient image
            base_gradient = create_gradient_image(colors, height=200)
            all_gradient_images.append(base_gradient)
            
            # Create the image with matplotlib
            plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
            plt.imshow(base_gradient, aspect='auto')
            plt.axis('off')
            
            # Determine text color based on average brightness of bottom-left area
            corner_region = base_gradient[-30:, :30, :]  
            avg_color = np.mean(corner_region, axis=(0, 1))
            brightness = (0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]) / 255
            text_color = 'black' if brightness > 0.5 else 'white'
            
            # Create text with improved styling
            font_size = int(final_height * 0.18)  # Larger text
            text = plt.text(
                0.01, 0.01,
                song_title,
                color=text_color,
                fontsize=font_size,
                fontname='Forte',
                fontstyle='italic',  # Italic for style
                transform=plt.gca().transAxes,
                va='bottom',
                ha='left'
            )
            
            # Add outline with opposite color for better visibility
            outline_color = 'white' if text_color == 'black' else 'black'
            text.set_path_effects([
                PathEffects.withStroke(linewidth=3, foreground=outline_color)
            ])
            
            # Save to a BytesIO object first
            buf = BytesIO()
            plt.savefig(
                buf,
                dpi=dpi,
                bbox_inches='tight',
                pad_inches=0,
                format='png'
            )
            plt.close()
            
            # Convert to PIL Image
            buf.seek(0)
            img = Image.open(buf)
            
            # Save individual image
            output_filename = f"{idx:02d}_{sanitize_filename(song_title)}.png"
            full_output_path = os.path.join(output_folder, output_filename)
            img.save(full_output_path)
            all_image_paths.append(full_output_path)
            
            print(f"Saved visualization: {output_filename}")
            
        except Exception as e:
            print(f"Error processing track {idx}: {e}")
    
    # Stack all images with margins
    if all_image_paths:
        print("Creating combined image...")
        
        # Create the combined image with the album title
        combined = stack_images_with_margin(
            all_image_paths, 
            margin=5, 
            border=30, 
            bg_color=bg_color,
            album_title=album_title  # Add the album title
        )
        
        # Save combined image
        combined_path = os.path.join(output_folder, f"{sanitize_filename(album_title)}_combined.png")
        combined.save(combined_path)
        print(f"Saved combined image: {combined_path}")
        
        # Open the final image
        try:
            if sys.platform == 'win32':
                os.startfile(combined_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', combined_path])
            else:
                subprocess.call(['xdg-open', combined_path])
        except Exception as e:
            print(f"Could not open image automatically: {e}")
            print(f"Combined image saved to: {combined_path}")
    
    print("Done!")