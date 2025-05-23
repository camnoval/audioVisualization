import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from threading import Thread
import webbrowser
import os
from main import main as run_main
import subprocess
import platform
import youtube_utils

class VisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Audio Visualizer")
        self.root.geometry("700x500")
        self.root.configure(bg="#1e1e1e")

        self.query_results = []
        self.selected_index = None

        self.build_ui()

    def build_ui(self):
        title = tk.Label(self.root, text="🎧 Audio Visualizer", font=("Helvetica", 20, "bold"), fg="white", bg="#1e1e1e")
        title.pack(pady=20)

        self.query_var = tk.StringVar()
        query_frame = tk.Frame(self.root, bg="#1e1e1e")
        tk.Entry(query_frame, textvariable=self.query_var, font=("Helvetica", 14), width=40).pack(side="left", padx=(0, 10))
        tk.Button(query_frame, text="Search", command=self.search_youtube, font=("Helvetica", 12)).pack(side="left")
        query_frame.pack(pady=10)

        self.result_listbox = tk.Listbox(self.root, font=("Helvetica", 12), width=80, height=6, bg="#2e2e2e", fg="white")
        self.result_listbox.pack(pady=10)

        tk.Button(self.root, text="Select and Visualize", command=self.start_visualization, font=("Helvetica", 12)).pack(pady=5)

        self.use_auto_color = tk.BooleanVar(value=True)
        color_frame = tk.Frame(self.root, bg="#1e1e1e")
        tk.Checkbutton(color_frame, text="Use album cover color", variable=self.use_auto_color, bg="#1e1e1e", fg="white",
                       activebackground="#1e1e1e", selectcolor="#1e1e1e", font=("Helvetica", 12)).pack(side="left")
        tk.Button(color_frame, text="Pick Custom Color", command=self.pick_color, font=("Helvetica", 12)).pack(side="left", padx=10)
        color_frame.pack(pady=10)

        self.status_text = tk.Text(self.root, height=10, bg="#2e2e2e", fg="white", font=("Courier", 10))
        self.status_text.pack(pady=10, padx=20, fill="both")

        self.custom_color = None

    def pick_color(self):
        color = colorchooser.askcolor(title="Choose background color")
        if color[0]:
            self.custom_color = tuple(map(int, color[0]))
            self.use_auto_color.set(False)
            self.log(f"Custom color selected: {self.custom_color}")

    def log(self, message):
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)

    def search_youtube(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Input required", "Please enter a YouTube link or search query.")
            return

        self.log(f"Searching for '{query}'...")
        try:
            results = youtube_utils.search_youtube_playlist(query, return_entries_only=True)
            self.query_results = results if results else []
            self.result_listbox.delete(0, tk.END)
            for idx, result in enumerate(self.query_results):
                title = result.get('title', f"Option {idx+1}")
                self.result_listbox.insert(tk.END, title)
            self.log(f"Found {len(self.query_results)} results.")
        except Exception as e:
            self.log(f"Search failed: {e}")

    def start_visualization(self):
        selected = self.result_listbox.curselection()
        if not selected:
            messagebox.showwarning("No selection", "Please select a result to visualize.")
            return
        self.selected_index = selected[0]

        query = self.query_var.get().strip()
        os.environ["AUDIOVISUALIZER_INPUT"] = query
        os.environ["AUDIOVISUALIZER_SELECTION_INDEX"] = str(self.selected_index)
        os.environ["AUDIOVISUALIZER_COLOR"] = "auto" if self.use_auto_color.get() else ",".join(map(str, self.custom_color))

        self.log("Starting visualization...")
        Thread(target=self.run_pipeline).start()

    def run_pipeline(self):
        try:
            run_main()
            self.log("✅ Done! Opening output folder...")
            self.open_output_folder()
        except Exception as e:
            self.log(f"❌ Error: {e}")

    def open_output_folder(self):
        from config import sanitize_filename
        album_title = os.environ.get("AUDIOVISUALIZER_INPUT", "output")
        folder = os.path.join(os.getcwd(), sanitize_filename(album_title))
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.call(["open", folder])
        else:
            subprocess.call(["xdg-open", folder])

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizerGUI(root)
    root.mainloop()
