import cv2
import random
import tkinter as tk
from tkinter import filedialog
from tkinter import ttk
from ultralytics import YOLO
from PIL import Image, ImageTk

# Load YOLO model
model = YOLO("best.pt")

class_colors = {}
def get_color_for_class(cls_id):
    if cls_id not in class_colors:
        class_colors[cls_id] = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255),
        )
    return class_colors[cls_id]

class VideoPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("YOLO Video Player")
        self.video_path = filedialog.askopenfilename(filetypes=[("Transport Stream Files", "*.ts")])
        if not self.video_path:
            print("No file selected, exiting.")
            exit()

        self.cap = cv2.VideoCapture(self.video_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame = 0
        self.playing = False
        self.buffer = {}

        self.label = tk.Label(root)
        self.label.pack()

        controls_frame = tk.Frame(root)
        controls_frame.pack()

        self.rewind10_btn = tk.Button(controls_frame, text="<< 10", command=self.rewind_10)
        self.rewind10_btn.grid(row=0, column=0)
        self.rewind1_btn = tk.Button(controls_frame, text="< 1", command=self.rewind_1)
        self.rewind1_btn.grid(row=0, column=1)
        self.play_btn = tk.Button(controls_frame, text="Play", command=self.play)
        self.play_btn.grid(row=0, column=2)
        self.pause_btn = tk.Button(controls_frame, text="Pause", command=self.pause)
        self.pause_btn.grid(row=0, column=3)
        self.forward1_btn = tk.Button(controls_frame, text="> 1", command=self.forward_1)
        self.forward1_btn.grid(row=0, column=4)
        self.forward10_btn = tk.Button(controls_frame, text=">> 10", command=self.forward_10)
        self.forward10_btn.grid(row=0, column=5)

        self.progress = ttk.Scale(root, from_=0, to=self.total_frames-1, orient=tk.HORIZONTAL, length=500, command=self.seek)
        self.progress.pack(fill='x', padx=10, pady=5)

        self.update_frame()

    def predict_and_draw(self, frame):
        results = model.predict(frame, conf=0.2, verbose=False)
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                label = model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])

                color = get_color_for_class(cls_id)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                text = f"{label} {conf:.2f}"
                (text_w, text_h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.4, 1)
                cv2.rectangle(frame, (x1, y1 - text_h - 5), (x1 + text_w, y1), color, -1)
                cv2.putText(frame, text, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
        return frame

    def get_frame(self, frame_num):
        if frame_num in self.buffer:
            return self.buffer[frame_num]
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        ret, frame = self.cap.read()
        if ret:
            processed_frame = self.predict_and_draw(frame)
            self.buffer[frame_num] = processed_frame
            if len(self.buffer) > 50:  # limit buffer size
                self.buffer.pop(next(iter(self.buffer)))
            return processed_frame
        return None

    def update_frame(self):
        if self.cap.isOpened():
            frame = self.get_frame(self.current_frame)
            if frame is not None:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                imgtk = ImageTk.PhotoImage(image=img)
                self.label.imgtk = imgtk
                self.label.config(image=imgtk)
                self.progress.set(self.current_frame)
            if self.playing:
                self.current_frame = min(self.current_frame+1, self.total_frames-1)
        self.root.after(30, self.update_frame)

    def play(self):
        self.playing = True

    def pause(self):
        self.playing = False

    def rewind_1(self):
        self.current_frame = max(self.current_frame-1, 0)

    def rewind_10(self):
        self.current_frame = max(self.current_frame-10, 0)

    def forward_1(self):
        self.current_frame = min(self.current_frame+1, self.total_frames-1)

    def forward_10(self):
        self.current_frame = min(self.current_frame+10, self.total_frames-1)

    def seek(self, val):
        self.current_frame = int(float(val))

if __name__ == "__main__":
    root = tk.Tk()
    player = VideoPlayer(root)
    root.mainloop()
