import numpy as np
import cv2
import datetime
import os
import json

##########################################################################
def get_poly_box_wh(poly_box): # (4,2)
    lt, rt, rb, lb = poly_box
    w = int((np.linalg.norm(lt - rt) + np.linalg.norm(lb - rb)) // 2)
    h = int((np.linalg.norm(lt - lb) + np.linalg.norm(rt - rb)) // 2)
    return w, h

def crop_obj_in_bg(bg_img, poly, w, h):
    poly = poly.astype(np.float32)
    pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
    M = cv2.getPerspectiveTransform(poly, pos)
    obj_img = cv2.warpPerspective(bg_img, M, (w, h))
    return obj_img, M

def crop_obj_in_bg2(bg_img, polys):
    obj_imgs = []
    for poly in polys:
        poly = poly.astype(np.float32)
        w, h = get_poly_box_wh(poly)
        pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
        M = cv2.getPerspectiveTransform(poly, pos)
        obj_img = cv2.warpPerspective(bg_img, M, (w, h))
        obj_imgs.append(obj_img)
    return obj_imgs

def crop_obj_in_bg3(bg_img, xyxys):
    obj_imgs = []
    for xyxy in xyxys:
        x1, y1 = np.min(xyxy, axis=0).astype(np.int32) # (n, 2)
        x2, y2 = np.max(xyxy, axis=0).astype(np.int32)
        obj_img = bg_img[y1:y2, x1:x2]
        obj_imgs.append(obj_img)
    return obj_imgs

def get_crop_img_and_M(img, poly):
    poly = poly.astype(np.float32)
    w, h = get_poly_box_wh(poly)
    pos = np.float32([[0,0], [w,0], [w,h], [0,h]])
    M = cv2.getPerspectiveTransform(poly, pos)
    crop_img = cv2.warpPerspective(img, M, (w, h))
    return crop_img, M
    
##########################################################################
def get_time_str(human_mode=False, day=False):
    now = datetime.datetime.now()
    if day:
        s = f"{now.year:04d}-{now.month:02d}-{now.day:02d}"
        return s
    if human_mode:
        s = f"{now.year:04d}-{now.month:02d}-{now.day:02d} {now.hour:02d}:{now.minute:02d}:{now.second:02d}"
    else:
        s = f"{now.year:04d}{now.month:02d}{now.day:02d}{now.hour:02d}{now.minute:02d}{now.second:02d}"
        s += f"_{now.microsecond:06d}"
    return s

##########################################################################
def manage_file_num(dir_path, max_size=500, num_remove=100):
    path = os.path.join(dir_path, "*.jpg")
    img_paths = sorted(path)
    if len(img_paths) < max_size: return

    for path in img_paths[:num_remove]:
        os.remove(path)

##########################################################################
def fix_ratio_resize_img(img, size, target='w'):
    h, w = img.shape[:2]
    ratio = h/w
    if target == 'w': resized_img = cv2.resize(img, dsize=(size, int(ratio * size)))
    else:             resized_img = cv2.resize(img, dsize=(int(size / ratio), size))
    return resized_img

##########################################################################
def clear_Q(Q):
    with Q.mutex:
        Q.queue.clear()
        
def clear_serial(ser):
    while True:
        if ser.read_all() == b'': break

##########################################################################
def get_diff_img(img1, img2):
    assert img1.shape == img2.shape
    
    # get diff
    result = cv2.absdiff(img1, img2)
    if len(result.shape) == 3:
        result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
    
    _, result = cv2.threshold(result, 5,255, cv2.THRESH_BINARY)
    
    # dilate
    # kernel = np.ones((3,3))
    kernel = np.ones((5,5))
    result = cv2.erode(result, kernel, iterations=1)
    result = cv2.dilate(result, kernel, iterations=2)
    return result

def diff2ratio(img):
    assert img.dtype == np.uint8
    assert len(img.shape) == 2
        
    ratio = np.sum(img/255.) / (img.shape[0]*img.shape[1])
    return ratio
        
def find_poly_in_img(img, min_area=0.05, max_area=0.7, scale=0.1):
    assert img.dtype == np.uint8
    
    # minimize img for speed.
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    mini_img = cv2.resize(img_gray, dsize=(0,0), fx=scale, fy=scale)
    mini_img_area = mini_img.shape[0] * mini_img.shape[1]

    # set mser
    mser = cv2.MSER_create()
    mser.setMinArea(int(mini_img_area*min_area))
    mser.setMaxArea(int(mini_img_area*max_area))

    # find poly
    regions, bboxes = mser.detectRegions(mini_img)
    if len(regions) == 0: return None
    rectangles = list(map(cv2.minAreaRect, regions))
    polygons = list(map(lambda x:cv2.boxPoints(x), rectangles))
    areas = list(map(cv2.contourArea, polygons))
    max_idx = np.argmax(areas)
    poly = (polygons[max_idx] / scale).astype(np.int32)

    return poly

def find_polys_in_img(img, min_area=0.03, max_area=0.7, scale=0.1):
    assert img.dtype == np.uint8
    
    img_area = img.shape[0] * img.shape[1]
    min_area *= img_area
    max_area *= img_area
    
    # find contours
    img_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img
    contours, _ = cv2.findContours(img_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if len(contours) == 0: return None

    # contours to polys
    rects = list(map(cv2.minAreaRect, contours))
    polys = list(map(lambda x:cv2.boxPoints(x), rects))
    polys = list(filter(lambda poly:min_area < cv2.contourArea(poly) < max_area, polys))
    polys = np.stack(polys).astype(np.int32) if polys else None
    
    return polys
    
def poly2clock(poly):
    # move centroid to zero
    centroid = np.mean(poly, axis=0) # (2,)
    new_poly = poly - centroid # (n, 2)

    # sort by radian
    # 이미지에서 볼때 좌상단 첫번째로 시계방향
    # 좌표계에서 볼때 좌하단 첫번재로 반시계방향
    rad = list(map(lambda x:np.arctan2(*x), new_poly[:,::-1])) # xy -> yx
    idxs = np.argsort(rad)
    return poly[idxs]

##########################################################################
def poly2json(path, labels, polys):
    assert len(labels) == len(polys)
    dic = {"shapes":[{"label":label,"points":poly.tolist()} for label,poly in zip(labels, polys)]}
    
    with open(path, 'w') as f:
        json.dump(dic, f, indent=2)
    
##########################################################################
def imread(path, mode=cv2.IMREAD_COLOR):
    encoded_img = np.fromfile(path, np.uint8)
    img = cv2.imdecode(encoded_img, mode)
    return img

def imwrite(path, img):
    result, encoded_img = cv2.imencode('.jpg', img)
    if result:
        with open(path, 'w') as f:
            encoded_img.tofile(f)
    return result

##########################################################################
def get_diff_score(img1, img2, size=(6,6)):
    small_img1 = cv2.resize(img1, size)
    small_img2 = cv2.resize(img2, size)
    
    diff = cv2.absdiff(small_img1, small_img2)
    diff[diff < 15] = 0
    diff[diff > 0] = 1
    return np.sum(diff)




        
