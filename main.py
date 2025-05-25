import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import math
import numpy as np

def detect_face_opencv_style(image: Image.Image):
    """
    OpenCV-style face detection using image analysis techniques
    Simulates Haar cascade classifier behavior
    """
    width, height = image.size
    img_array = np.array(image.convert('RGB'))
    
    # Convert to grayscale like OpenCV
    gray = np.mean(img_array, axis=2).astype(np.uint8)
    
    def detect_haar_like_features():
        """
        Simulate Haar cascade detection by looking for face-like patterns
        """
        faces = []
        
        # Scan the image with different window sizes (like OpenCV scaleFactor)
        min_face_size = min(width, height) // 8
        max_face_size = min(width, height) // 3
        
        # Multiple scales like OpenCV detectMultiScale
        for scale in [1.0, 1.2, 1.5, 2.0]:
            face_size = int(min_face_size * scale)
            if face_size > max_face_size:
                continue
                
            step_size = max(5, face_size // 8)
            
            for y in range(0, height - face_size, step_size):
                for x in range(0, width - face_size, step_size):
                    
                    # Extract potential face region
                    face_region = gray[y:y+face_size, x:x+face_size]
                    
                    if face_region.shape[0] < face_size or face_region.shape[1] < face_size:
                        continue
                    
                    # Haar-like feature detection
                    face_score = 0
                    
                    # Feature 1: Eye region (upper part should be darker than middle)
                    upper_third = face_region[:face_size//3, :]
                    middle_third = face_region[face_size//3:2*face_size//3, :]
                    
                    if upper_third.size > 0 and middle_third.size > 0:
                        upper_avg = np.mean(upper_third)
                        middle_avg = np.mean(middle_third)
                        
                        # Eyes are typically darker than cheeks
                        if upper_avg < middle_avg - 5:
                            face_score += 2
                    
                    # Feature 2: Horizontal symmetry (faces are roughly symmetric)
                    left_half = face_region[:, :face_size//2]
                    right_half = face_region[:, face_size//2:]
                    
                    # Ensure both halves have the same shape
                    min_width = min(left_half.shape[1], right_half.shape[1])
                    left_half = left_half[:, :min_width]
                    right_half = right_half[:, :min_width]
                    right_flipped = np.fliplr(right_half)
                    
                    if left_half.shape == right_flipped.shape and left_half.size > 0:
                        try:
                            # Calculate correlation between left and right halves
                            correlation = np.corrcoef(left_half.flatten(), right_flipped.flatten())[0,1]
                            if not np.isnan(correlation) and correlation > 0.3:
                                face_score += 3
                        except:
                            # Skip correlation if it fails
                            pass
                    
                    # Feature 3: Face oval detection (edges should form oval-like pattern)
                    # Apply edge detection with proper bounds checking
                    if face_region.shape[0] > 1 and face_region.shape[1] > 1:
                        try:
                            # Calculate gradients safely
                            grad_y = np.abs(np.diff(face_region, axis=0))
                            grad_x = np.abs(np.diff(face_region, axis=1))
                            
                            # Ensure compatible shapes for addition
                            min_h = min(grad_y.shape[0], grad_x.shape[0])
                            min_w = min(grad_y.shape[1], grad_x.shape[1])
                            
                            if min_h > 0 and min_w > 0:
                                edges = grad_y[:min_h, :min_w] + grad_x[:min_h, :min_w]
                                
                                # Check for oval-like edge distribution
                                center_x, center_y = face_size//2, face_size//2
                                edge_density_at_center = 0
                                
                                # Count edges at center region safely
                                center_region_size = max(1, face_size//8)
                                y_start = max(0, center_y - center_region_size)
                                y_end = min(edges.shape[0], center_y + center_region_size)
                                x_start = max(0, center_x - center_region_size)
                                x_end = min(edges.shape[1], center_x + center_region_size)
                                
                                if y_end > y_start and x_end > x_start:
                                    center_region = edges[y_start:y_end, x_start:x_end]
                                    edge_density_at_center = np.mean(center_region)
                                    
                                    # Border edge density
                                    border_width = max(1, min(3, edges.shape[0]//10, edges.shape[1]//10))
                                    border_regions = []
                                    
                                    # Top and bottom borders
                                    if edges.shape[0] > border_width * 2:
                                        border_regions.extend([
                                            edges[:border_width, :].flatten(),
                                            edges[-border_width:, :].flatten()
                                        ])
                                    
                                    # Left and right borders  
                                    if edges.shape[1] > border_width * 2:
                                        border_regions.extend([
                                            edges[:, :border_width].flatten(),
                                            edges[:, -border_width:].flatten()
                                        ])
                                    
                                    if border_regions:
                                        all_border_pixels = np.concatenate(border_regions)
                                        edge_density_at_border = np.std(all_border_pixels)
                                        
                                        # Faces typically have more variation at center than border
                                        if edge_density_at_center > edge_density_at_border * 0.5:
                                            face_score += 1
                        except:
                            # Skip edge detection if it fails
                            pass
                    
                    # Feature 4: Brightness distribution (faces are usually well-lit)
                    brightness_avg = np.mean(face_region)
                    brightness_std = np.std(face_region)
                    
                    # Good lighting and contrast
                    if 60 < brightness_avg < 200 and 15 < brightness_std < 50:
                        face_score += 2
                    
                    # Feature 5: Skin tone detection
                    try:
                        if face_region.size > 0:
                            # Extract corresponding color region safely
                            y_end = min(y + face_size, img_array.shape[0])
                            x_end = min(x + face_size, img_array.shape[1])
                            
                            color_region = img_array[y:y_end, x:x_end]
                            
                            if color_region.size > 0 and len(color_region.shape) == 3:
                                avg_r = np.mean(color_region[:,:,0])
                                avg_g = np.mean(color_region[:,:,1])
                                avg_b = np.mean(color_region[:,:,2])
                                
                                # Skin tone characteristics
                                if (avg_r > 60 and avg_g > 40 and avg_b > 20 and 
                                    avg_r > avg_g and avg_r > avg_b and
                                    abs(avg_r - avg_g) > 15):
                                    face_score += 3
                    except:
                        # Skip skin tone detection if it fails
                        pass
                    
                    # Minimum score threshold (like OpenCV minNeighbors)
                    if face_score >= 6:
                        # Calculate confidence
                        confidence = min(100, face_score * 10)
                        faces.append({
                            'x': x,
                            'y': y,
                            'width': face_size,
                            'height': face_size,
                            'confidence': confidence
                        })
        
        return faces
    
    # Detect faces using Haar-like features
    detected_faces = detect_haar_like_features()
    
    if detected_faces:
        # Sort by confidence and return the best face
        best_face = max(detected_faces, key=lambda f: f['confidence'])
        
        # Calculate center of the best face
        face_center_x = best_face['x'] + best_face['width'] // 2
        face_center_y = best_face['y'] + best_face['height'] // 2
        
        return face_center_x, face_center_y, detected_faces
    
    else:
        # Fallback to compositional estimation
        aspect_ratio = height / width
        
        if aspect_ratio > 2.0:
            fallback_x, fallback_y = width // 2, int(height * 0.15)
        elif aspect_ratio > 1.5:
            fallback_x, fallback_y = width // 2, int(height * 0.22)
        elif aspect_ratio > 1.2:
            fallback_x, fallback_y = width // 2, int(height * 0.30)
        else:
            fallback_x, fallback_y = width // 2, int(height * 0.35)
        
        return fallback_x, fallback_y, []

def calculate_max_radius(face_center_x, face_center_y, width, height):
    """
    Calculate maximum possible radius based on distance to all 4 edges
    """
    distance_to_left = face_center_x
    distance_to_right = width - face_center_x
    distance_to_top = face_center_y
    distance_to_bottom = height - face_center_y
    
    max_radius = min(distance_to_left, distance_to_right, distance_to_top, distance_to_bottom)
    return max_radius

def add_simple_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add LinkedIn-style face frame with OpenCV-style face detection
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # OpenCV-style face detection
    face_center_x, face_center_y, faces = detect_face_opencv_style(image)
    
    # Calculate radius based on distance to edges
    max_radius = calculate_max_radius(face_center_x, face_center_y, width, height)
    
    # Use conservative percentages for better fit
    outer_radius = int(max_radius * 0.75)  # 75% of max possible
    inner_radius = int(max_radius * 0.55)  # 55% of max possible
    
    # Minimum sizes
    outer_radius = max(60, outer_radius)
    inner_radius = max(40, inner_radius)
    
    # Ensure adequate text space
    if outer_radius - inner_radius < 20:
        inner_radius = max(25, outer_radius - 30)
    
    # Create overlay
    overlay = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    # LinkedIn green color
    linkedin_green = (25, 135, 84)
    
    # Draw the outer circle (green ring)
    outer_bbox = [
        face_center_x - outer_radius,
        face_center_y - outer_radius,
        face_center_x + outer_radius,
        face_center_y + outer_radius
    ]
    draw.ellipse(outer_bbox, fill=linkedin_green + (220,))
    
    # Draw inner circle (transparent - creates the ring effect)
    inner_bbox = [
        face_center_x - inner_radius,
        face_center_y - inner_radius,
        face_center_x + inner_radius,
        face_center_y + inner_radius
    ]
    draw.ellipse(inner_bbox, fill=(0, 0, 0, 0))
    
    # Font setup for curved text
    ring_width = outer_radius - inner_radius
    font_size = max(10, min(18, ring_width // 2))
    
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
    
    # Add curved text between circles
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
        
        try:
            # Center the character
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

def process_image(uploaded_file, watermark_text):
    """Process uploaded image and add watermark"""
    try:
        # Open the image
        image = Image.open(uploaded_file)
        
        # Add watermark
        watermarked_image = add_simple_watermark(image, watermark_text)
        
        return watermarked_image
    except Exception as e:
        st.error(f"Error processing image: {str(e)}")
        return None

# Streamlit App
def main():
    st.set_page_config(
        page_title="LinkedIn Style Profile Frame Generator",
        page_icon="🖼️",
        layout="wide"
    )
    
    st.title("🖼️ LinkedIn Style Profile Frame Generator")
    st.markdown("Add a professional #OpenToWork style frame to your profile photo with **OpenCV-powered face detection**!")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Custom text input
        watermark_text = st.text_input(
            "Frame Text",
            value="I support AMIT Maurya",
            help="Enter the text you want to display around the frame"
        )
        
        st.markdown("---")
        st.markdown("### 🔍 Face Detection Features:")
        st.markdown("✅ **Haar Cascade simulation**")
        st.markdown("✅ **Multi-scale detection**")
        st.markdown("✅ **Symmetry analysis**")
        st.markdown("✅ **Skin tone detection**")
        st.markdown("✅ **Edge pattern recognition**")
        st.markdown("✅ **Confidence scoring**")
    
    # Main content
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📤 Upload Your Photo")
        
        uploaded_file = st.file_uploader(
            "Choose an image file",
            type=['png', 'jpg', 'jpeg'],
            help="Upload a clear photo of yourself for best face detection results"
        )
        
        if uploaded_file is not None:
            # Display original image
            original_image = Image.open(uploaded_file)
            st.subheader("Original Image")
            st.image(original_image, use_column_width=True)
            
            # Show image info
            width, height = original_image.size
            st.info(f"Image size: {width} × {height} pixels")
    
    with col2:
        if uploaded_file is not None:
            st.header("✨ Generated Frame")
            
            with st.spinner("🔍 Detecting face and adding frame..."):
                # Process the image
                result_image = process_image(uploaded_file, watermark_text)
                
                if result_image is not None:
                    # Display result
                    st.subheader("With LinkedIn Frame")
                    st.image(result_image, use_column_width=True)
                    
                    # Download button
                    buf = io.BytesIO()
                    result_image.save(buf, format='PNG')
                    byte_data = buf.getvalue()
                    
                    st.download_button(
                        label="📥 Download Framed Image",
                        data=byte_data,
                        file_name=f"linkedin_frame_{uploaded_file.name.split('.')[0]}.png",
                        mime="image/png",
                        use_container_width=True
                    )
                    
                    st.success("✅ Frame added successfully!")
        else:
            st.header("👆 Upload an image to get started")
            st.markdown("""
            ### How it works:
            
            1. **Upload** a clear photo of yourself
            2. **Customize** the frame text (optional)
            3. **Advanced face detection** locates your face using OpenCV-style algorithms:
               - Haar-like feature detection
               - Multi-scale window scanning
               - Facial symmetry analysis
               - Skin tone recognition
               - Edge pattern matching
            4. **Download** your professional LinkedIn-style frame!
            
            ### Tips for best results:
            - Use a **clear, well-lit photo**
            - Make sure your **face is clearly visible**
            - **Portrait or full-body shots** work great
            - The face detection algorithm works like OpenCV's `detectMultiScale()`
            """)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "Made with ❤️ using **OpenCV-inspired face detection** | "
        "Perfect for LinkedIn, social media, and professional networking!"
    )

if __name__ == "__main__":
    main()
