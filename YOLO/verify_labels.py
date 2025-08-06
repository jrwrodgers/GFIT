import os

label_dir = r"C:\Users\jrwro\Documents\GitHub\GFIT\YOLO\train\labels"
class_count = 3  # Change this to your expected number of classes

for file in os.listdir(label_dir):
    if file.endswith(".txt"):
        with open(os.path.join(label_dir, file), "r") as f:
            for i, line in enumerate(f, 1):
                parts = line.strip().split()
                if parts and int(parts[0]) >= class_count:
                    print(f"Invalid class {parts[0]} in {file} line {i}")
