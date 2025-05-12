import re
import math

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
        import os
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