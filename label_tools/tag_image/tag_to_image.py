import streamlit as st
import os
import json
import pandas as pd
from typing import List, Dict, Any
import time
import contextlib

# --- Thread-Safe File Locking ---
@contextlib.contextmanager
def file_lock(lock_file):
    """ A context manager for file locking to ensure thread safety. """
    # Use mkdir for atomic lock acquisition
    lock_dir = lock_file + ".lock"
    try:
        # Loop with a timeout to acquire the lock
        timeout = 10.0  # 10 seconds
        start_time = time.time()
        while True:
            try:
                os.mkdir(lock_dir)
                break  # Lock acquired
            except FileExistsError:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Could not acquire lock file.")
                time.sleep(0.1)
        yield
    finally:
        if os.path.exists(lock_dir):
            os.rmdir(lock_dir)

# --- Configuration ---
IMAGE_EXTENSIONS = ['.png', '.jpg', '.jpeg', '.bmp', '.gif']
ANNOTATIONS_FILE_DEFAULT = "annotations.json"

# --- Helper Functions ---

def find_images(directory: str) -> List[str]:
    """Recursively finds all images in a directory."""
    image_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.lower().endswith(ext) for ext in IMAGE_EXTENSIONS):
                image_files.append(os.path.join(root, file))
    return sorted(image_files)

def load_annotations(filepath: str) -> Dict[str, Any]:
    """Loads annotations from a JSON file."""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_annotations(filepath: str, data: Dict[str, Any]):
    """Saves annotations to a JSON file."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def safe_update_annotation(json_filepath: str, image_name: str, image_path: str, new_tags: List[str], annotator: str) -> Dict[str, Any]:
    """
    Safely reads, updates, and writes a single image's annotation using a file lock.
    Returns the full, updated annotations dictionary.
    """
    with file_lock(json_filepath):
        # Read the latest data from the file inside the lock
        annotations = load_annotations(json_filepath)
        
        # Get or create the annotation entry and update it
        image_info = annotations.get(image_name, {})
        image_info['image_path'] = image_path
        image_info['tags'] = new_tags
        image_info['annotator'] = annotator
        annotations[image_name] = image_info
        
        # Write the modified data back to the file
        with open(json_filepath, 'w', encoding='utf-8') as f:
            json.dump(annotations, f, indent=4, ensure_ascii=False)
            
        return annotations

def filter_images_by_tag(image_files: List[str], annotations: Dict[str, Any], filter_tag: str) -> List[str]:
    """
    根据标签筛选图片列表
    """
    if filter_tag == "全部":
        return image_files
    elif filter_tag == "未标注":
        # 返回未标注或标注为unlabeled的图片
        filtered = []
        for image_path in image_files:
            image_name = os.path.basename(image_path)
            image_info = annotations.get(image_name, {})
            tags = image_info.get('tags', ['unlabeled'])
            if tags == ['unlabeled'] or not tags:
                filtered.append(image_path)
        return filtered
    else:
        # 返回包含指定标签的图片
        filtered = []
        for image_path in image_files:
            image_name = os.path.basename(image_path)
            image_info = annotations.get(image_name, {})
            tags = image_info.get('tags', [])
            if filter_tag in tags:
                filtered.append(image_path)
        return filtered

# --- Streamlit UI ---

st.set_page_config(layout="wide", page_title="图片标注工具")

st.title("图片标注工具 (Tag to Image)")

# --- Session State Initialization ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = False
if 'current_index' not in st.session_state:
    st.session_state.current_index = 0
if 'annotations' not in st.session_state:
    st.session_state.annotations = {}
if 'image_files' not in st.session_state:
    st.session_state.image_files = []
if 'filtered_image_files' not in st.session_state:
    st.session_state.filtered_image_files = []
if 'filter_tag' not in st.session_state:
    st.session_state.filter_tag = "全部"


# --- Sidebar for Configuration ---
with st.sidebar:
    st.header("⚙️ 配置")
    
    username = st.text_input("请输入你的名字", key="username")
    
    image_dir = st.text_input(
        "图片文件夹路径", 
        key="image_dir",
        help="输入存放图片的根目录，程序会自动递归查找所有图片。"
    )
    
    tags_input = st.text_input(
        "预设标签 (用逗号分隔)", 
        "标准系统框图,系统框图流向不确定,带基础电路图,父子图,串连省略,并联省略,其他,unlabel", 
        key="tags_input",
        help="输入所有可能的标签，用逗号隔开。"
    )
    
    start_index_input = st.number_input(
        "从第几张图片开始",
        min_value=1,
        value=1,
        step=1,
        key="start_index",
        help="设置加载后开始标注的第一张图片序号。"
    )

    json_path = st.text_input(
        "标签JSON文件路径", 
        os.path.join(os.getcwd(), ANNOTATIONS_FILE_DEFAULT), 
        key="json_path"
    )

    # 标签筛选选项
    if st.session_state.initialized:
        st.write("---")
        st.subheader("🔍 筛选选项")
        
        # 获取所有可用的标签
        available_tags = ["全部", "未标注"]
        if hasattr(st.session_state, 'tags'):
            available_tags.extend([tag for tag in st.session_state.tags if tag != 'unlabel'])
        
        # 标签筛选下拉框
        new_filter_tag = st.selectbox(
            "按标签筛选:",
            available_tags,
            index=available_tags.index(st.session_state.filter_tag) if st.session_state.filter_tag in available_tags else 0,
            key="filter_selectbox"
        )
        
        # 如果筛选条件改变，重新筛选图片
        if new_filter_tag != st.session_state.filter_tag:
            st.session_state.filter_tag = new_filter_tag
            st.session_state.filtered_image_files = filter_images_by_tag(
                st.session_state.image_files, 
                st.session_state.annotations, 
                st.session_state.filter_tag
            )
            st.session_state.current_index = 0  # 重置到第一张图片
            st.rerun()

    if st.button("🚀 加载图片和标签", use_container_width=True):
        if image_dir and os.path.isdir(image_dir) and tags_input and username:
            st.session_state.tags = [tag.strip() for tag in tags_input.split(',')]
            st.session_state.image_files = find_images(image_dir)
            st.session_state.annotations = load_annotations(json_path)
            
            if st.session_state.image_files:
                st.session_state.initialized = True
                
                # 初始化筛选后的图片列表
                st.session_state.filtered_image_files = filter_images_by_tag(
                    st.session_state.image_files, 
                    st.session_state.annotations, 
                    st.session_state.filter_tag
                )
                
                # Set start index based on user input
                num_images = len(st.session_state.filtered_image_files)
                start_index = st.session_state.start_index - 1 # Convert to 0-based index

                if 0 <= start_index < num_images:
                    st.session_state.current_index = start_index
                else:
                    st.session_state.current_index = 0
                    if num_images > 0:
                        st.warning(f"起始图片序号无效，将从第一张开始。有效范围是 1 到 {num_images}。")

                st.success(f"成功加载 {len(st.session_state.image_files)} 张图片！筛选后显示 {num_images} 张图片。")
            else:
                st.error("该目录下没有找到任何图片文件。")
                st.session_state.initialized = False
        else:
            st.error("请确保所有配置项都已正确填写，并且图片文件夹路径有效。")

    if st.session_state.initialized:
        st.header("📊 统计信息")

        # --- Statistics Calculation ---
        total_images = len(st.session_state.image_files)
        annotations = st.session_state.annotations
        tagged_count = 0
        annotator_stats = {}
        tag_stats = {}  # 新增：标签统计

        for ann in annotations.values():
            # Tagged if not default 'unlabeled' or empty
            if ann.get('tags') and ann.get('tags') != ['unlabeled']:
                tagged_count += 1
                annotator = ann.get('annotator', 'N/A')
                annotator_stats[annotator] = annotator_stats.get(annotator, 0) + 1
                
                # 统计每个标签的使用次数
                tags = ann.get('tags', [])
                for tag in tags:
                    if tag != 'unlabeled':  # 排除unlabeled标签
                        tag_stats[tag] = tag_stats.get(tag, 0) + 1
        
        tagged_percentage = (tagged_count / total_images) * 100 if total_images > 0 else 0
        st.metric("总图片数", f"{total_images}")
        st.metric("已标注数", f"{tagged_count} ({tagged_percentage:.1f}%)")

        # 显示标签统计
        if tag_stats:
            st.write("---")
            st.write("各标签使用统计:")
            df_tag_stats = pd.DataFrame(
                tag_stats.items(),
                columns=['标签', '使用次数']
            ).sort_values('使用次数', ascending=False).set_index('标签')
            
            # 添加百分比列
            df_tag_stats['百分比'] = (df_tag_stats['使用次数'] / tagged_count * 100).round(1).astype(str) + '%'
            
            st.dataframe(df_tag_stats, use_container_width=True)
            
            # 可选：添加条形图可视化
            st.write("标签使用分布图:")
            st.bar_chart(df_tag_stats['使用次数'])

        if annotator_stats:
            st.write("---")
            st.write("各标注员数量:")
            df_stats = pd.DataFrame(
                annotator_stats.items(),
                columns=['标注员', '数量']
            ).set_index('标注员')
            st.dataframe(df_stats, use_container_width=True)
        
        st.write("---")
        st.info(f"标签文件路径: {st.session_state.json_path}")


# --- Main Display Area ---

if not st.session_state.initialized:
    st.info("请在左侧侧边栏完成配置，然后点击'加载图片和标签'按钮开始。")
else:
    # 检查筛选后是否有图片
    if not st.session_state.filtered_image_files:
        st.warning(f"当前筛选条件 '{st.session_state.filter_tag}' 下没有找到任何图片。")
        st.info("请尝试更改筛选条件或检查您的标注数据。")
    else:
        # --- Navigation and Progress ---
        total_filtered_images = len(st.session_state.filtered_image_files)
        total_all_images = len(st.session_state.image_files)
        
        st.progress((st.session_state.current_index + 1) / total_filtered_images)
        
        # 显示当前筛选状态
        if st.session_state.filter_tag == "全部":
            st.write(f"#### 图片 {st.session_state.current_index + 1} / {total_filtered_images}")
        else:
            st.write(f"#### 图片 {st.session_state.current_index + 1} / {total_filtered_images} (筛选: {st.session_state.filter_tag})")
            st.caption(f"总图片数: {total_all_images} | 筛选后: {total_filtered_images}")

        # --- Get current image info ---
        current_image_path = st.session_state.filtered_image_files[st.session_state.current_index]
        image_name = os.path.basename(current_image_path)
        
        image_info = st.session_state.annotations.get(image_name, {})
        current_tags = image_info.get('tags', ['unlabeled']) # Default to unlabeled
        annotator = image_info.get('annotator', 'N/A')

        # --- Display Image and Tags ---
        col1, col2 = st.columns(2)

        with col1:
            st.image(current_image_path, use_column_width=True)

        with col2:
            st.write("##### **当前标签**")
            st.info(f"**标注人:** {annotator}")
            st.info(f"**标签:** {', '.join(current_tags)}")
            st.write("---")
            
            st.write("##### **点击按钮添加或移除标签**")
            # --- Tagging Buttons ---
            for tag in st.session_state.tags:
                is_selected = tag in current_tags and 'unlabeled' not in current_tags
                button_type = "primary" if is_selected else "secondary"
                
                if st.button(tag, key=f"tag_{tag}", use_container_width=True, type=button_type):
                    # Determine the new set of tags
                    new_tags = list(current_tags)
                    if 'unlabeled' in new_tags:
                        new_tags = [tag]
                    elif tag in new_tags:
                        new_tags.remove(tag)
                        if not new_tags:
                            new_tags = ['unlabeled']
                    else:
                        new_tags.append(tag)

                    # Safely update the annotation file
                    try:
                        updated_annotations = safe_update_annotation(
                            st.session_state.json_path,
                            image_name,
                            current_image_path,
                            new_tags,
                            st.session_state.username
                        )
                        st.session_state.annotations = updated_annotations
                        
                        # 重新筛选图片列表（因为标签改变可能影响筛选结果）
                        old_filtered_count = len(st.session_state.filtered_image_files)
                        st.session_state.filtered_image_files = filter_images_by_tag(
                            st.session_state.image_files, 
                            st.session_state.annotations, 
                            st.session_state.filter_tag
                        )
                        new_filtered_count = len(st.session_state.filtered_image_files)
                        
                        # 如果当前图片不再符合筛选条件，调整索引
                        if current_image_path not in st.session_state.filtered_image_files:
                            if st.session_state.current_index >= new_filtered_count:
                                st.session_state.current_index = max(0, new_filtered_count - 1)
                        
                        st.rerun()
                    except TimeoutError:
                        st.error("无法保存标签，文件正被其他用户使用。请稍后重试。")

            st.write("---")
            if st.button("🗑️ 删除当前标签", use_container_width=True, type="secondary"):
                try:
                    updated_annotations = safe_update_annotation(
                        st.session_state.json_path,
                        image_name,
                        current_image_path,
                        ['unlabeled'], # Reset tags
                        st.session_state.username
                    )
                    st.session_state.annotations = updated_annotations
                    
                    # 重新筛选图片列表
                    st.session_state.filtered_image_files = filter_images_by_tag(
                        st.session_state.image_files, 
                        st.session_state.annotations, 
                        st.session_state.filter_tag
                    )
                    
                    # 如果当前图片不再符合筛选条件，调整索引
                    if current_image_path not in st.session_state.filtered_image_files:
                        if st.session_state.current_index >= len(st.session_state.filtered_image_files):
                            st.session_state.current_index = max(0, len(st.session_state.filtered_image_files) - 1)
                    
                    st.rerun()
                except TimeoutError:
                    st.error("无法删除标签，文件正被其他用户使用。请稍后重试。")

        st.write("---")
        
        # --- Navigation Buttons ---
        nav_cols = st.columns([1, 1, 6])
        
        def go_prev():
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1

        def go_next():
            if st.session_state.current_index < len(st.session_state.filtered_image_files) - 1:
                st.session_state.current_index += 1
                
        nav_cols[0].button("⬅️ 上一张", on_click=go_prev, use_container_width=True)
        nav_cols[1].button("下一张 ➡️", on_click=go_next, use_container_width=True)
        
        st.caption("提示：你可以通过点击已选中的标签来取消它。")
        st.caption("关于快捷键：Streamlit本身不直接支持全局快捷键。最可靠的方式是使用鼠标点击按钮。")

# This is a HACK to try and get keyboard shortcuts. It's not guaranteed to work well.
# It injects javascript into the page to listen for keypresses.
from streamlit.components.v1 import html
html(f"""
<script>
const doc = window.parent.document;

const findAndClickButtonByText = (text) => {{
    const buttons = doc.querySelectorAll('button');
    for (const button of buttons) {{
        if (button.textContent.trim() === text) {{
            button.click();
            return;
        }}
    }};
}};

doc.addEventListener('keydown', function(e) {{
    // Prevent shortcuts from firing when user is typing in an input
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
        return;
    }}
    
    const key = e.key.toLowerCase();

    switch (key) {{
        case 'arrowleft':
        case 'a':
            findAndClickButtonByText('⬅️ 上一张');
            break;
        case 'arrowright':
        case 'd':
            findAndClickButtonByText('下一张 ➡️');
            break;
    }}
}});
</script>
""", height=0, width=0)