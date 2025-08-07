import json
from operator import truediv

import cv2
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageTk
import os
import glob
from pathlib import Path


DEBUG=True

class TaggerApp:
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

        # self.current_class = 0  # 0=Gate, 1=Flag, 3=pip, 4=quad
        # self.annotation_counts = {0: 0, 1: 0}
        self.saved_items = []
        self.state = 0 #1 for a gate , 2 for a flag
        self.points = []
        self.show_bounding_box = False


        # Canvas
        self.canvas = tk.Canvas(root, width=self.canvas_w, height=self.canvas_h, bg="black")
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.focus_set()
        self.canvas.bind("<Configure>", self.resize_canvas)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<Button-3>", self.start_pan)
        self.canvas.bind("<B3-Motion>", self.do_pan)
        self.canvas.bind("<MouseWheel>", self.on_zoom)
        self.canvas.bind("<Button-4>", lambda e: self.on_zoom(e, delta=1))
        self.canvas.bind("<Button-5>", lambda e: self.on_zoom(e, delta=-1))
        self.canvas.bind("<KeyPress>", self.on_key_press)
        self.canvas.bind("<space>", self.on_space)

        # Buttons
        btn_frame = tk.Frame(root)
        btn_frame.pack()
        tk.Button(btn_frame, text="Load Video", command=self.load_video).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="<<< Prev", command= lambda: self.prev_frame(15)).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="< Prev", command= lambda: self.prev_frame(1)).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Next >", command= lambda: self.next_frame(1)).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Next >>>", command= lambda: self.next_frame(15)).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Save", command=self.save_object).pack(side=tk.LEFT)
        tk.Button(btn_frame, text="Close", command=self.close).pack(side=tk.LEFT)
        self.stats_label = tk.Label(root, text="", font=("Arial", 10))
        self.stats_label.pack()
        self.progress_canvas = tk.Canvas(root, height=20, bg="gray")
        self.progress_canvas.pack(fill=tk.X)
        self.progress_canvas.bind("<Button-1>", self.scrub_to_frame)

        self.framecount_row = tk.Frame(root)  # Use CTkFrame for styling
        self.framecount_row.pack()

        self.frame_label = tk.Label(self.framecount_row, text=f"Frame={self.frame_index}", bg="white", font=("Arial", 14))
        self.frame_label.pack(side=tk.LEFT)

        self.checkbox_row = tk.Frame(root)  # Use CTkFrame for styling
        self.checkbox_row.pack()

        # Checkbox container

        self.check_var_1 = tk.StringVar(value="off")
        checkbox_top = tk.Checkbutton(
            master=self.checkbox_row,
            text="Show Bounding Boxes",
            variable=self.check_var_1,
            command=self.bounding_box_toggle
        )
        checkbox_top.pack()  # Top gap, no bottom gap

        self.text_row = tk.Frame(root)  # Use CTkFrame for styling
        self.text_row.pack()
        instructions=("Key Commands:\n f = start marking a flag \n"
                      "\"g\" = start marking a gate \n"
                      "\"h\" = start marking a cone \n"
                      "\"j\" = start marking a drone \n"
                      "\"ESC\" = stop marking\n"
                      "\"SPACE\" = save the marked object")
        label = tk.Label(self.text_row, text=instructions, bg="white", font=("Arial", 14), justify=tk.LEFT)
        label.pack(pady=10)

    def on_space(self,event):
        self.save_object()

    def bounding_box_toggle(self):
        if self.show_bounding_box:
            self.show_bounding_box = False
        else:
            self.show_bounding_box = True
        print(self.show_bounding_box)
        self.refresh_canvas()

    def close(self):
        self.root.destroy()

    #### space to save

    def on_key_press(self, event):
        key = event.char
        if DEBUG:
            print(f"Key press: {key}")
        if key.lower() == "f" and self.state == 0:
            self.state = 1
        elif key.lower() == "g" and self.state == 0:
            self.state = 2
        elif key.lower() == "h" and self.state == 0:
            self.state = 3
        elif key.lower() == "j" and self.state == 0:
            self.state = 4
        elif event.keysym == "Escape":
            self.state = 0
            self.points.clear()
            self.refresh_canvas()



    def resize_canvas(self, event):
        self.canvas_w, self.canvas_h = event.width, event.height
        self.refresh_canvas()

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video Files", "*.ts")])
        if not path: return
        self.cap = cv2.VideoCapture(path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.filename = os.path.splitext(os.path.basename(path))[0]
        os.makedirs("processed", exist_ok=True)
        self.frame_index = 0

        #self.buffered_frames = [] #buffer the frame every 10th say
        path = f"{self.filename}_polygons.json"
        try:
            with open(path, "r") as file:
                data = json.load(file)
                data_in_frames = []
                for item in data:
                    data_in_frames.append(item["frame"])
            self.saved_items = data_in_frames
        except FileNotFoundError:
            print("No existing objects .json file found")
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
        self.refresh_canvas()



    def refresh_canvas(self):
        self.frame_label.config(text=f"Frame={self.frame_index}")
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
        if DEBUG:
            if self.state == 1:
                print(f"Selecting a flag, npoints = {len(self.points)}")
            elif self.state == 2:
                print(f"Selecting a gate, npoints = {len(self.points)}")
            elif self.state == 3:
                print(f"Selecting a pip, npoints = {len(self.points)}")

        if self.state != 0:
            if self.state == 1:
                colour = "blue"
            else:
                colour = "red"
            transformed_pts = [(int(center_x + p[0]*scale), int(center_y + p[1]*scale)) for p in self.points]
            for x, y in transformed_pts:
                self.canvas.create_oval(x-5, y-5, x+5, y+5, fill=colour)
            if len(transformed_pts) == 4:
                self.canvas.create_polygon(transformed_pts, outline=colour, stipple="gray50", width=2)


        if self.frame_index in self.saved_items:
            if DEBUG:
                print(f"redrawing saved objects")
            path = f"{self.filename}_polygons.json"
            try:
                with open(path, "r") as file:
                    data = json.load(file)
                if DEBUG:
                    print(f"saved objects{data}")
                for object in data:
                    if object["frame"] == self.frame_index:
                        object_points=[]
                        if object["class_id"] == 0:
                            colour = "blue"
                        elif object["class_id"] == 1:
                            colour = "red"
                        elif object["class_id"] == 2:
                            colour = "cyan"
                        elif object["class_id"] == 3:
                            colour = "pink"
                        else:
                            colour = "green"

                        for point in object["points"]:
                            # transformed_pts = [(int(center_x + p[0] * scale), int(center_y + p[1] * scale)) for p in
                            #                    self.points]
                            x = center_x + point[0] * scale
                            y = center_y + point[1] * scale
                            object_points.append((x, y))
                            self.canvas.create_oval(x-5, y-5, x+5, y+5, fill="yellow")
                        self.canvas.create_polygon(object_points, outline=colour, stipple="gray50", width=2)
            except FileNotFoundError:
                print(f"saved objects not found")

            if self.show_bounding_box:
                print(f"drawing bounding box")
                path_root = "processed/"
                path_pattern = f"{self.filename}_{self.frame_index:04d}*.txt"
                print(f"{path_root}{path_pattern}")
                files = glob.glob(os.path.join(path_root, path_pattern))
                print(f"found {files}")
                img_h, img_w = self.original_frame.shape[:2]
                for object_file in files:
                    print(f"processing {object_file}")
                    try:
                        with open(object_file, "r") as file:
                            for line in file.readlines():
                                print(line)
                                numbers = list(map(float, line.strip().split()))
                                #print(numbers)

                                x = numbers[1] * img_w
                                y = numbers[2] * img_h
                                w = numbers[3] * img_w
                                h = numbers[4] * img_h
                                x1, x2 =center_x +(x - w / 2)* scale, center_x +(x + w / 2)* scale
                                y1, y2 = center_y+ (y - h / 2)* scale,center_y+ (y + h / 2)* scale
                                object_points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
                                #print(object_points)
                                self.canvas.create_polygon(object_points, outline="deeppink", stipple="gray50", width=1)
                    except FileNotFoundError:
                        print(f"File {path} not found")


        # Auto-save
        # if len(self.points) == 4:
        #     self.save_annotation()

        self.draw_progress_bar()

    def save_object(self):
        img_h, img_w = self.original_frame.shape[:2]
        x_coords = [p[0] for p in self.points]
        y_coords = [p[1] for p in self.points]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)

        x_center = ((x_min + x_max) / 2) / img_w
        y_center = ((y_min + y_max) / 2) / img_h
        box_w = (x_max - x_min) / img_w
        box_h = (y_max - y_min) / img_h

        class_id = self.state - 1
        ### check if file exists, need to create _1 _2 _3 for the number of items in this frame

        path_root = f"processed/{self.filename}_{self.frame_index:04d}"
        path_exists = True
        n=1
        while path_exists:
            if os.path.exists(f"{path_root}.txt"):
                print(f"File {path_root} already exists incrementing")
                path_root=f"processed/{self.filename}_{self.frame_index:04d}_{n}"
                n+=1
            else:
                path_exists=False
                print(f"Creating new file {path_root}")

        path = path_root + ".txt"
        with open(path, "w") as f:
            f.write(f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}\n")


        ## save the video frame
        #path = f"processed/{self.filename}_{self.frame_index:04d}.jpg"
        path = path_root + ".jpg"
        cv2.imwrite(path, self.original_frame)

        # save the polygons
        path = f"{self.filename}_polygons.json"
        try:
            with open(path, "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = []  # Create new list if file doesn't exist

        data_object = {"frame": self.frame_index,
                "class_id": class_id,
                "points": self.points
                }
        data.append(data_object)

        with open(path, "w") as f:
            f.write(json.dumps(data, indent=4))


        self.state=0
        self.points.clear()
        self.saved_items.append(self.frame_index)
        self.refresh_canvas()


    # def update_stats(self):
    #     stats = (
    #         f"Frame: {self.frame_index + 1}/{self.total_frames}  |  "
    #         f"Gates: {self.annotation_counts[0]}  |  Flags: {self.annotation_counts[1]}"
    #     )
    #     self.stats_label.config(text=stats)

    def draw_progress_bar(self):
        self.progress_canvas.delete("all")
        if self.total_frames == 0: return
        bar_w = self.progress_canvas.winfo_width()
        self.progress_canvas.create_rectangle(0, 0, bar_w, 20, fill="lightgray")

        for idx in self.saved_items:
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
        if self.state != 0:
            if len(self.points) < 4:
                self.points.append((x, y))

        for i, (px, py) in enumerate(self.points):
            dx = px * scale + center_x - event.x
            dy = py * scale + center_y - event.y
            if dx ** 2 + dy ** 2 < 100:
                self.dragging_point = i
                break
        self.refresh_canvas()

    def on_drag(self, event):
        if self.dragging_point is None: return
        if self.state == 0: return
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

    def prev_frame(self,n):
        self.frame_index -= n
        self.points.clear()
        self.load_frame()

    def next_frame(self,n):
        self.frame_index += n
        self.points.clear()
        self.load_frame()

# Entry Point
if __name__ == "__main__":
    root = tk.Tk()
    root.title("FPV Image Tagger ")
    TaggerApp(root)
    root.mainloop()
