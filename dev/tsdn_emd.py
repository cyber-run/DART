import numpy as np
import math
import cv2

class EMD:
    def __init__(self, tau=30, cell_array=[3, 3], center_pos=[10, 10], pos_mat=[3, 4], Ag=[0, 5], mode='trans', win_shift=[10, 10]):
        """
        Elementary Motion Detector
        :param tau: Time constant in Hz (Tau/dT in some literature)
        :param cell_array: (trans)num of cells in x, y (w, h); (loom&radial)num of cells in each layer and num of layer
        :param center_pos: Center location of the array
        :param pos_mat: (trans)distance between cells in x, y (w, h); (loom)radius and radial distance between layers; 
                        (radial)minial and maximal distance between layers
        :param Ag: distance between ChE and ChI in x, y (w, h); (loom&radial)radial distance between ChE and ChI, only position 0 is used
        :param mode: translation(trans), looming(loom) or radiation(radial)
        :win_size: size of the reprojection window, typically 2*frame size
        """
        self.pos_mat = pos_mat
        self.cell_array = cell_array
        self.tau = tau
        self.Ag = Ag
        self.rp_window = []
        self.win_shift = win_shift
        self.t_limit = 0
        self.refine_step = []    
        self.center_pos = center_pos
        self.Ch1E = np.zeros(cell_array)
        self.Ch1I = np.zeros(cell_array)
        self.Ch2E = np.zeros(cell_array)
        self.Ch2I = np.zeros(cell_array)
        self.Ch1E_prev = np.zeros(cell_array)
        self.Ch1I_prev = np.zeros(cell_array)
        self.Ch2E_prev = np.zeros(cell_array)
        self.Ch2I_prev = np.zeros(cell_array)
        self.Ch1E_rel = np.zeros(cell_array)
        self.Ch1I_rel = np.zeros(cell_array)
        self.Ch2E_rel = np.zeros(cell_array)
        self.Ch2I_rel = np.zeros(cell_array)
        self.LP1 = np.zeros(cell_array)
        self.LP2 = np.zeros(cell_array)
        self.LP1_prev = np.zeros(cell_array)
        self.LP2_prev = np.zeros(cell_array)
        self.LP1_rel = np.zeros(cell_array)
        self.LP2_rel = np.zeros(cell_array)
        self.Rexcite = []
        self.Rexcite_prev = []
        self.Rinhibit = []
        self.Rinhibit_prev = []
        self.Rexcite_rel = []
        self.Rinhibit_rel = []
        self.neuron_map = []
        self.neuron_map_prev = []
        self.neuron_map_rel = []
        self.neuron_hp = []
        self.Rmax = 0
        self.Rmax_prev = 0
        self.Rmax_rel = 0
        self.Rmean = 0
        self.Rmean_filtered = 0
        self.log = []
        self.log_prev = []
        self.log_rel = []
        self.mode = mode
        self.neuron_map_rim = []
        self.max_coord = []
        self.cord_xy = []
        self.sample_matrix_ChE_prev = []
        self.sample_matrix_ChI_prev = []
        self.matrix_location_ChE_prev = []
        self.matrix_location_ChI_prev = []
        self.frame_prev = []

        # Transform center position to start position for translational array
        start_x = center_pos[0] - 0.5 * ((cell_array[0] - 1) * pos_mat[0] + Ag[0])
        start_y = center_pos[1] - 0.5 * ((cell_array[1] - 1) * pos_mat[1] + Ag[1])
        start_pos = [int(start_x), int(start_y)]
        start_pos_p = np.add(start_pos, self.win_shift)

        if mode == 'loom':
            self.sample_matrix_ChE, self.matrix_location_ChE = self.get_sampling_matrix_loom(cell_array,
                                                                                             center_pos, pos_mat)
            self.sample_matrix_ChI, self.matrix_location_ChI = self.get_sampling_matrix_loom(cell_array, center_pos,
                                                                                             [pos_mat[0] + Ag[0],
                                                                                              pos_mat[1]])
            # print(self.matrix_location_ChI)
        elif mode == "rect":
            start_y = center_pos[1] - 0.5 * ((cell_array[1] - 1) * pos_mat[0] + Ag[0])
            start_pos = [int(start_x), int(start_y)]
            self.LP1_rel = []
            self.LP2_rel = []
            self.sample_matrix_ChE, self.matrix_location_ChE, self.sample_matrix_ChI, self.matrix_location_ChI = self.get_sampling_matrix_rect(cell_array,
                                                                                             start_pos, pos_mat, Ag)
        elif mode == "radial":
            center_pos_p = np.add(center_pos, self.win_shift)
            self.sample_matrix_ChE, self.matrix_location_ChE = self.get_sampling_matrix_radial(cell_array,
                                                                                             center_pos, pos_mat, ChI_offset=0)
            self.sample_matrix_ChI, self.matrix_location_ChI = self.get_sampling_matrix_radial(cell_array, center_pos, 
                                                                                               [pos_mat[0] + Ag[0], pos_mat[1] + Ag[1]], ChI_offset=Ag[0])
            self.sample_matrix_ChE_p, self.matrix_location_ChE_p = self.get_sampling_matrix_radial(cell_array,
                                                                                             center_pos_p, pos_mat, ChI_offset=0)
            self.sample_matrix_ChI_p, self.matrix_location_ChI_p = self.get_sampling_matrix_radial(cell_array, center_pos_p, 
                                                                                               [pos_mat[0] + Ag[0], pos_mat[1] + Ag[1]], ChI_offset=Ag[0])
        else:
            self.sample_matrix_ChE, self.matrix_location_ChE = self.get_sampling_matrix(cell_array, start_pos, pos_mat)
            self.sample_matrix_ChI, self.matrix_location_ChI = self.get_sampling_matrix(cell_array,
                                                                                        np.add(start_pos, Ag), pos_mat)
            self.sample_matrix_ChE_p, self.matrix_location_ChE_p = self.get_sampling_matrix(cell_array, start_pos_p, pos_mat)
            self.sample_matrix_ChI_p, self.matrix_location_ChI_p = self.get_sampling_matrix(cell_array,
                                                                                        np.add(start_pos_p, Ag), pos_mat)
            # print(self.sample_matrix_ChE)

        # Generate neuron topologic map
        if mode == "loom":
            for i in range(cell_array[1]):
                neuron_cache = np.zeros((3, cell_array[0]))
                neuron_cache[0, :] = i
                neuron_cache[1, :] = np.linspace(0, 2 * np.pi, cell_array[0])
                if i == 0:
                    self.neuron_map_rim = neuron_cache
                else:
                    self.neuron_map_rim = np.hstack([self.neuron_map_rim, neuron_cache])

    @staticmethod
    def get_sampling_matrix(cell_array, start_pos, pos_mat):
        """
        Generates coordinate for pixel extraction
        Convert to Tuple list
        """
        samp_mat = np.mgrid[start_pos[0]:(start_pos[0] + cell_array[0] * pos_mat[0]):pos_mat[0],
                   start_pos[1]: (start_pos[1] + cell_array[1] * pos_mat[1]): pos_mat[1]].reshape(2, -1)

        sampling_matrix = tuple(samp_mat.tolist())
        centre_points = tuple(np.array(samp_mat).T.tolist())

        return sampling_matrix, centre_points

    @staticmethod
    def get_sampling_matrix_loom(cell_array, start_pos, pos_mat):
        """
        For channels in looming mode only
        Generates coordinate for pixel extraction
        Convert to Tuple list
        """
        coord_polar = np.mgrid[0:2 * np.pi:((2 * np.pi) / cell_array[0]),
                      pos_mat[0]:(pos_mat[0] + pos_mat[1] * cell_array[1]):pos_mat[1]].reshape(2, -1)
        coord_cart = np.array([coord_polar[1] * np.cos(coord_polar[0]) + start_pos[0],
                               coord_polar[1] * np.sin(coord_polar[0]) + start_pos[1]]).astype(np.int)
        sampling_matrix = tuple(coord_cart.tolist())
        centre_points = tuple(coord_cart.T.tolist())

        return sampling_matrix, centre_points

    @staticmethod
    def get_sampling_matrix_radial(cell_array, start_pos, pos_mat, ChI_offset):
        """
        For channels in looming mode only
        Generates coordinate for pixel extraction
        Convert to Tuple list
        """
        if cell_array[1]>2:
            step_list = np.arange(pos_mat[0], pos_mat[1], (pos_mat[1]-pos_mat[0])*1/(cell_array[1]-2))
            step_list = np.append(ChI_offset, step_list)
            step_list = np.append(step_list, pos_mat[1])
            for i in range(1, len(step_list)):
                step_list[i] = step_list[i]+step_list[i-1]
        
        
        rad = np.arange(0,2 * np.pi,((2 * np.pi) / cell_array[0]))
        coord_polar = np.meshgrid(rad, step_list)
        coord_polar = np.array(coord_polar).reshape(2, -1)
        coord_cart = np.array([coord_polar[1] * np.cos(coord_polar[0]) + start_pos[0],
                               coord_polar[1] * np.sin(coord_polar[0]) + start_pos[1]]).astype(np.int)
        # print(coord_cart.shape)
        # print(coord_cart)
        sampling_matrix = tuple(coord_cart.tolist())
        centre_points = tuple(coord_cart.T.tolist())

        return sampling_matrix, centre_points
    
    @staticmethod
    def get_sampling_matrix_rect(cell_array, start_pos, pos_mat, Ag):
        """
        cell_array: num of cells in x and y
        pos_mat: [0] is distance in x and y, [1] is num of layers
        Inverse Ag depends on direction
        """
        width_bound = [start_pos[0]+pos_mat[0]*pos_mat[1], start_pos[0]+cell_array[0]*pos_mat[0]-pos_mat[0]*pos_mat[1]]
        height_bound = [start_pos[1]+pos_mat[0]*pos_mat[1], start_pos[1]+cell_array[1]*pos_mat[0]-pos_mat[0]*pos_mat[1]]
        samp_mat_x = np.mgrid[start_pos[0]:(start_pos[0] + cell_array[0] * pos_mat[0]):pos_mat[0],
                   start_pos[1]: (start_pos[1] + cell_array[1] * pos_mat[0]): pos_mat[0]].reshape(2, -1)
        x_mask = (samp_mat_x[0, :] < width_bound[0]) | (samp_mat_x[0, :] >= width_bound[1])
        samp_mat_x = samp_mat_x[:, x_mask]
        # print("sanity check: ", samp_mat_x)
        samp_mat_y = np.mgrid[start_pos[0]:(start_pos[0] + cell_array[0] * pos_mat[0]):pos_mat[0],
                   start_pos[1]: (start_pos[1] + cell_array[1] * pos_mat[0]): pos_mat[0]].reshape(2, -1)
        y_mask = (samp_mat_y[1, :] < height_bound[0]) | (samp_mat_y[1, :] >= height_bound[1])
        samp_mat_y = samp_mat_y[:, y_mask]
        
        # print("sanity check: ", samp_mat_y)
        samp_mat_x_I = samp_mat_x.copy()
        samp_mat_x_I[0,:] += Ag[0]
        samp_mat_y_I = samp_mat_y.copy()
        samp_mat_y_I[1,:] += Ag[0]
        # print("sanity check: ", samp_mat_y_I)
        samp_mat = np.concatenate((samp_mat_x, samp_mat_y), axis=1)
        samp_mat_I = np.concatenate((samp_mat_x_I, samp_mat_y_I), axis=1)
        sampling_matrix = tuple(samp_mat.tolist())
        centre_points = tuple(samp_mat.T.tolist())
        sampling_matrix_I = tuple(samp_mat_I.tolist())
        centre_points_I = tuple(samp_mat_I.T.tolist())
        return sampling_matrix, centre_points, sampling_matrix_I, centre_points_I
    
    def get_p_channels(self, frame_p, ch_curr, trans, samp_mat):
        if abs(max(trans))>=self.t_limit:
            ch_prev = ch_curr
        else:
            self.rp_window[self.win_shift[1]:self.win_shift[1]+frame_p.shape[0], self.win_shift[0]:self.win_shift[0]+frame_p.shape[1]] = frame_p
            samp_mat_p = np.array(samp_mat)
            samp_mat_p[0, :] += int(trans[0])
            samp_mat_p[1,:] += int(trans[1])
            ch_prev  = self.rp_window[(samp_mat_p[1]), (samp_mat_p[0])].reshape(ch_curr.shape)
            samp_mask = (ch_prev==0)
            samp_buffer = samp_mask*ch_curr
            ch_prev = ch_prev + samp_buffer

        return ch_prev
    
    def refine_projection(self, translation, frame_prev, frame):
        x_pos = max(self.sample_matrix_ChE[0])
        y_pos = max(self.sample_matrix_ChE[1])
        if translation[0] > 0:
            x_pos = min(self.sample_matrix_ChE[0])
        if translation[1] > 0:
            y_pos = min(self.sample_matrix_ChE[1])
        x_pos_ef = int(x_pos+translation[0])
        y_pos_ef = int(x_pos+translation[1])
        curr_zone = frame[y_pos-30:y_pos+30, x_pos-30:x_pos+30]
        eference_template = frame_prev[y_pos_ef:y_pos_ef+20, x_pos_ef:x_pos_ef+20]
        max_loc = self.template_matching(eference_template, curr_zone)
        return max_loc

    @staticmethod
    def template_matching(eference, curr):
        res = cv2.matchTemplate(curr, eference, cv2.TM_CCORR_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)
        return max_loc

    def update(self, frame, rot, trans):
        """
        Pass new frame to cell array and compute EMD result.
        Frame needs to be in monochrome
        cv2 and array indexing follows reversed order
        """
        frame_norm = self.normalize(frame)
        if self.frame_prev == []:
            self.frame_prev = frame_norm
            org_dim = frame.shape
            rp_dim = tuple(dim*2 for dim in org_dim)
            self.rp_window = np.zeros(rp_dim)
            self.t_limit = min(org_dim)/2
        Ch1E_list = frame_norm[(self.sample_matrix_ChE[1]), (self.sample_matrix_ChE[0])]
        Ch1I_list = frame_norm[(self.sample_matrix_ChI[1]), (self.sample_matrix_ChI[0])]
        self.Ch1E = Ch1E_list.reshape(self.Ch1E.shape)
        self.Ch1I = Ch1I_list.reshape(self.Ch1I.shape)
        self.Ch1E_prev = self.get_p_channels(self.frame_prev, self.Ch1E, trans, self.sample_matrix_ChE_p)
        self.Ch1I_prev = self.get_p_channels(self.frame_prev, self.Ch1I, trans, self.sample_matrix_ChI_p)
        self.Ch1E_rel = np.subtract(self.Ch1E, self.Ch1E_prev)
        self.Ch1I_rel = np.subtract(self.Ch1I, self.Ch1I_prev)
        self.Ch2I = self.Ch1E
        self.Ch2E = self.Ch1I
        self.Ch2I_prev = self.Ch1E_prev
        self.Ch2E_prev = self.Ch1I_prev
        self.Ch2I_rel = self.Ch1E_rel
        self.Ch2E_rel = self.Ch1I_rel
        self.lp_filter()

        self.Rexcite_rel = np.multiply(self.LP1_rel, self.Ch2E_rel)
        self.Rinhibit_rel = np.multiply(self.LP2_rel, self.Ch2I_rel)
        self.neuron_map_rel = np.subtract(self.Rinhibit_rel, self.Rexcite_rel)

        if self.mode == "loom":
            cell_id = np.argmax(abs(self.neuron_map_rel))
            flat_list = self.flat_it(self.neuron_map_rel)
            flat_list_prev = self.flat_it(self.neuron_map_prev)
            flat_list_rel = np.subtract(flat_list, flat_list_prev)
            self.neuron_map_rim[2, :] = flat_list
            self.Rmax = self.neuron_map_rel[cell_id]
            self.Rmean_filtered = np.mean([item for item in self.neuron_map_rel if item != 0])
        else:
            flat_list_rel = self.flat_it(self.neuron_map_rel)
            self.max_coord = np.argmax(flat_list_rel)
            self.cord_xy = np.unravel_index(self.max_coord, self.neuron_map_rel.shape)
            self.Rmax_rel = max(flat_list_rel, key=abs)
            self.log_rel.append(self.Rmax_rel)
        self.Rmean = np.mean(self.neuron_map_rel)
        self.frame_prev = frame_norm

    def update_rim(self, frame):
        """
        Pass new frame to cell array and compute EMD result.
        Frame needs to be in monochrome
        cv2 and array indexing follows reversed order
        """
        if self.frame_prev == []:
            self.frame_prev = frame
        frame_norm = self.normalize(frame)
        self.Ch1E_rel = frame_norm[(self.sample_matrix_ChE[1]), (self.sample_matrix_ChE[0])]
        self.Ch1I_rel = frame_norm[(self.sample_matrix_ChI[1]), (self.sample_matrix_ChI[0])]
        if self.LP1_rel == []:
            self.LP1_rel = np.zeros_like(self.Ch1E_rel)
            self.LP2_rel = np.zeros_like(self.Ch1E_rel)
        self.Ch2I_rel = self.Ch1E_rel
        self.Ch2E_rel = self.Ch1I_rel
        self.lp_filter()

        self.Rexcite_rel = np.multiply(self.LP1_rel, self.Ch2E_rel)
        self.Rinhibit_rel = np.multiply(self.LP2_rel, self.Ch2I_rel)
        """
        For testing purpose: background subtraction before passing to EMD
        """
        self.neuron_map_rel = np.subtract(self.Rinhibit_rel, self.Rexcite_rel)
        self.hp_filter(self.neuron_map_rel, tau_hp=150)

        self.max_coord = np.argmax(self.neuron_map_rel)
        self.cord_xy = np.unravel_index(self.max_coord, self.neuron_map_rel.shape)
        self.Rmax_rel = max(self.neuron_hp, key=abs)
        self.log_rel.append(self.Rmax_rel)
        self.Rmean = np.mean(self.neuron_map_rel)
        self.frame_prev = frame

    def flush(self):
        self.LP1_rel = self.Ch1E_rel
        self.LP2_rel = self.Ch1I_rel
        self.neuron_map_rel
        self.neuron_hp = []
        self.Rmax_rel = 0
    
    def hp_filter(self, src, tau_hp):
        """
        Forward Euler: x(t+1) = z(t) - ((z(t)-x(t))/tau +x(t))
        """
        if self.neuron_hp == []:
            self.neuron_hp = src
        # print(self.LP1)
        self.neuron_hp = src - np.add(np.divide(np.subtract(src, self.neuron_hp), tau_hp), self.neuron_hp)

    def lp_filter(self):
        """
        Forward Euler: x(t+1) = (z(t)-x(t))/tau +x(t)
        """
        self.LP1_rel = np.add(np.divide(np.subtract(self.Ch1E_rel, self.LP1_rel), self.tau), self.LP1_rel)
        self.LP2_rel = np.add(np.divide(np.subtract(self.Ch1I_rel, self.LP2_rel), self.tau), self.LP2_rel)

    @staticmethod
    def flat_it(lst):
        flat_list = [el for sublist in lst for el in sublist]
        return flat_list
    
    @staticmethod
    def normalize(src):
        # min_val = np.min(src)
        # max_val  = np.max(src)
        # dst = (src-min_val)/(max_val-min_val)
        dst = src/255
        return dst
    

class refine_projection:
    def __init__(self, center_pos=[100, 100], pos_mat=[2, 2], s_size=5, t_size=3):
        """
        s_size: n-by-n size of search window
        t_size: n-by-n size of match template 
        """
        self.search_window = np.zeros((s_size, s_size))
        self.template = np.zeros((t_size, t_size))
        self.frame_prev = []
        self.samp_frame = []
        self.samp_frame_p = []
        self.center_pos=center_pos
        self.result = []

        # start_x = center_pos[0] - 0.5 * ((cell_array[0] - 1) * pos_mat[0])
        # start_y = center_pos[1] - 0.5 * ((cell_array[1] - 1) * pos_mat[1])
        # start_pos = [int(start_x), int(start_y)]

        start_x_s = center_pos[0] - 0.5 * ((s_size - 1) * pos_mat[0])
        start_y_s = center_pos[1] - 0.5 * ((s_size - 1) * pos_mat[1])
        start_pos_s = [int(start_x_s), int(start_y_s)]
        start_x_t = center_pos[0] - 0.5 * ((t_size - 1) * pos_mat[0])
        start_y_t = center_pos[1] - 0.5 * ((t_size - 1) * pos_mat[1])
        start_pos_t = [int(start_x_t), int(start_y_t)]
        self.sample_matrix_s, self.matrix_location_s = self.get_sampling_matrix([5, 5], start_pos_s, pos_mat)
        self.sample_matrix_t, self.matrix_location_t = self.get_sampling_matrix([3, 3], start_pos_t, pos_mat)
        self.sample_matrix_p = []
        self.matrix_location_p = []
        
    
    @staticmethod
    def get_sampling_matrix(cell_array, start_pos, pos_mat):
        """
        Generates coordinate for pixel extraction
        Convert to Tuple list
        """
        samp_mat = np.mgrid[start_pos[0]:(start_pos[0] + cell_array[0] * pos_mat[0]):pos_mat[0],
                   start_pos[1]: (start_pos[1] + cell_array[1] * pos_mat[1]): pos_mat[1]].reshape(2, -1)

        sampling_matrix = tuple(samp_mat.tolist())
        centre_points = tuple(np.array(samp_mat).T.tolist())

        return sampling_matrix, centre_points

    @staticmethod
    def get_previous_channels(channel_coord, curr_channel, frame):
        channel_prev = np.zeros_like(curr_channel)
        height, width = frame.shape
        for i in range(len(channel_coord)):
            if channel_coord[i][0] < width and channel_coord[i][1] < height:
                channel_prev[i] = frame[channel_coord[i][1], channel_coord[i][0]]
            else:
                channel_prev[i] = curr_channel[i]

        return channel_prev
    
    @staticmethod
    def get_prev_frame_coords(ChE, rot, trans, origin):
        """
        Estimate where the ChE and ChI pixel location in the next time step based on rotation and translation
        """
        ChE_prev = []
        for i in range(len(ChE)):
            point = [ChE[i][0] - origin[0], ChE[i][1] - origin[1]]
            new_point = [point[0] * math.cos(rot) - point[1] * math.sin(rot),
                         point[1] * math.cos(rot) + point[0] * math.sin(rot)]
            new_point = [int(new_point[0] + trans[0] + origin[0]), int(new_point[1] + trans[1] + origin[1])]
            ChE_prev.append(new_point)
        sampling_ChE_prev = tuple(np.array(ChE_prev).T.tolist())

        return sampling_ChE_prev, ChE_prev
    
    def update(self, frame, rot, trans):
        # self.refine_step = self.refine_projection(trans, self.frame_prev, frame)
        frame_norm = self.normalize(frame)
        if self.frame_prev == []:
            self.frame_prev = frame_norm
        samp_list = frame_norm[(self.sample_matrix_s[1]), (self.sample_matrix_s[0])]
        self.search_window = samp_list.reshape(self.search_window.shape)
        self.sample_matrix_p, self.matrix_location_p = self.get_prev_frame_coords(self.matrix_location_t, rot, trans, self.center_pos)
        temp_list = self.frame_prev[(self.sample_matrix_p[1]), (self.sample_matrix_p[0])]
        # print('sample mat previous', self.sample_matrix_t)
        self.template = temp_list.reshape(self.template.shape)
        res = cv2.matchTemplate(self.search_window.astype(np.float32), self.template.astype(np.float32), cv2.TM_CCORR_NORMED)
        self.result = res

    @staticmethod
    def normalize(src):
        min_val = np.min(src)
        max_val  = np.max(src)
        dst = (src-min_val)/(max_val-min_val)
        return dst

        
class PID:
    def __init__(self, dt=1 / 100, kp=1, ki=0.3, kd=0.4):
        """Initialise PID controller for drone"""

        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.dt = dt
        self.integral = 0
        self.olderror = 0

    def update(self, ref, state, limit=1):
        """Update step for PID controller"""
        # Speed limiter
        e = ref - state
        if e > 10:
            e = 10
        elif e < -10:
            e = -10
        self.integral = self.integral + e * self.dt
        i = self.integral
        d = e - self.olderror
        self.olderror = e
        actuation = self.kp * e + self.ki * i + self.kd * d
        if actuation > limit:
            actuation = limit
        elif actuation < -limit:
            actuation = -limit

        return float(actuation)


def pose_shift(curr_state, prev_state, ppr):
    """
    Calculate pose shift between consecutive frames for tsdn_emd rot and trans
    self.rot is delta roll
    self.trans is delta [-yaw, -pitch] to align with openCV coordinate system
    """
    pose_change = np.subtract(curr_state, prev_state)
    rot_shift = pose_change[0]
    trans_shift = [pose_change[0] * ppr, -pose_change[1] * ppr]

    return trans_shift


def cell_wise_average(lat_response, long_response):
    lat_abs = np.abs(lat_response)
    long_abs = np.abs(long_response)
    neuron_map = (lat_abs + long_abs) / 2
    max_coord = np.argmax(EMD.flat_it(neuron_map))
    flat_list = EMD.flat_it(neuron_map)
    Rmax_mean = max(flat_list, key=abs)

    return neuron_map, max_coord, Rmax_mean

