import tkinter as tk
from tkinter import filedialog, colorchooser, messagebox
from threading import Thread
import webbrowser
import os
from main import main as run_main

class VisualizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🎵 Audio Visualizer")
        self.root.geometry("600x400")
        self.root.configure(bg="#1e1e1e")

        self.build_ui()

    def build_ui(self):
        # Title
        title = tk.Label(self.root, text="🎧 Audio Visualizer", font=("Helvetica", 20, "bold"), fg="white", bg="#1e1e1e")
        title.pack(pady=20)

        # Input field
        self.query_var = tk.StringVar()
        query_frame = tk.Frame(self.root, bg="#1e1e1e")
        tk.Entry(query_frame, textvariable=self.query_var, font=("Helvetica", 14), width=40).pack(side="left", padx=(0, 10))
        tk.Button(query_frame, text="Search or Load", command=self.start_visualization, font=("Helvetica", 12)).pack(side="left")
        query_frame.pack(pady=10)

        # Color option
        self.use_auto_color = tk.BooleanVar(value=True)
        color_frame = tk.Frame(self.root, bg="#1e1e1e")
        tk.Checkbutton(color_frame, text="Use album cover color", variable=self.use_auto_color, bg="#1e1e1e", fg="white",
                       activebackground="#1e1e1e", selectcolor="#1e1e1e", font=("Helvetica", 12)).pack(side="left")
        tk.Button(color_frame, text="Pick Custom Color", command=self.pick_color, font=("Helvetica", 12)).pack(side="left", padx=10)
        color_frame.pack(pady=10)

        # Status output
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

    def start_visualization(self):
        query = self.query_var.get().strip()
        if not query:
            messagebox.showwarning("Input required", "Please enter a YouTube link or search query.")
            return

        # Set environment variables to communicate options
        os.environ["VIS_INPUT"] = query
        os.environ["VIS_COLOR"] = "auto" if self.use_auto_color.get() else ",".join(map(str, self.custom_color))

        self.log("Starting visualization...")
        Thread(target=self.run_pipeline).start()

    def run_pipeline(self):
        try:
            run_main()
            self.log("✅ Done! Check your output folder.")
        except Exception as e:
            self.log(f"❌ Error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = VisualizerGUI(root)
    root.mainloop()
