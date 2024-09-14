'''
FINAL CODE
'''


import cv2
import numpy as np
import easyocr
import matplotlib.pyplot as plt

# --- Function Definitions ---

# Function to check if a string contains any digits.
def contains_numbers(text):
    return any(char.isdigit() for char in text)

# Function to calculate the angle of the line (for Hough Transform).
def calculate_line_angle(x1, y1, x2, y2):
    angle = np.arctan2(y2 - y1, x2 - x1) * 180 / np.pi
    return angle

# Function to extend bounding boxes by a fixed number of pixels.
def extend_bounding_box(bbox, image_width, image_height, extend_px=50):
    # Get coordinates of the bounding box (top-left, top-right, bottom-right, bottom-left).
    (tl, tr, br, bl) = bbox
    
    # Convert points to numpy arrays.
    tl = np.array(tl) 
    tr = np.array(tr)
    br = np.array(br)
    bl = np.array(bl)
    
    # Adjust points by extending by extend_px pixels.
    tl[0] = max(0, tl[0] - extend_px)
    tl[1] = max(0, tl[1] - extend_px)
    
    tr[0] = min(image_width - 1, tr[0] + extend_px)
    tr[1] = max(0, tr[1] - extend_px)
    
    br[0] = min(image_width - 1, br[0] + extend_px)
    br[1] = min(image_height - 1, br[1] + extend_px)
    
    bl[0] = max(0, bl[0] - extend_px)
    bl[1] = min(image_height - 1, bl[1] + extend_px)
    
    return [tuple(tl), tuple(tr), tuple(br), tuple(bl)]

# Function to classify lines in the cropped image region.
def classify_line(image, entity):
    # Convert to grayscale.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur, followed by Canny edge detection.
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    
    # Hough Line Transform.
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    
    # Classification based on line angles.
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = calculate_line_angle(x1, y1, x2, y2)

            # Check based on entity (height or width).
            if entity == 'width':
                if -10 <= angle <= 10:  # Horizontal
                    return 'width'
            elif entity == 'height':
                if 80 <= abs(angle) <= 100:  # Vertical
                    return 'height'
    
    return None  # If no lines are detected matching the entity.

# Function to draw bounding boxes on the image.
def draw_bounding_boxes(image, boxes, color=(0, 255, 0)):
    for box in boxes:
        box = np.array(box, dtype=np.int32)
        cv2.polylines(image, [box], isClosed=True, color=color, thickness=2)
    return image

# Function to display an image using Matplotlib.
def display_image(image, title="Image"):
    plt.imshow(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    plt.title(title)
    plt.axis('off')
    plt.show()

returnee = []

# Main function that processes the image. It only considers the specified entity (height or width).
def detect_entity_in_image(image_path, entity):
    """ Process an image to detect either 'height' (vertical lines) or 'width' (horizontal lines) based on the input entity.

    Args:
        image_path (str): Path to the image file.
        entity (str): Name of the entity to detect in the image. Either 'height' or 'width'.
    """
    # Initialize EasyOCR reader.
    reader = easyocr.Reader(['en'])
    
    # Load the image in OpenCV.
    image = cv2.imread(image_path)
    if image is None:
        print(f"Failed to load image: {image_path}")
        return None
    
    image_height, image_width = image.shape[:2]
    image_copy = image.copy()  # Make a copy for original annotation purposes.
    
    # Step 1: Detect all texts and show original bounding boxes.
    results = reader.readtext(image)  # List of (bbox, text, confidence)
    all_bboxes = [r[0] for r in results]  # Extract bounding boxes.
    
    # Visualize step: All bounding boxes.
    display_image(draw_bounding_boxes(image.copy(), all_bboxes), "All Bounding Boxes")
    
    # Step 2: Filter bounding boxes that contain numbers.
    number_bboxes_text = [(r[0], r[1]) for r in results if contains_numbers(r[1])]
    number_bboxes = [bbox for bbox, text in number_bboxes_text]
    
    # Visualize step: Bounding boxes with numbers.
    display_image(draw_bounding_boxes(image.copy(), number_bboxes, color=(255, 0, 0)), "Bounding Boxes with Numbers")
    
    # Step 3: Apply extension of 50px to the bounding boxes.
    extended_bboxes = [extend_bounding_box(bbox, image_width, image_height, extend_px=50) for bbox in number_bboxes]
    
    # Visualize step: Extend bounding boxes by 50px.
    display_image(draw_bounding_boxes(image.copy(), extended_bboxes, color=(0, 0, 255)), "Extended Bounding Boxes by 50px")
    
    # Step 4: Process the text regions with extended bounding boxes.
    found_entity = False  # This keeps track of whether we find the required entity (height or width).
    
    for bbox, (extended_bbox, text) in zip(number_bboxes, zip(extended_bboxes, [t[1] for t in number_bboxes_text])):
        # Convert extended_bbox into integer format for OpenCV cropping.
        x_min = int(min([point[0] for point in extended_bbox]))
        y_min = int(min([point[1] for point in extended_bbox]))
        x_max = int(max([point[0] for point in extended_bbox]))
        y_max = int(max([point[1] for point in extended_bbox]))
        
        # Crop the region of interest (ROI).
        roi = image[y_min:y_max, x_min:x_max]
        
        # Send the ROI to the classifier.
        classification_result = classify_line(roi, entity)
        
        # Annotate the original image with the classification result (width or height) if it matches the desired entity.
        if classification_result and classification_result == entity:
            print(f"Detected {entity} for text '{text}'")
            returnee = text
            cv2.putText(image_copy, classification_result, (x_min, y_min - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
            found_entity = True
    
    # Display the final annotated image after classification.
    display_image(image_copy, f"Final Classification: {entity.capitalize()}")
    
    if not found_entity:
        print(f"No {entity} found in the image.")
    else:
        print(f"Successfully found {entity}.")
    
    return returnee, results


# --- Example of how to call the function ---
image_path = '/content/Test_20_height/31adqhzE7SL.jpg'  # Update with actual image.
entity = 'height'  # Specify entity: 'height' or 'width'

# Call the function to detect the specified entity in the image.
found_entity, results= detect_entity_in_image(image_path, entity)
# print("HEREHERHERHERHERHERH")
# -------------------
# Final Output
print(found_entity)
# -------------------
# print("HEREHERHERHERHERHERH")

# Debug - Solved
# print("EUEUEUEUEUE")
# print(results[1])
# print("EUEUEUEUEUE")
