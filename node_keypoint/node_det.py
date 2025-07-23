from ultralytics import YOLO
from PIL import Image
import os 
os.environ['CUDA_VISIBLE_DEVICES']="2"



class YoloDet():

    def __init__(self):
        # Load a pretrained YOLO11n model
        self.det  = YOLO(os.path.join(os.path.dirname(os.path.abspath(__file__)),"node_det_v2_20250711.pt"))

    # Run inference on 'bus.jpg' with arguments
    def __call__(self, image_path,imgsz=1024,conf=0.25, iou=0.45,save_json=True,plots=True):
        results = self.det.predict(source=image_path, imgsz=imgsz, batch=1, conf=conf, iou=iou,save_json=save_json,plots=plots)
        return results[0]

    def convert_to_yolo_format(self, x1, y1, x2, y2, img_width, img_height):
        """
        将边界框坐标从 (x1, y1, x2, y2) 格式转换为YOLO格式 (x_center, y_center, width, height)
        所有值都归一化到 [0, 1] 范围
        """
        x_center = (x1 + x2) / 2 / img_width
        y_center = (y1 + y2) / 2 / img_height
        width = (x2 - x1) / img_width
        height = (y2 - y1) / img_height
        return x_center, y_center, width, height

if __name__ == "__main__":
    node_io = YoloDet()
    import cv2 
    
    image_path = "/data/home/libo/work/DataFactory/images/1.jpg"
    results = node_io(image_path)
    image = cv2.imread(image_path)
    h, w, c = image.shape
    
    print(f"图像尺寸: {w} x {h}")
    print("原始格式 (x1, y1, x2, y2) -> YOLO格式 (x_center, y_center, width, height):")
    
    for box in results.boxes:
        x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int).tolist()[0]
        node_box = [x1, y1, x2, y2]
        
        # 转换为YOLO格式
        x_center, y_center, width, height = node_io.convert_to_yolo_format(x1, y1, x2, y2, w, h)
        
        print(f"原始: {node_box} -> YOLO: [{x_center:.6f}, {y_center:.6f}, {width:.6f}, {height:.6f}]")
