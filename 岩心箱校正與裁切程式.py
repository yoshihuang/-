import cv2
import numpy as np
import os
import glob
import tkinter as tk
from tkinter import filedialog

# 全域變數，用於儲存滑鼠點擊的座標與縮放比例
points = []
scaling_factor = 1.0

def mouse_handler(event, x, y, flags, param):
    """處理滑鼠點擊事件的函數"""
    global points
    if event == cv2.EVENT_LBUTTONDOWN:
        # 記錄點擊位置
        points.append((x, y))
        # 在畫面上畫出紅點標示
        cv2.circle(param, (x, y), 5, (0, 0, 255), -1)
        cv2.imshow("Core Box Cropper", param)

def process_image(image_path, output_dir):
    """處理單張影像的校正與裁切"""
    global points, scaling_factor
    points = []
    
    # 讀取原始影像 (改用 imdecode 支援中文資料夾路徑讀取)
    img = cv2.imdecode(np.fromfile(image_path, dtype=np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        print(f"無法讀取影像: {image_path}")
        return

    # 為了讓高解析度照片能完整顯示在螢幕上，縮小顯示比例
    display_img = img.copy()
    height, width = display_img.shape[:2]
    max_dim = 900 # 視窗最大寬度或高度設定為 900 像素
    
    if max(height, width) > max_dim:
        scaling_factor = max_dim / float(max(height, width))
        display_img = cv2.resize(display_img, None, fx=scaling_factor, fy=scaling_factor)
    else:
        scaling_factor = 1.0

    print(f"\n正在處理: {image_path}")
    print("請依序點擊岩心箱的四個角落：")
    print("1. 左上角 (Top-Left)")
    print("2. 右上角 (Top-Right)")
    print("3. 右下角 (Bottom-Right)")
    print("4. 左下角 (Bottom-Left)")
    print("提示：如果不小心點錯，請按 'r' 鍵重設，或者按 'q' 鍵跳過這張圖片。")

    cv2.imshow("Core Box Cropper", display_img)
    cv2.setMouseCallback("Core Box Cropper", mouse_handler, display_img)

    while True:
        key = cv2.waitKey(1) & 0xFF
        # 如果收集到 4 個點，稍微等待一下就進行處理
        if len(points) == 4:
            cv2.waitKey(500) # 停頓 0.5 秒讓使用者看到最後一個點
            break
        # 按 'r' 重新點擊
        elif key == ord('r'):
            print("重設點擊座標，請重新點擊 4 個角落。")
            points = []
            display_img = cv2.resize(img.copy(), None, fx=scaling_factor, fy=scaling_factor)
            cv2.imshow("Core Box Cropper", display_img)
            cv2.setMouseCallback("Core Box Cropper", mouse_handler, display_img)
        # 按 'q' 跳過
        elif key == ord('q'):
            print("跳過此影像。")
            cv2.destroyAllWindows()
            return

    cv2.destroyAllWindows()

    if len(points) == 4:
        # 將顯示視窗上的座標，轉換回原始高解析度影像的真實座標
        orig_points = np.array([(int(p[0] / scaling_factor), int(p[1] / scaling_factor)) for p in points], dtype=np.float32)

        # 計算新影像的寬度 (取上邊和下邊長度的最大值)
        width_A = np.sqrt(((orig_points[2][0] - orig_points[3][0]) ** 2) + ((orig_points[2][1] - orig_points[3][1]) ** 2))
        width_B = np.sqrt(((orig_points[1][0] - orig_points[0][0]) ** 2) + ((orig_points[1][1] - orig_points[0][1]) ** 2))
        max_width = max(int(width_A), int(width_B))

        # 計算新影像的高度 (取左邊和右邊長度的最大值)
        height_A = np.sqrt(((orig_points[1][0] - orig_points[2][0]) ** 2) + ((orig_points[1][1] - orig_points[2][1]) ** 2))
        height_B = np.sqrt(((orig_points[0][0] - orig_points[3][0]) ** 2) + ((orig_points[0][1] - orig_points[3][1]) ** 2))
        max_height = max(int(height_A), int(height_B))

        # 設定目標(裁切後)的四個端點座標，呈現完美的正面矩形
        dst_points = np.array([
            [0, 0],
            [max_width - 1, 0],
            [max_width - 1, max_height - 1],
            [0, max_height - 1]
        ], dtype=np.float32)

        # 計算透視變換矩陣並進行影像轉換 (Perspective Transform)
        M = cv2.getPerspectiveTransform(orig_points, dst_points)
        warped = cv2.warpPerspective(img, M, (max_width, max_height))

        # 儲存至使用者選擇的輸出資料夾，並處理中文檔名儲存問題
        filename = os.path.basename(image_path)
        name, ext = os.path.splitext(filename)
        out_path = os.path.join(output_dir, f"{name}_正面裁切{ext}")
        
        # 使用 imencode 與 tofile 支援中文檔名寫入 (cv2.imwrite 遇到中文會失效)
        is_success, im_buf_arr = cv2.imencode(ext, warped)
        if is_success:
            im_buf_arr.tofile(out_path)
            print(f"✅ 成功儲存: {out_path}")
        else:
            print(f"❌ 儲存影像時發生錯誤: {out_path}")

def main():
    print("=== 岩心箱正面校正與裁切程式 ===")
    
    # 建立 tkinter 視窗 (隱藏主視窗)
    root = tk.Tk()
    # 將視窗推到最上層，避免被其他視窗擋住
    root.attributes('-topmost', True) 
    root.withdraw()
    
    # 1. 讓使用者選擇「來源照片」資料夾
    print("請在彈出的視窗中，選擇『來源照片』所在的資料夾...")
    input_dir = filedialog.askdirectory(title="1/2: 選擇「來源照片」資料夾")
    
    if not input_dir:
        print("您沒有選擇來源資料夾，程式結束。")
        return
    print(f"📁 來源資料夾: {input_dir}")
    
    # 2. 讓使用者選擇「輸出」資料夾
    print("請在彈出的視窗中，選擇要『儲存裁切後影像』的資料夾...")
    output_dir = filedialog.askdirectory(title="2/2: 選擇「輸出儲存」資料夾")
    
    if not output_dir:
        print("您沒有選擇輸出資料夾，程式結束。")
        return
        
    print(f"✅ 裁切後的影像將會儲存至: {output_dir}")
    
    # 抓取來源資料夾內所有的 jpg 圖片 (加入 os.path.join 對應所選路徑，大小寫皆支援)
    search_patterns = [
        os.path.join(input_dir, "*.jpg"),
        os.path.join(input_dir, "*.jpeg"),
        os.path.join(input_dir, "*.JPG"),
        os.path.join(input_dir, "*.JPEG")
    ]
    
    image_files = []
    for pattern in search_patterns:
        image_files.extend(glob.glob(pattern))
    
    # 過濾掉已經處理過(帶有_正面裁切)的圖片，避免同資料夾輸出時發生無限迴圈
    image_files = [f for f in image_files if "_正面裁切" not in f]

    if not image_files:
        print(f"在來源資料夾 {input_dir} 中找不到未處理的 .jpg 圖片檔案。")
        return

    print(f"共找到 {len(image_files)} 張圖片準備處理。")
    
    for img_path in image_files:
        process_image(img_path, output_dir)
        
    print("\n🎉 所有圖片處理完畢！")

if __name__ == "__main__":
    main()