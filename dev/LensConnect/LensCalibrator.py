import cv2
import numpy as np
import logging
import customtkinter as ctk
from PIL import Image, ImageTk
from LensConnect import LensController
from camera_manager import CameraManager
import threading

class LensCalibrator(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Lens Calibrator")
        self.geometry("800x600")

        self.camera_manager = CameraManager()

        self.lens_controller = LensController()

        self.lens_controller.scan_devices()
        self.lens_controller.connect(0)
        self.lens_controller.init_lens()

        self.focus_positions = []
        self.object_distances = []
        self.zoom_positions = []
        self.zoom_position = 0

        self.roi = None
        self.selecting_roi = False

        self.create_widgets()

    def create_widgets(self):
        self.video_label = ctk.CTkLabel(self, text="")
        self.video_label.pack()

        self.distance_entry = ctk.CTkEntry(self, placeholder_text="Enter distance")
        self.distance_entry.pack(pady=10)

        self.select_roi_button = ctk.CTkButton(self, text="Select ROI", command=self.select_roi)
        self.select_roi_button.pack(pady=10)

        self.calibrate_button = ctk.CTkButton(self, text="Calibrate", command=self.calibrate)
        self.calibrate_button.pack(pady=10)

        self.quit_button = ctk.CTkButton(self, text="Quit", command=self.quit)
        self.quit_button.pack(pady=10)

        self.zoom_slider = ctk.CTkSlider(self, from_=self.lens_controller.zoom_min, to=self.lens_controller.zoom_max,
                                         command=self.set_zoom_thread)
        self.zoom_slider.pack(pady=10)

        self.zoom_entry = ctk.CTkEntry(self, placeholder_text="Enter zoom position")
        self.zoom_entry.pack(pady=5)

        self.set_zoom_button = ctk.CTkButton(self, text="Set Zoom", command=self.set_zoom_from_entry)
        self.set_zoom_button.pack(pady=5)

        self.zoom_label = ctk.CTkLabel(self, text="Zoom Position: 0")
        self.zoom_label.pack(pady=5)

    def calculate_focus_score(self, image):
        gray = image
        sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=5)
        sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=5)
        sobel_magnitude = np.sqrt(sobelx**2 + sobely**2)
        focus_score = np.mean(sobel_magnitude)
        return focus_score

    def find_best_focus(self, object_distance, callback):
        best_focus_score = float('-inf')
        best_focus_position = -1

        for focus_position in range(self.lens_controller.focus_min, self.lens_controller.focus_max, 25):
            self.lens_controller.move_focus(focus_position)
            frame = self.camera_manager.latest_frame
            if frame is not None and self.roi is not None:
                x, y, w, h = self.roi
                roi_frame = frame[y:y+h, x:x+w]
                focus_score = self.calculate_focus_score(roi_frame)
                print(f"Focus Position: {focus_position}, Focus Score: {focus_score}")
                if focus_score > best_focus_score:
                    best_focus_score = focus_score
                    best_focus_position = focus_position

        self.focus_positions.append(best_focus_position)
        self.object_distances.append(object_distance)
        self.zoom_positions.append(self.zoom_position)
        self.lens_controller.move_focus(best_focus_position)
        callback(object_distance, best_focus_position, best_focus_score)

    def calibrate(self):
        if self.roi is None:
            print("Please select an ROI before calibrating.")
            return

        object_distance = self.distance_entry.get()
        if object_distance:
            try:
                object_distance = float(object_distance)
                threading.Thread(target=self.find_best_focus, args=(object_distance, self.calibration_callback)).start()
            except ValueError:
                print("Invalid input. Please enter a valid number.")
        else:
            print("Please enter a distance.")

    def calibration_callback(self, object_distance, best_focus_position, best_focus_score):
        print(f"Best focus position for distance {object_distance}: {best_focus_position} (Focus Score: {best_focus_score})")

    def select_roi(self):
        self.selecting_roi = True

    def update_video_feed(self):
        frame = self.camera_manager.latest_frame
        if frame is not None:
            if self.selecting_roi:
                self.roi = cv2.selectROI("Select ROI", frame, fromCenter=False, showCrosshair=True)
                cv2.destroyWindow("Select ROI")
                self.selecting_roi = False

            if self.roi is not None:
                x, y, w, h = self.roi
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(image)
            photo = ImageTk.PhotoImage(image)
            self.video_label.configure(image=photo)
            self.video_label.image = photo
        self.after(10, self.update_video_feed)

    def run(self):
        self.zoom_position = self.lens_controller.get_zoom_pos()
        self.zoom_slider.set(self.zoom_position)
        self.zoom_entry.insert(0, str(self.zoom_position))

        self.camera_manager.start_frame_thread()
        self.update_video_feed()

        self.mainloop()

        self.camera_manager.stop_frame_thread()
        self.lens_controller.disconnect()

    def set_zoom_thread(self, zoom_position):
        threading.Thread(target=self.set_zoom, args=(zoom_position,)).start()

    def set_zoom(self, zoom_position):
        zoom_position = int(zoom_position)
        self.lens_controller.move_zoom(zoom_position)
        self.zoom_position = zoom_position
        self.zoom_label.configure(text=f"Zoom Position: {zoom_position}")
        self.zoom_entry.delete(0, ctk.END)
        self.zoom_entry.insert(0, str(zoom_position))

    def set_zoom_from_entry(self):
        zoom_position = self.zoom_entry.get()
        if zoom_position:
            try:
                zoom_position = int(zoom_position)
                if self.lens_controller.zoom_min <= zoom_position <= self.lens_controller.zoom_max:
                    threading.Thread(target=self.set_zoom, args=(zoom_position,)).start()
                else:
                    print("Invalid zoom position. Please enter a value within the valid range.")
            except ValueError:
                print("Invalid input. Please enter a valid zoom position.")
        else:
            print("Please enter a zoom position.")

    def save_results(self, filename):
        with open(filename, 'w') as file:
            file.write("Object Distance,Focus Position,Zoom Position\n")
            for distance, focus_position, zoom_position in zip(self.object_distances, self.focus_positions, self.zoom_positions):
                file.write(f"{distance},{focus_position},{zoom_position}\n")

    def quit(self):
        self.save_results("lens_calibration.csv")
        self.destroy()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    calibrator = LensCalibrator()
    calibrator.run()