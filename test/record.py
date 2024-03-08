import cv2
import PySpin
import time, datetime
import logging

logging.basicConfig(level=logging.INFO)

record_time = 1
frequency = 220
time_delay = 0

system = PySpin.System.GetInstance()
cam_list = system.GetCameras()     
cam0 = cam_list.GetByIndex(0)
cam0.Init()
cam0.BeginAcquisition()

head_video0 = []

current_time = time.time()

previous_time = current_time

for n in range(record_time*frequency):
    head_video0.append(cv2.cvtColor(cam0.GetNextImage().GetNDArray(), cv2.COLOR_BGR2RGB))

    previous_time = current_time
    current_time = time.time()
    time_delay = 0.99*time_delay + 0.01*(current_time - previous_time)

    if time_delay != 0:
        print(1/time_delay)

cam0.EndAcquisition()
previous_time = time.time()

fourcc = cv2.VideoWriter_fourcc(*'XVID')


out0 = cv2.VideoWriter("dev/videos/Head_0.avi", fourcc, 220, (cam0.Width.GetValue(), cam0.Height.GetValue()))
for image_data0 in head_video0:
    #image_rgb0 = cv2.cvtColor(image_data0, cv2.COLOR_BGR2RGB)
    out0.write(image_data0)
    # send_frame(ControlIP, ControlPort, image_data0)
    # if receive_string(CameraPort) != "frame received":
        # print("error")

out0.release()
print("Save time: "+str(time.time() - previous_time))