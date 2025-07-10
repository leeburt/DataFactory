import base64
from PIL import Image
import io

class ImageProcessor:
    """图像处理工具类"""
    
    @staticmethod
    def encode_image(image_path: str) -> str:
        """将图像文件编码为base64字符串，若宽或高大于1800则等比例缩放"""
        try:
            with Image.open(image_path) as img:
                # width, height = img.size
                # max_size = 1800
                # if width > max_size or height > max_size:
                #     # 计算缩放比例
                #     scale = min(max_size / width, max_size / height)
                #     new_size = (int(width * scale), int(height * scale))
                #     # 使用新的Resampling.LANCZOS替代已弃用的ANTIALIAS
                #     img = img.resize(new_size, Image.Resampling.LANCZOS)
                # 转为字节流再编码
                buffered = io.BytesIO()
                img.save(buffered, format=img.format or 'PNG')
                img_bytes = buffered.getvalue()
                return base64.b64encode(img_bytes).decode('utf-8')
        except Exception as e:
            raise Exception(f"图像编码失败: {str(e)}") 