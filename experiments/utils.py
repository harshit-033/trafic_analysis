# ai/utils.py
import cv2, numpy as np

def image_entropy(gray):
    hist = cv2.calcHist([gray],[0],None,[256],[0,256])
    hist = hist.ravel()/hist.sum()
    hist = hist[hist>0]
    return -np.sum(hist * np.log2(hist))

def bbox_center(bbox):
    x1,y1,x2,y2 = bbox
    return ((x1+x2)/2, (y1+y2)/2)

def map_to_lane(center, lane_rois):
    # lane_rois: list of polygons
    # return lane_id if point inside ROI polygon
    pass
