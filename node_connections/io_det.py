from ultralytics import YOLO
from PIL import Image
import os 
os.environ['CUDA_VISIBLE_DEVICES']="-1"
class YoloDet():

    def __init__(self):
        # Load a pretrained YOLO11n model
        self.det  = YOLO(os.path.join(os.path.dirname(os.path.abspath(__file__)),"port_det_v2_20250711.pt"))

    # Run inference on 'bus.jpg' with arguments

    def __call__(self, image_path,imgsz=1024,conf=0.25, iou=0.45,save_json=True,plots=True):
        results = self.det.predict(source=image_path, imgsz=imgsz, batch=1, conf=conf, iou=iou,save_json=save_json,plots=plots)
        return results[0]