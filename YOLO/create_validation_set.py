import os
import random
import shutil

# Paths
train_images_dir = 'train/images'
train_labels_dir = 'train/labels'
val_images_dir = 'val/images'
val_labels_dir = 'val/labels'

# Create val directories if they don't exist
os.makedirs(val_images_dir, exist_ok=True)
os.makedirs(val_labels_dir, exist_ok=True)

# Get all image files in train/images (common YOLO extensions)
image_extensions = ['.jpg', '.jpeg', '.png']
image_files = [f for f in os.listdir(train_images_dir)
               if os.path.splitext(f)[1].lower() in image_extensions]

# Take 10% random sample
num_val = max(1, int(len(image_files) * 0.1))
val_image_files = random.sample(image_files, num_val)

# Move image-label pairs to val/
for img_file in val_image_files:
    base_name = os.path.splitext(img_file)[0]
    label_file = base_name + '.txt'

    # Define full paths
    img_src = os.path.join(train_images_dir, img_file)
    label_src = os.path.join(train_labels_dir, label_file)
    img_dst = os.path.join(val_images_dir, img_file)
    label_dst = os.path.join(val_labels_dir, label_file)

    # Move image
    shutil.move(img_src, img_dst)

    # Move label (if exists)
    if os.path.exists(label_src):
        shutil.move(label_src, label_dst)
    else:
        print(f"⚠️ Warning: Label file missing for image {img_file}")

print(f"✅ Moved {num_val} image-label pairs to val/")
