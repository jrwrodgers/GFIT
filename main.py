import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import os

class AnnotatorApp:
    def __init__(self, root):
        self.root = root
        self.cap = None
        self.original_frame = None
        self.frame_index = 0
        self.total_frames = 0
        self.filename = ""
        self.canvas_w, self.canvas_h = 1280, 720

        # State
        self.points = []
        self.dragging_point = None
        self.zoom_scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.pan_start_x = None
        self.pan_start_y = None

        self.current_class = 0  # 0=Gate, 1=Flag
        self.annotation_counts = {0: 0, 1: 0}
        self.saved_frames = set()

        # Canvas
        self.canvas = tk.Canvas(root, width=self.canvas_w, height=self.canvas_h, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.bind("<Configure>", self.resize_canvas)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self.on_zoom(e, delta=1))  # Linux
        self.canvas.bind("<Button-5>", lambda e: self.on_zoom(e, delta=-1)) # Linux

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()
        tk.Button(btn_frame, text="Load Video", command=self.load_video).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="<< Prev", command=self.prev_frame).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Next >>", command=self.next_frame).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Gate", command=lambda: self.set_class(0)).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Flag", command=lambda: self.set_class(1)).pack(side=tk.LEFT)

        self.stats_label = tk.Label(root, text="", font=("Arial", 10))
        self.stats_label.pack()

        self.progress_canvas = tk.Canvas(root, height=20, bg="gray")
        self.progress_canvas.pack(fill=tk.X)
        self.progress_canvas.bind("<Button-1>", self.scrub_to_frame)

    def resize_canvas(self, event):
        self.canvas_w, self.canvas_h = event.width, event.height
        self.refresh_canvas()

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.ts")])
        if not path: return
        self.cap = cv2.VideoCapture(path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.filename = os.path.splitext(os.path.basename(path))[0]
        os.makedirs("annotations", exist_ok=True)
        self.frame_index = 0
        self.points.clear()
        self.saved_frames.clear()
        self.annotation_counts = {0: 0, 1: 0}
        self.load_frame()

    def load_frame(self):
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index)
        ret, frame = self.cap.read()
        if not ret: return
        self.original_frame = frame
        self.points.clear()
        self.offset_x = 0
        self.offset_y = 0
        self.zoom_scale = 1.0

        # Load existing annotation
        path = f"annotations/{self.filename}_{self.frame_index:04d}.txt"
        if os.path.exists(path):
            with open(path) as f:
                lines = f.readlines()
            if lines:
                class_id, xc, yc, bw, bh = map(float, lines[-1].strip().split())
                img_h, img_w = self.original_frame.shape[:2]
                x = xc * img_w
                y = yc * img_h
                w = bw * img_w
                h = bh * img_h
                x1, x2 = x - w / 2, x + w / 2
                y1, y2 = y - h / 2, y + h / 2
                self.points = [(x1, y1), (x2, y1), (x2, y2), (x1, y2)]
                self.current_class = int(class_id)
                self.saved_frames.add(self.frame_index)
                self.annotation_counts[self.current_class] += 1
        self.refresh_canvas()

    def set_class(self, class_id):
        self.current_class = class_id
        self.refresh_canvas()

    def refresh_canvas(self):
        self.canvas.delete("all")
        if self.original_frame is None: return

        frame = cv2.cvtColor(self.original_frame, cv2.COLOR_BGR2RGB)
        img_h, img_w = frame.shape[:2]
        scale = min(self.canvas_w / img_w, self.canvas_h / img_h) * self.zoom_scale
        new_w, new_h = int(img_w * scale), int(img_h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
        img = Image.fromarray(resized)
        self.tk_img = ImageTk.PhotoImage(img)

        center_x = (self.canvas_w - new_w) // 2 + self.offset_x
        center_y = (self.canvas_h - new_h) // 2 + self.offset_y
        self.canvas.create_image(center_x, center_y, anchor=tk.NW, image=self.tk_img)

        # Draw annotation
        transformed_pts = [(int(center_x + p[0]*scale), int(center_y + p[1]*scale)) for p in self.points]
        for x, y in transformed_pts:
            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="red")
        if len(transformed_pts) == 4:
            color = "green" if self.current_class == 0 else "blue"
            self.canvas.create_polygon(transformed_pts, outline=color, fill="", width=2)

        # Auto-save
        if len(self.points) == 4:
            self.save_annotation()

        self.update_stats()
        self.draw_progress_bar()

    def save_annotation(self):
        img_h, img_w = self.original_frame.shape[:2]
        x_coords = [p[0] for p in self.points]
        y_coords = [p[1] for p in self.points]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        x_center = ((x_min + x_max) / 2) / img_w
        y_center = ((y_min + y_max) / 2) / img_h
        box_w = (x_max - x_min) / img_w
        box_h = (y_max - y_min) / img_h

        class_id = self.current_class
        path = f"annotations/{self.filename}_{self.frame_index:04d}.txt"
        with open(path, "w") as f:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")

        self.saved_frames.add(self.frame_index)

    def update_stats(self):
        stats = (
            f"Frame: {self.frame_index + 1}/{self.total_frames}  |  "
            f"Gates: {self.annotation_counts[0]}  |  Flags: {self.annotation_counts[1]}"
        )
        self.stats_label.config(text=stats)

    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        if self.total_frames == 0: return
        bar_w = self.progress_canvas.winfo_width()
        self.progress_canvas.create_rectangle(0, 0, bar_w, 20, fill="lightgray")

        for idx in self.saved_frames:
            x = int(bar_w * idx / self.total_frames)
            self.progress_canvas.create_line(x, 0, x, 20, fill="darkgreen", width=2)

        current_x = int(bar_w * self.frame_index / self.total_frames)
        self.progress_canvas.create_line(current_x, 0, current_x, 20, fill="green", width=4)

    def scrub_to_frame(self, event):
        bar_w = self.progress_canvas.winfo_width()
        clicked_frame = int(event.x / bar_w * self.total_frames)
        clicked_frame = max(0, min(clicked_frame, self.total_frames - 1))
        self.frame_index = clicked_frame
        self.points.clear()
        self.load_frame()

    def on_click(self, event):
        img_h, img_w = self.original_frame.shape[:2]
        scale = min(self.canvas_w / img_w, self.canvas_h / img_h) * self.zoom_scale
        center_x = (self.canvas_w - img_w * scale) // 2 + self.offset_x
        center_y = (self.canvas_h - img_h * scale) // 2 + self.offset_y
        x = (event.x - center_x) / scale
        y = (event.y - center_y) / scale

        if len(self.points) < 4:
            self.points.append((x, y))
        else:
            for i, (px, py) in enumerate(self.points):
                dx = px * scale + center_x - event.x
                dy = py * scale + center_y - event.y
                if dx ** 2 + dy ** 2 < 100:
                    self.dragging_point = i
                    break
        self.refresh_canvas()

    def on_drag(self, event):
        if self.dragging_point is None: return
        img_h, img_w = self.original_frame.shape[:2]
        scale = min(self.canvas_w / img_w, self.canvas_h / img_h) * self.zoom_scale
        center_x = (self.canvas_w - img_w * scale) // 2 + self.offset_x
        center_y = (self.canvas_h - img_h * scale) // 2 + self.offset_y
        x = (event.x - center_x) / scale
        y = (event.y - center_y) / scale
        self.points[self.dragging_point] = (x, y)
        self.refresh_canvas()

    def on_zoom(self, event, delta=None):
        old_scale = self.zoom_scale
        factor = 1.2 if (event.delta > 0 or delta == 1) else 0.8
        new_scale = old_scale * factor
        mouse_x, mouse_y = event.x, event.y
        img_h, img_w = self.original_frame.shape[:2]
        img_scale = min(self.canvas_w / img_w, self.canvas_h / img_h)
        true_scale = img_scale * old_scale

        center_x = (self.canvas_w - img_w * true_scale) // 2 + self.offset_x
        center_y = (self.canvas_h - img_h * true_scale) // 2 + self.offset_y

        rel_x = (mouse_x - center_x) / true_scale
        rel_y = (mouse_y - center_y) / true_scale

        new_true_scale = img_scale * new_scale
        self.offset_x = mouse_x - rel_x * new_true_scale - (self.canvas_w - img_w * new_true_scale) // 2
        self.offset_y = mouse_y - rel_y * new_true_scale - (self.canvas_h - img_h * new_true_scale) // 2

        self.zoom_scale = new_scale
        self.refresh_canvas()

    def start_pan(self, event):
        self.pan_start_x = event.x
        self.pan_start_y = event.y

    def do_pan(self, event):
        dx = event.x - self.pan_start_x
        dy = event.y - self.pan_start_y
        self.offset_x += dx
        self.offset_y += dy
        self.pan_start_x = event.x
        self.pan_start_y = event.y
        self.refresh_canvas()

    def prev_frame(self):
        if self.frame_index > 0:
            self.frame_index -= 1
            self.points.clear()
            self.load_frame()

    def next_frame(self):
        if self.frame_index < self.total_frames - 1:
            self.frame_index += 1
            self.points.clear()
            self.load_frame()

# Entry Point
if __name__ == "__main__":
    root = tk.Tk()
    root.title("FPV Annotator")
    AnnotatorApp(root)
    root.mainloop()
