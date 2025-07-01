
from PIL import Image, ImageDraw
import os 
import sys 
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from node_connections.io_det import YoloDet as io_det
from node_connections.node_det import YoloDet as node_det


class NodeIO():
    def __init__(self):
        self.io_det = io_det()
        self.node_det = node_det()

    def _draw_box_to_image(self,image_path,results_io,results_node,save_path=None):
        image = Image.open(image_path)
        draw = ImageDraw.Draw(image)
        io_name=results_io.names
        for box in results_io.boxes:
            x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int).tolist()[0]
            io_box = [x1, y1, x2, y2]
            cls_id = box.cls.cpu().numpy().astype(int).tolist()[0]
            conf = box.conf.cpu().numpy().astype(float).tolist()[0]
            ##获取io的名称
            draw.rectangle(io_box, outline='red', width=2)
            draw.text((x1, y1-10), f"{io_name[cls_id]}:{conf:.2f}", fill='blue')


        for box in results_node.boxes:
            x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int).tolist()[0]
            node_box = [x1, y1, x2, y2]
            draw.rectangle(node_box, outline='blue', width=2)
        if save_path is not None:
            image.save(save_path)
        return image_path
    
    def get_all_node_io(self,results_io,results_node):
        node_io_dict = {}
        def iou(box1,box2):
            x1, y1, x2, y2 = box1
            x3, y3, x4, y4 = box2
            x_inter = max(0, min(x2, x4) - max(x1, x3))
            y_inter = max(0, min(y2, y4) - max(y1, y3))
            inter = x_inter * y_inter
            union = (x2 - x1) * (y2 - y1) + (x4 - x3) * (y4 - y3) - inter
            return inter / union
        for box in results_node.boxes:
            x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int).tolist()[0]
            node_box = [x1, y1, x2, y2]
            if str(node_box) not in node_io_dict:
                node_io_dict[str(node_box)] = {"input":[],"output":[]}
            io_name=results_io.names
            for box in results_io.boxes:
                x1, y1, x2, y2 = box.xyxy.cpu().numpy().astype(int).tolist()[0]
                io_box = [x1, y1, x2, y2]
                cls_id = box.cls.cpu().numpy().astype(int).tolist()[0]
                conf = box.conf.cpu().numpy().astype(float).tolist()[0]
                if iou(node_box,io_box) > 0:
                    node_io_dict[str(node_box)][io_name[cls_id]].append(io_box)
        return node_io_dict

    def __call__(self, image_path,imgsz=1024,conf=0.25, iou=0.45,save_json=True,plots=True):
        print(image_path)
        results_io = self.io_det(image_path,640,conf, iou,save_json,plots)
        results_node = self.node_det(image_path,imgsz,conf, iou,save_json,plots)
        ## 识别图中的节点，然后根据输入和输出模型的结果，识别出节的输入和输出
        save_path = os.path.join("/data/home/libo/work/DataFactory/.cache/debug_image", "io_det.jpg")
        # self._draw_box_to_image(image_path,results_io,results_node,save_path)
        node_io_map = self.get_all_node_io(results_io,results_node)
        return results_io,results_node,node_io_map
    

if __name__ == "__main__":
    node_io = NodeIO()
    image_path = "/data/home/libo/work/DataFactory/.cache/模拟电路框图/PLL.jpg"
    results_io,results_node,node_io_map = node_io(image_path)
    # print(results_io)
    # print(results_node)
    print(node_io_map)