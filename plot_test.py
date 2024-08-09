import pandas as pd
import matplotlib.pyplot as plt
import customtkinter as ctk
from tkinter import filedialog
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import cv2
from PIL import Image
from tkSliderWidget import Slider
from plot_utils import PlotUtils

class DataVisualizer:
    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Data Visualizer")
        self.root.geometry("1600x900")
        self.file_path = None
        self.video_path = None
        self.cap = None
        self.video_label = None
        self.after_id = None
        self.plot_canvas = None

        self.is_playing = False
        self.is_slider_moving = False

        self.frame = ctk.CTkFrame(root)
        self.frame.pack(pady=20, padx=20, fill='both', expand=True)

        self.load_button = ctk.CTkButton(self.frame, text="Load Parquet File", command=self.load_file)
        self.load_button.grid(row=0, column=0, padx=10, pady=10)

        self.play_button = ctk.CTkButton(self.frame, text="Play", command=self.toggle_playback)
        self.play_button.grid(row=0, column=1, padx=10, pady=10)

        self.video_frame = ctk.CTkFrame(self.frame)
        self.video_frame.grid(row=1, column=0, padx=10, pady=10, sticky='nsew')
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(0, weight=3)

        self.plot_frame = ctk.CTkFrame(self.frame)
        self.plot_frame.grid(row=1, column=1, padx=10, pady=10, sticky='nsew')
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid_columnconfigure(1, weight=1)

        self.plot_frame.grid_rowconfigure(0, weight=1)
        self.plot_frame.grid_columnconfigure(0, weight=1)

        self.plot_dropdown = ctk.CTkComboBox(self.plot_frame, values=["Trajectory", "Pan/Tilt"], 
                                             command=self.update_plot, state='readonly')
        self.plot_dropdown.grid(row=1, column=0, padx=10, pady=10)

        self.slider_frame = ctk.CTkFrame(self.frame)
        self.slider_frame.grid(row=2, column=0, columnspan=2, padx=10, pady=10, sticky='ew')

        self.slider = Slider(
            self.slider_frame,
            width=800,
            height=50,
            min_val=0,
            max_val=1000,
            init_lis=[0, 0, 1000],
            show_value=True,
            removable=False,
            addable=False
            )
        
        self.slider.pack(fill=ctk.X, expand=True)
        self.slider.setValueChangeCallback(self.on_slider_changed)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def load_file(self) -> None:
        self.file_path = filedialog.askopenfilename(filetypes=[("Parquet files", "*.parquet")])
        if self.file_path:
            base_name = self.file_path.split("/")[-1].replace("data_", "").replace(".parquet", "")
            self.video_path = f"{self.file_path.rsplit('/', 1)[0]}/{base_name}.mp4"

            print(f"Data file name: {base_name + '.parquet'}")
            print(f"Video file name: {self.video_path}")

            if self.video_path:
                cap = cv2.VideoCapture(self.video_path)
                total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                cap.release()

                self.slider.max_val = total_frames
                self.slider.init_lis = [0, 0, total_frames]
                self.slider.bars[1]["Value"] = 0
                self.slider.bars[2]["Value"] = total_frames

            self.visualize_data()

    def update_plot(self, event=None):
        selected_plot = self.plot_dropdown.get()

        if hasattr(self, 'time_stamps') and hasattr(self, 'desired_pan') and hasattr(self, 'encoder_pan') and hasattr(self, 'desired_tilt') and hasattr(self, 'encoder_tilt') and hasattr(self, 'target_x') and hasattr(self, 'target_y') and hasattr(self, 'target_z'):
            if selected_plot == "Trajectory":
                fig = PlotUtils.create_trajectory_plot(self.target_x, self.target_y, self.target_z, figsize=(6, 4))
            elif selected_plot == "Pan/Tilt":
                fig = PlotUtils.create_pan_tilt_plots(self.time_stamps, self.desired_pan, self.encoder_pan, self.desired_tilt, self.encoder_tilt, figsize=(6, 6))
            else:
                # No plot selected, clear the plot canvas
                if self.plot_canvas is not None:
                    self.plot_canvas.get_tk_widget().destroy()
                    self.plot_canvas = None
                return

            if self.plot_canvas is not None:
                self.plot_canvas.get_tk_widget().destroy()

            fig.tight_layout()
            self.plot_canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
            self.plot_canvas.draw()
            self.plot_canvas.get_tk_widget().grid(row=0, column=0, padx=10, pady=10, sticky='nsew')

    def visualize_data(self) -> None:
        if not self.file_path:
            print("Error: No file selected.")
            return

        try:
            plt.style.use('dark_background')
            df = pd.read_parquet(self.file_path)
            df = df.sort_values('time_stamp_ms')

            slider_values = self.slider.getValues()
            if len(slider_values) >= 3:
                start_frame = int(slider_values[0])
                current_frame = int(slider_values[1])
                end_frame = int(slider_values[2])

                start_idx = int((start_frame / self.slider.max_val) * len(df))
                end_idx = int((end_frame / self.slider.max_val) * len(df))
                df = df.iloc[start_idx:end_idx]

                df['time_stamp_s'] = df['time_stamp_ms'] / 1000
                self.time_stamps = df['time_stamp_s']
                self.desired_pan = df['desired_pan']
                self.encoder_pan = df['encoder_pan']
                self.desired_tilt = df['desired_tilt']
                self.encoder_tilt = df['encoder_tilt']
                target_coords = df['target position'].apply(pd.Series)
                self.target_x = target_coords[0]
                self.target_y = target_coords[1]
                self.target_z = target_coords[2]

                self.update_plot()

                self.display_video()

        except Exception as e:
            print(f"Error: Failed to load and visualize data: {e}")

    def toggle_playback(self):
        if self.is_playing:
            self.is_playing = False
            self.play_button.configure(text="Play")
        else:
            self.is_playing = True
            self.play_button.configure(text="Pause")
            self.play_video()

    def on_slider_changed(self, values):
        self.is_slider_moving = True

    def play_video(self):
        if not self.is_playing or self.cap is None:
            return

        current_frame = int(self.slider.getValues()[1])
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

        while self.is_playing:
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img = ctk.CTkImage(img, size=(800, 600))
                self.video_label.configure(image=img)
                current_frame += 1
                self.slider._Slider__moveBar(1, current_frame / self.slider.max_val)
                self.root.update()
            else:
                self.is_playing = False
                self.play_button.configure(text="Play")
                break

    def display_video(self) -> None:
        if self.video_path is None:
            return

        self.cap = cv2.VideoCapture(self.video_path)

        if not self.cap.isOpened():
            print(f"Error: Failed to open video file: {self.video_path}")
            return

        if self.video_label is None:
            self.video_label = ctk.CTkLabel(self.video_frame, text="")
            self.video_label.pack(fill=ctk.BOTH, expand=True)

        self.update_frame()

    def update_frame(self) -> None:
        if self.cap is None:
            return

        current_frame = int(self.slider.getValues()[1])
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, current_frame)

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            if self.is_slider_moving and not self.is_playing:
                frame = cv2.pyrDown(frame)
                frame = cv2.pyrDown(frame)
                img = Image.fromarray(frame)
                img = ctk.CTkImage(img, size=(800, 600))
                self.is_slider_moving = False
            else:
                img = Image.fromarray(frame)
                img = ctk.CTkImage(img, size=(800, 600))
            self.video_label.configure(image=img)
        else:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.after_id = self.root.after(30, self.update_frame)

    def on_closing(self) -> None:
        if self.cap is not None:
            self.cap.release()
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
        self.root.quit()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    app = DataVisualizer(root)
    root.mainloop()