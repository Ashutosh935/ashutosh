from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from PIL import Image, ImageDraw, ImageFont
import io
import math
import os
from typing import Optional

app = FastAPI(title="Photo Watermark Service", version="1.0.0")

def add_circular_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add a circular watermark with curved text to an image
    """
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    # Create a copy to work with
    img_with_watermark = image.copy()
    
    # Calculate dimensions
    width, height = img_with_watermark.size
    min_dimension = min(width, height)
    
    # Circle parameters
    circle_radius = min_dimension // 4
    circle_center = (width // 2, height // 2)
    
    # Create overlay for watermark
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Draw semi-transparent circle background
    circle_bbox = [
        circle_center[0] - circle_radius,
        circle_center[1] - circle_radius,
        circle_center[0] + circle_radius,
        circle_center[1] + circle_radius
    ]
    
    # Green circle background (similar to LinkedIn's #OpenToWork)
    draw.ellipse(circle_bbox, fill=(34, 139, 34, 180))  # Semi-transparent green
    
    # Try to load a font, fallback to default if not available
    try:
        font_size = max(12, circle_radius // 8)
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        try:
            font = ImageFont.load_default()
        except:
            # If default font fails, we'll draw without font
            font = None
    
    if font:
        # Calculate text positioning for curved text
        text_radius = circle_radius - 20
        text_angle_step = 2 * math.pi / len(text)
        
        # Draw text along the circle
        for i, char in enumerate(text):
            angle = i * text_angle_step - math.pi/2  # Start from top
            
            # Calculate position for each character
            x = circle_center[0] + text_radius * math.cos(angle)
            y = circle_center[1] + text_radius * math.sin(angle)
            
            # Draw character
            draw.text((x, y), char, fill='white', font=font, anchor='mm')
    
    # Alternative: Draw text horizontally across the circle if curved text is too complex
    else:
        # Fallback: simple horizontal text
        text_bbox = draw.textbbox((0, 0), text)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        text_x = circle_center[0] - text_width // 2
        text_y = circle_center[1] - text_height // 2
        
        draw.text((text_x, text_y), text, fill='white')
    
    # Composite the overlay onto the original image
    img_with_watermark = Image.alpha_composite(img_with_watermark, overlay)
    
    return img_with_watermark

def detect_face_center(image: Image.Image):
    """
    Improved face detection logic for different image types
    """
    width, height = image.size
    
    # Calculate aspect ratio to determine image type
    aspect_ratio = height / width
    
    if aspect_ratio > 1.5:
        # Very tall image (full body or long portrait)
        # Face is likely in the top 20% of the image
        face_center_x = width // 2
        face_center_y = int(height * 0.20)  # 20% from top for full body shots
    elif aspect_ratio > 1.2:
        # Portrait image (shoulders and up)
        # Face is in the top 30% of image
        face_center_x = width // 2
        face_center_y = int(height * 0.30)  # 30% from top for portraits
    elif aspect_ratio > 0.8:
        # Square-ish image
        # Face is usually in upper center
        face_center_x = width // 2
        face_center_y = int(height * 0.35)
    else:
        # Landscape image
        # Face could be anywhere, assume center
        face_center_x = width // 2
        face_center_y = int(height * 0.4)
    
    # Additional logic: for very tall images, assume it's a full body shot
    # and the face is in the very top portion
    if height > width * 2:
        face_center_y = int(height * 0.15)  # Very top for full body shots
    
    return face_center_x, face_center_y

def calculate_max_radius(face_center_x, face_center_y, width, height):
    """
    Calculate maximum possible radius based on distance to all 4 edges
    """
    # Distance from face center to each edge
    distance_to_left = face_center_x
    distance_to_right = width - face_center_x
    distance_to_top = face_center_y
    distance_to_bottom = height - face_center_y
    
    # Maximum radius is the minimum of all 4 distances
    max_radius = min(distance_to_left, distance_to_right, distance_to_top, distance_to_bottom)
    
    return max_radius

def add_simple_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add LinkedIn-style face frame with precise radius calculation
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # Detect face center
    face_center_x, face_center_y = detect_face_center(image)
    
    # Calculate maximum possible radius based on distance to edges
    max_radius = calculate_max_radius(face_center_x, face_center_y, width, height)
    
    # Use a percentage of max radius for the circles
    # Outer radius: 80% of max possible (leaves 20% margin)
    # Inner radius: 60% of max possible 
    outer_radius = int(max_radius * 0.8)
    inner_radius = int(max_radius * 0.6)
    
    # Ensure minimum readable sizes
    outer_radius = max(60, outer_radius)  # Minimum 60px
    inner_radius = max(40, inner_radius)  # Minimum 40px
    
    # Ensure there's enough space for text between circles
    if outer_radius - inner_radius < 20:
        inner_radius = max(20, outer_radius - 25)
    
    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # LinkedIn green color
    linkedin_green = (25, 135, 84)
    
    # Draw the ring between inner and outer circles
    # First draw outer circle (filled)
    outer_bbox = [
        face_center_x - outer_radius,
        face_center_y - outer_radius,
        face_center_x + outer_radius,
        face_center_y + outer_radius
    ]
    draw.ellipse(outer_bbox, fill=linkedin_green + (200,))
    
    # Then draw inner circle (transparent) to create the ring effect
    inner_bbox = [
        face_center_x - inner_radius,
        face_center_y - inner_radius,
        face_center_x + inner_radius,
        face_center_y + inner_radius
    ]
    draw.ellipse(inner_bbox, fill=(0, 0, 0, 0))  # Transparent inner circle
    
    # Font setup for curved text
    ring_width = outer_radius - inner_radius
    font_size = max(8, min(16, ring_width // 2))  # Font size based on ring width
    
    try:
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        
        font = None
        for font_path in font_paths:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue
        
        if not font:
            font = ImageFont.load_default()
            
    except:
        font = ImageFont.load_default()
    
    # Add curved text between the circles
    text_radius = (inner_radius + outer_radius) // 2  # Middle of the ring
    
    # Format text like LinkedIn
    if "support" in text.lower() and "amit" in text.lower():
        display_text = "#I SUPPORT AMIT MAURYA"
    else:
        display_text = f"#{text.upper()}"
    
    # Calculate text positioning around the circle
    text_length = len(display_text)
    angle_per_char = (2 * math.pi * 0.75) / text_length  # Use 75% of circle
    start_angle = -math.pi * 0.375  # Start from left side
    
    # Draw each character along the curved path
    for i, char in enumerate(display_text):
        angle = start_angle + i * angle_per_char
        
        # Calculate position
        x = face_center_x + text_radius * math.cos(angle)
        y = face_center_y + text_radius * math.sin(angle)
        
        # Draw character (should always be within bounds due to our radius calculation)
        try:
            # Try to center the character
            char_bbox = draw.textbbox((0, 0), char, font=font)
            char_width = char_bbox[2] - char_bbox[0]
            char_height = char_bbox[3] - char_bbox[1]
            
            char_x = x - char_width // 2
            char_y = y - char_height // 2
            
            draw.text((char_x, char_y), char, fill='white', font=font)
        except:
            # Fallback positioning
            draw.text((x-font_size//4, y-font_size//4), char, fill='white', font=font)
    
    # Apply the overlay
    img_with_watermark = Image.alpha_composite(img_with_watermark, overlay)
    return img_with_watermark

@app.post("/add-watermark/")
async def add_watermark_to_photo(
    file: UploadFile = File(...),
    text: Optional[str] = "I support AMIT Maurya",
    style: Optional[str] = "simple"  # "simple" or "curved"
):
    """
    Upload a photo and add a circular watermark with custom text
    """
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    try:
        # Read the uploaded image
        image_data = await file.read()
        image = Image.open(io.BytesIO(image_data))
        
        # Add watermark based on style
        if style == "curved":
            watermarked_image = add_circular_watermark(image, text)
        else:
            watermarked_image = add_simple_watermark(image, text)
        
        # Convert back to RGB if needed for JPEG output
        if watermarked_image.mode == 'RGBA':
            # Create white background
            rgb_image = Image.new('RGB', watermarked_image.size, (255, 255, 255))
            rgb_image.paste(watermarked_image, mask=watermarked_image.split()[-1])
            watermarked_image = rgb_image
        
        # Save to bytes
        output_buffer = io.BytesIO()
        watermarked_image.save(output_buffer, format='JPEG', quality=95)
        output_buffer.seek(0)
        
        # Return the watermarked image
        return StreamingResponse(
            io.BytesIO(output_buffer.read()),
            media_type="image/jpeg",
            headers={"Content-Disposition": "attachment; filename=watermarked_image.jpg"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

@app.get("/")
async def root():
    return {
        "message": "Photo Watermark Service",
        "endpoints": {
            "POST /add-watermark/": "Upload photo and add watermark",
            "Parameters": {
                "file": "Image file to upload",
                "text": "Custom watermark text (optional, default: 'I support AMIT Maurya')",
                "style": "Watermark style - 'simple' or 'curved' (optional, default: 'simple')"
            }
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
