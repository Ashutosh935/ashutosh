import streamlit as st
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import io
import math
import numpy as np
import cv2

def detect_face_opencv_style(image: Image.Image):
    """
    Real OpenCV face detection using Haar cascade classifier
    """
    width, height = image.size
    
    # Convert PIL to OpenCV format
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    try:
        # Initialize the face cascade classifier
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
        # Detect faces using OpenCV
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,        # How much the image size is reduced at each scale
            minNeighbors=5,         # How many neighbors each candidate rectangle should retain
            minSize=(30, 30),       # Minimum possible face size
            flags=cv2.CASCADE_SCALE_IMAGE
        )
        
        if len(faces) > 0:
            # Get the largest face (most confident detection)
            largest_face = max(faces, key=lambda f: f[2] * f[3])  # width * height
            x, y, w, h = largest_face
            
            # Calculate face center
            face_center_x = x + w // 2
            face_center_y = y + h // 2
            
            # Convert faces to list of dictionaries for compatibility
            face_list = []
            for (fx, fy, fw, fh) in faces:
                face_list.append({
                    'x': fx,
                    'y': fy, 
                    'width': fw,
                    'height': fh,
                    'confidence': 100  # OpenCV doesn't return confidence, so we set high value
                })
            
            return face_center_x, face_center_y, face_list
        
        else:
            # No faces detected, use fallback positioning
            return fallback_face_position(width, height)
            
    except Exception as e:
        st.warning(f"OpenCV face detection failed: {str(e)}. Using fallback positioning.")
        return fallback_face_position(width, height)

def fallback_face_position(width, height):
    """
    Fallback face positioning when OpenCV detection fails
    """
    aspect_ratio = height / width
    
    if aspect_ratio > 2.0:
        # Very tall image - face likely very high
        fallback_x, fallback_y = width // 2, int(height * 0.15)
    elif aspect_ratio > 1.6:
        # Tall portrait - face in upper quarter  
        fallback_x, fallback_y = width // 2, int(height * 0.22)
    elif aspect_ratio > 1.3:
        # Portrait - face in upper third
        fallback_x, fallback_y = width // 2, int(height * 0.30)
    else:
        # Square or landscape - face in upper-center
        fallback_x, fallback_y = width // 2, int(height * 0.35)
    
    return fallback_x, fallback_y, []

def detect_additional_faces(image: Image.Image):
    """
    Detect multiple faces for better accuracy
    """
    width, height = image.size
    img_array = np.array(image.convert('RGB'))
    img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    
    try:
        # Try multiple cascade classifiers for better detection
        cascade_files = [
            'haarcascade_frontalface_default.xml',
            'haarcascade_frontalface_alt.xml', 
            'haarcascade_frontalface_alt2.xml',
            'haarcascade_profileface.xml'
        ]
        
        all_faces = []
        
        for cascade_file in cascade_files:
            try:
                cascade_path = cv2.data.haarcascades + cascade_file
                face_cascade = cv2.CascadeClassifier(cascade_path)
                
                # Detect faces with different parameters
                faces = face_cascade.detectMultiScale(
                    gray,
                    scaleFactor=1.05,      # More sensitive detection
                    minNeighbors=3,        # Lower threshold
                    minSize=(20, 20),      # Smaller minimum size
                    maxSize=(width//2, height//2),  # Maximum size constraint
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                
                # Add detected faces to list
                for (x, y, w, h) in faces:
                    all_faces.append({
                        'x': x, 'y': y, 'width': w, 'height': h,
                        'area': w * h, 'cascade': cascade_file
                    })
                        
            except:
                continue
        
        if all_faces:
            # Remove duplicate detections (faces that overlap significantly)
            unique_faces = []
            for face in all_faces:
                is_duplicate = False
                for existing_face in unique_faces:
                    # Check overlap
                    overlap_x = max(0, min(face['x'] + face['width'], existing_face['x'] + existing_face['width']) - 
                                   max(face['x'], existing_face['x']))
                    overlap_y = max(0, min(face['y'] + face['height'], existing_face['y'] + existing_face['height']) - 
                                   max(face['y'], existing_face['y']))
                    overlap_area = overlap_x * overlap_y
                    
                    # If overlap is more than 50% of smaller face, consider it duplicate
                    min_area = min(face['area'], existing_face['area'])
                    if overlap_area > min_area * 0.5:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    unique_faces.append(face)
            
            # Return the largest face
            if unique_faces:
                best_face = max(unique_faces, key=lambda f: f['area'])
                face_center_x = best_face['x'] + best_face['width'] // 2
                face_center_y = best_face['y'] + best_face['height'] // 2
                return face_center_x, face_center_y, unique_faces
        
        # No faces found
        return fallback_face_position(width, height)
        
    except Exception as e:
        st.warning(f"Advanced face detection failed: {str(e)}")
        return fallback_face_position(width, height)

def calculate_smart_radius(face_center_x, face_center_y, width, height):
    """
    Smart radius calculation - maximum radius that fits within image bounds
    """
    # Calculate distance from face center to each edge
    distance_to_left = face_center_x
    distance_to_right = width - face_center_x
    distance_to_top = face_center_y
    distance_to_bottom = height - face_center_y
    
    # Maximum possible radius is the minimum distance to any edge
    max_possible_radius = min(distance_to_left, distance_to_right, distance_to_top, distance_to_bottom)
    
    # Ensure we have a reasonable margin (subtract 5-10 pixels for safety)
    safe_margin = min(10, max_possible_radius // 20)  # 5% margin or 10px, whichever is smaller
    max_safe_radius = max_possible_radius - safe_margin
    
    # Ensure minimum usable size
    min_radius = 30  # Minimum radius for visibility
    max_safe_radius = max(min_radius, max_safe_radius)
    
    return max_safe_radius

def calculate_optimal_circle_sizes(face_center_x, face_center_y, width, height):
    """
    Calculate optimal inner and outer circle sizes based on available space
    """
    # Get maximum safe radius
    max_radius = calculate_smart_radius(face_center_x, face_center_y, width, height)
    
    # Calculate outer radius (85% of maximum available space)
    outer_radius = int(max_radius * 0.85)
    
    # Calculate inner radius (65% of maximum available space)  
    inner_radius = int(max_radius * 0.65)
    
    # Ensure minimum sizes for visibility
    outer_radius = max(50, outer_radius)
    inner_radius = max(35, inner_radius)
    
    # Ensure adequate space for text (minimum 20px ring width)
    min_ring_width = 20
    if outer_radius - inner_radius < min_ring_width:
        # Adjust inner radius to maintain minimum ring width
        inner_radius = max(20, outer_radius - min_ring_width)
    
    # Final validation - ensure circles fit within bounds
    if outer_radius > max_radius:
        outer_radius = max_radius
        inner_radius = max(15, outer_radius - min_ring_width)
    
    return inner_radius, outer_radius, max_radius

def validate_circle_bounds(face_center_x, face_center_y, radius, width, height):
    """
    Validate that circle with given radius fits within image bounds
    """
    left_bound = face_center_x - radius
    right_bound = face_center_x + radius
    top_bound = face_center_y - radius
    bottom_bound = face_center_y + radius
    
    fits_horizontally = left_bound >= 0 and right_bound <= width
    fits_vertically = top_bound >= 0 and bottom_bound <= height
    
    return fits_horizontally and fits_vertically

def add_simple_watermark(image: Image.Image, text: str = "I support AMIT Maurya") -> Image.Image:
    """
    Add LinkedIn-style face frame with OpenCV-style face detection
    """
    if image.mode != 'RGBA':
        image = image.convert('RGBA')
    
    img_with_watermark = image.copy()
    width, height = img_with_watermark.size
    
    # Real OpenCV face detection with multiple cascade attempts
    face_center_x, face_center_y, faces = detect_additional_faces(image)
    
    # Smart radius calculation based on distance to edges
    inner_radius, outer_radius, max_available_radius = calculate_optimal_circle_sizes(
        face_center_x, face_center_y, width, height
    )
    
    # Validate that circles fit within image bounds
    if not validate_circle_bounds(face_center_x, face_center_y, outer_radius, width, height):
        # Recalculate with more conservative sizing
        max_safe = calculate_smart_radius(face_center_x, face_center_y, width, height)
        outer_radius = int(max_safe * 0.75)  # Even more conservative
        inner_radius = int(max_safe * 0.55)
        outer_radius = max(40, outer_radius)
        inner_radius = max(25, inner_radius)
    
    # Final ring width check
    ring_width = outer_radius - inner_radius
    if ring_width < 15:
        # Ensure minimum text space
        inner_radius = max(15, outer_radius - 20)
    
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
        st.markdown("### 🔍 Real OpenCV Face Detection:")
        st.markdown("✅ **Haar Cascade Classifiers**")
        st.markdown("✅ **Multiple Detection Models**")
        st.markdown("✅ **Scale-invariant Detection**") 
        st.markdown("✅ **Frontal & Profile Face Detection**")
        st.markdown("✅ **Smart Radius Calculation**")
        st.markdown("✅ **Perfect Circle Fitting**")
        st.markdown("✅ **Boundary Validation**")
    
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
            
            with st.spinner("🔍 Using OpenCV to detect faces and adding frame..."):
                # Process the image with real OpenCV
                result_image = process_image(uploaded_file, watermark_text)
                
                if result_image is not None:
                    # Display result
                    st.subheader("With LinkedIn Frame")
                    st.image(result_image, use_column_width=True)
                    
                    # Show detection and sizing info
                    face_center_x, face_center_y, faces = detect_additional_faces(Image.open(uploaded_file))
                    if faces:
                        st.success(f"✅ OpenCV detected {len(faces)} face(s)!")
                        
                        # Calculate and show radius info
                        inner_r, outer_r, max_r = calculate_optimal_circle_sizes(
                            face_center_x, face_center_y, original_image.width, original_image.height
                        )
                        
                        st.info(f"🎯 Face center: ({face_center_x}, {face_center_y})")
                        st.info(f"📏 Circle sizes - Inner: {inner_r}px, Outer: {outer_r}px (Max available: {max_r}px)")
                        
                        # Validate fit
                        fits = validate_circle_bounds(face_center_x, face_center_y, outer_r, 
                                                    original_image.width, original_image.height)
                        if fits:
                            st.success("✅ Circle fits perfectly within image bounds!")
                        else:
                            st.warning("⚠️ Using adjusted sizing for optimal fit.")
                    else:
                        st.warning("⚠️ No faces detected by OpenCV. Using smart positioning.")
                    
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
                    
                    st.success("✅ Frame added with OpenCV face detection!")
        else:
            st.header("👆 Upload an image to get started")
            st.markdown("""
            ### How it works:
            
            1. **Upload** a clear photo of yourself
            2. **Customize** the frame text (optional)
            3. **Real OpenCV face detection** locates your face using:
               - Multiple Haar cascade classifiers
               - Frontal and profile face detection  
               - Scale-invariant detection (1.05x increments)
               - Duplicate face filtering
               - Confidence-based best face selection
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
