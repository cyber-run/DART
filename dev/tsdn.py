import logging
logging.basicConfig(level=logging.INFO)

import time, cv2, imutils, threading, cProfile, math, queue
import tsdn_emd as tsdn
import matplotlib.pyplot as plt
from scipy.io import savemat, loadmat

class TSDN_Tracker():
    def __init__(self, filename, f_h, f_w, sim_flag=False):
        if sim_flag:
            print('Simulating')
            self.cap = cv2.VideoCapture('dev/videos/DF_0204.mp4')
            f_w = int(self.cap.get(3))
            f_h = int(self.cap.get(4))

            self.frame_queue = queue.Queue(maxsize=1)
            self.coord_queue = queue.Queue(maxsize=1)
            self.stop_event = threading.Event()

        self.cam_res = [270, 360]
        self.down_scale_factor = 1

        self.down_scale = (int(self.cam_res[1]/self.down_scale_factor), int(self.cam_res[0]/self.down_scale_factor))
        self.vf_center = [self.down_scale[0]/2-1, self.down_scale[1]/2-1]
        
        self.frame_width = f_w
        self.frame_height = f_h
        
        self.vf_center = [300, 300]
        self.vf_center_prev = self.vf_center
        self.vf_length = 200
        self.roi = [self.vf_center[1]-self.vf_length, self.vf_center[1]+self.vf_length, self.vf_center[0]-self.vf_length, self.vf_center[0]+self.vf_length]
        self.translation = [0, 0]

        self.tau = 60
        self.lat_emd = tsdn.EMD(self.tau, cell_array=[25, 25], center_pos=self.vf_center, pos_mat=[5, 5], Ag=[5, 0], mode='trans', win_shift=[180, 135])
        self.long_emd = tsdn.EMD(self.tau, cell_array=[25, 25], center_pos=self.vf_center, pos_mat=[5, 5], Ag=[5, 0], mode='trans', win_shift=[180, 135])
        self.refine_mapping = tsdn.refine_projection(self.vf_center, pos_mat=[5, 5])
        self.rmax_log =  []

        self.translation = [0, 0]
        
        self.pitch_control = tsdn.PID()
        self.yaw_control = tsdn.PID()

        # Initialize pose variables
        self.curr_pose = [0, 0]
        self.prev_pose = [0, 0]

        # Initialize data logging
        self.frame_log = []
        self.ts_map = []
        self.lat_ts_map = []
        self.long_ts_map = []
        self.lat_che_map = []
        self.long_che_map = []
        self.long_che_p_map = []
        self.lat_che_p_map = []
        self.trans_log = []
        self.pos_vec_log = []
        self.pos_log = []
        self.step = []
        self.match_res = []
        self.rp_log = []
        self.mdic ={"raw": self.frame_log, "rp": self.rp_log, "mm_map": self.ts_map, "lat_map": self.lat_ts_map, "long_map": self.long_ts_map, "lat_che": self.lat_che_map, "long_che_map": self.long_che_map, 
            "lat_che_p_map": self.lat_che_p_map, "long_che_p_map": self.long_che_p_map, "translation": self.trans_log, "encoder_pos": self.pos_log, 'ppd': 256, 'step':self.step, 'matching':self.match_res}
        self.filename = filename

        self.start = 0
        self.rot = 0
        self.off_set = 90  # Angle offset from origin
        self.out_field = 0
        self.counter = 0
        self.desired_state = 0
        self.rim_trig = 0
        self.visual_field_prev = []
        self.prev_time = time.perf_counter()

        self.curr_frame = None
        self.freq_start = None

    def track(self, frame):
        self.curr_frame = frame
        start_t = time.perf_counter()
        # Read frame
        grey_scale = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(grey_scale, (5, 5), 0)
        self.visual_field = blurred[self.roi[0]:self.roi[1], self.roi[2]:self.roi[3]]     # [height, width]
        
        # Calculate EMD
        self.lat_emd.update(self.visual_field, 0, self.translation)
        self.long_emd.update(self.visual_field, 0, self.translation)
        mm_map, mm_coord, Rmax_mean = tsdn.cell_wise_average(self.lat_emd.neuron_map_rel, self.long_emd.neuron_map_rel)
        pos_vec = [a - b for a, b in zip(self.lat_emd.matrix_location_ChE[mm_coord], self.lat_emd.center_pos)]
        
        if abs(Rmax_mean) > 0.0001:
            yaw_goal = pos_vec[0]
            pitch_goal = pos_vec[1]
        else:
            yaw_goal = 0
            pitch_goal = 0
            
        yaw_action = self.yaw_control.update(self.vf_center[0] + yaw_goal, self.vf_center[0], limit=15)
        pitch_action = self.pitch_control.update(self.vf_center[1] + pitch_goal, self.vf_center[1], limit=15)
        
        self.vf_center = [int(self.vf_center[0]+yaw_action), int(self.vf_center[1]+pitch_action)]
        if self.vf_center[0] < self.vf_length:
            self.vf_center[0] = self.vf_length
        if self.vf_center[1] < self.vf_length:
            self.vf_center[1] = self.vf_length
        if self.vf_center[0] > self.frame_width-self.vf_length:
            self.vf_center[0] = self.frame_width-self.vf_length
        if self.vf_center[1] > self.frame_height-self.vf_length:
            self.vf_center[1] = self.frame_height-self.vf_length

        self.roi = [self.vf_center[1]-self.vf_length, self.vf_center[1]+self.vf_length, self.vf_center[0]-self.vf_length, self.vf_center[0]+self.vf_length]
        self.translation = [self.vf_center[0]-self.vf_center_prev[0], self.vf_center[1]-self.vf_center_prev[1]]
        self.vf_center_prev = self.vf_center
        
        logging.info(f"Track duration: {time.perf_counter() - start_t:.4f} s")

    def log_data(self):
        self.lat_ts_map.append(self.lat_emd.neuron_map_rel)
        self.long_ts_map.append(self.long_emd.neuron_map_rel)
        self.lat_che_map.append(self.lat_emd.Ch1E)
        self.lat_che_p_map.append(self.lat_emd.Ch1E_prev)
        self.long_che_map.append(self.long_emd.Ch1E)
        self.long_che_p_map.append(self.long_emd.Ch1E_prev)
        self.pos_log.append(self.curr_pose)
        self.match_res.append(self.refine_mapping.result)
        self.rp_log.append(self.lat_emd.rp_window)

    def shutdown(self):
        return

    def start_tracker(self):
        logging.info('Tracker started')
        self.freq_start = time.perf_counter()
        n = 0

        while not self.stop_event.is_set() and self.cap.isOpened():
            ret, raw_frame = self.cap.read()

            if not ret:
                break  # If no frame is returned, exit the loop

            self.track(frame=raw_frame)
            n += 1

            frame = raw_frame

            self.curr_frame = frame

            coord_max = self.vf_center

            try:
                self.frame_queue.put_nowait(frame)
            except queue.Full:
                pass  # If the queue is full, skip this frame
            try:
                self.coord_queue.put_nowait(coord_max)
            except queue.Full:
                pass  # If the queue is full, skip this frame

        delta_t = time.perf_counter() - self.freq_start
        print(f"Frames processed: {n} in {delta_t:.4f} s")
        print(f"Frame rate: {n/delta_t:.4f} fps")
        self.cap.release()
        self.shutdown()

    def start_visualizer(self):
        logging.info('Visualizer started')

        while not self.stop_event.is_set():
            start_t = time.perf_counter()
            if not self.frame_queue.empty() and not self.coord_queue.empty():
                canvas = self.frame_queue.get()
                coord = self.coord_queue.get()

                cv2.circle(canvas, (coord[0], coord[1]), 10, (255, 255, 255), 2)
                canvas = cv2.resize(canvas, (960, 720))
                cv2.imshow('visual field', canvas)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    cv2.destroyAllWindows()
                    self.stop_event.set()  # Signal all threads to stop
                    break
            
            logging.info(f"Visualizer duration: {time.perf_counter() - start_t:.4f} s")

    def start_sim(self):
        self.camera_thread = threading.Thread(target=self.start_tracker, daemon=True)
        self.visualization_thread = threading.Thread(target=self.start_visualizer, daemon=True)
        self.camera_thread.start()
        self.visualization_thread.start()

    def stop_sim(self):
        self.stop_event.set()
        self.camera_thread.join()
        self.visualization_thread.join()
        self.shutdown()

    def start_tracking(self):
        self.camera_thread = threading.Thread(target=self.start_tracker, daemon=True)
        self.camera_thread.start()

    def stop_tracking(self):
        self.stop_event.set()
        self.camera_thread.join()
        self.shutdown()

    def get_frame(self):
        if self.curr_frame is not None:
            return self.curr_frame 

def main():
    tsdn = TSDN_Tracker(filename='rim_tracking.mat', f_h=0, f_w=0, sim_flag=True)

    tsdn.start_sim()

    time.sleep(100)

    tsdn.stop_sim()

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()