import sys
import os
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM

def convert_svg_to_png(svg_path):
    if not os.path.exists(svg_path):
        print(f"Error: {svg_path} does not exist.")
        return None
        
    png_path = svg_path.replace(".svg", ".png")
    print(f"Converting {svg_path} to {png_path}...")
    try:
        drawing = svg2rlg(svg_path)
        renderPM.drawToFile(drawing, png_path, fmt="PNG")
        print("Conversion successful.")
        return png_path
    except Exception as e:
        print(f"Failed to convert SVG: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) > 1:
        convert_svg_to_png(sys.argv[1])
    else:
        print("Usage: python convert_svg.py <path_to_svg>")
