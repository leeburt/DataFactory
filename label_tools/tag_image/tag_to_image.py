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

    if st.button("🚀 加载图片和标签", use_container_width=True):
        if image_dir and os.path.isdir(image_dir) and tags_input and username:
            st.session_state.tags = [tag.strip() for tag in tags_input.split(',')]
            st.session_state.image_files = find_images(image_dir)
            st.session_state.annotations = load_annotations(json_path)
            
            if st.session_state.image_files:
                st.session_state.initialized = True
                
                # Set start index based on user input
                num_images = len(st.session_state.image_files)
                start_index = st.session_state.start_index - 1 # Convert to 0-based index

                if 0 <= start_index < num_images:
                    st.session_state.current_index = start_index
                else:
                    st.session_state.current_index = 0
                    st.warning(f"起始图片序号无效，将从第一张开始。有效范围是 1 到 {num_images}。")

                st.success(f"成功加载 {num_images} 张图片！")
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

        for ann in annotations.values():
            # Tagged if not default 'unlabeled' or empty
            if ann.get('tags') and ann.get('tags') != ['unlabeled']:
                tagged_count += 1
                annotator = ann.get('annotator', 'N/A')
                annotator_stats[annotator] = annotator_stats.get(annotator, 0) + 1
        
        tagged_percentage = (tagged_count / total_images) * 100 if total_images > 0 else 0
        st.metric("总图片数", f"{total_images}")
        st.metric("已标注数", f"{tagged_count} ({tagged_percentage:.1f}%)")

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
    st.info("请在左侧侧边栏完成配置，然后点击“加载图片和标签”按钮开始。")
else:
    # --- Navigation and Progress ---
    total_images = len(st.session_state.image_files)
    st.progress((st.session_state.current_index + 1) / total_images)
    st.write(f"#### 图片 {st.session_state.current_index + 1} / {total_images}")

    # --- Get current image info ---
    current_image_path = st.session_state.image_files[st.session_state.current_index]
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
        if st.session_state.current_index < len(st.session_state.image_files) - 1:
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
        }}
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