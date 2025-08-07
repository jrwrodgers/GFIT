import os
import cv2
import random

# === CONFIGURATION ===
image_dir = 'train/images'
label_dir = 'train/labels'
class_colors = {}  # Will assign a random color per class
class_names = {}   # Optional: Map class IDs to names here if you want (e.g., {0: "cat", 1: "dog"})
image_exts = ['.jpg', '.jpeg', '.png']
window_name = "YOLO Label Viewer"

# === Load and sort image files ===
image_files = sorted([f for f in os.listdir(image_dir) if os.path.splitext(f)[1].lower() in image_exts])
index = 0

# === Draw bounding boxes ===
def draw_boxes(img, label_path):
    h, w = img.shape[:2]
    if not os.path.exists(label_path):
        return img

    with open(label_path, 'r') as f:
        for line in f.readlines():
            parts = line.strip().split()
            if len(parts) != 5:
                continue
            cls_id, x_center, y_center, box_w, box_h = map(float, parts)
            cls_id = int(cls_id)

            # Convert normalized coords to pixel values
            x1 = int((x_center - box_w / 2) * w)
            y1 = int((y_center - box_h / 2) * h)
            x2 = int((x_center + box_w / 2) * w)
            y2 = int((y_center + box_h / 2) * h)

            # Assign a unique color to each class
            if cls_id not in class_colors:
                class_colors[cls_id] = [random.randint(0, 255) for _ in range(3)]

            color = class_colors[cls_id]
            label = class_names.get(cls_id, str(cls_id))

            cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)
            cv2.putText(img, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    return img

# === Viewer loop ===
while True:
    if not image_files:
        print("No images found.")
        break

    img_name = image_files[index]
    base_name = os.path.splitext(img_name)[0]
    img_path = os.path.join(image_dir, img_name)
    label_path = os.path.join(label_dir, base_name + '.txt')

    img = cv2.imread(img_path)
    if img is None:
        print(f"Failed to load {img_path}")
        continue

    img_with_boxes = draw_boxes(img.copy(), label_path)
    cv2.imshow(window_name, img_with_boxes)

    key = cv2.waitKey(0)

    if key == ord('q') or key == 27:  # 'q' or ESC to quit
        break
    elif key in [ord('d'), 83]:  # 'd' or right arrow
        index = (index + 1) % len(image_files)
    elif key in [ord('a'), 81]:  # 'a' or left arrow
        index = (index - 1) % len(image_files)

cv2.destroyAllWindows()
