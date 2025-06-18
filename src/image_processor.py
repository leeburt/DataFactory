import base64

class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图像文件编码为base64字符串"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            raise Exception(f"图像编码失败: {str(e)}") 