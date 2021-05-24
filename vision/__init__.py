import cv2
import numpy as np
# from cv2 import cv


class HsvFilter:
    def __init__(self, h_min=None, h_max=None, s_min=None, s_max=None, v_min=None, v_max=None, s_add=None, s_sub=None, v_add=None, v_sub=None):
        self.h_min = h_min
        self.h_max = h_max
        self.s_min = s_min
        self.s_max = s_max
        self.v_min = v_min
        self.v_max = v_max
        self.s_add = s_add
        self.s_sub = s_sub
        self.v_add = v_add
        self.v_sub = v_sub


class EdgeFilter:
    def __init__(self, kernel_size=None, erode_iter=None, dilate_iter=None, canny1=None, canny2=None):
        self.kernel_size = kernel_size
        self.erode_iter = erode_iter
        self.dilate_iter = dilate_iter
        self.canny1 = canny1
        self.canny2 = canny2


class CVWrapper:

    @staticmethod
    def get_points(rectangles):
        return {(int(x + w / 2), int(y + h / 2)) for x, y, w, h in rectangles}

    @staticmethod
    def find_points(observer, target, threshold, max_results):
        return CVWrapper.get_points(CVWrapper.find(observer, target, threshold, max_results))

    @staticmethod
    def apply_hsv(img, hsv):
        def channels_shift(c, v):
            if v > 0:
                lim = 255 - v
                c[c >= lim] = 255
                c[c < lim] += v
            elif v < 0:
                v = -v
                lim = v
                c[c <= lim] = 0
                c[c > lim] -= v
            return c

        hsv_img = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        h, s, v = cv2.split(hsv_img)
        s = channels_shift(s, hsv.s_add)
        s = channels_shift(s, -hsv.s_sub)
        v = channels_shift(v, hsv.v_add)
        v = channels_shift(v, -hsv.v_sub)
        hsv_img = cv2.merge([h, s, v])

        _min_ = np.array([hsv.h_min, hsv.s_min, hsv.v_min])
        _max_ = np.array([hsv.h_max, hsv.s_max, hsv.v_max])
        mask = cv2.inRange(hsv_img, _min_, _max_)
        result = cv2.bitwise_and(hsv_img, hsv_img, mask=mask)
        return cv2.cvtColor(result, cv2.COLOR_HSV2BGR)

    # @staticmethod
    # def init_gui_window(self):
    #     cv2.namedWindow('Filter GUI', cv2.WINDOW_NORMAL)
    #     cv2.resizeWindow('Filter GUI', width=320, height=700)
    #     cv2.setWindowProperty()
    #
    #     def handler(pos):
    #         pass
    #
    #     cv2.createTrackbar('h_min', 'Filter GUI', 0, 179, handler)
    #     cv2.createTrackbar('h_max', 'Filter GUI', 0, 179, handler)
    #     cv2.createTrackbar('s_min', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('s_max', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('v_min', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('v_max', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('s_add', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('s_sub', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('v_add', 'Filter GUI', 0, 255, handler)
    #     cv2.createTrackbar('v_sub', 'Filter GUI', 0, 255, handler)
    #
    #     cv2.setTrackbarPos('h_max', 'Filter GUI', 179)
    #     cv2.setTrackbarPos('s_max', 'Filter GUI', 255)
    #     cv2.setTrackbarPos('v_max', 'Filter GUI', 255)
    #
    #     cv2.createTrackbar('kernel_size', 'Filter GUI', 1, 30, handler)
    #     cv2.createTrackbar('erode_iter', 'Filter GUI', 1, 5, handler)
    #     cv2.createTrackbar('dilate_iter', 'Filter GUI', 1, 5, handler)
    #     cv2.createTrackbar('canny1', 'Filter GUI', 0, 200, handler)
    #     cv2.createTrackbar('canny2', 'Filter GUI', 0, 500, handler)
    #
    #     cv2.setTrackbarPos('kernel_size', 'Filter GUI', 5)
    #     cv2.setTrackbarPos('canny1', 'Filter GUI', 100)
    #     cv2.setTrackbarPos('canny2', 'Filter GUI', 200)

    @staticmethod
    def find(observer, target, threshold, max_results):
        target_wh = (target.shape[1], target.shape[0])
        result = cv2.matchTemplate(observer, target, cv2.TM_CCOEFF_NORMED)
        good_cases = list(zip(*np.where(result >= threshold)[::-1]))

        if not good_cases:
            return np.array([], dtype=np.int32).reshape(0, 4)

        rectangles = []
        for case in good_cases:
            rect = [case[0], case[1], target_wh[0], target_wh[1]]
            rectangles.append(rect)
            rectangles.append(rect)

        rectangles, w = cv2.groupRectangles(np.array(rectangles).tolist(), groupThreshold=1, eps=0.5)
        return rectangles[:max_results] if len(rectangles) > max_results else rectangles