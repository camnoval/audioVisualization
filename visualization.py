import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patheffects as PathEffects
from PIL import Image, ImageDraw, ImageFont
from collections import Counter
from io import BytesIO
import os
from config import sanitize_filename, get_text_color, get_font_path_from_matplotlib

def create_gradient_image(colors, height=100, target_width=1000):
    """Create a consistent-width gradient image from color list"""
    width = len(colors)
    if width == 0:
        return np.zeros((height, target_width, 3), dtype=np.uint8)

    img = np.zeros((height, target_width, 3), dtype=np.uint8)

    for i in range(min(width, target_width)):
        img[:, i, :] = colors[i]

    # If there's a bunch of silence fill remaining with last valid color until it reaches target width (this is to handle a glitch)
    if width < target_width:
        img[:, width:, :] = colors[-1]

    return img


def get_dominant_color(images):
    """Compute a perceptually balanced dominant color from the list of images (e.g., album covers)"""
    all_pixels = []

    for img in images:
        if isinstance(img, np.ndarray):
            pil_img = Image.fromarray(img)
        else:
            pil_img = img

        pil_img = pil_img.resize((50, 50))
        pixels = list(pil_img.getdata())

        filtered = [p[:3] for p in pixels if isinstance(p, tuple) and 20 < sum(p[:3]) < 740]
        all_pixels.extend(filtered)

    if not all_pixels:
        return (0, 0, 0)

    avg = tuple(int(np.mean([p[i] for p in all_pixels])) for i in range(3))
    print(f"\nCalculated average RGB color from album art: {avg}")
    return avg

def create_track_visualization(gradient_image, title, output_path):
    """Create visualization for a single track"""
    # Fixed output dimensions
    final_width = 1000
    final_height = 100
    dpi = 100
    fig_w = final_width / dpi
    fig_h = final_height / dpi
    
    # Create the image with matplotlib
    plt.figure(figsize=(fig_w, fig_h), dpi=dpi)
    plt.imshow(gradient_image, aspect='auto')
    plt.axis('off')
    
    # Determine text color based on average brightness of bottom-left area
    corner_region = gradient_image[-30:, :30, :]  
    avg_color = np.mean(corner_region, axis=(0, 1))
    brightness = (0.299 * avg_color[0] + 0.587 * avg_color[1] + 0.114 * avg_color[2]) / 255
    text_color = 'black' if brightness > 0.5 else 'white'
    
    # Create text with improved styling
    font_size = int(final_height * 0.18)  # Larger text
    text = plt.text(
        0.01, 0.01,
        title,
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
    
    # Convert to PIL Image and save
    buf.seek(0)
    img = Image.open(buf)
    img.save(output_path)
    
    return output_path

def stack_images_with_margin(image_files, margin=10, border=30, bg_color=None, album_title=None):
    """Stack multiple images with margin between them and border around with adaptive title sizing"""
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
    
    # Calculate ideal title height based on image dimensions
    # For wider images, we can use a larger title area
    # Assume that title height should be proportional to the width but with min/max limits
    min_title_height = 60  # Minimum title space
    max_title_height = 150  # Maximum title space
    
    # Base the title height on total image dimensions
    # Use square root of total area as a reference to avoid extreme ratios
    image_area = width * total_height
    sqrt_area = (image_area ** 0.5)
    
    if album_title:
        # Longer titles need more space
        title_length_factor = min(1.5, max(0.8, len(album_title) / 30))
        title_height = int(min(max_title_height, 
                               max(min_title_height, sqrt_area * 0.1 * title_length_factor)))
    else:
        title_height = 0
    
    print(f"Using title height: {title_height}px for width: {width}px")
    
    # Create new image with margin for border
    combined = Image.new('RGB', 
                        (width + 2*border, total_height + 2*border + title_height),
                        color=bg_color)
    
    # Add album title if provided
    if album_title and title_height > 0:
        try:
            from PIL import ImageFont, ImageDraw
            
            # Simplify display title
            if " [" in album_title:
                display_title = album_title.split(" [")[0]
            elif " {" in album_title:
                display_title = album_title.split(" {")[0]
            else:
                display_title = album_title

            draw = ImageDraw.Draw(combined)

            # Font loading
            forte_path = get_font_path_from_matplotlib('Forte')
            fallback_font = "arialbd.ttf"  # You can adjust this if you want another fallback
            font_path = forte_path or fallback_font

            max_font_size = int(title_height * 0.7)
            min_font_size = 20

            # Try to fit title in one line
            for font_size in range(max_font_size, min_font_size - 1, -2):
                font = ImageFont.truetype(font_path, font_size)
                bbox = draw.textbbox((0, 0), display_title, font=font)
                text_width = bbox[2] - bbox[0]
                if text_width <= width:
                    break
            else:
                # If no font size fits, break into two lines
                words = display_title.split()
                midpoint = len(words) // 2
                line1 = ' '.join(words[:midpoint])
                line2 = ' '.join(words[midpoint:])
                line1_font = ImageFont.truetype(font_path, max(min_font_size, int(title_height * 0.35)))
                line2_font = ImageFont.truetype(font_path, max(min_font_size, int(title_height * 0.35)))

                text_color = get_text_color(bg_color)
                outline_color = (0, 0, 0) if text_color == (255, 255, 255) else (255, 255, 255)
                anchor_x = (width + 2 * border) // 2
                y1 = int(title_height * 0.3)
                y2 = int(title_height * 0.7)

                for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                    draw.text((anchor_x + dx, y1 + dy), line1, font=line1_font, fill=outline_color, anchor="mm")
                    draw.text((anchor_x + dx, y2 + dy), line2, font=line2_font, fill=outline_color, anchor="mm")

                draw.text((anchor_x, y1), line1, font=line1_font, fill=text_color, anchor="mm")
                draw.text((anchor_x, y2), line2, font=line2_font, fill=text_color, anchor="mm")
                print(f"Added title in two lines: '{line1}' / '{line2}'")
                return combined  # Skip single-line drawing below

            # If it fit in one line
            font = ImageFont.truetype(font_path, font_size)
            text_color = get_text_color(bg_color)
            outline_color = (0, 0, 0) if text_color == (255, 255, 255) else (255, 255, 255)
            outline_size = max(2, int(font_size * 0.05))
            x = (width + 2 * border) // 2
            y = title_height // 2

            for dx, dy in [(-outline_size, -outline_size), (outline_size, -outline_size),
                        (-outline_size, outline_size), (outline_size, outline_size)]:
                draw.text((x + dx, y + dy), display_title, fill=outline_color, font=font, anchor="mm")
            draw.text((x, y), display_title, fill=text_color, font=font, anchor="mm")
            print(f"Added title: '{display_title}' with font size {font_size}")

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

def create_combined_image(image_paths, output_folder, album_title, bg_color=None):
    """Create and save a combined image from all track visualizations"""
    combined = stack_images_with_margin(
        image_paths, 
        margin=5, 
        border=30, 
        bg_color=bg_color,
        album_title=album_title
    )
    
    # Save combined image
    combined_path = os.path.join(output_folder, f"{sanitize_filename(album_title)}_combined.png")
    combined.save(combined_path)
    print(f"Saved combined image: {combined_path}")
    
    return combined_path