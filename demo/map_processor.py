import cv2
import numpy as np

class Map:
    def __init__(self, path):
        self.original = cv2.imread(path)

        gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5,5), 0)

        edges = cv2.Canny(gray, 30, 100)
        kernel_dilate = np.ones((3,3), np.uint8)
        th = cv2.dilate(edges, kernel_dilate, iterations=2)

        contours, _ = cv2.findContours(th, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        self.regions = {}
        for c in contours:
            # Đã giảm ngưỡng từ 20 xuống 5 để bắt được các đảo nhỏ
            if cv2.contourArea(c) < 5: 
                continue
            mask = np.zeros(gray.shape, np.uint8)
            cv2.drawContours(mask, [c], -1, 255, -1)
            self.regions[len(self.regions)] = mask

        if len(self.regions) > 0:
            areas = [(r, np.sum(mask)) for r, mask in self.regions.items()]
            largest = max(areas, key=lambda x: x[1])[0]
            del self.regions[largest]

        self.regions = {i: m for i, m in enumerate(self.regions.values())}

        print("Total Regions detected:", len(self.regions))

        # -------- Xây dựng danh sách láng giềng --------
        self.neighbors = {r: [] for r in self.regions}
        kernel_neighbor = np.ones((5,5), np.uint8)

        for r1 in self.regions:
            for r2 in self.regions:
                if r1 >= r2:
                    continue
                dilated = cv2.dilate(self.regions[r1], kernel_neighbor, iterations=4)
                overlap = cv2.bitwise_and(dilated, self.regions[r2])
                if np.any(overlap):
                    self.neighbors[r1].append(r2)
                    self.neighbors[r2].append(r1)

    def draw(self, assignment):
        base = self.original.copy()
        
        # Khởi tạo kernel để giãn nở mặt nạ màu
        kernel = np.ones((3, 3), np.uint8)
        
        for r, mask in self.regions.items():
            if r in assignment:
                # Giãn nở mặt nạ 2 lần để lấp kín khoảng trắng sát viền
                full_mask = cv2.dilate(mask, kernel, iterations=2)
                base[full_mask == 255] = assignment[r]
                
        # Khôi phục lại đường nét đen gốc để bản đồ sắc nét
        gray = cv2.cvtColor(self.original, cv2.COLOR_BGR2GRAY)
        _, original_edges = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        base[original_edges == 0] = (0, 0, 0)
        
        return base