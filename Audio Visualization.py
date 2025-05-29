import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox, ttk
from threading import Thread
import webbrowser
import os
import platform
import youtube_utils
from PIL import Image, ImageTk
import sys
import io
import time

# Ensure parent directory is on sys.path so relative imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from audioVisualization.main import main as run_main
from config import sanitize_filename
import visualization

class ColorPreviewWindow(tk.Toplevel):
    def __init__(self, master, combined_path, album_title):
        super().__init__(master)
        self.title("🎨 Real-Time Color Preview")
        self.geometry("600x400")
        self.combined_path = combined_path
        self.album_title = album_title
        self.output_folder = os.path.dirname(combined_path)

        self.r = tk.IntVar(value=128)
        self.g = tk.IntVar(value=0)
        self.b = tk.IntVar(value=128)

        for i, (label, var) in enumerate(zip(("R", "G", "B"), (self.r, self.g, self.b))):
            tk.Label(self, text=label).grid(row=0, column=i)
            tk.Scale(self, from_=0, to=255, orient=tk.HORIZONTAL, variable=var,
                     command=lambda e: self.update_preview()).grid(row=1, column=i, padx=5, pady=5)

        self.preview_label = tk.Label(self)
        self.preview_label.grid(row=2, column=0, columnspan=3, pady=10)

        tk.Button(self, text="✅ Apply", command=self.apply_color).grid(row=3, column=0, pady=10)
        tk.Button(self, text="❌ Cancel", command=self.destroy).grid(row=3, column=2, pady=10)

        self.update_preview()

    def update_preview(self):
        rgb = (self.r.get(), self.g.get(), self.b.get())
        try:
            image_files = sorted([
                os.path.join(self.output_folder, f)
                for f in os.listdir(self.output_folder)
                if f.endswith(".png") and "_combined" not in f
            ])
            preview_path = visualization.create_combined_image(
                image_files=image_files,
                output_folder=self.output_folder,
                album_title=self.album_title,
                bg_color=rgb
            )
            preview_img = Image.open(preview_path)
            preview_img.thumbnail((400, 300))
            img_tk = ImageTk.PhotoImage(preview_img)
            self.preview_label.configure(image=img_tk)
            self.preview_label.image = img_tk
            self.preview_file = preview_path
        except Exception as e:
            print(f"[ERROR] Preview update failed: {e}")

    def apply_color(self):
        self.master.output_image_path = self.preview_file
        self.master.load_preview()
        self.destroy()

class VisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Audio Visualizer")
        self.root.geometry("900x500")
        self.root.configure(bg="#1e1e1e")

        self.query_results = []
        self.selected_index = None
        self.custom_color = None
        self.output_image_path = None

        self.build_ui()

    def build_ui(self):
        main_frame = tk.Frame(self.root, bg="#1e1e1e")
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        left_frame = tk.Frame(main_frame, bg="#1e1e1e")
        left_frame.pack(side="left", fill="both", expand=True)

        right_frame = tk.Frame(main_frame, bg="#1e1e1e")
        right_frame.pack(side="right", fill="y")

        title = tk.Label(
            left_frame,
            text="🎧 Audio Visualizer",
            font=("Helvetica", 20, "bold"),
            fg="white",
            bg="#1e1e1e"
        )
        title.pack(pady=(5, 0))

        instruction = tk.Label(
            left_frame,
            text="Paste a YouTube playlist link, full album video, or search a title",
            font=("Helvetica", 11),
            fg="lightgray",
            bg="#1e1e1e"
        )
        instruction.pack(pady=(0, 10))

        self.query_var = tk.StringVar()
        query_frame = tk.Frame(left_frame, bg="#1e1e1e")
        tk.Entry(
            query_frame,
            textvariable=self.query_var,
            font=("Helvetica", 14),
            width=40
        ).pack(side="left", padx=(0, 10))
        tk.Button(
            query_frame,
            text="Search / Load",
            command=self.search_youtube,
            font=("Helvetica", 12)
        ).pack(side="left")
        query_frame.pack(pady=5)

        self.result_listbox = tk.Listbox(
            left_frame,
            font=("Helvetica", 12),
            width=60,
            height=5,
            bg="#2e2e2e",
            fg="white"
        )
        self.result_listbox.pack(pady=5)

        self.use_auto_color = tk.BooleanVar(value=True)
        color_frame = tk.Frame(left_frame, bg="#1e1e1e")
        tk.Checkbutton(
            color_frame,
            text="Use album cover color",
            variable=self.use_auto_color,
            bg="#1e1e1e",
            fg="white",
            activebackground="#1e1e1e",
            selectcolor="#1e1e1e",
            font=("Helvetica", 12)
        ).pack(side="left")
        self.color_button = tk.Button(
            color_frame,
            text="Change Background Color",
            command=self.pick_color,
            font=("Helvetica", 12),
            state="disabled"  # start disabled until image is generated
        )
        self.color_button.pack(side="left", padx=10)
        color_frame.pack(pady=5)

        tk.Button(
            left_frame,
            text="Select and Visualize",
            command=self.start_visualization,
            font=("Helvetica", 12)
        ).pack(pady=5)

        self.status_text = tk.Text(
            left_frame,
            height=8,
            bg="#2e2e2e",
            fg="white",
            font=("Courier", 10)
        )
        self.status_text.pack(pady=5, padx=10, fill="both", expand=True)

        self.progress = ttk.Progressbar(
            right_frame,
            orient="vertical",
            length=200,
            mode="determinate"
        )
        self.progress.pack(pady=10)

        self.image_label = tk.Label(right_frame, bg="#1e1e1e")
        self.image_label.pack(pady=10)

        self.save_button = tk.Button(
            right_frame,
            text="💾 Save As",
            command=self.save_image,
            font=("Helvetica", 12),
            state="disabled"
        )
        self.save_button.pack(pady=5)

    def log(self, message):
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)

    def pick_color(self):
        if not self.output_image_path or not os.path.exists(self.output_image_path):
            self.log("⚠️ No combined image to update.")
            return

        color = colorchooser.askcolor(title="Pick a background color")
        if not color or not color[0]:
            return  # user canceled

        rgb = tuple(map(int, color[0]))
        self.custom_color = rgb
        self.use_auto_color.set(False)
        self.log(f"🎨 Updating background color to RGB{rgb}")

        try:
            from config import sanitize_filename
            import visualization

            folder = os.path.dirname(self.output_image_path)
            album_title = os.path.basename(self.output_image_path).replace("_combined.png", "")

            image_paths = sorted([
                os.path.join(folder, f)
                for f in os.listdir(folder)
                if f.endswith(".png") and "_combined" not in f
            ])

            new_combined_path = visualization.create_combined_image(
                image_paths=image_paths,
                output_folder=folder,
                album_title=album_title,
                bg_color=rgb
            )

            self.output_image_path = new_combined_path
            self.load_preview()
            self.log("✅ Background updated successfully.")
        except Exception as e:
            self.log(f"❌ Failed to update background: {e}")

        def log(self, message):
            self.status_text.insert(tk.END, message + "\n")
            self.status_text.see(tk.END)

    def search_youtube(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Input required", "Please enter a YouTube link or search query.")
            return

        self.log(f"🔎 Searching for: {query}")

        if "youtube.com" in query or "youtu.be" in query or "list=" in query:
            try:
                info = youtube_utils.load_youtube_url(query)
                if not info:
                    self.log("❌ Could not load video or playlist. It may not contain multiple tracks or chapters.")
                    return
                self.query_results = [info]
                self.result_listbox.delete(0, tk.END)
                self.result_listbox.insert(tk.END, info.get('title', 'Direct Video/Playlist'))
                self.result_listbox.select_set(0)
                self.result_listbox.activate(0)
                self.log(f"✅ Loaded: {info.get('title')}")
            except Exception as e:
                self.log(f"❌ Error loading link: {e}")
            return

        try:
            results = youtube_utils.search_youtube_playlist(query + " playlist", return_entries_only=True)
            if not results:
                results = youtube_utils.search_youtube_playlist(query + " full album", return_entries_only=True)

            if not results:
                results = youtube_utils.search_youtube_playlist(query, return_entries_only=True)

            if not results:
                self.log("❌ No search results found.")
                return

            self.query_results = results
            self.result_listbox.delete(0, tk.END)
            for idx, result in enumerate(self.query_results):
                title = result.get('title', f"Option {idx+1}")
                self.result_listbox.insert(tk.END, title)
            self.result_listbox.select_set(0)
            self.result_listbox.activate(0)
            self.log(f"✅ Found {len(self.query_results)} results. Click one, then 'Select and Visualize'.")
        except Exception as e:
            self.log(f"❌ Search failed: {e}")

    def start_visualization(self):
        selected = self.result_listbox.curselection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a result to visualize.")
            return
        self.selected_index = selected[0]

        query = self.query_var.get().strip()
        if "youtube.com" in query or "youtu.be" in query or "list=" in query:
            os.environ["AUDIOVISUALIZER_DIRECT_URL"] = query
        else:
            os.environ["AUDIOVISUALIZER_INPUT"] = query
            os.environ["AUDIOVISUALIZER_SELECTION_INDEX"] = str(self.selected_index)

        os.environ["AUDIOVISUALIZER_COLOR"] = (
            "auto" if self.use_auto_color.get() else ",".join(map(str, self.custom_color))
        )

        self.progress['value'] = 0
        self.save_button.config(state="disabled")
        self.color_button.config(state="disabled")  # disable color change while generating
        self.status_text.delete(1.0, tk.END)
        self.log("⏳ Starting visualization...")
        Thread(target=self.run_pipeline).start()

    def run_pipeline(self):
        try:
            import contextlib

            class StreamInterceptor(io.StringIO):
                def write(this, txt):
                    if txt.strip():
                        self.log(txt.strip())
                        if txt.startswith("[PROGRESS]"):
                            try:
                                percent = int(txt.split()[1].replace("%", ""))
                                self.progress['value'] = percent
                            except:
                                pass
                        elif txt.startswith("[OUTPUT]"):
                            self.output_image_path = txt.replace("[OUTPUT]", "").strip()
                    super().write(txt)

            stream = StreamInterceptor()
            with contextlib.redirect_stdout(stream), contextlib.redirect_stderr(stream):
                run_main()

            self.log("✅ Done generating image.")
            self.color_button.config(state="normal")  # allow recoloring now
            self.load_preview()
        except Exception as e:
            self.log(f"❌ Error: {e}")

    def load_preview(self):
        time.sleep(0.5)
        if not self.output_image_path:
            self.log("⚠️ No output image path set.")
            return

        for _ in range(5):
            if os.path.exists(self.output_image_path):
                break
            time.sleep(0.5)

        if os.path.exists(self.output_image_path):
            try:
                img = Image.open(self.output_image_path)
                img.thumbnail((200, 200))
                img_tk = ImageTk.PhotoImage(img)
                self.image_label.configure(image=img_tk)
                self.image_label.image = img_tk
                self.save_button.config(state="normal")
                self.log("✅ Image preview loaded.")
            except Exception as e:
                self.log(f"⚠️ Error loading image preview: {e}")
        else:
            self.log(f"⚠️ Image file not found: {self.output_image_path}")

    def save_image(self):
        if self.output_image_path:
            target = filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG files", "*.png")])
            if target:
                try:
                    import shutil
                    shutil.copy(self.output_image_path, target)
                    self.log(f"✅ Image saved to: {target}")
                except Exception as e:
                    self.log(f"❌ Failed to save image: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizerGUI(root)
    root.mainloop()
