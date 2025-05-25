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
    Add a LinkedIn-style circular watermark with green border
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # Circle parameters - positioned in bottom right
    circle_size = min(width, height) // 4  # Smaller size
    margin = 30
    circle_x = width - circle_size - margin
    circle_y = height - circle_size - margin
    
    # LinkedIn-style colors
    green_color = (25, 135, 84)  # LinkedIn green
    border_width = 8
    
    # Draw outer green border circle
    draw.ellipse([circle_x, circle_y, circle_x + circle_size, circle_y + circle_size], 
                fill=green_color + (220,), outline=green_color + (255,), width=border_width)
    
    # Draw inner semi-transparent white background
    inner_margin = border_width + 5
    inner_circle_size = circle_size - (inner_margin * 2)
    inner_x = circle_x + inner_margin
    inner_y = circle_y + inner_margin
    
    draw.ellipse([inner_x, inner_y, inner_x + inner_circle_size, inner_y + inner_circle_size], 
                fill=(255, 255, 255, 200))  # Semi-transparent white
    
    # Add text with better font handling
    try:
        font_size = max(10, circle_size // 12)
        # Try different font paths for different systems
        font_paths = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/Windows/Fonts/arial.ttf",
            "arial.ttf"
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
    
    # Format text for better fit
    if "support" in text.lower() and "amit" in text.lower():
        # Split into two lines for better readability
        lines = ["I support", "AMIT Maurya"]
    else:
        # Split text into lines to fit in circle
        words = text.split()
        lines = []
        current_line = []
        max_chars_per_line = 12  # Adjust based on circle size
        
        for word in words:
            test_line = ' '.join(current_line + [word])
            if len(test_line) <= max_chars_per_line:
                current_line.append(word)
            else:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                else:
                    lines.append(word)
        
        if current_line:
            lines.append(' '.join(current_line))
    
    # Draw text lines
    try:
        line_height = font.getbbox('A')[3] if hasattr(font, 'getbbox') else font_size + 2
    except:
        line_height = font_size + 2
        
    total_text_height = len(lines) * line_height
    start_y = circle_y + (circle_size - total_text_height) // 2
    
    for i, line in enumerate(lines):
        try:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
        except:
            text_width = len(line) * (font_size // 2)  # Rough estimate
            
        text_x = circle_x + (circle_size - text_width) // 2
        text_y = start_y + i * line_height
        
        # Draw text with green color to match LinkedIn style
        draw.text((text_x, text_y), line, fill=green_color + (255,), font=font)
    
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
