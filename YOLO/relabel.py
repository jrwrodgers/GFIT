import os

from torch.ao.quantization.pt2e.graph_utils import update_equivalent_types_dict

# 📂 Set your labels folder path
labels_dir = r"C:\Users\jrwro\Documents\GitHub\GFIT\YOLO\train\labels"

# ✅ Loop through all label files
for file_name in os.listdir(labels_dir):
    if file_name.endswith(".txt"):
        file_path = os.path.join(labels_dir, file_name)

        updated_lines = []
        with open(file_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                print(parts)
                if not parts:
                    continue  # Skip empty lines

                try:
                    # Reduce class ID by 1
                    class_id = int(parts[0]) - 1

                    # Prevent negative IDs (skip line if invalid)
                    if class_id < 0:
                        print(f"⚠️ Skipping negative class in {file_name}: {line.strip()}")
                        continue

                    # Rebuild the line
                    new_line = " ".join([str(class_id)] + parts[1:])
                    updated_lines.append(new_line)
                    print(updated_lines)

                except ValueError:
                    print(f"⚠️ Invalid line in {file_name}: {line.strip()}")

        # ✅ Overwrite file with updated content
        with open(file_path, "w") as f:
            for new_line in updated_lines:
                f.write(new_line + "\n")

        print(f"✅ Updated: {file_name}")

print("🎉 All label files processed successfully!")
