from collections import namedtuple
from PIL import ImageTk, Image
import tkinter as tk
import numpy as np
import cv2

class LabelCanvas(tk.Canvas):
    def __init__(self, *args, img_arr=None, isrect=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.pack(pady=20)
        
        # Mouse
        self.bind("<Button-1>", self.on_click)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.init_selected)
        
        # value
        self.dot_size = 10
        self.before_magnf_value = 1.
        self.magnf_value = 1.
        self.isrect = isrect
        self.rotate_num = 0
        
        # image
        self.origin_img = img_arr
        self.origin_img_pil = None
        self.img_pil = None
        self.img_tk = None
        self.img_xy = np.array([0,0])
        self.img_cent = np.array([0,0])
        
        # make
        self.create_items()
        self.apply_img(img_arr)
    
    def create_items(self):
        self.points = np.array([[250,250], [400,250], [400,400], [250,400]])
        self.point_ids = []

        self.image_id = self.create_image(*self.img_cent, image=self.img_tk)
        
        # create poly
        self.poly_id = self.create_polygon(*self.points.ravel(), outline='#44f', fill='')
        
        # create 4-dots
        for pos in self.points:
            p = self.create_oval(pos[0]-self.dot_size, pos[1]-self.dot_size, 
                                 pos[0]+self.dot_size, pos[1]+self.dot_size, fill="#4f0")
            self.point_ids.append(p)
            
    def get_distance(self, xy1, xy2):
        xy1 = np.array(xy1)
        xy2 = np.array(xy2)
        return np.linalg.norm(xy1-xy2)
    
    def get_centroid(self, coord):
        coord = np.array(coord).reshape(-1, 2)
        return np.mean(coord, axis=0)
            
    def on_click(self, event):
        self.startxy = [event.x, event.y]
        
        # select nearest item
        self.pick_id, self.pick_idx = None, None
        min_dist = 9999
        for i, _id in enumerate(self.point_ids):
            cent = self.get_centroid(self.coords(_id))
            dist = self.get_distance(self.startxy, cent)
            if dist < min_dist:
                self.pick_id, self.pick_idx, min_dist = _id, i, dist
                
############################################################################################
    def moving_limit(self):
        right__limit = min(self.points[[1,2], 0])
        left___limit = max(self.points[[0,3], 0])
        top____limit = max(self.points[[0,1], 1])
        bottom_limit = min(self.points[[2,3], 1])
        
        # limit x
        if self.pick_idx==0 and self.points[0, 0] > right__limit: self.points[0, 0] = right__limit
        if self.pick_idx==1 and self.points[1, 0] < left___limit: self.points[1, 0] = left___limit
        if self.pick_idx==2 and self.points[2, 0] < left___limit: self.points[2, 0] = left___limit
        if self.pick_idx==3 and self.points[3, 0] > right__limit: self.points[3, 0] = right__limit
        # limit y
        if self.pick_idx==0 and self.points[0, 1] > bottom_limit: self.points[0, 1] = bottom_limit
        if self.pick_idx==1 and self.points[1, 1] > bottom_limit: self.points[1, 1] = bottom_limit
        if self.pick_idx==2 and self.points[2, 1] < top____limit: self.points[2, 1] = top____limit
        if self.pick_idx==3 and self.points[3, 1] < top____limit: self.points[3, 1] = top____limit
    
    def apply_points(self):
        self.coords(self.poly_id, *self.points.ravel()) # poly update
        for i, _id in enumerate(self.point_ids):
            pos = self.points[i]
            self.coords(_id, pos[0]-self.dot_size, pos[1]-self.dot_size, 
                             pos[0]+self.dot_size, pos[1]+self.dot_size) # dot update
            
    def on_drag(self, event):
        # get dx,dy
        endxy = [event.x, event.y]
        dx, dy = np.array([endxy[0]-self.startxy[0], endxy[1]-self.startxy[1]])
        
        # update
        self.points[self.pick_idx] += np.array([dx,dy])
        self.moving_limit()
        
        # rect일 경우 같이 이동
        if self.isrect:
            dic = {0:[3,1], 1:[2,0], 2:[1,3], 3:[0,2]}
            x_idx, y_idx = dic[self.pick_idx]
            self.points[x_idx][0] = self.points[self.pick_idx][0]
            self.points[y_idx][1] = self.points[self.pick_idx][1]
        
        self.apply_points()
        self.startxy = endxy

    def init_selected(self, event):
        self.pick_id = None
        self.pick_idx = None
        
############################################################################################
    def set_img_pil(self):
        assert 0.1 <= self.magnf_value <= 10.0
        if self.origin_img_pil is None: return
        
        # 이미지 줌인/줌아웃 적용
        w, h = self.origin_img_pil.size
        self.img_pil = self.origin_img_pil.resize((int(w*self.magnf_value), int(h*self.magnf_value)), Image.LANCZOS)
        
        # 이미지 회전 적용
        img_arr = np.array(self.img_pil)
        for _ in range(self.rotate_num):
            img_arr = cv2.rotate(img_arr, cv2.ROTATE_90_CLOCKWISE)
        self.img_pil = Image.fromarray(img_arr)
        
    def update_image(self):
        self.img_tk = ImageTk.PhotoImage(self.img_pil) if self.img_pil else None
        self.itemconfig(self.image_id, image=self.img_tk)
        self.coords(self.image_id, *self.img_cent)
        
    def zoom_in(self, value=0.2):
        self.before_magnf_value = self.magnf_value
        self.magnf_value += value
        try: self.set_img_pil()
        except: self.magnf_value = self.before_magnf_value
        self.update_img_xy_cent()
        self.update_image()
        self.apply_points()
        
    def zoom_out(self, value=0.2):
        self.before_magnf_value = self.magnf_value
        self.magnf_value -= value
        try: self.set_img_pil()
        except: self.magnf_value = self.before_magnf_value
        self.update_img_xy_cent()
        self.update_image()
        self.apply_points()
        
    def update_img_xy_cent(self):
        center_xy = np.array([self.winfo_width()/2, self.winfo_height()/2])
        # 절대좌표 -> 상대좌표
        relative_img_xy = self.img_xy - center_xy
        relative_img_cent = self.img_cent - center_xy
        relative_points = self.points - center_xy
        # 상대좌표 조정
        relative_img_xy = relative_img_xy / self.before_magnf_value * self.magnf_value
        relative_img_cent = relative_img_cent / self.before_magnf_value * self.magnf_value
        relative_points = relative_points / self.before_magnf_value * self.magnf_value
        # 상대좌표 -> 절대좌표
        self.img_xy = relative_img_xy + center_xy
        self.img_cent = relative_img_cent + center_xy
        self.points = relative_points + center_xy
        
    def rotate_img(self):
        # 좌표변환
        self.img_xy -= self.img_cent
        self.img_xy = self.img_xy[::-1]
        self.img_xy += self.img_cent
        
        # 회전수 변환
        self.rotate_num += 1
        self.rotate_num %= 4
        
        # 이미지 적용
        self.set_img_pil()
        self.update_image()
        
############################################################################################
    def apply_img(self, origin_img_arr):
        if origin_img_arr is None: return
    
        self.origin_img = origin_img_arr
        
        # 이미지 크기 조정
        win_size_hw = self.winfo_height(), self.winfo_width()
        img_arr, magnf_value = self.fit_img(origin_img_arr, win_size_hw)
        self.magnf_value = magnf_value
        
        # 초기 좌표 계산
        self.img_cent = np.array(win_size_hw[::-1])/2
        self.img_xy = self.img_cent - np.array(img_arr.shape[-2::-1])/2
        
        # 이미지 적용
        self.origin_img_pil = Image.fromarray(origin_img_arr[:,:,::-1])
        self.img_pil = Image.fromarray(img_arr[:,:,::-1])
        self.update_image()
        
    def fit_img(self, img, size):
        wh, ww = size
        h, w = img.shape[:2]
        magnf_value = min(wh/h, ww/w)
        new_img = cv2.resize(img, dsize=(0,0), fx=magnf_value, fy=magnf_value)
        return new_img, magnf_value
        
############################################################################################
    def move_right(self, value=150):
        self.points[:, 0] -= value
        self.apply_points()
        self.img_xy[0] -= value
        self.img_cent[0] -= value
        self.update_image()
    
    def move_left(self, value=150):
        self.points[:, 0] += value
        self.apply_points()
        self.img_xy[0] += value
        self.img_cent[0] += value
        self.update_image()
    
    def move_down(self, value=150):
        self.points[:, 1] -= value
        self.apply_points()
        self.img_xy[1] -= value
        self.img_cent[1] -= value
        self.update_image()
    
    def move_up(self, value=150):
        self.points[:, 1] += value
        self.apply_points()
        self.img_xy[1] += value
        self.img_cent[1] += value
        self.update_image()
    
############################################################################################
    def reset_items(self):
        self.points = np.array([[250,250], [400,250], [400,400], [250,400]])
        self.apply_points()
        
        self.origin_img = None
        self.rotate_num = 0
        self.magnf_value = 1.
        self.img_cent = np.array([0,0])
        self.img_xy = np.array([0,0])
        self.origin_img_pil = None
        self.img_pil = None
        self.update_image()
    
############################################################################################
    def rotate90_points(self, points, center, n=1):
        assert points.shape == (4,2)
        assert center.shape == (2,)
        
        points = points.astype(np.float32)
        center = center.astype(np.float32)
        
        # 반시계방향
        for _ in range(n):
            points -= center
            points[:,0] *= -1
            points = points[:,::-1]
            points += center
            
        return points

    def get_points_with_img(self):
        if self.origin_img_pil is None: return None
    
        # 홀수 회전되 있는 경우
        img_xy = self.img_xy
        img_pil_size = self.img_pil.size
        if self.rotate_num%2 == 1:
            img_xy -= self.img_cent
            img_xy = img_xy[::-1]
            img_xy += self.img_cent
            img_pil_size = self.img_pil.size[::-1]
            
        # 좌표회전
        self.points = self.rotate90_points(self.points, self.img_cent, n=self.rotate_num)
        
        # 좌표이동
        points = self.points - img_xy
        
        # 좌표변환
        points = points / np.array(img_pil_size) * np.array(self.origin_img_pil.size)
        
        return points
        # rect이면 좌상단,우하단만
        # if self.isrect: return points[[0,2]]
        # return points
        
        
        

        
        
