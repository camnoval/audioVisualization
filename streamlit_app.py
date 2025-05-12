import streamlit as st
import os
import sys
import tempfile
import audio_processing
import visualization
import youtube_utils
from config import sanitize_filename
import matplotlib.pyplot as plt

# Set page configuration
st.set_page_config(
    page_title="Audio Color Visualizer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better appearance
st.markdown("""
<style>
    .main .block-container {
        padding-top: 2rem;
    }
    .stButton>button {
        width: 100%;
    }
    .stImage {
        margin-bottom: 1rem;
    }
    .ad-container {
        padding: 10px;
        background-color: #f0f0f0;
        border-radius: 5px;
        margin: 10px 0;
        text-align: center;
        color: #333;
    }
</style>
""", unsafe_allow_html=True)

# Title and description
st.title("🎵 Audio Color Visualizer")
st.markdown("""
Convert your favorite music into beautiful color visualizations! This tool analyzes the 
frequency content of audio and creates a unique color pattern.

*How it works:* Different frequencies are mapped to different colors of the visible spectrum, 
creating a visual representation of your music.
""")

# Add a small ad banner
st.markdown("""
<div class="ad-container">
    <strong>Support our work!</strong> Check out our premium audio tools at <a href="https://example.com">example.com</a>
</div>
""", unsafe_allow_html=True)

# Main operation modes in sidebar
st.sidebar.header("Options")
operation_mode = st.sidebar.radio(
    "Choose operation mode",
    ["Search YouTube", "Upload audio file"]
)

# Color selection options in sidebar
st.sidebar.header("Visualization Style")
use_custom_bg = st.sidebar.checkbox("Use custom background color")
bg_color = None

if use_custom_bg:
    color_option = st.sidebar.selectbox(
        "Choose background color",
        ["Black", "White", "Midnight Blue", "Dark Red", "Dark Green", "Custom RGB"]
    )
    
    color_map = {
        "Black": (0, 0, 0),
        "White": (255, 255, 255),
        "Midnight Blue": (25, 25, 112),
        "Dark Red": (139, 0, 0),
        "Dark Green": (0, 100, 0)
    }
    
    if color_option == "Custom RGB":
        r = st.sidebar.slider("Red", 0, 255, 50)
        g = st.sidebar.slider("Green", 0, 255, 50)
        b = st.sidebar.slider("Blue", 0, 255, 50)
        bg_color = (r, g, b)
    else:
        bg_color = color_map[color_option]

# Create a temporary directory for processing
temp_dir = tempfile.mkdtemp()

# Function to process results and display
def process_and_display_tracks(tracks, album_title):
    if not tracks:
        st.error("No valid tracks found.")
        return
    
    st.write(f"## Processing {len(tracks)} tracks from: {album_title}")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    all_image_paths = []
    all_gradient_images = []
    
    # Process each track
    for idx, track in enumerate(tracks, start=1):
        status_text.text(f"Processing track {idx}/{len(tracks)}: {track['title']}")
        
        try:
            # Download if URL is provided, otherwise use existing file
            if 'url' in track:
                audio_file, song_title, _ = youtube_utils.download_youtube_audio_and_metadata(
                    track['url'], 
                    output_filename=os.path.join(temp_dir, f"track_{idx:02d}.wav")
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
            full_output_path = os.path.join(temp_dir, output_filename)
            
            visualization.create_track_visualization(
                base_gradient, song_title, full_output_path
            )
            all_image_paths.append(full_output_path)
            
            # Update progress
            progress_bar.progress((idx) / len(tracks))
            
        except Exception as e:
            st.error(f"Error processing track {idx}: {str(e)}")
    
    status_text.text("Creating combined visualization...")
    
    # Create the combined image
    if all_image_paths:
        combined_path = visualization.create_combined_image(
            all_image_paths,
            temp_dir,
            album_title,
            bg_color
        )
        
        # Display the combined image
        st.image(combined_path, caption=f"{album_title} - Color Visualization", use_column_width=True)
        
        # Download button for the image
        with open(combined_path, "rb") as file:
            btn = st.download_button(
                label="Download Combined Image",
                data=file,
                file_name=f"{sanitize_filename(album_title)}_visualization.png",
                mime="image/png"
            )
        
        # Display individual tracks in an expander
        with st.expander("Show Individual Track Visualizations"):
            cols = st.columns(3)
            for i, img_path in enumerate(all_image_paths):
                with cols[i % 3]:
                    st.image(img_path, use_column_width=True)
    
    # Success message
    status_text.text("Processing complete!")
    
    # Add another ad at the bottom
    st.markdown("""
    <div class="ad-container">
        <strong>Love this tool?</strong> Support us by sharing with friends or <a href="https://example.com/donate">donating</a>!
    </div>
    """, unsafe_allow_html=True)

# YouTube search mode
if operation_mode == "Search YouTube":
    query = st.text_input("Enter album or song name:", placeholder="e.g., Pink Floyd Dark Side of the Moon")
    
    if st.button("Search and Visualize"):
        if query:
            with st.spinner("Searching YouTube..."):
                result = youtube_utils.search_youtube_playlist(query)
                
                if not result:
                    st.error("No results found. Please try a different search term.")
                else:
                    # Extract album title
                    album_title = result.get('title', query)
                    st.success(f"Found: {album_title}")
                    
                    # Extract tracks based on whether it's a playlist or a single album video
                    if 'entries' in result:
                        # It's a playlist
                        st.info(f"Found playlist with {len(result['entries'])} tracks")
                        tracks = youtube_utils.extract_tracks_from_playlist(result)
                    else:
                        # It's a single video - try to split if it has chapters
                        st.info(f"Found video, checking for chapters...")
                        tracks = youtube_utils.split_album_video(result, temp_dir)
                    
                    # Process and display the tracks
                    process_and_display_tracks(tracks, album_title)
        else:
            st.warning("Please enter an album or song name to search.")

# Upload audio file mode
else:
    st.write("Upload your own audio file for visualization:")
    
    uploaded_file = st.file_uploader("Choose an audio file", type=["mp3", "wav", "m4a", "flac"])
    title = st.text_input("Enter a title for your visualization:", placeholder="My Awesome Track")
    
    if uploaded_file is not None and st.button("Generate Visualization"):
        with st.spinner("Processing audio..."):
            # Save the uploaded file to temp directory
            audio_path = os.path.join(temp_dir, "uploaded_audio.wav")
            
            with open(audio_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            # Convert non-WAV files to WAV using FFmpeg if needed
            if not uploaded_file.name.lower().endswith('.wav'):
                original_path = audio_path
                audio_path = os.path.join(temp_dir, "converted_audio.wav")
                
                try:
                    subprocess.run([
                        'ffmpeg', '-i', original_path, 
                        '-acodec', 'pcm_s16le', 
                        '-ar', '44100', 
                        '-y', audio_path
                    ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception as e:
                    st.error(f"Error converting audio: {str(e)}")
                    st.stop()
            
            # Create a single track with the uploaded file
            track_title = title if title else os.path.splitext(uploaded_file.name)[0]
            tracks = [{
                'id': 'uploaded',
                'title': track_title,
                'file': audio_path
            }]
            
            # Process and display the track
            process_and_display_tracks(tracks, track_title)

# Add footer with credits
st.markdown("---")
st.markdown("""
*Audio Color Visualizer* - Created with ❤️ using Streamlit | 
[GitHub](https://github.com/yourusername/audio-visualizer) | 
[About Me](https://example.com)
""")