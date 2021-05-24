import numpy as np
import win32con
import win32con as wcon
import win32ui as wui
import win32gui as wgui
import win32api as wapi
import win32process as wproc
import psutil
import ctypes

from macro import Player

class WindowCapture:
    @staticmethod
    def callback(hwnd, hwnds):
        if wgui.IsWindowVisible(hwnd) and wgui.IsWindowEnabled(hwnd):
            # hwnds[wgui.GetClassName(hwnd)] = hwnd
            hwnds[wgui.GetWindowText(hwnd)] = hwnd
        return True

    def __init__(self, window_name, sub_window):
        self.window_name = window_name
        self.sub_window = sub_window

        self.hwnd = wgui.FindWindow(None, window_name)
        # self.hwndEx = wgui.FindWindowEx(self.hwnd, None, sub_window, None)
        if sub_window != '':
            self.hwndEx = WindowCapture.get_window_subs(self.hwnd)[sub_window]
        else:
            self.hwndEx = self.hwnd

        self.win = wui.CreateWindowFromHandle(self.hwndEx)
        #self.hwndEx = self.win.GetSafeHwnd()
        #self.hwnd = None
        #if self.hwnd is None:
        # hwnds = {}
        # wgui.EnumWindows(self.callback, hwnds)
        # print(hwnds)

        # self.wh = wui.CreateWindowFromHandle(hwnds[window_name])
        # self.hwnd = self.wh.GetSafeHwnd()  # if not self.hwnd else None
        # else:
        #     self.wh = wui.CreateW(self.hwnd)

        if not self.hwndEx or not self.hwnd:
            raise Exception(f'Window not found!')
        wt_rect = WindowCapture.get_window_rect(self.hwndEx)
        window_rect = wgui.GetWindowRect(self.hwndEx)

        self.x = wt_rect[0]
        self.y = wt_rect[1]

        self.offset_x = wt_rect[0]-window_rect[0]
        self.offset_y = wt_rect[1]-window_rect[1]

        # self.wh.ReleaseCapture()

    def focus(self):
        wgui.SetForegroundWindow(self.hwnd)

    def mouse_move(self, pos_long):
        self.win.SendMessage(wcon.WM_MOUSEMOVE, 0, pos_long)

    def press_left(self, pos_long):
        self.win.SendMessage(wcon.WM_LBUTTONDOWN, wcon.MK_LBUTTON, pos_long) # self.hwndEx,

    def release_left(self, pos_long):
        self.win.SendMessage(wcon.WM_LBUTTONUP, 0, pos_long) # self.hwndEx,

    def press_right(self, pos_long):
        self.win.SendMessage(wcon.WM_LBUTTONDOWN, wcon.MK_LBUTTON, pos_long) # self.hwndEx,

    def release_right(self, pos_long):
        self.win.SendMessage(wcon.WM_LBUTTONUP, 0, pos_long) # self.hwndEx,

    @staticmethod
    def s_mouse_move(pos):
        wapi.mouse_event(wcon.MOUSEEVENTF_MOVE | wcon.MOUSEEVENTF_ABSOLUTE,
                         int(pos[0] * Player.SCREEN_SCALE_X),
                         int(pos[1] * Player.SCREEN_SCALE_Y),
                         0, 0)

    @staticmethod
    def s_press_left(pos):
        wapi.mouse_event(wcon.MOUSEEVENTF_MOVE | wcon.MOUSEEVENTF_ABSOLUTE | wcon.MOUSEEVENTF_LEFTDOWN,
                         int(pos[0] * Player.SCREEN_SCALE_X),
                         int(pos[1] * Player.SCREEN_SCALE_Y),
                         0, 0)

    @staticmethod
    def s_release_left(pos):
        wapi.mouse_event(wcon.MOUSEEVENTF_MOVE | wcon.MOUSEEVENTF_ABSOLUTE | wcon.MOUSEEVENTF_LEFTUP,
                         int(pos[0] * Player.SCREEN_SCALE_X),
                         int(pos[1] * Player.SCREEN_SCALE_Y),
                         0, 0)

    @staticmethod
    def s_press_right(pos):
        wapi.mouse_event(wcon.MOUSEEVENTF_MOVE | wcon.MOUSEEVENTF_ABSOLUTE | wcon.MOUSEEVENTF_RIGHTDOWN,
                         int(pos[0] * Player.SCREEN_SCALE_X),
                         int(pos[1] * Player.SCREEN_SCALE_Y),
                         0, 0)

    @staticmethod
    def s_release_right(pos):
        wapi.mouse_event(wcon.MOUSEEVENTF_MOVE | wcon.MOUSEEVENTF_ABSOLUTE | wcon.MOUSEEVENTF_RIGHTUP,
                         int(pos[0] * Player.SCREEN_SCALE_X),
                         int(pos[1] * Player.SCREEN_SCALE_Y),
                         0, 0)

    def get_screen_pos(self, pos):
        return pos[0] + self.x, pos[1] + self.y

    def get_window_pos(self, pos):
        return pos[0] - self.x, pos[1] - self.y

    @staticmethod
    def s_as_long(pos):
        return wapi.MAKELONG(pos[0], pos[1])

    def get_screen_pos_as_long(self, pos):
        return wapi.MAKELONG(pos[0] + self.x, pos[1] + self.y)

    def get_window_pos_as_long(self, pos):
        return wapi.MAKELONG(pos[0] - self.x, pos[1] - self.y)

    def fast_capture(self, x, y, w, h):
        w_dc = wgui.GetWindowDC(self.hwndEx)
        dc_obj = wui.CreateDCFromHandle(w_dc)
        c_dc = dc_obj.CreateCompatibleDC()
        data_bit_map = wui.CreateBitmap()
        data_bit_map.CreateCompatibleBitmap(dc_obj, w, h)
        c_dc.SelectObject(data_bit_map)
        c_dc.BitBlt((0, 0), (w, h), dc_obj, (x+self.offset_x, y+self.offset_y), wcon.SRCCOPY)

        array = data_bit_map.GetBitmapBits(True)
        img = np.frombuffer(array, dtype='uint8')
        img.shape = (h, w, 4)
        img = img[:, :, :3]
        img = np.dstack((img, np.zeros((h, w), dtype=np.uint8) + 255))

        dc_obj.DeleteDC()
        c_dc.DeleteDC()
        wgui.ReleaseDC(self.hwndEx, w_dc)
        wgui.DeleteObject(data_bit_map.GetHandle())

        return img

    def fast_capture_center(self, x, y, w, h):
        return self.fast_capture(x - int(w / 2), y - int(h / 2), w, h)

    @staticmethod
    def window_list():
        def win_enum_handler(hwnd, ctx):
            if wgui.IsWindowVisible(hwnd):
                print(hex(hwnd), wgui.GetWindowText(hwnd))
        wgui.EnumWindows(win_enum_handler, None)

    @staticmethod
    def get_window_hwnd(window_name):
        return wgui.FindWindow(None, window_name)

    @staticmethod
    def get_window_rect(hwnd):
        dwmapi = ctypes.WinDLL("dwmapi")

        rect = ctypes.wintypes.RECT()
        WORD_TYPE = 9
        dwmapi.DwmGetWindowAttribute(ctypes.wintypes.HWND(hwnd), ctypes.wintypes.DWORD(WORD_TYPE),
                                     ctypes.byref(rect), ctypes.sizeof(rect))

        return rect.left, rect.top, rect.right, rect.bottom

    @staticmethod
    def s_fast_capture(hwnd, x, y, w, h):
        wt_rect = WindowCapture.get_window_rect(hwnd)
        window_rect = wgui.GetWindowRect(hwnd)

        wDC = wgui.GetWindowDC(hwnd)
        dcObj = wui.CreateDCFromHandle(wDC)
        cDC = dcObj.CreateCompatibleDC()
        dataBitMap = wui.CreateBitmap()
        dataBitMap.CreateCompatibleBitmap(dcObj, w, h)
        cDC.SelectObject(dataBitMap)
        cDC.BitBlt((0, 0), (w, h), dcObj, (x+(wt_rect[0]-window_rect[0]), y), wcon.SRCCOPY)
        # dataBitMap.SaveBitmapFile(cDC, "out.bmp")

        array = dataBitMap.GetBitmapBits(True)
        img = np.frombuffer(array, dtype='uint8')
        img.shape = (h, w, 4)
        img = img[:, :, :3]
        img = np.dstack((img, np.zeros((h, w), dtype=np.uint8) + 255))

        dcObj.DeleteDC()
        cDC.DeleteDC()
        wgui.ReleaseDC(hwnd, wDC)
        wgui.DeleteObject(dataBitMap.GetHandle())
        return img

    @staticmethod
    def s_fast_capture_center(hwnd, x, y, w, h):
        return WindowCapture.fast_capture(hwnd, x - int(w/2), y - int(h/2), w, h)

    @staticmethod
    def fast_screen_capture(x, y, w, h):
        hdesktop = wgui.GetDesktopWindow()

        # width = wapi.GetSystemMetrics(wcon.SM_CXVIRTUALSCREEN)
        # height = wapi.GetSystemMetrics(wcon.SM_CYVIRTUALSCREEN)
        # left = wapi.GetSystemMetrics(wcon.SM_XVIRTUALSCREEN)
        # top = wapi.GetSystemMetrics(wcon.SM_YVIRTUALSCREEN)

        desktop_dc = wgui.GetWindowDC(hdesktop)
        img_dc = wui.CreateDCFromHandle(desktop_dc)
        mem_dc = img_dc.CreateCompatibleDC()
        screenshot = wui.CreateBitmap()
        screenshot.CreateCompatibleBitmap(img_dc, w, h)
        mem_dc.SelectObject(screenshot)
        mem_dc.BitBlt((0, 0), (w, h), img_dc, (x, y), wcon.SRCCOPY)

        array = screenshot.GetBitmapBits(True)
        img = np.frombuffer(array, dtype='uint8')
        img.shape = (h, w, 4)

        img_dc.DeleteDC()
        mem_dc.DeleteDC()
        wgui.ReleaseDC(hdesktop, desktop_dc)
        wgui.DeleteObject(screenshot.GetHandle())

        return img

    @staticmethod
    def fast_screen_capture_center(x, y, w, h):
        return WindowCapture.fast_screen_capture(x - int(w/2), y - int(h/2), w, h)

    @staticmethod
    def get_foreground_window_name():
        return wgui.GetWindowText(wgui.GetForegroundWindow())

    @staticmethod
    def get_window_subs(hwnd):
        def callback(hwnd, hwnds):
            if wgui.IsWindowVisible(hwnd) and wgui.IsWindowEnabled(hwnd):
                hwnds[wgui.GetClassName(hwnd)] = hwnd
            return True
        hwnds = {}
        wgui.EnumChildWindows(hwnd, callback, hwnds)
        return hwnds

    @staticmethod
    def get_foreground_window_subs():
        def callback(hwnd, hwnds):
            if wgui.IsWindowVisible(hwnd) and wgui.IsWindowEnabled(hwnd):
                # hwnds[wgui.GetClassName(hwnd)] = hwnd
                hwnds.append(wgui.GetClassName(hwnd))
            return True
        hwnds = []
        wgui.EnumChildWindows(wgui.GetForegroundWindow(), callback, hwnds)
        return hwnds

    @staticmethod
    def get_foreground_window_class():
        return wgui.GetClassName(wgui.GetForegroundWindow())

    @staticmethod
    def get_foreground_window_handler():
        return wgui.GetForegroundWindow()

    # @staticmethod
    # def get_foreground_window_executable():
    #     for p in wmi_connect.query('SELECT Name FROM Win32_Process WHERE ProcessId = %s' % str(wproc.GetWindowThreadProcessId(wgui.GetForegroundWindow()))):
    #         return p.Name

    @staticmethod
    def get_foreground_window_executable():
        pid = wproc.GetWindowThreadProcessId(wgui.GetForegroundWindow())
        return psutil.Process(pid[-1]).name()
