import cv2
import tkinter as tk
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import time
import threading

# Import các module
from map_processor import Map
from CSP import CSP

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Map Coloring AI - Compare Algorithms")
        self.root.geometry("1200x650")

        # ------ MENU BÊN TRÁI ------
        self.left = tk.Frame(root, bg="#7FB3C8", width=300)
        self.left.pack(side=tk.LEFT, fill=tk.Y)

        tk.Label(self.left, text="MAP COLORING",
                 bg="#7FB3C8", fg="white",
                 font=("Arial", 18, "bold")).pack(pady=15)

        self.round_button("Tải Ảnh Lên", self.load).pack(pady=8)
        self.round_button("So Sánh 2 Thuật Toán", self.compare_both).pack(pady=8)
        self.round_button("Tạm Dừng", self.pause).pack(pady=8)
        self.round_button("Tiếp Tục", self.resume).pack(pady=8)
        self.round_button("Hủy Bỏ", self.cancel).pack(pady=8)

        # Cập nhật Label
        self.time_label_1 = tk.Label(self.left, text="Bản đồ 1 (FC): 0s", bg="#7FB3C8", fg="white", font=("Arial", 11, "bold"))
        self.time_label_1.pack(pady=(20, 5))
        
        self.time_label_2 = tk.Label(self.left, text="Bản đồ 2 (AC-3): 0s", bg="#7FB3C8", fg="white", font=("Arial", 11, "bold"))
        self.time_label_2.pack(pady=5)

        # ------ KHU VỰC HIỂN THỊ BẢN ĐỒ ------
        self.right_frame = tk.Frame(root, bg="#f0f0f0")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        self.frame1 = tk.Frame(self.right_frame, bg="white", highlightbackground="gray", highlightthickness=1)
        self.frame1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(self.frame1, text="Forward Checking (FC)", bg="white", font=("Arial", 12, "bold")).pack(pady=5)
        self.canvas1 = tk.Canvas(self.frame1, bg="white")
        self.canvas1.pack(fill=tk.BOTH, expand=True)

        self.frame2 = tk.Frame(self.right_frame, bg="white", highlightbackground="gray", highlightthickness=1)
        self.frame2.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        tk.Label(self.frame2, text="Pure AC-3 (MAC)", bg="white", font=("Arial", 12, "bold")).pack(pady=5)
        self.canvas2 = tk.Canvas(self.frame2, bg="white")
        self.canvas2.pack(fill=tk.BOTH, expand=True)

        self.canvas1.bind("<Configure>", self.on_resize)
        self.canvas2.bind("<Configure>", self.on_resize)

        # ------ QUẢN LÝ TRẠNG THÁI ------
        self.map = None
        self.colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0)]
        
        self.assignment_1 = {}
        self.running_1 = False
        self.control_1 = {'paused': False, 'stop': False}
        self.start_1 = 0
        self.time_1 = 0
        self.csp1 = None

        self.assignment_2 = {}
        self.running_2 = False
        self.control_2 = {'paused': False, 'stop': False}
        self.start_2 = 0
        self.time_2 = 0
        self.csp2 = None

        self.pause_start = 0
        self.total_paused = 0

    def round_button(self, text, command):
        canvas = tk.Canvas(self.left, width=220, height=40, bg="#7FB3C8", highlightthickness=0)
        r = 20
        x1, y1, x2, y2 = 5, 5, 215, 35
        canvas.create_oval(x1,y1,x1+r,y1+r, fill="white", outline="")
        canvas.create_oval(x2-r,y1,x2,y1+r, fill="white", outline="")
        canvas.create_oval(x1,y2-r,x1+r,y2, fill="white", outline="")
        canvas.create_oval(x2-r,y2-r,x2,y2, fill="white", outline="")
        canvas.create_rectangle(x1+r/2,y1,x2-r/2,y2, fill="white", outline="")
        canvas.create_rectangle(x1,y1+r/2,x2,y2-r/2, fill="white", outline="")
        canvas.create_text(110,20,text=text,font=("Arial",11,"bold"), fill="#333333")
        canvas.bind("<Button-1>", lambda e: command())
        return canvas

    def load(self):
        path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.png *.jpeg")])
        if path:
            self.map = Map(path)
            self.cancel() 
            self.root.update_idletasks()
            self.show(self.map.original, self.canvas1, 'tk_img1')
            self.show(self.map.original, self.canvas2, 'tk_img2')

    def show(self, img_bgr, canvas, tk_img_attr):
        cw = max(canvas.winfo_width(), 1)
        ch = max(canvas.winfo_height(), 1)
        h, w = img_bgr.shape[:2]
        scale = min(cw / w, ch / h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img_bgr, (new_w, new_h))
        img = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img)
        setattr(self, tk_img_attr, ImageTk.PhotoImage(pil))
        canvas.delete("all")
        canvas.create_image(cw//2, ch//2, image=getattr(self, tk_img_attr))

    def on_resize(self, event):
        if self.map is not None:
            if not self.running_1 and not self.running_2:
                img1 = self.map.draw(self.assignment_1)
                img2 = self.map.draw(self.assignment_2)
                self.show(img1, self.canvas1, 'tk_img1')
                self.show(img2, self.canvas2, 'tk_img2')

    def pause(self):
        if self.running_1 or self.running_2:
            self.control_1['paused'] = True
            self.control_2['paused'] = True
            self.pause_start = time.time()

    def resume(self):
        if self.running_1 or self.running_2:
            self.control_1['paused'] = False
            self.control_2['paused'] = False
            self.total_paused += time.time() - self.pause_start

    def cancel(self):
        self.control_1['stop'] = True
        self.control_2['stop'] = True
        self.running_1 = False
        self.running_2 = False
        self.assignment_1 = {}
        self.assignment_2 = {}
        self.total_paused = 0
        if self.map:
            self.show(self.map.original, self.canvas1, 'tk_img1')
            self.show(self.map.original, self.canvas2, 'tk_img2')
        self.time_label_1.config(text="Bản đồ 1 (FC): 0s")
        self.time_label_2.config(text="Bản đồ 2 (AC-3): 0s")

    def animate_step_1(self, r, c):
        self.assignment_1[r] = c
        img = self.map.draw(self.assignment_1)
        self.root.after(0, lambda: self.show(img, self.canvas1, 'tk_img1'))
        time.sleep(0.05) 

    def animate_step_2(self, r, c):
        self.assignment_2[r] = c
        img = self.map.draw(self.assignment_2)
        self.root.after(0, lambda: self.show(img, self.canvas2, 'tk_img2'))
        time.sleep(0.05) 

    def compare_both(self):
        if not self.map or (self.running_1 or self.running_2):
            return
        self.cancel() 
        self.control_1 = {'paused': False, 'stop': False}
        self.control_2 = {'paused': False, 'stop': False}
        threading.Thread(target=self.solve_1, daemon=True).start()
        threading.Thread(target=self.solve_2, daemon=True).start()
        self.update_timers()

    def solve_1(self):
        self.running_1 = True
        self.start_1 = time.time()
        self.csp1 = CSP(list(self.map.regions.keys()), self.map.neighbors, self.colors, callback=self.animate_step_1, control=self.control_1)
        domains1 = {r: self.colors[:] for r in self.map.regions}
        self.csp1.solve_fc(self.assignment_1, domains1)
        self.running_1 = False
        self.check_completion()

    def solve_2(self):
        self.running_2 = True
        self.start_2 = time.time()
        self.csp2 = CSP(list(self.map.regions.keys()), self.map.neighbors, self.colors, callback=self.animate_step_2, control=self.control_2)
        domains2 = {r: self.colors[:] for r in self.map.regions}
        self.csp2.solve_ac3(self.assignment_2, domains2)
        self.running_2 = False
        self.check_completion()

    def update_timers(self):
        if self.running_1 or self.running_2:
            if self.control_1['paused']:
                self.root.after(100, self.update_timers)
                return
            current = time.time()
            if self.running_1:
                self.time_1 = current - self.start_1 - self.total_paused
                self.time_label_1.config(text=f"Bản đồ 1 (FC): {round(self.time_1, 2)}s")
            if self.running_2:
                self.time_2 = current - self.start_2 - self.total_paused
                self.time_label_2.config(text=f"Bản đồ 2 (AC-3): {round(self.time_2, 2)}s")
            self.root.after(100, self.update_timers)

    def check_completion(self):
        if not self.running_1 and not self.running_2 and not self.control_1['stop']:
            msg = (
                f"BẢN ĐỒ 1 (FORWARD CHECKING)\n"
                f"- Thời gian: {round(self.time_1, 2)}s\n"
                f"- Số bước thử màu: {self.csp1.steps}\n"
                f"- Số lần quay lui: {self.csp1.backtracks}\n\n"
                f"BẢN ĐỒ 2 (PURE AC-3)\n"
                f"- Thời gian: {round(self.time_2, 2)}s\n"
                f"- Số bước thử màu: {self.csp2.steps}\n"
                f"- Số lần quay lui: {self.csp2.backtracks}"
            )
            self.root.after(0, lambda: messagebox.showinfo("Kết quả Benchmark", msg))