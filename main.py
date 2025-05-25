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

def add_simple_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add a LinkedIn-style circular watermark exactly like #OpenToWork - small ring in corner
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Circle parameters - SMALL ring in bottom right corner like LinkedIn
    circle_size = min(width, height) // 8  # Much smaller - like LinkedIn
    margin = 15
    circle_x = width - circle_size - margin
    circle_y = height - circle_size - margin
    
    # LinkedIn exact green color
    linkedin_green = (25, 135, 84)
    ring_width = 4  # Thinner ring
    
    # Draw ONLY the green ring border (no fill)
    draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                outline=linkedin_green, width=ring_width)
    
    # Add very light white background inside for text visibility
    inner_margin = ring_width
    inner_size = circle_size - (inner_margin * 2)
    inner_x = circle_x + inner_margin
    inner_y = circle_y + inner_margin
    
    draw.ellipse([inner_x, inner_y, inner_x + inner_size, inner_y + inner_size], 
                fill=(255, 255, 255, 180))  # Light white background
    
    # Font for small text
    try:
        font_size = max(6, circle_size // 20)  # Very small font
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
    
    # Simple text layout - just center the text in the small circle
    center_x = circle_x + circle_size // 2
    center_y = circle_y + circle_size // 2
    
    # Format text to fit in small circle
    if "support" in text.lower() and "amit" in text.lower():
        lines = ["I support", "AMIT Maurya"]
    else:
        # Split long text into multiple lines
        words = text.split()
        lines = []
        current_line = []
        
        for word in words:
            if len(' '.join(current_line + [word])) <= 8:  # Short lines for small circle
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                current_line = [word]
        
        if current_line:
            lines.append(' '.join(current_line))
    
    # Draw text in center of small circle
    line_height = font_size + 1
    total_height = len(lines) * line_height
    start_y = center_y - total_height // 2
    
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(line) * (font_size // 2)
            
        text_x = center_x - text_width // 2
        text_y = start_y + i * line_height
        
        # Draw text in LinkedIn green
        draw.text((text_x, text_y), line, fill=linkedin_green, font=font)
    
    # Composite
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
