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
        # Face is likely in the top 25% of the image
        face_center_x = width // 2
        face_center_y = int(height * 0.15)  # Much higher up for full body shots
    elif aspect_ratio > 1.2:
        # Portrait image (shoulders and up)
        # Face is in the top 30-40% of image
        face_center_x = width // 2
        face_center_y = int(height * 0.25)  # Higher up for portraits
    elif aspect_ratio > 0.8:
        # Square-ish image
        # Face is usually in upper center
        face_center_x = width // 2
        face_center_y = int(height * 0.35)
    else:
        # Landscape image
        # Face could be anywhere, assume center-left or center-right
        face_center_x = width // 2
        face_center_y = int(height * 0.4)
    
    # Additional logic: for very tall images, assume it's a full body shot
    # and the face is in the very top portion
    if height > width * 2:
        face_center_y = int(height * 0.12)  # Very top for full body shots
    
    return face_center_x, face_center_y

def add_simple_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add LinkedIn-style face frame with improved face detection
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # Detect face center with improved logic
    face_center_x, face_center_y = detect_face_center(image)
    
    # Calculate aspect ratio for better radius calculation
    aspect_ratio = height / width
    
    # Smart radius calculation based on image dimensions and type
    if aspect_ratio > 1.5:
        # Full body shot - smaller circle relative to image
        base_radius = min(width, height) // 8
    elif aspect_ratio > 1.2:
        # Portrait shot - medium circle
        base_radius = min(width, height) // 6
    else:
        # Square or landscape - larger circle
        base_radius = min(width, height) // 5
    
    # Maximum possible radius based on face center position
    max_radius_x = min(face_center_x, width - face_center_x)
    max_radius_y = min(face_center_y, height - face_center_y)
    max_radius = min(max_radius_x, max_radius_y)
    
    # Use smaller of calculated radius and max possible radius
    inner_radius = min(base_radius, int(max_radius * 0.7))
    outer_radius = min(base_radius + 30, int(max_radius * 0.9))
    
    # Ensure minimum sizes
    inner_radius = max(40, inner_radius)
    outer_radius = max(inner_radius + 20, outer_radius)
    
    # If circle would be too big for the detected face position, reduce it
    if face_center_y - outer_radius < 0:
        # Circle would go above image, reduce size
        max_allowed_radius = face_center_y - 10
        if max_allowed_radius > 30:
            outer_radius = max_allowed_radius
            inner_radius = max(30, outer_radius - 25)
    
    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # LinkedIn green color
    linkedin_green = (25, 135, 84)
    
    # Draw the ring between inner and outer circles
    outer_bbox = [
        face_center_x - outer_radius,
        face_center_y - outer_radius,
        face_center_x + outer_radius,
        face_center_y + outer_radius
    ]
    draw.ellipse(outer_bbox, fill=linkedin_green + (200,))
    
    # Inner transparent circle
    inner_bbox = [
        face_center_x - inner_radius,
        face_center_y - inner_radius,
        face_center_x + inner_radius,
        face_center_y + inner_radius
    ]
    draw.ellipse(inner_bbox, fill=(0, 0, 0, 0))
    
    # Font setup
    ring_width = outer_radius - inner_radius
    font_size = max(6, min(14, ring_width // 2))
    
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
    
    # Add curved text
    text_radius = (inner_radius + outer_radius) // 2
    
    # Format text
    if "support" in text.lower() and "amit" in text.lower():
        display_text = "#I SUPPORT AMIT MAURYA"
    else:
        display_text = f"#{text.upper()}"
    
    # Text positioning
    text_length = len(display_text)
    angle_per_char = (2 * math.pi * 0.75) / text_length
    start_angle = -math.pi * 0.375
    
    # Draw curved text
    for i, char in enumerate(display_text):
        angle = start_angle + i * angle_per_char
        
        x = face_center_x + text_radius * math.cos(angle)
        y = face_center_y + text_radius * math.sin(angle)
        
        # Only draw if within bounds
        if 0 <= x <= width and 0 <= y <= height:
            try:
                char_bbox = draw.textbbox((0, 0), char, font=font)
                char_width = char_bbox[2] - char_bbox[0]
                char_height = char_bbox[3] - char_bbox[1]
                
                char_x = x - char_width // 2
                char_y = y - char_height // 2
                
                draw.text((char_x, char_y), char, fill='white', font=font)
            except:
                draw.text((x-font_size//4, y-font_size//4), char, fill='white', font=font)
    
    # Apply overlay
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
