import cv2
import numpy as np

class Map:
    def __init__(self, path):
        # 1. ĐỌC ẢNH GỐC
        img_array = np.fromfile(path, np.uint8)
        self.original = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if self.original is None:
            raise ValueError(f"Không thể đọc được ảnh từ đường dẫn: {path}")

        gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)

        # 2. TỐI ƯU HÓA TÌM VIỀN CHO BẢN ĐỒ VIỀN TRẮNG/MỎNG
        # Giảm cực mạnh độ blur để không làm mất các đường ranh giới tỉnh mỏng
        blurred = cv2.GaussianBlur(gray, (3, 3), 0)

        # Hạ ngưỡng dò Canny xuống rất thấp để nhạy hơn với các viền mờ, độ tương phản thấp
        edges = cv2.Canny(blurred, 10, 50)

        # Dùng kernel nhỏ nối viền để đóng kín các tỉnh, tránh làm mất các tỉnh diện tích nhỏ (như Bắc Ninh, Hà Nam)
        kernel_dilate = np.ones((2, 2), np.uint8)
        th = cv2.dilate(edges, kernel_dilate, iterations=2)

        contours, _ = cv2.findContours(th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        # 3. TRÍCH XUẤT CÁC VÙNG (REGIONS)
        self.regions = {}
        for c in contours:
            # Tăng diện tích tối thiểu lọc nhiễu lặt vặt
            if cv2.contourArea(c) < 50: 
                continue
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [c], -1, 255, -1)
            self.regions[len(self.regions)] = mask

        # Xóa vùng bao phủ lớn nhất (thường là background biển/nền xám ngoài cùng)
        if len(self.regions) > 0:
            areas = [(r, np.sum(mask)) for r, mask in self.regions.items()]
            largest = max(areas, key=lambda x: x[1])[0]
            del self.regions[largest]

        # Đánh lại index thứ tự các tỉnh
        self.regions = {i: m for i, m in enumerate(self.regions.values())}
        
        # In ra console để kiểm tra độ chính xác (Hy vọng sẽ ra con số quanh mức 63 tỉnh)
        print("Total Regions detected:", len(self.regions))

        # 4. TÍNH TOÁN TỌA ĐỘ TRUNG TÂM ĐỂ CHÈN SỐ
        self.centers = {}
        for r, mask in self.regions.items():
            M = cv2.moments(mask)
            if M["m00"] != 0:
                cX = int(M["m10"] / M["m00"])
                cY = int(M["m01"] / M["m00"])
            else:
                coords = np.argwhere(mask == 255)
                if len(coords) > 0:
                    cY, cX = coords[0]
                else:
                    cX, cY = 0, 0
            self.centers[r] = (cX - 5, cY + 5)

        # 5. CHUẨN BỊ MẶT NẠ ĐỔ MÀU VÀ TẠO VIỀN ĐEN
        self.draw_masks = {}
        for r, mask in self.regions.items():
            # Xói mòn mặt nạ một chút (erode) để chừa không gian trống cho đường viền
            eroded_mask = cv2.erode(mask, np.ones((2,2), np.uint8), iterations=1)
            self.draw_masks[r] = (eroded_mask == 255)

        # Sử dụng chính đường viền Canny đã xử lý để làm mặt nạ viền đen nhân tạo
        self.edge_mask = (th == 255)

        # 6. XÂY DỰNG DANH SÁCH LÁNG GIỀNG BẰNG ĐỘ CHỒNG LẤP (OVERLAP)
        self.neighbors = {r: [] for r in self.regions}
        kernel_neighbor = np.ones((5, 5), np.uint8)

        for r1 in self.regions:
            for r2 in self.regions:
                if r1 >= r2:
                    continue
                dilated = cv2.dilate(self.regions[r1], kernel_neighbor, iterations=3)
                overlap = cv2.bitwise_and(dilated, self.regions[r2])
                if np.any(overlap):
                    self.neighbors[r1].append(r2)
                    self.neighbors[r2].append(r1)

    def draw(self, assignment):
        base = self.original.copy()
        
        # Đổ màu vào các tỉnh thành
        for r, color in assignment.items():
            base[self.draw_masks[r]] = color
                
        # Phủ viền đen cứng lên toàn bộ ranh giới để tách biệt rõ ràng các tỉnh
        base[self.edge_mask] = (0, 0, 0)
        
        # Chèn số
        for r, center in self.centers.items():
            cv2.putText(base, str(r), center, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(base, str(r), center, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
        
        return base