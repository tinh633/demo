import time

class CSP:
    def __init__(self, regions, neighbors, colors, callback=None, control=None):
        self.regions = regions
        self.neighbors = neighbors
        self.colors = colors
        self.callback = callback
        self.control = control
        # Thêm 2 biến đếm để so sánh hiệu năng
        self.steps = 0
        self.backtracks = 0

    def _wait(self):
        while self.control['paused'] and not self.control['stop']:
            time.sleep(0.05)
        return self.control['stop']

    # ==========================================
    # CÁC HÀM HEURISTIC TỐI ƯU
    # ==========================================
    def select_unassigned_variable(self, assignment, domains):
        """
        Kết hợp MRV (Minimum Remaining Values) và Degree Heuristic.
        - Chọn vùng có ít lựa chọn màu nhất (MRV). 
        - Nếu có nhiều vùng cùng số lượng lựa chọn, ưu tiên vùng có nhiều láng giềng chưa tô màu nhất (Degree).
        """
        unassigned = [x for x in self.regions if x not in assignment]
        
        def degree(var):
            return sum(1 for n in self.neighbors[var] if n not in assignment)
        
        # Sắp xếp theo MRV tăng dần, sau đó theo Degree giảm dần (thêm dấu -)
        return min(unassigned, key=lambda x: (len(domains[x]), -degree(x)))

    def order_domain_values(self, var, assignment, domains):
        """
        LCV (Least Constraining Value)
        - Ưu tiên chọn màu gây ra ít sự ràng buộc (ít làm giảm lựa chọn) nhất cho các láng giềng xung quanh.
        """
        def count_conflicts(color):
            conflicts = 0
            for n in self.neighbors[var]:
                if n not in assignment and color in domains[n]:
                    conflicts += 1
            return conflicts
        
        return sorted(domains[var], key=count_conflicts)

    def is_safe(self, var, color, assignment):
        """Kiểm tra xem gán màu có bị trùng láng giềng không (dành cho Backtracking cơ bản)"""
        for n in self.neighbors[var]:
            if n in assignment and assignment[n] == color:
                return False
        return True


    # ==========================================
    # THUẬT TOÁN 1: STANDARD BACKTRACKING
    # ==========================================
    def solve_backtracking(self, assignment, domains):
        if self.control['stop']:
            return False

        if len(assignment) == len(self.regions):
            return True

        # Chọn biến theo MRV + Degree Heuristic
        r = self.select_unassigned_variable(assignment, domains)

        # Chọn giá trị màu theo LCV
        for c in self.order_domain_values(r, assignment, domains):
            if self.control['stop']:
                return False

            if self.is_safe(r, c, assignment):
                self.steps += 1
                assignment[r] = c

                if self.callback:
                    if self._wait():
                        return False
                    self.callback(r, c)

                if self.solve_backtracking(assignment, domains):
                    return True

                # Nhánh này sai, phải quay lui
                del assignment[r]
                self.backtracks += 1

        return False


    # ==========================================
    # THUẬT TOÁN 2: FORWARD CHECKING (FC)
    # ==========================================
    def solve_fc(self, assignment, domains):
        if self.control['stop']:
            return False

        if len(assignment) == len(self.regions):
            return True

        # Chọn biến theo MRV + Degree Heuristic
        r = self.select_unassigned_variable(assignment, domains)

        # Chọn giá trị màu theo LCV
        for c in self.order_domain_values(r, assignment, domains):
            if self.control['stop']:
                return False

            # Ghi nhận 1 bước thử gán màu
            self.steps += 1
            assignment[r] = c

            if self.callback:
                if self._wait():
                    return False
                self.callback(r, c)

            # --- FORWARD CHECKING ---
            local_domains = {k: v[:] for k, v in domains.items()}
            fc_valid = True
            
            for n in self.neighbors[r]:
                if n not in assignment:
                    if c in local_domains[n]:
                        local_domains[n].remove(c)
                        if len(local_domains[n]) == 0: # Phát hiện ngõ cụt sớm
                            fc_valid = False
                            break
            
            if fc_valid:
                if self.solve_fc(assignment, local_domains):
                    return True

            # Nhánh này sai, phải quay lui
            del assignment[r]
            self.backtracks += 1

        return False


    # ==========================================
    # THUẬT TOÁN 3: AC-3 (MAC)
    # ==========================================
    def solve_ac3(self, assignment, domains):
        if self.control['stop']:
            return False

        if len(assignment) == len(self.regions):
            return True

        # Chọn biến theo MRV + Degree Heuristic
        r = self.select_unassigned_variable(assignment, domains)

        # Chọn giá trị màu theo LCV
        for c in self.order_domain_values(r, assignment, domains):
            if self.control['stop']:
                return False

            # Ghi nhận 1 bước thử gán màu
            self.steps += 1
            assignment[r] = c

            if self.callback:
                if self._wait():
                    return False
                self.callback(r, c)

            local_domains = {k: v[:] for k, v in domains.items()}
            # Gán màu c cho r nghĩa là domain của r bây giờ chỉ còn [c]
            local_domains[r] = [c]
            
            # Khởi tạo hàng đợi AC-3 với các cung (neighbor -> r)
            queue = [(n, r) for n in self.neighbors[r] if n not in assignment]
            
            # Chạy lan truyền ràng buộc AC-3
            if self._ac3_propagate(queue, local_domains, assignment):
                if self.solve_ac3(assignment, local_domains):
                    return True

            # Nhánh này sai, phải quay lui
            del assignment[r]
            self.backtracks += 1

        return False

    def _ac3_propagate(self, queue, domains, assignment):
        while queue:
            xi, xj = queue.pop(0)
            if self._revise(domains, xi, xj):
                if not domains[xi]:
                    return False # Hết lựa chọn màu (Domain Wipeout)
                
                # Nếu domain của xi bị thay đổi, phải kiểm tra lại láng giềng của xi
                for xk in self.neighbors[xi]:
                    if xk != xj and xk not in assignment:
                        queue.append((xk, xi))
        return True

    def _revise(self, domains, xi, xj):
        revised = False
        for x in domains[xi][:]:
            # Bài toán tô màu: xi phải khác xj.
            if len(domains[xj]) == 1 and domains[xj][0] == x:
                domains[xi].remove(x)
                revised = True
        return revised