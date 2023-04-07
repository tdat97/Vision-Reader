from collections import namedtuple
from glob import glob
from tqdm import tqdm
import numpy as np
import json
import time
import cv2
import os


def json2label(path, return_dic=True): # json 경로
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    labels = [shape["label"] for shape in data["shapes"]]
    points = np.float32([shape["points"] for shape in data["shapes"]]) # (n, 2?, 2)
    if return_dic:
        return dict(zip(labels, points))
    else:
        return labels, points

def get_poly_box_wh(poly_box): # (4, 2)
    lt, rt, rb, lb = poly_box
    w = int((np.linalg.norm(lt - rt) + np.linalg.norm(lb - rb)) // 2)
    h = int((np.linalg.norm(lt - lb) + np.linalg.norm(rt - rb)) // 2)
    return w, h

def crop_obj_in_bg(bg_img, polys):
    obj_imgs = []
    for poly in polys:
        poly = poly.astype(np.float32)
        w, h = get_poly_box_wh(poly)
        pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
        M = cv2.getPerspectiveTransform(poly, pos)
        obj_img = cv2.warpPerspective(bg_img, M, (w, h))
        obj_imgs.append(obj_img)
    return obj_imgs

def get_crop_img_and_M(img, poly):
    poly = poly.astype(np.float32)
    w, h = get_poly_box_wh(poly)
    pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
    M = cv2.getPerspectiveTransform(poly, pos)
    crop_img = cv2.warpPerspective(img, M, (w, h))
    return crop_img, M

def imread(path, mode=cv2.IMREAD_COLOR):
    encoded_img = np.fromfile(path, np.uint8)
    img = cv2.imdecode(encoded_img, mode)
    return img

#########################################################################################
class SinglePolyDetector():
    def __init__(self, img_path, json_path, pick_labels=[], n_features=2000):
        img_gray = imread(img_path, cv2.IMREAD_GRAYSCALE)
        assert img_gray is not None, "img_path is not correct."
        
        poly_dict = json2label(json_path)
        
        polys = [poly_dict[label] for label in pick_labels]
            
        # assert (target_label_name in self.labels) or (target_label_name==''), "Invalid label_name."
        
        # 0번 index를 target으로
        # target_idx = self.labels.index(target_label_name)
        # self.label[0], self.label[target_idx] = self.label[target_idx], self.label[0]
        # polys[0], polys[target_idx] = polys[target_idx], polys[0]
        
        # keypoints
        self.detector = cv2.ORB_create(n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING2, crossCheck=True)
        crop_img_gray, M = get_crop_img_and_M(img_gray, polys[0])
        self.kp, self.desc = self.detector.detectAndCompute(crop_img_gray, None)
        
        # transform polygons
        polys = np.stack(polys).astype(np.float32)
        polys = cv2.perspectiveTransform(polys, M)
        self.src_polys = polys
        
    def __call__(self, img):
        if img.ndim == 2: img_gray = img
        else: img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # match
        kp, desc = self.detector.detectAndCompute(img_gray, None)
        if len(kp) < 100: return None, None
        matches = self.matcher.match(self.desc, desc)
        
        # get keypoints of matches
        src_pts = np.float32([self.kp[m.queryIdx].pt for m in matches])
        dst_pts = np.float32([kp[m.trainIdx].pt for m in matches])
        
        # src_polys -> dst_polys
        M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RHO, 5.0)
        if mask.sum() / mask.size < 0.15: return None, None
        dst_polys = cv2.perspectiveTransform(self.src_polys, M)
        
        # get crop_imgs # 이래야 항상 크기가 일정함
        h, w = img.shape[:2]
        inv_M = cv2.getPerspectiveTransform(dst_polys[0], self.src_polys[0])
        img_trans = cv2.warpPerspective(img, inv_M, (w, h))
        crop_imgs = crop_obj_in_bg(img_trans, self.src_polys)
        
        return dst_polys, crop_imgs
    
#########################################################################################
class ObjInfo():
    def __init__(self, name, img_bgr, label2poly, detector):
        self.name = name # 여기선 code
        
        obj_poly = label2poly["object"]
        polys = np.float32(list(label2poly.values())) # (n, 4, 2)
        crop_bgr, M = get_crop_img_and_M(img_bgr, obj_poly)
        self.src_polys = cv2.perspectiveTransform(polys, M)
        self.labels = list(label2poly.keys())
        
        crop_gray = cv2.cvtColor(crop_bgr, cv2.COLOR_BGR2GRAY)
        self.kp, self.desc = detector.detectAndCompute(crop_gray, None)
    
    def __repr__(self):
        return f"ObjInfo({self.name})"

class MultiPolyDetector():
    def __init__(self, img_dir_path, json_dir_path, n_features=2000, logger=None, pick_names=None):
        # create detector, matcher
        self.detector = cv2.ORB_create(n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING2, crossCheck=True)
        self.logger = logger
        
        self.obj_info_list = set()
        
        # for update_check
        self.names = set()
        self.img_dir_path = img_dir_path
        self.json_dir_path = json_dir_path
        
        # 초기 정보 가져오기
        self.update(pick_names=pick_names)
        
        # warm up
        temp = np.zeros((100,100,3), dtype=np.uint8)
        _, _, _ = self.predict(temp)
        
    def predict(self, img):
        # 새로운 이미지 특징점
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)    
        kp, desc = self.detector.detectAndCompute(gray, None)
        if len(kp) < 50: return None, None, None
    
        best_obj, best_acc, best_M = None, 0, None
        for obj_info in self.obj_info_list:
            # 사전 데이터와 들어온 데이터를 매칭
            matches = self.matcher.match(obj_info.desc, desc)
            if len(matches) < 30: continue
            src_pts = np.float32([obj_info.kp[m.queryIdx].pt for m in matches])
            dst_pts = np.float32([kp[m.trainIdx].pt for m in matches])
            M, mask = cv2.findHomography(src_pts, dst_pts, cv2.RHO, 5.0)
            accuracy = np.sum(mask) / len(mask)
            # 최고 정확도 선택
            if best_acc < accuracy:
                best_obj, best_acc, best_M = obj_info, accuracy, M
        
        if self.logger:
            self.logger.debug(f"Best Acc : {best_acc*100:0.2f}% \t Best_Obj : {best_obj}")
        if best_acc < 0.20: return None, None, None

        # src_polys -> dst_polys
        dst_polys = cv2.perspectiveTransform(best_obj.src_polys, best_M)
        
        # get crop imgs # 이래야 크기가 일정함
        i = best_obj.labels.index('object')
        w, h = get_poly_box_wh(best_obj.src_polys[i])
        inv_M = cv2.getPerspectiveTransform(dst_polys[i], best_obj.src_polys[i])
        img_trans = cv2.warpPerspective(img, inv_M, (w, h))
        crop_imgs = crop_obj_in_bg(img_trans, best_obj.src_polys)
                        
        return best_obj, dst_polys, crop_imgs
        
    def update(self, pick_names=None):
        # 파일 경로 가져오기
        img_paths = glob(os.path.join(self.img_dir_path, "*.png"))
        json_paths = glob(os.path.join(self.json_dir_path, "*.json"))
        
        # 파일이름만 빼기 (코드)
        img_names = set(map(lambda path:path.split('\\')[-1].split('.')[0], img_paths))
        json_names = set(map(lambda path:path.split('\\')[-1].split('.')[0], json_paths))
        
        # 교집합
        names = img_names & json_names
        if len(pick_names): names &= set(pick_names)
        # if names == self.names: return
        self.names = names
    
        # 다시 불러오기
        names_list = list(names)
        func = lambda name:imread(os.path.join(self.img_dir_path, f"{name}.png"))
        img_list = list(map(func, names_list))
        func = lambda name:json2label(os.path.join(self.json_dir_path, f"{name}.json"))
        label2poly_list = list(map(func, names_list))
        _zip = zip(names_list, img_list, label2poly_list)
        self.obj_info_list = list(map(lambda x:ObjInfo(*x, self.detector), _zip))
        
    