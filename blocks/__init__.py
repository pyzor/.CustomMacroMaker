import codecs
import os
import io
import sys
import wx
from numpy import record
from pynput import keyboard
from wx.lib.platebtn import PlateButton
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.intctrl import IntCtrl
from wx.lib.intctrl import EVT_INT
from wx.lib.masked.numctrl import NumCtrl
from wx.lib.dialogs import scrolledMessageDialog
from wx.stc import *
import json
import ctypes
import cv2
# import cv2.  cv
import re
import string
import pynput
import macro
import numpy as np
import imageio
import json
import vision
from time import time
from custom import RangeSlider

import window_capture
from window_capture import WindowCapture
from mmap import ACCESS_READ, mmap

# sys.stdout.flush()
# sys.stdout.write(' \n')

ctypes.windll.shcore.SetProcessDpiAwareness(2)

APP_FRAME_START_POS = (0, 0)
APP_FRAME_SIZE = (1280, 720)
APP_FRAME_SIZE_PANEL = (1264, 681)
SET_VALUE_DIALOG_SIZE = (420, 320)
SET_VAR_NAME_DIALOG_SIZE = (240, 90)
ADD_ELEMENT_DIALOG_SIZE = (320, 320)

MACROS_HANDLER = macro.MacrosHandler()

# QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
ACTIONS_LIST = {
    'set': ['var_name', 'value_type', 'value'],
    'while': ['condition', 'actions'],
    'break': ['if', 'condition'],
    'macros': ['events'],
    'load_image': ['var_name', 'raw_image'],
    'capture_image': ['var_name', 'window', 'x', 'y', 'w', 'h'],
    'capture_image_mouse_pos': ['var_name', 'window', 'w', 'h'],
    'screenshot_image': ['var_name', 'x', 'y', 'w', 'h'],
    'screenshot_image_mouse_pos': ['var_name', 'w', 'h'],
    'find_window': ['var_name', 'window_name', 'sub_window'],
    'mouse_move': ['var_name', 'window_space', 'window'],
    'mouse_button': ['var_name', 'action', 'button', 'window_space', 'window'],
    'focus_window': ['window'],
    'hsv_filter': ['var_name', 'h_min', 'h_max', 's_min', 's_max', 'v_min', 'v_max', 's_add', 's_sub', 'v_add', 'v_sub'],
    'find': ['return_var', 'observer', 'target', 'threshold', 'max_results', 'use_hsv', 'hsv'],
    'list': ['list_var', 'action', 'value', 'index_type', 'index_int', 'index_var'],
    'math': ['return_var', 'value1_type', 'value1_num', 'value1_var', 'operation', 'value2_type', 'value2_num', 'value2_var'],
    'if': ['condition', 'actions'],
    'apply_hsv': ['return_var', 'image_var', 'hsv'],
    'wait': ['value_type', 'value_num', 'value_var'],
    'sum': ['return_var', 'list_var'],
}

OPERATORS_LIST = {
    "==": "equal to",
    "!=": "not equal to",
    ">": "greater than",
    "<": "less than",
    ">=": "greater than or equal to",
    "<=": "less than or equal to"
}

CONDITIONS_LIST = {
    "value": ["value_type", "value"],
    "variable": ["var_name"],
    "compare": ["left_key", "operator", "right_key"],
    "and": ["left_key", "right_key"],
    "or": ["left_key", "right_key"],
    "length": ['var_name']
}

VALUE_TYPES = [
    'none_type',
    'number',
    'boolean',
    'string'
]

LAST_ITEM_ID = 0

VARIABLES = {}

JBM_FONT = None
CROSS_BPM = None
RECORD_ICO = None


def overrides(interface_class):
    def overrider(method):
        assert (method.__name__ in dir(interface_class))
        return method

    return overrider


def do_nothing(event):
    pass


def number_input_filter(event):
    keycode = event.GetKeyCode()
    obj = event.GetEventObject()
    val = obj.GetValue()
    point = obj.GetInsertionPoint()
    if keycode == wx.WXK_NONE:
        pass
    elif chr(keycode) in string.digits:
        if len(val) > 0:
            if val[0] == '-' and point == 0:
                obj.SetInsertionPoint(point + 1)
                point += 1
        event.Skip()
    elif chr(keycode) not in string.printable:
        event.Skip()
    elif chr(keycode) == '-':
        if len(val) == 0:
            obj.SetValue('-')
            obj.SetInsertionPoint(point + 1)
        elif val[0] == '-':
            obj.SetValue(val[1:])
            obj.SetInsertionPoint(point - 1)
        else:
            obj.SetValue('-' + val)
            obj.SetInsertionPoint(point + 1)
    elif chr(keycode) == '.' and '.' not in val:
        if len(val) > 0:
            if val[0] == '-' and point == 0:
                obj.SetInsertionPoint(point + 1)
                point += 1
        event.Skip()
    return


def integer_input_filter(event):
    keycode = event.GetKeyCode()
    obj = event.GetEventObject()
    val = obj.GetValue()
    point = obj.GetInsertionPoint()
    if keycode == wx.WXK_NONE:
        pass
    elif chr(keycode) in string.digits:
        event.Skip()
    elif chr(keycode) not in string.printable:
        event.Skip()
    return


def boolean_input_filter(event):
    obj = event.GetEventObject()
    if obj.IsChecked():
        obj.SetLabel('True')
    else:
        obj.SetLabel('False')


def string_input_filter(event):
    keycode = event.GetKeyCode()
    if keycode == wx.WXK_NONE:
        pass
    elif chr(keycode) in string.ascii_lowercase:
        event.Skip()
    elif chr(keycode) == '_':
        event.Skip()
    elif chr(keycode) not in string.printable:
        event.Skip()
    return


class CMMPanel(ScrolledPanel):
    parent_frame = None

    mouse_frame_pos = wx.Point(0, 0)

    def __init__(self, parent):
        super().__init__(parent=parent)
        self.parent_frame = parent
        self.SetFocus()

        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.__block_list = []

        self.SetBackgroundColour(wx.Colour(255, 255, 255))

        self.__main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.__main_sizer)

        self.__add_button = PlateButton(self, id=999, label='[   + Add   ]', style=4)
        self.__add_button.Bind(event=wx.EVT_BUTTON, handler=self.__b_add, id=999)
        self.__add_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__add_button.SetPressColor(wx.Colour(180, 210, 180))
        self.__add_button.SetFont(JBM_FONT)
        self.__add_button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.__add_button_sizer.Add(self.__add_button, 0, wx.ALL, 4)
        self.add_element(self.__add_button_sizer, flag=wx.ALIGN_CENTER)

        self.dnd = DragAndDrop(self)

        self.mouse_listener = pynput.mouse.Listener(
            on_move=self.on_mouse_move,
            # on_scroll=self.__on_scroll,
            on_click=self.on_mouse_click)

        self.mouse_listener.start()
        self.mouse_listener.wait()

    def on_mouse_move(self, x, y):
        self.mouse_frame_pos = self.parent_frame.ScreenToClient((x, y))

        self.dnd.on_mouse_move()

    def on_mouse_click(self, x, y, button, pressed):
        pass

    def show_blocks(self):
        for block in self.__block_list:
            if block.get_name() != 'dnd_blank':
                block.show()
        self.sort_list_of_blocks()
        self.update_ui()

    def sort_list_of_blocks(self):
        self.__block_list.sort(key=lambda b: b.get_pos()[1])

        hidden_blocks = 0
        for block in self.__block_list:
            if block.is_shown():
                block.set_index(self.__block_list.index(block) - hidden_blocks)
            else:
                hidden_blocks += 1
        self.Layout()

    def get_list_of_blocks_by_y_pos(self):
        list_of_coors = []
        for block in self.__block_list:
            list_of_coors.append((block.get_pos()[1] - 2, block))
        return list_of_coors

    def get_list_of_actions(self):
        actions = []
        for block in self.__block_list:
            block.update()
            if block.get_name() != 'dnd_blank':
                # if block.get_name() !=
                # actions.append({'action_name': block.get_name(), 'keys': block.get_keys()})
                actions.append(block.dump_save())
        return actions

    def __refresh_scrolling(self):
        self.SetupScrolling(scroll_x=False, rate_x=16, rate_y=16, scrollToTop=False)

    def __b_add(self, event):
        result = 0
        with AddElementDialog() as dlg:
            dlg.SetPosition(self.ClientToScreen((APP_FRAME_SIZE[0] / 2 - ADD_ELEMENT_DIALOG_SIZE[0] / 2,
                                                 APP_FRAME_SIZE[1] / 2 - ADD_ELEMENT_DIALOG_SIZE[1] / 2)))
            result = dlg.ShowModal()
        if result != wx.ID_OK:
            self.add_block(block_id=result)

    def add_block(self, action=None, block_id=None, index=None, update=True):
        # QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
        block = None
        if ((action is not None) and action['action_name'] == 'set') or block_id == 1000:
            if action is not None:
                block = Set(self,
                            var_name=action['keys']['var_name'],
                            value_type=action['keys']['value_type'],
                            value=action['keys']['value'],
                            index=index)
            else:
                block = Set(self, index=index)
        elif ((action is not None) and action['action_name'] == 'while') or block_id == 1001:
            if action is not None:
                block = While(self,
                              condition=action['keys']['condition'],
                              actions=action['keys']['actions'],
                              index=index)
            else:
                block = While(self, index=index)
        elif ((action is not None) and action['action_name'] == 'break') or block_id == 1002:
            if action is not None:
                block = Break(self,
                              if_bool=action['keys']['if'],
                              condition=action['keys']['condition'],
                              index=index)
            else:
                block = Break(self, index=index)
        elif ((action is not None) and action['action_name'] == 'macros') or block_id == 1003:
            if action is not None:
                block = Macros(self,
                               events=action['keys']['events'],
                               index=index)
            else:
                block = Macros(self, events=[], index=index)
        elif ((action is not None) and action['action_name'] == 'load_image') or block_id == 1004:
            if action is not None:
                block = LoadImage(self,
                                  var_name=action['keys']['var_name'],
                                  raw_image=action['keys']['raw_image'],
                                  index=index)
            else:
                block = LoadImage(self, index=index)
        elif ((action is not None) and action['action_name'] == 'capture_image') or block_id == 1005:
            if action is not None:
                block = CaptureImage(self,
                                     var_name=action['keys']['var_name'],
                                     # process_exe=action['keys']['process_exe'],
                                     window=action['keys']['window'],
                                     x=action['keys']['x'],
                                     y=action['keys']['y'],
                                     w=action['keys']['w'],
                                     h=action['keys']['h'],
                                     index=index)
            else:
                block = CaptureImage(self, index=index)
        elif ((action is not None) and action['action_name'] == 'capture_image_mouse_pos') or block_id == 1006:
            if action is not None:
                block = CaptureImageMousePos(self,
                                             var_name=action['keys']['var_name'],
                                             window=action['keys']['window'],
                                             w=action['keys']['w'],
                                             h=action['keys']['h'],
                                             index=index)
            else:
                block = CaptureImageMousePos(self, index=index)
        elif ((action is not None) and action['action_name'] == 'screenshot_image') or block_id == 1007:
            if action is not None:
                block = ScreenshotImage(self,
                                        var_name=action['keys']['var_name'],
                                        x=action['keys']['x'],
                                        y=action['keys']['y'],
                                        w=action['keys']['w'],
                                        h=action['keys']['h'],
                                        index=index)
            else:
                block = ScreenshotImage(self, index=index)
        elif ((action is not None) and action['action_name'] == 'screenshot_image_mouse_pos') or block_id == 1008:
            if action is not None:
                block = ScreenshotImageMousePos(self,
                                                var_name=action['keys']['var_name'],
                                                w=action['keys']['w'],
                                                h=action['keys']['h'],
                                                index=index)
            else:
                block = ScreenshotImageMousePos(self, index=index)
        elif ((action is not None) and action['action_name'] == 'find_window') or block_id == 1009:
            if action is not None:
                block = FindWindow(self,
                                   var_name=action['keys']['var_name'],
                                   window_name=action['keys']['window_name'],
                                   sub_window=action['keys']['sub_window'],
                                   index=index)
            else:
                block = FindWindow(self, index=index)
        elif ((action is not None) and action['action_name'] == 'mouse_move') or block_id == 1010:
            if action is not None:
                block = MouseMove(self,
                                  var_name=action['keys']['var_name'],
                                  window_space=action['keys']['window_space'],
                                  window=action['keys']['window'],
                                  index=index)
            else:
                block = MouseMove(self, index=index)
        elif ((action is not None) and action['action_name'] == 'mouse_button') or block_id == 1011:
            if action is not None:
                block = MouseButton(self,
                                  var_name=action['keys']['var_name'],
                                  action=action['keys']['action'],
                                  button=action['keys']['button'],
                                  window_space=action['keys']['window_space'],
                                  window=action['keys']['window'],
                                  index=index)
            else:
                block = MouseButton(self, index=index)
        elif ((action is not None) and action['action_name'] == 'focus_window') or block_id == 1012:
            if action is not None:
                block = FocusWindow(self,
                                  window=action['keys']['window'],
                                  index=index)
            else:
                block = FocusWindow(self, index=index)
        elif ((action is not None) and action['action_name'] == 'hsv_filter') or block_id == 1013:
            if action is not None:
                block = HSVFilter(self,
                                  var_name=action['keys']['var_name'],
                                  h_min=action['keys']['h_min'],
                                  h_max=action['keys']['h_max'],
                                  s_min=action['keys']['s_min'],
                                  s_max=action['keys']['s_max'],
                                  v_min=action['keys']['v_min'],
                                  v_max=action['keys']['v_max'],
                                  s_add=action['keys']['s_add'],
                                  s_sub=action['keys']['s_sub'],
                                  v_add=action['keys']['v_add'],
                                  v_sub=action['keys']['v_sub'],
                                  index=index)
            else:
                block = HSVFilter(self, index=index)
        elif ((action is not None) and action['action_name'] == 'find') or block_id == 1014:
            if action is not None:
                block = Find(self,
                             return_var=action['keys']['return_var'],
                             observer=action['keys']['observer'],
                             target=action['keys']['target'],
                             threshold=action['keys']['threshold'],
                             max_results=action['keys']['max_results'],
                             use_hsv=action['keys']['use_hsv'],
                             hsv=action['keys']['hsv'],
                             index=index)
            else:
                block = Find(self, index=index)
        elif ((action is not None) and action['action_name'] == 'list') or block_id == 1015:
            if action is not None:
                block = List(self,
                             list_var=action['keys']['list_var'],
                             action=action['keys']['action'],
                             value=action['keys']['value'],
                             index_type=action['keys']['index_type'],
                             index_int=action['keys']['index_int'],
                             index_var=action['keys']['index_var'],
                             index=index)
            else:
                block = List(self, index=index)
        elif ((action is not None) and action['action_name'] == 'math') or block_id == 1016:
            if action is not None:
                block = Math(self,
                             return_var=action['keys']['return_var'],
                             value1_type=action['keys']['value1_type'],
                             value1_num=action['keys']['value1_num'],
                             value1_var=action['keys']['value1_var'],
                             operation=action['keys']['operation'],
                             value2_type=action['keys']['value2_type'],
                             value2_num=action['keys']['value2_num'],
                             value2_var=action['keys']['value2_var'],
                             index=index)
            else:
                block = Math(self, index=index)
        elif ((action is not None) and action['action_name'] == 'if') or block_id == 1017:
            if action is not None:
                block = If(self,
                              condition=action['keys']['condition'],
                              actions=action['keys']['actions'],
                              index=index)
            else:
                block = If(self, index=index)
        elif ((action is not None) and action['action_name'] == 'apply_hsv') or block_id == 1018:
            if action is not None:
                block = ApplyHSV(self,
                              return_var=action['keys']['return_var'],
                              image_var=action['keys']['image_var'],
                              hsv=action['keys']['hsv'],
                              index=index)
            else:
                block = ApplyHSV(self, index=index)
        elif ((action is not None) and action['action_name'] == 'wait') or block_id == 1019:
            if action is not None:
                block = Wait(self,
                              value_type=action['keys']['value_type'],
                              value_num=action['keys']['value_num'],
                              value_var=action['keys']['value_var'],
                              index=index)
            else:
                block = Wait(self, index=index)
        elif ((action is not None) and action['action_name'] == 'sum') or block_id == 1020:
            if action is not None:
                block = Sum(self,
                              return_var=action['keys']['return_var'],
                              list_var=action['keys']['list_var'],
                              index=index)
            else:
                block = Sum(self, index=index)
        if block is not None:
            self.__block_list.append(block)
            if update:
                block.show()
                self.update_ui()
        self.sort_list_of_blocks()
        return block

    def set_block_pos(self, block, index):
        self.__main_sizer.Detach(block.main_sizer)
        if index == -1:
            self.__main_sizer.Add(sizer=block.main_sizer, proportion=0,
                                  flag=wx.ALIGN_LEFT | wx.EXPAND, border=4)
        else:
            self.__main_sizer.Insert(index=index, sizer=block.main_sizer, proportion=0,
                                     flag=wx.ALIGN_LEFT | wx.EXPAND, border=4)
        self.Layout()
        self.sort_list_of_blocks()

        # print(block, index, self.)
        # print(self.__block_list)

    def update_ui(self):
        self.__refresh_scrolling()
        self.parent_frame.update_status_bar()
        self.Layout()

    def add_element(self, sizer, proportion=0, flag=wx.ALL, border=4, index=None):
        if index is None:
            self.__main_sizer.Add(sizer=sizer, proportion=proportion, flag=flag, border=border)
        else:
            self.__main_sizer.Insert(index=index, sizer=sizer, proportion=proportion, flag=flag, border=border)

    def get_block_index(self, block):
        return self.__block_list.index(block)

    def remove_from_sizer(self, sizer, block, update=True):
        self.__main_sizer.Remove(sizer)
        if block is not None:
            for b in self.__block_list:
                if b == block:
                    self.__block_list.remove(b)
                    break
        if update:
            self.update_ui()

    def detach_add_button_sizer(self):
        self.__main_sizer.Detach(self.__add_button_sizer)

    def attach_add_button_sizer(self):
        self.__main_sizer.Add(self.__add_button_sizer, 0, flag=wx.ALIGN_CENTER)

    def get_blocks(self):
        return self.__block_list

    def get_pos(self):
        return self.parent_frame.GetPosition()

    def update(self):
        for i in self.__block_list:
            i.update()

    def on_close(self):
        self.mouse_listener.stop()
        self.mouse_listener = None

    def __on_close(self, event):
        self.Destroy()
        event.Skip()


class AddElementDialog(wx.Dialog):
    # QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
    dic = {'Set': 1000,
           'While': 1001,
           'Break': 1002,
           'Macros': 1003,
           'Load Image': 1004,
           'Capture Image': 1005,
           'Capture Image Mouse Pos': 1006,
           'Screenshot Image': 1007,
           'Screenshot Image Mouse Pos': 1008,
           'Find Window': 1009,
           'Mouse Move': 1010,
           'Mouse Button': 1011,
           'Focus Window': 1012,
           'HSV Filter': 1013,
           'Find': 1014,
           'List': 1015,
           'Math': 1016,
           'If': 1017,
           'Apply HSV': 1018,
           'Wait': 1019,
           'Sum': 1020,
           }

    des = {'Set': "Sets specific value for a Variable.",
           'While': "While loop.",
           'Break': "Breaks current loop or a cycle to continue executing next actions.",
           'Macros': "Plays prerecorded macros that emulates mouse and keyboard events.",
           'Load Image': "Loads image data and then stores it in variable.",
           'Capture Image': "Takes a screenshot of a specific window and then stores it in a "
                            "variable."
                            "Be careful, not all windows support this type of image capture!",
           'Capture Image Mouse Pos': "Takes a screenshot of a specific window and then stores it in a "
                                      "variable."
                                      " The center of the image will be located at the position of the mouse cursor. "
                                      "Be careful, not all windows support this type of image capture!",
           'Screenshot Image': "Takes a screenshot of a screen and then stores it in a variable.",
           'Screenshot Image Mouse Pos': "Takes a screenshot of a screen and then stores it in a variable."
                                         " The center of the image will be located at the position of the mouse cursor. ",
           'Find Window': "Finds window by its name. Returns window handler that can be used for later.",
           'Mouse Move': "Moves mouse cursor to the given position. ",
                         # "Also can be specified to operate inside a specific window.",
           'Mouse Button': "Performs the selected action with the selected mouse button at the given position.",
           'Focus Window': "Brings the given window to the foreground.",
           'HSV Filter': 'Used to create HSV filter and store it in a variable.',
           'Find': 'Used to find objects on the given image. Threshold used for the assignment of pixel values.'
                   'Max results limits the number of objects it tries to find. Also you can apply hsv filter'
                   ' for better results.',
           'List': 'Helps with performing actions with a list.',
           'Math': 'Helps with performing actions with a numbers.',
           'If': 'If statement.',
           'Apply HSV': 'Applies hsv filter on an image.',
           'Wait': 'Halts macros for a specific time. Be aware that if you are using this - interrupting macros with f5 may not work right away.',
           'Sum': 'Returns sum of numbers in a given list.',
           }

    def __init__(self):
        global ADD_ELEMENT_DIALOG_SIZE
        wx.Dialog.__init__(self, None, title='Add element', size=ADD_ELEMENT_DIALOG_SIZE,
                           style=wx.STAY_ON_TOP | wx.DIALOG_NO_PARENT)
        self.panel = wx.Panel(self)
        self.SetSize(ADD_ELEMENT_DIALOG_SIZE)
        self.panel.SetSize(ADD_ELEMENT_DIALOG_SIZE)

        self.panel.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        self.panel.Bind(wx.EVT_MOTION, self.__mm)
        self.panel.Bind(wx.EVT_LEFT_UP, self.__mlu)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(main_sizer)
        main_sizer.Fit(self.panel)
        self.panel.Layout()

        title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        title = wx.StaticText(self.panel, label=' Add new element')
        title.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        title.Bind(wx.EVT_MOTION, self.__mm)
        title.Bind(wx.EVT_LEFT_UP, self.__mlu)

        self.close_button = PlateButton(self.panel, id=wx.ID_ANY, label='Close', style=4)
        self.close_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.close_button.SetPressColor(wx.Colour(210, 180, 180))
        self.close_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__on_close)
        global JBM_FONT
        self.close_button.SetFont(JBM_FONT)

        title_sizer.Add(title, 1, wx.ALL | wx.ALIGN_CENTER, 1)
        title_sizer.Add(self.close_button, 0, wx.ALL | wx.ALIGN_CENTER, 1)

        main_sizer.Add(title_sizer, 0, wx.ALL | wx.EXPAND, 2)
        title_line = wx.StaticLine(self.panel)
        title_line.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        title_line.Bind(wx.EVT_MOTION, self.__mm)
        title_line.Bind(wx.EVT_LEFT_UP, self.__mlu)
        title_line.SetFocus()
        main_sizer.Add(title_line, 0, wx.ALL | wx.EXPAND, -1)

        self.description = wx.StaticText(self.panel, label='', style=wx.ALIGN_LEFT | wx.ST_NO_AUTORESIZE)
        self.description.SetLabel('If you can see this - programmer is bad.')

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.listbox = wx.ListBox(self.panel, id=wx.ID_ANY, choices=[_ for _ in self.dic.keys()],
                                  style=wx.LB_SINGLE | wx.LB_NEEDED_SB, name='Elements')  # | wx.LB_SORT
        self.listbox.Bind(event=wx.EVT_LISTBOX, handler=self.__on_listbox)
        self.listbox.Bind(event=wx.EVT_LISTBOX_DCLICK, handler=self.__on_add)
        self.listbox.Select(0)
        self.__on_listbox()

        content_description_sizer = wx.BoxSizer(wx.VERTICAL)
        description_title = wx.StaticText(self.panel, label='Description:')

        content_description_sizer.Add(description_title, 0, wx.ALL | wx.EXPAND | wx.ALIGN_LEFT, 1)
        content_description_sizer.Add(self.description, 1, wx.ALL | wx.EXPAND | wx.ALIGN_LEFT, 1)

        content_sizer.Add(self.listbox, 1, wx.ALL | wx.EXPAND, 3)
        content_sizer.Add(content_description_sizer, 1, wx.ALL | wx.EXPAND, 1)

        main_sizer.Add(content_sizer, 1, wx.ALL | wx.EXPAND, 1)
        low_line = wx.StaticLine(self.panel)
        main_sizer.Add(low_line, 0, wx.ALL | wx.EXPAND, -1)

        last_sizer = wx.BoxSizer(wx.HORIZONTAL)

        help_text = wx.StaticText(self.panel, label='Select an item from the list to add.')

        self.add_button = PlateButton(self.panel, id=wx.ID_ANY, label='Add', style=4)
        self.add_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.add_button.SetPressColor(wx.Colour(180, 210, 180))
        self.add_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__on_add)
        self.add_button.SetFont(JBM_FONT)

        last_sizer.Add(help_text, 1, wx.ALL | wx.ALIGN_CENTER, 1)
        last_sizer.Add(self.add_button, 0, wx.ALL | wx.ALIGN_CENTER, 1)

        main_sizer.Add(last_sizer, 0, wx.ALL | wx.EXPAND, 2)

        self.panel.Layout()

        wx.CallAfter(self.Refresh)

    def __mld(self, event):
        self.Refresh()
        self.ld_pos = self.panel.ClientToScreen(event.GetPosition())
        self.w_pos = self.panel.ClientToScreen(self.panel.GetPosition())
        self.panel.CaptureMouse()

    def __mm(self, event):
        if event.Dragging() and event.LeftIsDown() and self.panel.HasCapture():
            d_pos = self.panel.ClientToScreen(event.GetPosition())
            n_pos = (self.w_pos.x + (d_pos.x - self.ld_pos.x), self.w_pos.y + (d_pos.y - self.ld_pos.y))
            self.Move(n_pos)

    def __mlu(self, event):
        if self.panel.HasCapture():
            self.panel.ReleaseMouse()

    def __on_listbox(self, event=None):
        self.description.SetLabel(self.des.get(self.listbox.GetString(self.listbox.GetSelection())))

    def __on_close(self, event):
        self.close_button.Destroy()
        self.EndModal(wx.ID_OK)

    def __on_add(self, event):
        self.add_button.Destroy()
        self.EndModal(self.dic.get(self.listbox.GetString(self.listbox.GetSelection())))


class NewVarDialog(wx.Dialog):
    def __init__(self):
        global SET_VAR_NAME_DIALOG_SIZE
        wx.Dialog.__init__(self, None, title='New variable', size=SET_VAR_NAME_DIALOG_SIZE,
                           style=wx.STAY_ON_TOP | wx.DIALOG_NO_PARENT)
        self.panel = wx.Panel(self)
        self.SetSize(SET_VAR_NAME_DIALOG_SIZE)
        self.panel.SetSize(SET_VAR_NAME_DIALOG_SIZE)

        self.panel.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        self.panel.Bind(wx.EVT_MOTION, self.__mm)
        self.panel.Bind(wx.EVT_LEFT_UP, self.__mlu)

        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(main_sizer)
        main_sizer.Fit(self.panel)
        self.panel.Layout()

        title_sizer = wx.BoxSizer(wx.HORIZONTAL)

        title = wx.StaticText(self.panel, label=' New variable')
        title.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        title.Bind(wx.EVT_MOTION, self.__mm)
        title.Bind(wx.EVT_LEFT_UP, self.__mlu)

        self.close_button = PlateButton(self.panel, id=wx.ID_ANY, label='Close', style=4)
        self.close_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.close_button.SetPressColor(wx.Colour(210, 180, 180))
        self.close_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__on_close)

        title_sizer.Add(title, 1, wx.ALL | wx.ALIGN_CENTER, 1)
        title_sizer.Add(self.close_button, 0, wx.ALL | wx.ALIGN_CENTER, 1)

        main_sizer.Add(title_sizer, 0, wx.ALL | wx.EXPAND, 2)
        title_line = wx.StaticLine(self.panel)
        title_line.Bind(wx.EVT_LEFT_DOWN, self.__mld)
        title_line.Bind(wx.EVT_MOTION, self.__mm)
        title_line.Bind(wx.EVT_LEFT_UP, self.__mlu)
        title_line.SetFocus()
        main_sizer.Add(title_line, 0, wx.ALL | wx.EXPAND, -1)

        content_input_sizer = wx.BoxSizer(wx.VERTICAL)

        self.new_var = wx.TextCtrl(self.panel, id=wx.ID_ANY, style=wx.TE_PROCESS_ENTER)
        self.new_var.Bind(wx.EVT_CHAR, string_input_filter)
        self.new_var.Bind(wx.EVT_TEXT_ENTER, self.__on_ok)

        content_input_sizer.Add(self.new_var, 0, wx.ALL | wx.EXPAND, 1)

        main_sizer.Add(content_input_sizer, 1, wx.ALL | wx.EXPAND, 1)
        low_line = wx.StaticLine(self.panel)
        main_sizer.Add(low_line, 0, wx.ALL | wx.EXPAND, -1)

        last_sizer = wx.BoxSizer(wx.HORIZONTAL)

        help_text = wx.StaticText(self.panel, label='Enter a name for the new variable.')

        self.ok_button = PlateButton(self.panel, id=wx.ID_ANY, label='OK', style=4)
        self.ok_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.ok_button.SetPressColor(wx.Colour(180, 210, 180))
        self.ok_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__on_ok)

        last_sizer.Add(help_text, 1, wx.ALL | wx.ALIGN_CENTER, 1)
        last_sizer.Add(self.ok_button, 0, wx.ALL | wx.ALIGN_CENTER, 1)

        main_sizer.Add(last_sizer, 0, wx.ALL | wx.EXPAND, 2)
        self.panel.Layout()
        wx.CallAfter(self.Refresh)

    def __mld(self, event):
        self.Refresh()
        self.ld_pos = self.panel.ClientToScreen(event.GetPosition())
        self.w_pos = self.panel.ClientToScreen(self.panel.GetPosition())
        self.panel.CaptureMouse()

    def __mm(self, event):
        if event.Dragging() and event.LeftIsDown() and self.panel.HasCapture():
            d_pos = self.panel.ClientToScreen(event.GetPosition())
            n_pos = (self.w_pos.x + (d_pos.x - self.ld_pos.x), self.w_pos.y + (d_pos.y - self.ld_pos.y))
            self.Move(n_pos)

    def __mlu(self, event):
        if self.panel.HasCapture():
            self.panel.ReleaseMouse()

    def __on_close(self, event):
        self.close_button.Destroy()
        self.EndModal(wx.ID_OK)

    def __on_ok(self, event):
        value = self.new_var.GetValue()
        if list(VARIABLES.keys()).__contains__(value):
            return
        else:
            VARIABLES[self.new_var.GetValue()] = {'value_type': None, 'value': None}
        self.new_var.Destroy()
        self.ok_button.Destroy()
        self.EndModal(list(VARIABLES.keys()).index(value))


class SetValueDialog(wx.Dialog):
    # QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
    dic = {'none_type': 1000,
           'number': 1001,
           'coords': 1002,
           'boolean': 1003,
           'string': 1004,
           'mouse_pos': 1005,
           'list': 1006,
           'get': 1007,
           'image': 1008,
           'hwnd': 1009,
           'hsv_filter': 1010,
           }

    def __init__(self, set_value):
        self.set_value = set_value
        global SET_VALUE_DIALOG_SIZE
        wx.Dialog.__init__(self, None, title='Set value', size=SET_VALUE_DIALOG_SIZE,
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.panel = wx.Panel(self)
        self.SetSize(SET_VALUE_DIALOG_SIZE)
        self.panel.SetSize(SET_VALUE_DIALOG_SIZE)
        main_sizer = wx.BoxSizer(wx.VERTICAL)
        self.panel.SetSizer(main_sizer)
        main_sizer.Fit(self.panel)
        self.panel.Layout()

        self.value_input = wx.BoxSizer(wx.VERTICAL)

        content_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.listbox = wx.ListBox(self.panel, id=wx.ID_ANY, choices=[_ for _ in self.dic.keys()],
                                  style=wx.LB_SINGLE | wx.LB_NEEDED_SB, name='Value types')  # | wx.LB_SORT
        self.listbox.Bind(event=wx.EVT_LISTBOX, handler=self.__on_listbox)
        self.listbox.Select(0)

        self.content_input_sizer = wx.BoxSizer(wx.VERTICAL)
        description_title = wx.StaticText(self.panel, label='Input:')

        self.content_input_sizer.Add(description_title, 0, wx.ALL | wx.EXPAND | wx.ALIGN_LEFT, 1)
        self.content_input_sizer.Add(self.value_input, 1, wx.ALL | wx.EXPAND | wx.ALIGN_LEFT, 1)

        self.__on_listbox()

        content_sizer.Add(self.listbox, 1, wx.ALL | wx.EXPAND, 3)
        content_sizer.Add(self.content_input_sizer, 1, wx.ALL | wx.EXPAND, 1)

        main_sizer.Add(content_sizer, 1, wx.ALL | wx.EXPAND, 1)
        low_line = wx.StaticLine(self.panel)
        main_sizer.Add(low_line, 0, wx.ALL | wx.EXPAND, -1)

        last_sizer = wx.BoxSizer(wx.HORIZONTAL)

        help_text = wx.StaticText(self.panel, label='Select an value type from the list.')

        self.add_button = PlateButton(self.panel, id=wx.ID_ANY, label='Set value', style=4)
        self.add_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.add_button.SetPressColor(wx.Colour(180, 210, 180))
        self.add_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__on_add)

        last_sizer.Add(help_text, 1, wx.ALL | wx.ALIGN_CENTER, 1)
        last_sizer.Add(self.add_button, 0, wx.ALL | wx.ALIGN_CENTER, 1)

        main_sizer.Add(last_sizer, 0, wx.ALL | wx.EXPAND, 2)
        self.panel.Layout()
        wx.CallAfter(self.Refresh)

    def __on_listbox(self, event=None):
        self.content_input_sizer.Detach(self.value_input)
        self.value_input.Clear(True)
        self.value_input = wx.BoxSizer(wx.VERTICAL)
        # QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
        if self.listbox.GetString(self.listbox.GetSelection()) == 'none_type':
            lbl_none = wx.StaticText(self.panel, label='None')
            self.value_input.Add(lbl_none, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'number':
            num_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_num = wx.StaticText(self.panel, label='Number')
            self.content = wx.TextCtrl(self.panel, size=(128, -1))
            self.content.Bind(wx.EVT_CHAR, number_input_filter)
            num_sizer.Add(lbl_num, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            num_sizer.Add(self.content, 0, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(num_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'coords':
            x_sizer = wx.BoxSizer(wx.HORIZONTAL)
            y_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_x = wx.StaticText(self.panel, label='X')
            lbl_y = wx.StaticText(self.panel, label='Y')
            self.int_x = IntCtrl(parent=self.panel, id=wx.ID_ANY, size=(64, -1), allow_none=False, allow_long=False,
                                 min=0, max=ctypes.windll.user32.GetSystemMetrics(78))
            self.int_y = IntCtrl(parent=self.panel, id=wx.ID_ANY, size=(64, -1), allow_none=False, allow_long=False,
                                 min=0, max=ctypes.windll.user32.GetSystemMetrics(79))
            x_sizer.Add(lbl_x, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            x_sizer.Add(self.int_x, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            y_sizer.Add(lbl_y, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            y_sizer.Add(self.int_y, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(x_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(y_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'boolean':
            boolean_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_bool = wx.StaticText(self.panel, label='Boolean')
            self.bool_in = wx.CheckBox(self.panel, label='False')
            self.bool_in.Bind(event=wx.EVT_CHECKBOX, handler=boolean_input_filter)
            boolean_sizer.Add(lbl_bool, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            boolean_sizer.Add(self.bool_in, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(boolean_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'string':
            string_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_str = wx.StaticText(self.panel, label='String', size=(24, -1))
            self.text_in = wx.TextCtrl(self.panel, id=wx.ID_ANY, size=(96, -1))
            self.text_in.Bind(wx.EVT_CHAR, string_input_filter)
            string_sizer.Add(lbl_str, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            string_sizer.Add(self.text_in, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(string_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'mouse_pos':
            mouse_pos_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_mouse_pos = wx.StaticText(self.panel,
                                          label='Gets current mouse position as a coords when this block is executed.',
                                          style=wx.ST_NO_AUTORESIZE, size=(200, 64))
            mouse_pos_sizer.Add(lbl_mouse_pos, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(mouse_pos_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'list':
            mouse_pos_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_mouse_pos = wx.StaticText(self.panel, label='Creates new empty list.', style=wx.ST_NO_AUTORESIZE,
                                          size=(200, 64))
            mouse_pos_sizer.Add(lbl_mouse_pos, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(mouse_pos_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'image':
            image_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_image = wx.StaticText(self.panel, label='Creates new empty image.', style=wx.ST_NO_AUTORESIZE,
                                      size=(200, 64))
            image_sizer.Add(lbl_image, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(image_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'hwnd':
            hwnd_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_hwnd = wx.StaticText(self.panel, label='Creates new empty window handler.', style=wx.ST_NO_AUTORESIZE,
                                     size=(200, 64))
            hwnd_sizer.Add(lbl_hwnd, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(hwnd_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'hsv_filter':
            hsv_sizer = wx.BoxSizer(wx.HORIZONTAL)
            lbl_hsv = wx.StaticText(self.panel, label='Creates new empty HSV filter.', style=wx.ST_NO_AUTORESIZE,
                                     size=(200, 64))
            hsv_sizer.Add(lbl_hsv, 1, wx.ALL | wx.ALIGN_CENTER, 1)
            self.value_input.Add(hsv_sizer, 0, wx.ALL | wx.ALIGN_CENTER, 1)
        elif self.listbox.GetString(self.listbox.GetSelection()) == 'get':
            list_name_sizer = wx.BoxSizer(wx.VERTICAL)
            self.list_index_sizer = wx.BoxSizer(wx.VERTICAL)

            name_text = wx.StaticText(self.panel, label='List variable name')
            self.name_choice = wx.Choice(self.panel, id=wx.ID_ANY, size=(128, -1))
            self.name_choice.Set(list(VARIABLES.keys()))
            self.name_choice.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

            index_text = wx.StaticText(self.panel, label='Index')
            self.index_type_choice = wx.Choice(self.panel, id=wx.ID_ANY, size=(128, -1), )
            self.index_type_choice.Set(['integer', 'variable name'])
            self.index_type_choice.Select(0)
            self.index_type_choice.Bind(event=wx.EVT_CHOICE, handler=self.on_index_type_choice)
            self.index_type_choice.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
            self.index_input_sizer = wx.BoxSizer(wx.HORIZONTAL)

            list_name_sizer.Add(name_text, 0, wx.ALL | wx.ALIGN_LEFT, 1)
            list_name_sizer.Add(self.name_choice, 0, wx.ALL | wx.ALIGN_LEFT, 1)

            self.list_index_sizer.Add(index_text, 0, wx.ALL | wx.ALIGN_LEFT, 1)
            self.list_index_sizer.Add(self.index_type_choice, 0, wx.ALL | wx.ALIGN_LEFT, 1)
            self.list_index_sizer.Add(self.index_input_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 1)

            self.value_input.Add(list_name_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 1)
            self.value_input.Add(self.list_index_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 1)

            self.on_index_type_choice()

        self.content_input_sizer.Add(self.value_input, 1, wx.ALL | wx.EXPAND | wx.ALIGN_LEFT, 1)
        self.panel.Layout()
        wx.CallAfter(self.Refresh)

    def on_index_type_choice(self, event=None):
        self.list_index_sizer.Detach(self.index_input_sizer)
        self.index_input_sizer.Clear(True)
        self.index_input_sizer = wx.BoxSizer(wx.VERTICAL)

        if self.index_type_choice.GetString(self.index_type_choice.GetSelection()) == 'integer':
            self.content = wx.TextCtrl(self.panel, size=(128, -1))
            self.content.Bind(wx.EVT_CHAR, integer_input_filter)
        elif self.index_type_choice.GetString(self.index_type_choice.GetSelection()) == 'variable name':
            self.content = wx.Choice(self.panel, id=wx.ID_ANY, size=(128, -1))
            self.content.Set(list(VARIABLES.keys()))
            self.content.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.index_input_sizer.Add(self.content, 0, wx.ALIGN_LEFT, 0)
        self.list_index_sizer.Add(self.index_input_sizer, 0, wx.ALL | wx.ALIGN_LEFT, 1)
        self.panel.Layout()
        wx.CallAfter(self.Refresh)

    def __on_close(self, event):
        self.EndModal(wx.ID_OK)

    def __on_add(self, event):
        retcode = self.dic.get(self.listbox.GetString(self.listbox.GetSelection()))
        # QUOTE_FOR_FINDING_WHERE_TO_ADD_ACTIONS
        if retcode == self.dic['none_type']:
            self.set_value(None, 'none_type')
        if retcode == self.dic['number']:
            if self.content.Value not in ['.', '-.', '-']:
                self.set_value(float(self.content.Value), 'number')
            else:
                self.set_value(float(0), 'number')
        if retcode == self.dic['coords']:
            self.set_value((self.int_x.Value, self.int_y.Value), 'coords')
        if retcode == self.dic['boolean']:
            self.set_value(self.bool_in.IsChecked(), 'boolean')
        if retcode == self.dic['string']:
            self.set_value(self.text_in.GetValue(), 'string')
        if retcode == self.dic['mouse_pos']:
            self.set_value('CURRENT_MOUSE_POSITION', 'mouse_pos')
        if retcode == self.dic['list']:
            self.set_value([], 'list')
        if retcode == self.dic['image']:
            self.set_value(None, 'image')
        if retcode == self.dic['hwnd']:
            self.set_value(None, 'hwnd')
        if retcode == self.dic['hsv_filter']:
            self.set_value(None, 'hsv_filter')
        if retcode == self.dic['get']:
            if self.name_choice.GetSelection() == -1:
                return
            list_name = self.name_choice.GetString(self.name_choice.GetSelection())
            index_type = self.index_type_choice.GetString(self.index_type_choice.GetSelection())

            if index_type == 'integer':
                if self.content.GetValue() == '':
                    return
            elif index_type == 'variable name':
                if self.content.GetSelection() == -1:
                    return

            index_value = int(self.content.GetValue()) if index_type == 'integer' else self.content.GetString(
                self.content.GetSelection()) if index_type == 'variable name' else None
            self.set_value({'list': list_name,
                            'index': {
                                'type': index_type,
                                'value': index_value
                            }}, 'get')
        self.add_button.Destroy()
        self.EndModal(retcode)


class ScriptDialog(wx.Dialog):
    def __init__(self, actions, set_script):
        self.set_script = set_script
        global APP_FRAME_SIZE
        wx.Dialog.__init__(self, None, title='Script', size=APP_FRAME_SIZE,
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.panel = wx.Panel(self)
        self.panel.SetSize(APP_FRAME_SIZE_PANEL)
        self.panel.SetBackgroundColour(wx.Colour(255, 255, 255))
        self.panel.update_status_bar = self.update_status_bar
        self.panel.get_pos = self.GetPosition()

        self.__panel = CMMPanel(self.panel)
        self.__panel.SetSize(APP_FRAME_SIZE_PANEL)
        self.__status_bar = wx.StatusBar(self)
        self.__status_bar.SetFieldsCount(2)
        self.__status_bar.SetBackgroundColour(wx.Colour(240, 240, 240))
        self.update_status_bar()

        pre_sizer = wx.BoxSizer(wx.VERTICAL)
        pre_sizer.Add(self.__panel, 1, wx.EXPAND | wx.ALL, 0)
        pre_sizer.Add(self.__status_bar, 0, wx.EXPAND | wx.ALL, 0)
        self.panel.SetSizer(pre_sizer)

        self.panel.Layout()
        self.__panel.Layout()
        wx.CallAfter(self.Refresh)

        if actions is not None:
            for action in actions:
                self.__panel.add_block(action=action)
            self.__panel.update()

    def update_status_bar(self):
        self.__status_bar.SetStatusText(f'Blocks count: {len(self.__panel.get_blocks())}', 1)

    def update(self):
        self.__panel.update()

    def __on_close(self, event=None):
        self.set_script(self.__panel.get_list_of_actions())
        self.__panel.on_close()
        self.__panel.Destroy()
        self.panel.Destroy()
        self.EndModal(wx.ID_OK)


class ElementHolder:
    def __init__(self, panel, code_name, parent=None):
        self.type = None
        self.content = None
        self.child_holders = []
        self.code_name = code_name
        self.parent_holder = parent

        self.main_panel = panel
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.child_sizer = wx.BoxSizer(wx.VERTICAL)
        self.line_sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.holder = wx.BoxSizer(wx.HORIZONTAL)
        self.panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.line = wx.StaticLine(self.main_panel, style=wx.LI_VERTICAL)
        self.line.SetForegroundColour(wx.Colour(245, 245, 255))
        self.line.SetBackgroundColour(wx.Colour(245, 245, 255))
        self.line.Hide()

        self.panel = wx.Panel(self.main_panel)
        self.panel.SetBackgroundColour(wx.Colour(245, 245, 255))
        self.panel.SetSizer(self.panel_sizer)
        self.text = wx.StaticText(self.panel, label='Condition')

        self.set_content()

        self.panel_sizer.Add(self.text, 1, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 3)

        self.panel.Layout()

        self.holder.Add(self.panel, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 2)
        self.holder.Add(self.content, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTRE_VERTICAL, 2)

        self.line_sizer.Add(self.line, 0, wx.LEFT | wx.RIGHT | wx.EXPAND, 2)
        self.line_sizer.Add(self.child_sizer, 1, wx.ALL | wx.EXPAND, 0)

        self.sizer.Add(self.holder, 1, wx.ALL | wx.EXPAND, 0)
        self.sizer.Add(self.line_sizer, 0, wx.ALL | wx.EXPAND, 0)

    def add_child(self, child):
        self.child_sizer.Add(child.sizer, 0, wx.TOP | wx.LEFT | wx.EXPAND, 3)
        self.child_holders.append(child)
        self.line.Show()
        # self.main_panel.setup_scrolling()
        self.main_panel.Layout()

    def clear_child_holders(self):
        for holder in self.child_holders:
            holder.remove()
            self.child_sizer.Remove(holder.sizer)
        self.child_holders = []
        self.line.Hide()
        self.main_panel.Layout()

    def get_child_by_code_name(self, code_name):
        for holder in self.child_holders:
            if holder.code_name == code_name:
                return holder
        return None

    def remove_child_by_code_name(self, code_name):
        for holder in self.child_holders:
            if holder.code_name == code_name:
                holder.remove()
                self.child_sizer.Remove(holder.sizer)
                self.child_holders.remove(holder)
                return
        if len(self.child_holders) < 1:
            self.line.Hide()
        self.main_panel.Layout()

    def set_content(self):
        pass

    def dump_save(self):
        dump = {self.code_name: {}}
        dump[self.code_name]['type'] = self.type
        if self.type != 'empty':
            dump[self.code_name]['keys'] = self.dump_data
        return dump

    @property
    def dump_data(self):
        childes = {}
        for child in self.child_holders:
            if child.type == 'label':
                continue
            save = child.dump_save()
            if save is not None:
                childes[child.code_name] = save[child.code_name]
        return childes

    def remove(self, event=None):
        self.clear_child_holders()
        self.sizer.Clear(True)
        self.sizer.Layout()


class ChoiceHolder(ElementHolder):
    def __init__(self, panel, choice_set, code_name, parent=None, keys=None):
        self.choice_set = choice_set
        super().__init__(panel, code_name, parent)

        if keys is not None:
            if keys['type'] != 'empty':
                self.content.Select(choice_set.index(keys['type']))
                self.type = keys['type']
                self.choice(keys=keys['keys'])
            else:
                self.type = 'empty'
        else:
            self.content.Select(0)
            self.choice()

    @overrides(ElementHolder)
    def set_content(self):
        self.content = wx.Choice(self.main_panel, id=wx.ID_ANY, size=(240, -1))
        self.content.Set(self.choice_set)
        self.content.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.content.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

    def choice(self, event=None, keys=None):
        self.clear_child_holders()

        self.type = self.content.GetString(self.content.GetSelection())

        if self.type == 'value':
            v_type = 'none_type' if keys is None else keys['value_type']
            value = None if keys is None else keys['value']
            value_type_holder = ValueHolder(self.main_panel, 'value_type', 'value_type', self, value=v_type)
            value_type_holder.text.SetLabel('Type')
            value_holder = ValueHolder(self.main_panel, v_type, 'value', self, value=value)
            value_holder.text.SetLabel('Value')
            self.add_child(value_type_holder)
            self.add_child(value_holder)
        elif self.type == 'variable':
            value = None
            if keys is not None and list(VARIABLES.keys()).__contains__(keys['var_name']):
                value = keys['var_name']
            var_name_holder = ValueHolder(self.main_panel, 'var_name', 'var_name', self, value)
            var_name_holder.text.SetLabel('Variable')
            self.add_child(var_name_holder)
        elif self.type == 'compare':
            cond_list = list(CONDITIONS_LIST.keys())
            left_keys = keys['left_key'] if keys is not None else {'type': 'empty'}
            left_key_holder = ChoiceHolder(self.main_panel, cond_list, 'left_key', self, keys=left_keys)
            left_key_holder.text.SetLabel('Left value')
            operator_value = keys['operator'] if keys is not None else None
            operator_holder = ValueHolder(self.main_panel, 'operator', 'operator', self, value=operator_value)
            operator_holder.text.SetLabel('Operator')
            right_keys = keys['right_key'] if keys is not None else {'type': 'empty'}
            right_key_holder = ChoiceHolder(self.main_panel, cond_list, 'right_key', self, keys=right_keys)
            right_key_holder.text.SetLabel('Right value')
            self.add_child(left_key_holder)
            self.add_child(operator_holder)
            self.add_child(right_key_holder)
        elif self.type == 'and' or self.type == 'or':
            cond_list = list(CONDITIONS_LIST.keys())
            left_keys = keys['left_key'] if keys is not None else {'type': 'empty'}
            left_key_holder = ChoiceHolder(self.main_panel, cond_list, 'left_key', self, keys=left_keys)
            left_key_holder.text.SetLabel('')
            operator_holder = LabelHolder(self.main_panel, self.type, self)
            operator_holder.text.SetLabel('And' if self.type == 'and' else 'Or')
            right_keys = keys['right_key'] if keys is not None else {'type': 'empty'}
            right_key_holder = ChoiceHolder(self.main_panel, cond_list, 'right_key', self, keys=right_keys)
            right_key_holder.text.SetLabel('')
            self.add_child(left_key_holder)
            self.add_child(operator_holder)
            self.add_child(right_key_holder)
        elif self.type == 'length':
            value = None
            if keys is not None and list(VARIABLES.keys()).__contains__(keys['var_name']):
                value = keys['var_name']
            var_name_holder = ValueHolder(self.main_panel, 'var_name', 'var_name', self, value)
            var_name_holder.text.SetLabel('List')
            self.add_child(var_name_holder)

        self.main_panel.SetupScrolling(scroll_x=False, rate_x=16, rate_y=16, scrollToTop=False)
        # self.main_panel.ScrollChildIntoView(wx.Window.FindFocus())


class ValueHolder(ElementHolder):
    def __init__(self, panel, value_type, code_name, parent=None, value=None):
        self.value_type = value_type
        self.value = value
        self.type = 'value' if self.value_type != 'value_type' else 'value_type'
        super().__init__(panel, code_name, parent)

    @overrides(ElementHolder)
    def set_content(self):
        if self.value_type is None:
            self.content = wx.StaticText(self.main_panel, label='value_type is None', size=(240, -1))
            self.content.SetForegroundColour(wx.Colour(255, 0, 0))
        elif self.value_type == 'none_type':
            self.content = wx.Panel(self.main_panel, size=(240, -1))
            self.content.SetBackgroundColour(wx.Colour(250, 250, 255))
            content_sizer = wx.BoxSizer(wx.HORIZONTAL)
            content_text = wx.StaticText(self.content, label='None', size=(240, -1))
            content_sizer.Add(content_text, 1, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 3)
            self.content.SetSizer(content_sizer)
            self.content.Layout()
        elif self.value_type == 'number':
            self.content = wx.TextCtrl(self.main_panel, size=(240, -1))
            self.content.SetValue(f'{self.value}' if self.value is not None else '')
            self.content.Bind(wx.EVT_CHAR, number_input_filter)
        elif self.value_type == 'boolean':
            self.content = wx.Panel(self.main_panel, size=(240, -1))
            self.content.SetBackgroundColour(wx.Colour(250, 250, 255))
            content_sizer = wx.BoxSizer(wx.HORIZONTAL)
            self.content_boolean = wx.CheckBox(self.content, label=(
                'True' if self.value else 'False') if self.value is not None else 'False')
            if self.value is not None:
                self.content_boolean.SetValue(self.value)
            self.content_boolean.Bind(event=wx.EVT_CHECKBOX, handler=boolean_input_filter)
            content_sizer.Add(self.content_boolean, 1, wx.ALL | wx.ALIGN_CENTRE_VERTICAL, 3)
            self.content.SetSizer(content_sizer)
            self.content.Layout()
        elif self.value_type == 'string':
            self.content = wx.TextCtrl(self.main_panel, size=(240, -1))
            self.content.SetValue(self.value if self.value is not None else '')
            self.content.Bind(wx.EVT_CHAR, string_input_filter)
        elif self.value_type == 'operator':
            operators_list = list(OPERATORS_LIST.keys())
            self.content = wx.Choice(self.main_panel, id=wx.ID_ANY, size=(240, -1))
            self.content.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
            self.content.Set(operators_list)
            if self.value is not None:
                self.content.Select(operators_list.index(self.value))
            else:
                self.content.Select(0)
            self.content.Bind(event=wx.EVT_CHOICE, handler=self.__on_operator_choice)
        elif self.value_type == 'value_type':
            self.content = wx.Choice(self.main_panel, id=wx.ID_ANY, size=(240, -1))
            self.content.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
            self.content.Set(VALUE_TYPES)
            if self.value is not None:
                self.content.Select(VALUE_TYPES.index(self.value))
            self.content.Bind(event=wx.EVT_CHOICE, handler=self.__on_value_type_choice)
        elif self.value_type == 'var_name':
            self.content = wx.Choice(self.main_panel, id=wx.ID_ANY, size=(240, -1))
            self.content.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
            self.content.Set(list(VARIABLES.keys()))
            if self.value is not None:
                self.content.Select(list(VARIABLES.keys()).index(self.value))
            self.content.Bind(event=wx.EVT_CHOICE, handler=self.__on_value_type_choice)

    def get_stored_value(self):
        value = None
        if self.value_type == 'number':
            value = float(self.content.GetValue())
        elif self.value_type == 'boolean':
            value = self.content_boolean.IsChecked()
        elif self.value_type == 'string':
            value = self.content.GetValue()
        elif self.value_type == 'operator' or self.value_type == 'value_type' or self.value_type == 'var_name':
            value = self.content.GetString(self.content.GetSelection())
        return value

    def __re_add_value_child(self, value_type):
        self.parent_holder.remove_child_by_code_name('value')
        value_holder = ValueHolder(self.main_panel, value_type, 'value', self)
        value_holder.text.SetLabel('Value')
        self.parent_holder.add_child(value_holder)

    def __contains_value_type_child(self, value_type):
        return self.parent_holder.get_child_by_code_name('value').value_type == value_type

    def __on_value_type_choice(self, event=None):
        selection = self.content.GetString(self.content.GetSelection())
        if selection == 'none_type' and not self.__contains_value_type_child('none_type'):
            self.__re_add_value_child('none_type')
        elif selection == 'number' and not self.__contains_value_type_child('number'):
            self.__re_add_value_child('number')
        elif selection == 'boolean' and not self.__contains_value_type_child('boolean'):
            self.__re_add_value_child('boolean')
        elif selection == 'string' and not self.__contains_value_type_child('string'):
            self.__re_add_value_child('string')

    @staticmethod
    def __on_operator_choice(event):
        event.Skip()

    @overrides(ElementHolder)
    def dump_save(self):
        return {self.code_name: self.dump_data()}

    @overrides(ElementHolder)
    def dump_data(self):
        return self.get_stored_value()


class LabelHolder(ElementHolder):
    def __init__(self, panel, code_name, parent=None):
        super().__init__(panel, code_name, parent)
        self.type = 'label'

    @overrides(ElementHolder)
    def set_content(self):
        self.content = wx.BoxSizer(wx.HORIZONTAL)


class SetConditionDialog(wx.Dialog):
    def __init__(self, condition, set_condition):
        self.set_condition = set_condition
        global APP_FRAME_SIZE
        wx.Dialog.__init__(self, None, title='Condition', size=APP_FRAME_SIZE,
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.panel2 = ScrolledPanel(self, -1, size=APP_FRAME_SIZE_PANEL, pos=(0, 0),
                                    style=wx.VSCROLL | wx.ALWAYS_SHOW_SB)  # APP_FRAME_SIZE_PANEL
        self.panel2.SetupScrolling(scroll_x=False, rate_x=16, rate_y=16, scrollToTop=False)
        self.panel2.SetBackgroundColour('#FFFFFF')

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        if condition is not None:
            if condition['type'] == 'compare' or condition['type'] == 'and' or condition['type'] == 'or':
                self.main_holder = ChoiceHolder(self.panel2, ['compare', 'and', 'or'], 'condition', keys=condition)
        else:
            self.main_holder = ChoiceHolder(self.panel2, ['compare', 'and', 'or'], 'condition')

        self.main_sizer.Add(self.main_holder.sizer, 0, wx.ALL | wx.EXPAND, 5)

        self.panel2.SetSizer(self.main_sizer)
        wx.CallAfter(self.Refresh)

    def __on_close(self, event=None):
        condition = self.main_holder.dump_save()
        self.set_condition(condition['condition'])
        self.panel2.Destroy()
        self.EndModal(wx.ID_OK)


class Action:
    def __init__(self, name, keys):
        self.action_name = name
        self.keys = {}
        if keys is not None:
            for key in keys:
                self.keys[key] = None

    def get_name(self):
        return self.action_name

    def get_key(self, key):
        return self.keys[key]

    def get_keys(self):
        return self.keys

    def set_key(self, key, value):
        self.keys[key] = value

    def dump_save(self):
        return {'action_name': self.action_name,
                'keys': self.keys}


class DragAndDrop:
    def __init__(self, panel):
        self.parent_panel = panel
        self.dnd_block = DNDBlank(self.parent_panel)
        self.dnd_block.text.SetLabel(
            ' - Press: Left mouse button to move selected block here. Right mouse button to cancel.')
        self.parent_panel.get_blocks().append(self.dnd_block)
        self.is_dragging = False
        self.block_index = None
        self.block = None

        pos = self.parent_panel.mouse_frame_pos
        self.panel = wx.Panel(self.parent_panel, size=(0, 0), pos=(pos[0] - 29 / 2, pos[1] - 29 / 2))
        self.panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        self.panel.Hide()
        self.panel.Bind(wx.EVT_LEFT_UP, self.place)
        self.panel.Bind(wx.EVT_RIGHT_UP, self.cancel)
        self.panel.Layout()

    def drag(self, block):
        if self.is_dragging:
            return
        self.block = block
        self.block.hide()
        self.block_index = self.parent_panel.get_block_index(self.block)
        self.dnd_block.show()
        self.dnd_block.set_pos(self.block_index)
        self.panel.CaptureMouse()

        self.is_dragging = True

    def drop(self, index):
        if not self.is_dragging:
            return

        self.dnd_block.hide()
        self.block.show()
        self.block.set_pos(index)
        self.dnd_block.set_pos(0)

        self.is_dragging = False

    def on_mouse_move(self):
        if self.is_dragging:
            items = self.parent_panel.get_list_of_blocks_by_y_pos()

            for case in items:
                if case[1] == self.block:
                    continue
                if self.parent_panel.mouse_frame_pos[1] < case[0] + 33 or case == items[-1]:
                    if case[1] != self.dnd_block:
                        self.dnd_block.set_pos(items.index(case))
                        self.parent_panel.Layout()
                    break

    def stop_capture(self):
        if self.panel.HasCapture():
            self.panel.ReleaseMouse()

    def place(self, event):
        self.stop_capture()
        self.drop(self.parent_panel.get_block_index(self.dnd_block))

    def cancel(self, event):
        self.stop_capture()
        self.drop(self.block_index)


class Block(Action):

    def __init__(self, panel, name, keys, index=None):
        super().__init__(name=name, keys=keys)
        if panel is None:
            return
        self.panel = panel

        self.panel.detach_add_button_sizer()

        self.main_sizer = wx.BoxSizer(wx.VERTICAL)

        panel_sizer = wx.BoxSizer(wx.HORIZONTAL)

        mover_sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        remove_sizer = wx.BoxSizer(wx.HORIZONTAL)

        self.bg_panel = wx.Panel(self.panel)
        self.bg_panel.Hide()
        self.bg_panel.SetSizer(panel_sizer)
        self.bg_panel.SetBackgroundColour(wx.Colour(245, 245, 255))

        self.add_elements()

        self.mover = PlateButton(self.bg_panel, id=wx.ID_ANY, name='mover', style=4, size=(29, 29))
        self.mover.SetBackgroundColour(wx.Colour(210, 210, 255))
        self.mover.SetPressColor(wx.Colour(190, 190, 255))
        self.mover.SetPressColor(wx.Colour(180, 180, 245))
        self.mover.Bind(event=wx.EVT_LEFT_UP, handler=self.dnd_mover)

        mover_sizer.Add(self.mover, 1, wx.ALL, 0)

        remove_b = PlateButton(self.bg_panel, id=wx.ID_ANY, name='remove', style=4, size=(29, 29), bmp=CROSS_BPM)
        remove_b.SetBackgroundColour(wx.Colour(140, 0, 0))
        remove_b.SetForegroundColour(wx.Colour(255, 255, 255))
        remove_b.SetPressColor(wx.Colour(60, 0, 0))
        remove_b.Bind(event=wx.EVT_LEFT_UP, handler=self.remove)

        remove_sizer.Add(remove_b, 1, wx.ALL | wx.CENTER | wx.EXPAND, 0)

        panel_sizer.Add(mover_sizer, 0, wx.EXPAND, 4)
        panel_sizer.Add(self.sizer, 1, wx.LEFT | wx.RIGHT | wx.EXPAND, 4)
        panel_sizer.Add(remove_sizer, 0, wx.LEFT | wx.EXPAND, 4)

        self.main_sizer.Add(self.bg_panel, 0, wx.LEFT | wx.RIGHT | wx.TOP | wx.EXPAND, 4)

        self.panel.add_element(sizer=self.main_sizer, flag=wx.ALIGN_LEFT | wx.EXPAND, index=index)

        self.panel.attach_add_button_sizer()

        self.panel.Layout()

    def set_index(self, index):
        self.mover.SetLabel(f'{index}')
        self.mover.Refresh()

    def update(self):
        pass

    def add_elements(self):
        pass

    def show(self):
        if not self.bg_panel.IsShown():
            self.bg_panel.Show()
            self.bg_panel.Layout()

    def hide(self):
        if self.bg_panel.IsShown():
            self.bg_panel.Hide()
            self.bg_panel.Layout()

    def is_shown(self):
        return self.bg_panel.IsShown()

    def get_pos(self):
        return self.bg_panel.GetPosition()

    def set_pos(self, index):
        self.panel.set_block_pos(self, index)

    def dnd_mover(self, event):
        self.panel.dnd.drag(self)

    def remove(self, event=None):
        self.main_sizer.Clear(True)
        self.panel.remove_from_sizer(self.main_sizer, block=self)


class Set(Block):
    def __init__(self, panel, var_name=None, value_type=None, value=None, index=None):
        super().__init__(panel=panel, name='set', keys=ACTIONS_LIST['set'], index=index)
        self.keys['var_name'] = var_name
        self.keys['value_type'] = value_type
        self.keys['value'] = value
        if self.keys['var_name'] is not None:
            global VARIABLES
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()
            # self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))
        if self.keys['value'] is not None:
            self.__value_label.SetLabel(f"{self.keys['value']}")
        if self.keys['value_type'] is not None:
            self.__b_set_value.SetLabel(self.keys['value_type'])
            self.bg_panel.Layout()

        if self.keys['value_type'] == 'get':
            self.__value_label.SetLabel(f"({self.keys['value']['index']['value']})")
            self.__b_set_value.SetLabel(f"{self.keys['value']['list']}.get")
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Set     ')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()
        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        text = wx.StaticText(self.bg_panel, label='to')

        self.__b_set_value = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Select', style=4)
        self.__b_set_value.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__b_set_value.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_set_value.Bind(event=wx.EVT_LEFT_UP, handler=self.set_value_dialog)

        self.__value_label = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_set_value, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__value_label, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    @overrides(Block)
    def update(self):
        self.update_choices()

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()) + ['[New]'])
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        if self.__ch_var.GetString(self.__ch_var.GetSelection()) == '[New]':
            self.__ch_var.Select(-1)
            with NewVarDialog() as dlg:
                dlg.SetPosition(self.panel.ClientToScreen((APP_FRAME_SIZE[0] / 2 - SET_VALUE_DIALOG_SIZE[0] / 2,
                                                           APP_FRAME_SIZE[1] / 2 - SET_VALUE_DIALOG_SIZE[1] / 2)))
                result = dlg.ShowModal()
                if result != wx.ID_OK:
                    self.keys['var_name'] = list(VARIABLES.keys())[result]
                    self.panel.update()
                    self.__ch_var.Select(result)
        else:
            self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def set_value_dialog(self, event):
        if self.__ch_var.GetSelection() == -1:
            return

        with SetValueDialog(self.set_value) as dlg:
            dlg.SetPosition(self.panel.ClientToScreen((APP_FRAME_SIZE[0] / 2 - SET_VALUE_DIALOG_SIZE[0] / 2,
                                                       APP_FRAME_SIZE[1] / 2 - SET_VALUE_DIALOG_SIZE[1] / 2)))
            result = dlg.ShowModal()

    def set_value(self, value, value_type):
        self.keys['value'] = value
        self.keys['value_type'] = value_type
        if VARIABLES[self.keys['var_name']] is None:
            VARIABLES[self.keys['var_name']] = {}
        # VARIABLES[self.keys['var_name']]['value_type'] = value_type

        if value_type == 'get':
            self.__value_label.SetLabel(f"({value['index']['value']})")
            self.__b_set_value.SetLabel(f"{value['list']}.get")
            self.bg_panel.Layout()
            return

        self.__value_label.SetLabel(f"{self.keys['value']}")
        self.__b_set_value.SetLabel(value_type)
        self.bg_panel.Layout()

    def get_var_name(self):
        return self.keys['var_name']


class While(Block):
    def __init__(self, panel, condition=None, actions=None, index=None):
        super().__init__(panel=panel, name='while', keys=ACTIONS_LIST['while'], index=index)
        if condition is not None:
            self.keys['condition'] = condition
        else:
            self.keys['condition'] = {
                "type": "compare",
                "keys": {
                    "left_key": {
                        "type": "empty"
                    },
                    "operator": "==",
                    "right_key": {
                        "type": "empty"
                    }
                }
            }

        if actions is not None:
            self.keys['actions'] = actions
            self.find_var_names(self.keys['actions'])
        else:
            self.keys['actions'] = []
        self.__action_count_label.SetLabel(f"Action count: {len(self.keys['actions'])}")

    def find_var_names(self, actions):
        for action in actions:
            if action['action_name'] == 'set' and not list(VARIABLES.keys()).__contains__(action['keys']['var_name']):
                VARIABLES[action['keys']['var_name']] = {}
            elif action['action_name'] == 'while':
                self.find_var_names(action['keys']['actions'])

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='While')
        self.__ch_condition = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Condition', style=4)
        self.__ch_condition.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__ch_condition.Bind(event=wx.EVT_LEFT_UP, handler=self.on_condition)

        text = wx.StaticText(self.bg_panel, label='do')

        b_script = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Script', style=4)
        b_script.SetBackgroundColour(wx.Colour(224, 224, 224))
        b_script.Bind(event=wx.EVT_LEFT_UP, handler=self.open_script)

        self.__action_count_label = wx.StaticText(self.bg_panel, label='')

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_condition, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(b_script, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__action_count_label, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def choice(self, event):
        if self.__ch_condition.GetString(self.__ch_condition.GetSelection()) == 'True':
            self.keys['condition'] = True
        elif self.__ch_condition.GetString(self.__ch_condition.GetSelection()) == 'False':
            self.keys['condition'] = False

    def on_condition(self, event):
        with SetConditionDialog(self.keys['condition'], self.set_condition) as dlg:
            result = dlg.ShowModal()

    def set_condition(self, condition):
        self.keys['condition'] = condition

    def open_script(self, event):
        with ScriptDialog(self.keys['actions'], self.set_actions) as dlg:
            dlg.SetPosition(self.panel.get_pos())
            result = dlg.ShowModal()

    def set_actions(self, actions):
        self.keys['actions'] = actions
        self.__action_count_label.SetLabel(f"Action count: {len(self.keys['actions'])}")

    def get_condition(self):
        return self.keys['condition']


class Break(Block):
    def __init__(self, panel, if_bool=False, condition=None, index=None):
        super().__init__(panel=panel, name='break', keys=ACTIONS_LIST['break'], index=index)
        self.keys['if'] = if_bool
        self.keys['condition'] = condition

        if self.keys['if']:
            self.bool_if.SetValue(True)

        if self.keys['condition'] is None:
            self.keys['condition'] = {
                "type": "compare",
                "keys": {
                    "left_key": {
                        "type": "empty"
                    },
                    "operator": "==",
                    "right_key": {
                        "type": "empty"
                    }
                }
            }

        self.update_button()

    @overrides(Block)
    def add_elements(self):
        text = wx.StaticText(self.bg_panel, label='Break')

        self.bool_if = wx.CheckBox(self.bg_panel, label='if')
        self.bool_if.Bind(event=wx.EVT_CHECKBOX, handler=self.bool_input)

        self.b_condition = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Condition', style=4)
        self.b_condition.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.b_condition.Bind(event=wx.EVT_LEFT_UP, handler=self.on_condition)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.bool_if, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.b_condition, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def on_condition(self, event):
        with SetConditionDialog(self.keys['condition'], self.set_condition) as dlg:
            result = dlg.ShowModal()

    def set_condition(self, condition):
        self.keys['condition'] = condition

    def update_button(self):
        if self.keys['if']:
            self.b_condition.Show()
        else:
            self.b_condition.Hide()
        self.bg_panel.Layout()

    def bool_input(self, event=None):
        obj = event.GetEventObject()
        if obj.IsChecked():
            self.keys['if'] = True
        else:
            self.keys['if'] = False
        self.update_button()


class DNDBlank(Block):
    def __init__(self, panel, index=None):
        super().__init__(panel=panel, name='dnd_blank', keys=None, index=index)

    @overrides(Block)
    def add_elements(self):
        self.text = wx.StaticText(self.bg_panel, label='')

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.text, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)


class RecordingDialog(wx.Dialog):
    def __init__(self, set_events):
        wx.Dialog.__init__(self, None, title='Recording', size=(240, 120),
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.set_events = set_events
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        textStart = wx.StaticText(self, label="press <F11> to start recording")
        textStop = wx.StaticText(self, label="press <F12> to stop recording")
        self.state = wx.StaticText(self, label="Waiting...")

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(textStart, 0, 0, 0)
        sizer.Add(textStop, 0, 0, 0)
        sizer.Add(self.state, 0, 0, 0)
        self.SetSizer(sizer)

        MACROS_HANDLER.handleRecording(self.__provoking_func)

    def __provoking_func(self, recording, events):
        if recording:
            self.state.SetLabel("Recording.")
        else:
            self.state.SetLabel(f"Recorded {len(events)} events")

    def __on_close(self, event):
        MACROS_HANDLER.stopHandlingRecording()
        if MACROS_HANDLER.recorder.isRecording() or MACROS_HANDLER.recorder.isDelaying():
            MACROS_HANDLER.recorder.stopRecording()

        self.set_events(MACROS_HANDLER.recorder.getEvents())
        self.EndModal(wx.ID_OK)


class MacrosDialog(wx.Dialog):
    def __init__(self, events, set_events):
        self.macros_event_blocks = []

        self.set_events = set_events
        wx.Dialog.__init__(self, None, title='Macros Editor', size=APP_FRAME_SIZE,
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.__setupToolsBar()
        self.__setupEventsWindow()
        # self.__setupEventsBar()

        self.__loadEvents(events)

        # button1 = wx.Button(self.panel2, label="Button 1", pos=(0, 50), size=(50, 50))

        # self.eventSizer = wx.BoxSizer(wx.VERTICAL)

        # self.eventSizer.Add(button1, 0, wx.ALL, 5)

    def addEventSizer(self, sizer, proportion=0, flag=wx.ALL, border=0, index=None):
        if index is None:
            self.eventSizer.Add(sizer=sizer, proportion=proportion, flag=flag, border=border)
        else:
            self.eventSizer.Insert(index=index, sizer=sizer, proportion=proportion, flag=flag, border=border)

    def getEventsLen(self):
        return len(self.macros_event_blocks)

    def __setupToolsBar(self):
        self.panel_toolbar = wx.Panel(self, size=(APP_FRAME_SIZE_PANEL[0], 28), pos=(0, 2), style=0)
        self.panel_toolbar.SetBackgroundColour('#F0F0F0')

        self.toolbar_sizer = wx.BoxSizer(wx.HORIZONTAL)

        record_button = wx.BitmapButton(self.panel_toolbar, id=wx.ID_ANY, bitmap=RECORD_ICO, size=(24, 24))
        record_button.SetCanFocus(False)
        record_button.SetBackgroundColour(wx.Colour(224, 224, 224))
        record_button.Bind(event=wx.EVT_LEFT_UP, handler=self.__onRecord)

        self.toolbar_sizer.Add(record_button, 0, 0, 0)
        self.panel_toolbar.SetSizer(self.toolbar_sizer)

    def __setupEventsWindow(self):
        self.scintilla = StyledTextCtrl(self, size=(APP_FRAME_SIZE_PANEL[0], APP_FRAME_SIZE_PANEL[1] - 28), pos=(0, 30),
                                        name='macros')
        self.scintilla.SetUseHorizontalScrollBar(0)
        # self.scintilla.SetLexer(STC_LEX_SQL)
        self.scintilla.StyleSetSpec(STC_STYLE_DEFAULT, "size:10,face:Courier New")
        self.scintilla.SetMarginLeft(0)
        self.scintilla.SetMarginRight(0)
        self.scintilla.SetMarginType(0, STC_MARGIN_NUMBER)
        self.scintilla.SetMarginWidth(0, 42)

        faces = {'mono': 'Courier New', 'helv': 'Arial', 'size': 10}
        # self.scintilla.StyleSetSpec(STC_H_DEFAULT, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
        # self.scintilla.StyleSetSpec(STC_H_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        self.scintilla.StyleSetSpec(STC_STYLE_LINENUMBER, "fore:#007F7F,size:10")
        self.scintilla.Layout()

    # def __setupEventsBar(self):
    #     self.panel_eventsBar = wx.Panel(self, size=(APP_FRAME_SIZE_PANEL[0], APP_FRAME_SIZE_PANEL[1] - 530),
    #                                     pos=(0, 530), style=0)
    #     self.panel_eventsBar.SetBackgroundColour('#F05050')
    #
    #     add_event_b = PlateButton(self.panel_eventsBar, id=wx.ID_ANY, label='Add event', style=4, size=(200, 40))
    #     add_event_b.SetBackgroundColour(wx.Colour(224, 224, 224))
    #     add_event_b.Bind(event=wx.EVT_LEFT_UP, handler=self.__add_Event)
    #     add_event_b.SetFont(JBM_FONT)
    #
    #     sizer = wx.BoxSizer(wx.HORIZONTAL)
    #     sizer.Add(add_event_b, 0, 0, 0)
    #
    #     self.panel_eventsBar.SetSizer(sizer)
    #     self.panel_eventsBar.Layout()

    # def __add_Event(self, e):
    #     event = "keyboard.press t n"
    #     # insertionPoint = self.scintilla.GetInsertionPoint()
    #     # insertionPoint = self.scintilla.GetLineEndPosition(self.scintilla.GetCurrentLine())
    #     # self.scintilla.InsertText(insertionPoint, event)
    #
    #     self.scintilla.NewLine(self.scintilla.GetCurrentLine(), "WTF")
    #     # self.scintilla.SelectNone()
    #     # self.scintilla.SetInsertionPoint(insertionPoint+len(event))

    def __loadEvents(self, events):
        text = ''
        for event in events:
            text += event['type'] + ' ' + str(event['timing']) + ' '
            if event['type'] in macro.MacrosEvents.COORDS_EVENTS:
                text += str(event['keys']['x']) + ' ' + str(event['keys']['y']) + ' '
            if event['type'] in macro.MacrosEvents.BUTTON_EVENTS:
                try:
                    text += str(event['keys']['button']) + ' '
                except KeyError:
                    text += str(event['keys']['key']) + ' '
            text += '\n'
        self.scintilla.SetText(text)
        #     self.macros_event_blocks.append(MacrosEventBlock(self, event))
        # self.panel_eventList.Layout()
        # self.setupScrollingEvents()
        pass

    def __on_close(self, event):
        text = self.scintilla.GetText().replace('\r', '').replace('\t', '').split(" \n")

        events = []
        for line in text:
            if line == "":
                continue
            words = line.split(' ')

            if len(words) < 3:
                continue
            if words[0] in macro.MacrosEvents.KEYBOARD_EVENTS:
                events.append({
                    'type': words[0],
                    'timing': float(words[1]),
                    'keys': {
                        'key': int(words[2])
                    }
                })
                continue
            if len(words) < 4:
                continue
            if words[0] == macro.MacrosEvents.MOUSE_MOVED:
                events.append({
                    'type': macro.MacrosEvents.MOUSE_MOVED,
                    'timing': float(words[1]),
                    'keys': {
                        'x': int(words[2]),
                        'y': int(words[3])
                    }
                })
                continue
            if len(words) < 4:
                continue
            if words[0] in macro.MacrosEvents.MOUSE_EVENTS:
                events.append({
                    'type': words[0],
                    'timing': float(words[1]),
                    'keys': {
                        'button': words[4],
                        'x': int(words[2]),
                        'y': int(words[3])
                    }
                })
                continue

        self.set_events(events)
        self.EndModal(wx.ID_OK)

    def __onRecord(self, event):
        self.scintilla.SetFocus()
        with RecordingDialog(self.__loadEvents) as dlg:
            result = dlg.ShowModal()


class Macros(Block):
    def __init__(self, panel, events=None, index=None):
        super().__init__(panel=panel, name='macros', keys=ACTIONS_LIST['macros'], index=index)
        if events is not None:
            self.keys['events'] = events
        else:
            self.keys['events'] = []

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Play macros. ')
        self.__b_edit = PlateButton(self.bg_panel, id=wx.ID_ANY, label='[   Edit   ]', style=4)
        self.__b_edit.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__b_edit.Bind(event=wx.EVT_LEFT_UP, handler=self.on_edit)
        self.__b_edit.SetFont(JBM_FONT)

        self.__events_count_label = wx.StaticText(self.bg_panel, label='')

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_edit, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__events_count_label, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def set_events(self, events):
        self.keys['events'] = events

    def on_edit(self, event=None):
        with MacrosDialog(self.keys['events'], self.set_events) as dlg:
            result = dlg.ShowModal()


class LoadImage(Block):
    def __init__(self, panel, var_name=None, raw_image=None, index=None):
        super().__init__(panel=panel, name='load_image', keys=ACTIONS_LIST['load_image'], index=index)
        self.keys['var_name'] = var_name
        self.keys['raw_image'] = raw_image

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Load Image to')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__b_open_file = PlateButton(self.bg_panel, id=wx.ID_ANY, label='File', style=4)
        self.__b_open_file.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__b_open_file.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_open_file.Bind(event=wx.EVT_LEFT_UP, handler=self.open_file)

        self.__b_show = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Show', style=4)
        self.__b_show.SetBackgroundColour(wx.Colour(210, 210, 255))
        self.__b_show.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_show.Bind(event=wx.EVT_LEFT_UP, handler=self.show_img)

        empty_label = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_open_file, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_show, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_label, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    @overrides(Block)
    def update(self):
        self.update_choices()

    def update_choices(self):
        # image_vars = []
        # for v in list(VARIABLES.keys()):
        #     if VARIABLES[v]['value_type'] == 'image':
        #         image_vars.append(v)
        # self.__ch_var.Set(image_vars)
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def open_file(self, event):
        file_dlg = wx.FileDialog(self.bg_panel, "Open image file", "", "", "*.png", wx.FD_OPEN)
        if file_dlg.ShowModal() == wx.ID_OK:
            self.open_path = file_dlg.GetPath()
        else:
            return

        img = imageio.imread(self.open_path)
        for row in img:
            for column in row:
                temp = column[0]
                column[0] = column[2]
                column[2] = temp

        self.keys['raw_image'] = json.dumps(img.tolist())

    def show_img(self, event):
        if self.keys['raw_image'] is None:
            return
        img_load = np.array(json.loads(self.keys['raw_image'])).astype('uint8')
        cv2.setWindowProperty('image', cv2.WND_PROP_AUTOSIZE, cv2.WINDOW_AUTOSIZE)
        cv2.imshow('image', img_load)


class WindowCapturingDialog(wx.Dialog):
    def __init__(self, set_window):
        wx.Dialog.__init__(self, None, title='Window Capture', size=(600, 240),
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.set_window = set_window
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        textStart = wx.StaticText(self, label="1. Select window.")
        textStop = wx.StaticText(self, label="2. Press <F11> to save window name.")
        # self.win_exe = wx.StaticText(self, label="Waiting...")
        self.win_name = wx.StaticText(self, label="Waiting...")

        self.__sub_windows = wx.Choice(self, id=wx.ID_ANY, size=(590, -1), )
        self.__sub_windows.Show(False)


        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(textStart, 0, 0, 0)
        sizer.Add(textStop, 0, 0, 0)
        # sizer.Add(self.win_exe, 0, 0, 0)
        sizer.Add(self.win_name, 0, 0, 0)
        sizer.Add(self.__sub_windows, 0, 0, 0)
        self.SetSizer(sizer)

        MACROS_HANDLER.add_keyboard_callback(keyboard.Key.f11, self.key_callback)

    def key_callback(self):
        self.win_name.SetLabel(WindowCapture.get_foreground_window_name())
        self.__sub_windows.Show()
        self.__sub_windows.Set(WindowCapture.get_foreground_window_subs())
        self.__sub_windows.Select(0)
        self.Layout()

    def __on_close(self, event):
        MACROS_HANDLER.remove_keyboard_callback(keyboard.Key.f11, self.key_callback)
        if self.win_name.GetLabel() != "Waiting...":
            self.set_window(self.win_name.GetLabel(), self.__sub_windows.GetString(self.__sub_windows.GetSelection()))
        self.EndModal(wx.ID_OK)


class FindWindow(Block):
    def __init__(self, panel, var_name=None, window_name=None, sub_window=None, index=None):
        super().__init__(panel=panel, name='find_window', keys=ACTIONS_LIST['find_window'], index=index)
        self.keys['var_name'] = var_name
        # self.keys['process_exe'] = process_exe      # , process_exe=None
        self.keys['window_name'] = window_name
        self.keys['sub_window'] = sub_window

        l_upd = False

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()
        if self.keys['window_name'] is not None:  # (self.keys['process_exe'] is not None) and
            # self.__b_win_sel.SetToolTip(f"{self.keys['window_name']}")  # {self.keys['process_exe']}
            self.__in__win.SetValue(self.keys['window_name'])
            l_upd = True
        if self.keys['sub_window'] is not None:
            self.__in__sub.SetValue(self.keys['sub_window'])
            l_upd = True

        if l_upd:
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Find window ')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__b_win_sel = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Window Finder', style=4)
        self.__b_win_sel.SetToolTip("")
        self.__b_win_sel.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__b_win_sel.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_win_sel.Bind(event=wx.EVT_LEFT_UP, handler=self.select_window)

        winname_txt = wx.StaticText(self.bg_panel, label=" Window Name:")
        self.__in__win = wx.TextCtrl(self.bg_panel, size=(320, -1))
        self.__in__sub = wx.TextCtrl(self.bg_panel, size=(320, -1))
        # self.__in__win.Bind(wx.EVT_CHAR, string_input_filter)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_win_sel, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(winname_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__win, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in__sub, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_keys(self):
        self.keys['window_name'] = self.__in__win.GetValue()
        self.keys['sub_window'] = self.__in__sub.GetValue()

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}

    @overrides(Block)
    def update(self):
        self.update_choices()

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def __set_window(self, window_name, sub_window):
        self.keys['window_name'] = window_name
        self.keys['sub_window'] = sub_window
        # self.__b_win_sel.SetToolTip(f"{self.keys['window_name']}")
        self.__in__win.SetValue(self.keys['window_name'])
        self.__in__sub.SetValue(self.keys['sub_window'])
        self.bg_panel.Layout()

    def select_window(self, event):
        with WindowCapturingDialog(self.__set_window) as dlg:
            result = dlg.ShowModal()


class CaptureImage(Block):
    def __init__(self, panel, var_name=None, window=None, x=None, y=None, w=None, h=None, index=None):
        super().__init__(panel=panel, name='capture_image', keys=ACTIONS_LIST['capture_image'], index=index)
        self.keys['var_name'] = var_name
        self.keys['window'] = window
        self.keys['x'] = x
        self.keys['y'] = y
        self.keys['w'] = w
        self.keys['h'] = h

        l_upd = False

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()
        if self.keys['window'] is not None:  # (self.keys['process_exe'] is not None) and
            VARIABLES[self.keys['window']] = {}
            self.update_choices_handler()

        if self.keys['x'] is not None:
            self.__in__x.SetValue(f"{self.keys['x']}")
            l_upd = True
        if self.keys['y'] is not None:
            self.__in__y.SetValue(f"{self.keys['y']}")
            l_upd = True
        if self.keys['w'] is not None:
            self.__in__w.SetValue(f"{self.keys['w']}")
            l_upd = True
        if self.keys['h'] is not None:
            self.__in__h.SetValue(f"{self.keys['h']}")
            l_upd = True

        if l_upd:
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Capture Image to')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        handler_txt = wx.StaticText(self.bg_panel, label=' Handler:')

        self.__ch_handler = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices_handler()
        self.__ch_handler.Bind(event=wx.EVT_CHOICE, handler=self.choice_handler)
        self.__ch_handler.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        x_txt = wx.StaticText(self.bg_panel, label=' X:')
        self.__in__x = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__x.SetValue('0')
        self.__in__x.Bind(wx.EVT_CHAR, integer_input_filter)

        y_txt = wx.StaticText(self.bg_panel, label=' Y:')
        self.__in__y = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__y.SetValue('0')
        self.__in__y.Bind(wx.EVT_CHAR, integer_input_filter)

        w_txt = wx.StaticText(self.bg_panel, label=' W:')
        self.__in__w = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__w.SetValue('0')
        self.__in__w.Bind(wx.EVT_CHAR, integer_input_filter)

        h_txt = wx.StaticText(self.bg_panel, label=' H:')
        self.__in__h = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__h.SetValue('0')
        self.__in__h.Bind(wx.EVT_CHAR, integer_input_filter)

        # self.__b_preview = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Preview', style=4)
        # self.__b_preview.SetBackgroundColour(wx.Colour(224, 224, 224))
        # self.__b_preview.SetPressColor(wx.Colour(190, 180, 0))
        # self.__b_preview.Bind(event=wx.EVT_LEFT_UP, handler=self.preview)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(handler_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__ch_handler, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(x_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__x, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(y_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__y, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(w_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__w, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(h_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        # sizer.Add(self.__b_preview, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_keys(self):
        self.keys['x'] = int(self.__in__x.GetValue())
        self.keys['y'] = int(self.__in__y.GetValue())
        self.keys['w'] = int(self.__in__w.GetValue())
        self.keys['h'] = int(self.__in__h.GetValue())

    @overrides(Block)
    def update(self):
        self.update_choices()
        self.update_choices_handler()

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def update_choices_handler(self):
        self.__ch_handler.Set(list(VARIABLES.keys()))
        if self.keys['window'] is not None:
            self.__ch_handler.Select(list(VARIABLES.keys()).index(self.keys['window']))

    def choice_handler(self, event):
        self.keys['window'] = self.__ch_handler.GetString(self.__ch_handler.GetSelection())

    # def preview(self, event):
    #     self.update_keys()
    #     img = WindowCapture.fast_capture(WindowCapture.get_window_hwnd(self.keys['window_name']), self.keys['x'],
    #                                      self.keys['y'], self.keys['w'],
    #                                      self.keys['h'])
    #     if img is None:
    #         return
    #
    #     cv2.imshow('Preview', img)


class CaptureImageMousePos(Block):
    def __init__(self, panel, var_name=None, window=None, w=None, h=None, index=None):
        super().__init__(panel=panel, name='capture_image_mouse_pos', keys=ACTIONS_LIST['capture_image_mouse_pos'],
                         index=index)
        self.keys['var_name'] = var_name
        self.keys['window'] = window
        self.keys['w'] = w
        self.keys['h'] = h

        l_upd = False

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()
        if self.keys['window'] is not None:  # (self.keys['process_exe'] is not None) and
            VARIABLES[self.keys['window']] = {}
            self.update_choices_handler()

        if self.keys['w'] is not None:
            self.__in__w.SetValue(f"{self.keys['w']}")
            l_upd = True
        if self.keys['h'] is not None:
            self.__in__h.SetValue(f"{self.keys['h']}")
            l_upd = True

        if l_upd:
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Capture Image (Mouse Pos) to')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        handler_txt = wx.StaticText(self.bg_panel, label=' Handler:')

        self.__ch_handler = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices_handler()
        self.__ch_handler.Bind(event=wx.EVT_CHOICE, handler=self.choice_handler)
        self.__ch_handler.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        w_txt = wx.StaticText(self.bg_panel, label=' W:')
        self.__in__w = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__w.SetValue('0')
        self.__in__w.Bind(wx.EVT_CHAR, integer_input_filter)

        h_txt = wx.StaticText(self.bg_panel, label=' H:')
        self.__in__h = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__h.SetValue('0')
        self.__in__h.Bind(wx.EVT_CHAR, integer_input_filter)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(handler_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__ch_handler, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(w_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__w, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(h_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_keys(self):
        self.keys['w'] = int(self.__in__w.GetValue())
        self.keys['h'] = int(self.__in__h.GetValue())

    @overrides(Block)
    def update(self):
        self.update_choices()
        self.update_choices_handler()

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def update_choices_handler(self):
        self.__ch_handler.Set(list(VARIABLES.keys()))
        if self.keys['window'] is not None:
            self.__ch_handler.Select(list(VARIABLES.keys()).index(self.keys['window']))

    def choice_handler(self, event):
        self.keys['window'] = self.__ch_handler.GetString(self.__ch_handler.GetSelection())


class ScreenshotImage(Block):
    def __init__(self, panel, var_name=None, x=None, y=None, w=None, h=None, index=None):
        super().__init__(panel=panel, name='screenshot_image', keys=ACTIONS_LIST['screenshot_image'], index=index)
        self.keys['var_name'] = var_name
        self.keys['x'] = x
        self.keys['y'] = y
        self.keys['w'] = w
        self.keys['h'] = h

        l_upd = False

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()

        if self.keys['x'] is not None:
            self.__in__x.SetValue(f"{self.keys['x']}")
            l_upd = True
        if self.keys['y'] is not None:
            self.__in__y.SetValue(f"{self.keys['y']}")
            l_upd = True
        if self.keys['w'] is not None:
            self.__in__w.SetValue(f"{self.keys['w']}")
            l_upd = True
        if self.keys['h'] is not None:
            self.__in__h.SetValue(f"{self.keys['h']}")
            l_upd = True

        if l_upd:
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Screenshot Image to')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        x_txt = wx.StaticText(self.bg_panel, label=' X:')
        self.__in__x = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__x.SetValue('0')
        self.__in__x.Bind(wx.EVT_CHAR, integer_input_filter)

        y_txt = wx.StaticText(self.bg_panel, label=' Y:')
        self.__in__y = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__y.SetValue('0')
        self.__in__y.Bind(wx.EVT_CHAR, integer_input_filter)

        w_txt = wx.StaticText(self.bg_panel, label=' W:')
        self.__in__w = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__w.SetValue('0')
        self.__in__w.Bind(wx.EVT_CHAR, integer_input_filter)

        h_txt = wx.StaticText(self.bg_panel, label=' H:')
        self.__in__h = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__h.SetValue('0')
        self.__in__h.Bind(wx.EVT_CHAR, integer_input_filter)

        self.__b_preview = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Preview', style=4)
        self.__b_preview.SetBackgroundColour(wx.Colour(210, 210, 255))
        self.__b_preview.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_preview.Bind(event=wx.EVT_LEFT_UP, handler=self.preview)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(x_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__x, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(y_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__y, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(w_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__w, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(h_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_preview, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_keys(self):
        self.keys['x'] = int(self.__in__x.GetValue())
        self.keys['y'] = int(self.__in__y.GetValue())
        self.keys['w'] = int(self.__in__w.GetValue())
        self.keys['h'] = int(self.__in__h.GetValue())

    @overrides(Block)
    def update(self):
        self.update_choices()

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def preview(self, event):
        self.update_keys()
        img = WindowCapture.fast_screen_capture(self.keys['x'], self.keys['y'], self.keys['w'], self.keys['h'])

        if img is None:
            return

        cv2.imshow('Preview', img)


class ScreenshotImageMousePos(Block):
    def __init__(self, panel, var_name=None, w=None, h=None, index=None):
        super().__init__(panel=panel, name='screenshot_image_mouse_pos',
                         keys=ACTIONS_LIST['screenshot_image_mouse_pos'], index=index)
        self.keys['var_name'] = var_name
        self.keys['w'] = w
        self.keys['h'] = h

        l_upd = False

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()

        if self.keys['w'] is not None:
            self.__in__w.SetValue(f"{self.keys['w']}")
            l_upd = True
        if self.keys['h'] is not None:
            self.__in__h.SetValue(f"{self.keys['h']}")
            l_upd = True

        if l_upd:
            self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Screenshot Image (Mouse Pos) to')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()

        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        w_txt = wx.StaticText(self.bg_panel, label=' W:')
        self.__in__w = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__w.SetValue('0')
        self.__in__w.Bind(wx.EVT_CHAR, integer_input_filter)

        h_txt = wx.StaticText(self.bg_panel, label=' H:')
        self.__in__h = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__h.SetValue('0')
        self.__in__h.Bind(wx.EVT_CHAR, integer_input_filter)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(w_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__w, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(h_txt, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(self.__in__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_keys(self):
        self.keys['w'] = int(self.__in__w.GetValue())
        self.keys['h'] = int(self.__in__h.GetValue())

    @overrides(Block)
    def update(self):
        self.update_choices()

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())


class MouseMove(Block):
    def __init__(self, panel, var_name=None, window_space=False, window=None, index=None):
        super().__init__(panel=panel, name='mouse_move', keys=ACTIONS_LIST['mouse_move'], index=index)
        self.keys['var_name'] = var_name
        self.keys['window_space'] = window_space
        self.keys['window'] = window

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()

        if self.keys['window_space']:
            self.bool_in_win.SetValue(True)
            self.bool_in_win.SetLabel('Window space?   Handler:')
            self.__ch_handler.Show()
            self.bg_panel.Layout()

        if self.keys['window'] is not None:
            VARIABLES[self.keys['window']] = {}
            self.update_choices_handler()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Mouse Move   Coords:')
        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()
        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)


        self.bool_in_win = wx.CheckBox(self.bg_panel, label='Window space? ')
        self.bool_in_win.Bind(event=wx.EVT_CHECKBOX, handler=self.bool_input)

        self.__ch_handler = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices_handler()
        self.__ch_handler.Bind(event=wx.EVT_CHOICE, handler=self.choice_handler)
        self.__ch_handler.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_handler.Show(False)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.bool_in_win, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_handler, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def bool_input(self, event):
        obj = event.GetEventObject()
        if obj.IsChecked():
            self.keys['window_space'] = True
            obj.SetLabel('Window space?   Handler:')
            self.__ch_handler.Show()
        else:
            self.keys['window_space'] = False
            obj.SetLabel('Window space? ')
            self.__ch_handler.Show(False)
        self.bg_panel.Layout()

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    @overrides(Block)
    def update(self):
        self.update_choices()
        self.update_choices_handler()

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def update_choices_handler(self):
        self.__ch_handler.Set(list(VARIABLES.keys()))
        if self.keys['window'] is not None:
            self.__ch_handler.Select(list(VARIABLES.keys()).index(self.keys['window']))

    def choice_handler(self, event):
        self.keys['window'] = self.__ch_handler.GetString(self.__ch_handler.GetSelection())


class MouseButton(Block):
    def __init__(self, panel, var_name=None, action=None, button=None, window_space=False, window=None, index=None):
        super().__init__(panel=panel, name='mouse_button', keys=ACTIONS_LIST['mouse_button'], index=index)
        self.keys['var_name'] = var_name
        self.keys['action'] = action
        self.keys['button'] = button
        self.keys['window_space'] = window_space
        self.keys['window'] = window

        if self.keys['var_name'] is not None:
            VARIABLES[self.keys['var_name']] = {}
            self.update_choices()

        if self.keys['action'] is not None:
            self.__ch_action.Select(["click", 'press', 'release'].index(self.keys['action']))
        else:
            self.keys['action'] = 'click'

        if self.keys['button'] is not None:
            self.__ch_button.Select(["left", 'right'].index(self.keys['button']))
        else:
            self.keys['button'] = 'left'

        if self.keys['window_space']:
            self.bool_in_win.SetValue(True)
            self.bool_in_win.SetLabel('Window space?   Handler:')
            self.__ch_handler.Show()
            self.bg_panel.Layout()

        if self.keys['window'] is not None:
            VARIABLES[self.keys['window']] = {}
            self.update_choices_handler()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Mouse Button   Coords:')

        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()
        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__ch_action = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_action.Set(["click", 'press', 'release'])
        self.__ch_action.Bind(event=wx.EVT_CHOICE, handler=self.action_input)
        self.__ch_action.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_action.Select(0)

        self.__ch_button = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_button.Set(["left", 'right'])
        self.__ch_button.Bind(event=wx.EVT_CHOICE, handler=self.button_input)
        self.__ch_button.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_button.Select(0)

        self.bool_in_win = wx.CheckBox(self.bg_panel, label='Window space? ')
        self.bool_in_win.Bind(event=wx.EVT_CHECKBOX, handler=self.bool_input)

        self.__ch_handler = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices_handler()
        self.__ch_handler.Bind(event=wx.EVT_CHOICE, handler=self.choice_handler)
        self.__ch_handler.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_handler.Show(False)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_action, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_button, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.bool_in_win, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_handler, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def bool_input(self, event):
        obj = event.GetEventObject()
        if obj.IsChecked():
            self.keys['window_space'] = True
            obj.SetLabel('Window space?   Handler:')
            self.__ch_handler.Show()
        else:
            self.keys['window_space'] = False
            obj.SetLabel('Window space? ')
            self.__ch_handler.Show(False)
        self.bg_panel.Layout()

    @overrides(Block)
    def update(self):
        self.update_choices()
        self.update_choices_handler()

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def update_choices_handler(self):
        self.__ch_handler.Set(list(VARIABLES.keys()))
        if self.keys['window'] is not None:
            self.__ch_handler.Select(list(VARIABLES.keys()).index(self.keys['window']))

    def choice_handler(self, event):
        self.keys['window'] = self.__ch_handler.GetString(self.__ch_handler.GetSelection())

    def action_input(self, event):
        self.keys['action'] = self.__ch_action.GetString(self.__ch_action.GetSelection())

    def button_input(self, event):
        self.keys['button'] = self.__ch_button.GetString(self.__ch_button.GetSelection())


class FocusWindow(Block):
    def __init__(self, panel, window=None, index=None):
        super().__init__(panel=panel, name='focus_window', keys=ACTIONS_LIST['focus_window'], index=index)
        self.keys['window'] = window

        if self.keys['window'] is not None:  # (self.keys['process_exe'] is not None) and
            VARIABLES[self.keys['window']] = {}
            self.update_choices_handler()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Focus Window ')

        self.__ch_handler = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices_handler()
        self.__ch_handler.Bind(event=wx.EVT_CHOICE, handler=self.choice_handler)
        self.__ch_handler.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_handler, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_choices_handler(self):
        self.__ch_handler.Set(list(VARIABLES.keys()))
        if self.keys['window'] is not None:
            self.__ch_handler.Select(list(VARIABLES.keys()).index(self.keys['window']))

    def choice_handler(self, event):
        self.keys['window'] = self.__ch_handler.GetString(self.__ch_handler.GetSelection())

    @overrides(Block)
    def update(self):
        self.update_choices_handler()


class HSVFilterDialog(wx.Dialog):
    def __init__(self, set_hsv, filter):
        wx.Dialog.__init__(self, None, title='HSV Filter', size=(760, 380),
                           style=wx.DIALOG_NO_PARENT | wx.DEFAULT_DIALOG_STYLE)
        self.filter : vision.HsvFilter = filter
        self.set_hsv = set_hsv
        self.Bind(event=wx.EVT_CLOSE, handler=self.__on_close)

        self.demo_img = None
        self.max_size = 320

        s__h = wx.BoxSizer(wx.HORIZONTAL)
        self.t__h = wx.StaticText(self, label=f'Hue')
        self.__s__h = RangeSlider(self, lowValue=self.filter.h_min, highValue=self.filter.h_max, minValue=0, maxValue=179, size=(240, -1))
        self.__s__h.Bind(wx.EVT_SLIDER, self.__h_changed)
        s__h.Add(self.__s__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__h.Add(self.t__h, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        s__s = wx.BoxSizer(wx.HORIZONTAL)
        self.t__s = wx.StaticText(self, label=f'Saturation')
        self.__s__s = RangeSlider(self, lowValue=self.filter.s_min, highValue=self.filter.s_max, minValue=0, maxValue=255, size=(240, -1))
        self.__s__s.Bind(wx.EVT_SLIDER, self.__s_changed)
        s__s.Add(self.__s__s, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__s.Add(self.t__s, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        s__v = wx.BoxSizer(wx.HORIZONTAL)
        self.t__v = wx.StaticText(self, label=f'Value')
        self.__s__v = RangeSlider(self, lowValue=self.filter.v_min, highValue=self.filter.v_max, minValue=0, maxValue=255, size=(240, -1))
        self.__s__v.Bind(wx.EVT_SLIDER, self.__v_changed)
        s__v.Add(self.__s__v, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__v.Add(self.t__v, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        # Saturation Add
        s__s_add = wx.BoxSizer(wx.HORIZONTAL)
        self.t__s_add = wx.StaticText(self, label=f'Saturation Add')
        self.__s__s_add = wx.Slider(self, value=self.filter.s_add, minValue=0, maxValue=255, size=(240, -1), style=wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS)
        self.__s__s_add.Bind(wx.EVT_SLIDER, self.__s_add_changed)
        s__s_add.Add(self.__s__s_add, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__s_add.Add(self.t__s_add, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        s__s_sub = wx.BoxSizer(wx.HORIZONTAL)
        self.t__s_sub = wx.StaticText(self, label=f'Saturation Sub')
        self.__s__s_sub = wx.Slider(self, value=self.filter.s_sub, minValue=0, maxValue=255, size=(240, -1), style=wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS)
        self.__s__s_sub.Bind(wx.EVT_SLIDER, self.__s_sub_changed)
        s__s_sub.Add(self.__s__s_sub, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__s_sub.Add(self.t__s_sub, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        # Saturation Add
        s__v_add = wx.BoxSizer(wx.HORIZONTAL)
        self.t__v_add = wx.StaticText(self, label=f'Value Add')
        self.__s__v_add = wx.Slider(self, value=self.filter.v_add, minValue=0, maxValue=255, size=(240, -1), style=wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS)
        self.__s__v_add.Bind(wx.EVT_SLIDER, self.__v_add_changed)
        s__v_add.Add(self.__s__v_add, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__v_add.Add(self.t__v_add, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        s__v_sub = wx.BoxSizer(wx.HORIZONTAL)
        self.t__v_sub = wx.StaticText(self, label=f'Value Sub')
        self.__s__v_sub = wx.Slider(self, value=self.filter.v_sub, minValue=0, maxValue=255, size=(240, -1), style=wx.SL_HORIZONTAL|wx.SL_MIN_MAX_LABELS)
        self.__s__v_sub.Bind(wx.EVT_SLIDER, self.__v_sub_changed)
        s__v_sub.Add(self.__s__v_sub, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        s__v_sub.Add(self.t__v_sub, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        s_sliders = wx.BoxSizer(wx.VERTICAL)
        s_sliders.Add(s__h, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__s, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__v, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__s_add, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__s_sub, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__v_add, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
        s_sliders.Add(s__v_sub, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)

        # self.image_handler = wx.StaticBitmap(self, size=(320, 320))
        self.image_handler = wx.BitmapButton(self, size=(320, 320), style=wx.BORDER_NONE)
        self.image_handler.Bind(event=wx.EVT_LEFT_UP, handler=self.open_file)


        preview_sizer = wx.BoxSizer(wx.VERTICAL)
        preview_sizer.Add(self.image_handler, 1, wx.EXPAND, 0)


        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(s_sliders, 0, 0, 0)
        sizer.Add(preview_sizer, 1, 0, 0)

        self.SetSizer(sizer)
        self.Layout()

        self.last_time = time()

    def __h_changed(self, event):
        self.filter.h_min, self.filter.h_max = self.__s__h.GetValues()
        self.update_demo()

    def __s_changed(self, event):
        self.filter.s_min, self.filter.s_max = self.__s__s.GetValues()
        self.update_demo()

    def __v_changed(self, event):
        self.filter.v_min, self.filter.v_max = self.__s__v.GetValues()
        self.update_demo()

    def __s_add_changed(self, event):
        self.filter.s_add = self.__s__s_add.GetValue()
        self.update_demo()

    def __s_sub_changed(self, event):
        self.filter.s_sub = self.__s__s_sub.GetValue()
        self.update_demo()

    def __v_add_changed(self, event):
        self.filter.v_add = self.__s__v_add.GetValue()
        self.update_demo()

    def __v_sub_changed(self, event):
        self.filter.v_sub = self.__s__v_sub.GetValue()
        self.update_demo()

    @staticmethod
    def to_wx_bitmap(cv2_image):
        height, width = cv2_image.shape[:2]

        cv2_image_rgb = cv2.cvtColor(cv2_image, cv2.COLOR_BGR2RGB)
        return wx.Bitmap.FromBuffer(width, height, cv2_image_rgb)

    def update_demo(self):
        current_time = time()
        if (current_time - self.last_time) < 0.03333:
            return
        self.last_time = current_time
        if self.demo_img is not None:
            self.image_handler.SetBitmap(self.scale_bmp(
                HSVFilterDialog.to_wx_bitmap(vision.CVWrapper.apply_hsv(self.demo_img, self.filter))))

    def scale_bmp(self, bmp : wx.Bitmap):
        img = bmp.ConvertToImage()
        W = img.GetWidth()
        H = img.GetHeight()
        if W > H:
            NewW = self.max_size
            NewH = self.max_size * H / W
        else:
            NewH = self.max_size
            NewW = self.max_size * W / H
        return wx.Bitmap(img.Scale(NewW, NewH))

    def open_file(self, event):
        file_dlg = wx.FileDialog(self, "Open image file", "", "", "*.png", wx.FD_OPEN)
        if file_dlg.ShowModal() == wx.ID_OK:
            open_path = file_dlg.GetPath()
        else:
            return

        img = imageio.imread(open_path)
        for row in img:
            for column in row:
                temp = column[0]
                column[0] = column[2]
                column[2] = temp
        self.demo_img = img
        self.update_demo()

    def __on_close(self, event):
        self.set_hsv(self.filter)
        self.EndModal(wx.ID_OK)


class HSVFilter(Block):
    def __init__(self,
                 panel,
                 var_name=None,
                 h_min=0,
                 h_max=179,
                 s_min=0,
                 s_max=255,
                 v_min=0,
                 v_max=255,
                 s_add=0,
                 s_sub=0,
                 v_add=0,
                 v_sub=0,
                 index=None):
        super().__init__(panel=panel, name='hsv_filter', keys=ACTIONS_LIST['hsv_filter'], index=index)
        self.keys['var_name'] = var_name
        self.set_hsv(h_min, h_max, s_min, s_max, v_min, v_max, s_add, s_sub, v_add, v_sub)

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='HSV Filter ')

        self.__ch_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_choices()
        self.__ch_var.Bind(event=wx.EVT_CHOICE, handler=self.choice)
        self.__ch_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__b_settings = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Open Settings', style=4)
        self.__b_settings.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__b_settings.SetPressColor(wx.Colour(190, 180, 0))
        self.__b_settings.Bind(event=wx.EVT_LEFT_UP, handler=self.open_settings)

        self.__filter_values = wx.StaticText(self.bg_panel, label="")

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__b_settings, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__filter_values, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def set_hsv(self, h_min, h_max, s_min, s_max, v_min, v_max, s_add, s_sub, v_add, v_sub):
        self.keys['h_min'] = h_min
        self.keys['h_max'] = h_max
        self.keys['s_min'] = s_min
        self.keys['s_max'] = s_max
        self.keys['v_min'] = v_min
        self.keys['v_max'] = v_max
        self.keys['s_add'] = s_add
        self.keys['s_sub'] = s_sub
        self.keys['v_add'] = v_add
        self.keys['v_sub'] = v_sub
        self.update_text()

    def set_hsv_filter(self, filter : vision.HsvFilter ):
        self.keys['h_min'] = filter.h_min
        self.keys['h_max'] = filter.h_max
        self.keys['s_min'] = filter.s_min
        self.keys['s_max'] = filter.s_max
        self.keys['v_min'] = filter.v_min
        self.keys['v_max'] = filter.v_max
        self.keys['s_add'] = filter.s_add
        self.keys['s_sub'] = filter.s_sub
        self.keys['v_add'] = filter.v_add
        self.keys['v_sub'] = filter.v_sub
        self.update_text()

    def __as_hsv_filter(self):
        return vision.HsvFilter(self.keys['h_min'], self.keys['h_max'], self.keys['s_min'], self.keys['s_max'], self.keys['v_min'], self.keys['v_max'], self.keys['s_add'], self.keys['s_sub'], self.keys['v_add'], self.keys['v_sub'])

    def update_text(self):
        self.__filter_values.SetLabel(f"[{self.keys['h_min']}, {self.keys['h_max']}, {self.keys['s_min']}, {self.keys['s_max']}, {self.keys['v_min']}, {self.keys['v_max']}, {self.keys['s_add']}, {self.keys['s_sub']}, {self.keys['v_add']}, {self.keys['v_sub']}]")
        self.bg_panel.Layout()

    @overrides(Block)
    def update(self):
        self.update_choices()

    def update_choices(self):
        self.__ch_var.Set(list(VARIABLES.keys()))
        if self.keys['var_name'] is not None:
            self.__ch_var.Select(list(VARIABLES.keys()).index(self.keys['var_name']))

    def choice(self, event):
        self.keys['var_name'] = self.__ch_var.GetString(self.__ch_var.GetSelection())

    def open_settings(self, event=None):
        with HSVFilterDialog(self.set_hsv_filter, self.__as_hsv_filter()) as dlg:
            result = dlg.ShowModal()


class Find(Block):
    def __init__(self, panel, return_var=None, observer=None, target=None, threshold=0.5, max_results=10, use_hsv=False, hsv=None, index=None):
        super().__init__(panel=panel, name='find', keys=ACTIONS_LIST['find'], index=index)
        self.keys['return_var'] = return_var
        self.keys['observer'] = observer
        self.keys['target'] = target
        self.keys['threshold'] = threshold
        self.keys['max_results'] = max_results
        self.keys['use_hsv'] = use_hsv
        self.keys['hsv'] = hsv

        if self.keys['return_var'] is not None:
            VARIABLES[self.keys['return_var']] = {}
            self.update_ch_return_var()

        if self.keys['observer'] is not None:
            VARIABLES[self.keys['observer']] = {}
            self.update_ch_observer()

        if self.keys['target'] is not None:
            VARIABLES[self.keys['target']] = {}
            self.update_ch_target()

        if self.keys['threshold'] is not None:
            self.__in__threshold.SetValue(f"{self.keys['threshold']}")

        if self.keys['max_results'] is not None:
            self.__in__max_results.SetValue(f"{self.keys['max_results']}")

        if self.keys['use_hsv']:
            self.bool_use_hsv.SetValue(True)
            self.__ch_hsv.Show()

        if self.keys['hsv'] is not None:
            VARIABLES[self.keys['hsv']] = {}
            self.update_ch_hsv()

        self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Find ')


        txt_return_var = wx.StaticText(self.bg_panel, label=' Result:')
        self.__ch_return_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_return_var()
        self.__ch_return_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_return_var)
        self.__ch_return_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_observer = wx.StaticText(self.bg_panel, label=' Observer:')
        self.__ch_observer = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_observer()
        self.__ch_observer.Bind(event=wx.EVT_CHOICE, handler=self.choice_observer)
        self.__ch_observer.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_target = wx.StaticText(self.bg_panel, label=' Target:')
        self.__ch_target = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_target()
        self.__ch_target.Bind(event=wx.EVT_CHOICE, handler=self.choice_target)
        self.__ch_target.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_threshold = wx.StaticText(self.bg_panel, label=' Threshold:')
        self.__in__threshold = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__threshold.Bind(wx.EVT_CHAR, number_input_filter)

        txt_max_results = wx.StaticText(self.bg_panel, label=' Max Results:')
        self.__in__max_results = wx.TextCtrl(self.bg_panel, size=(64, -1))
        self.__in__max_results.Bind(wx.EVT_CHAR, number_input_filter)

        self.bool_use_hsv = wx.CheckBox(self.bg_panel, label='hsv')
        self.bool_use_hsv.Bind(event=wx.EVT_CHECKBOX, handler=self.bool_input)

        txt_hsv = wx.StaticText(self.bg_panel, label=' Filter:')
        self.__ch_hsv = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_hsv()
        self.__ch_hsv.Bind(event=wx.EVT_CHOICE, handler=self.choice_hsv)
        self.__ch_hsv.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_hsv.Show(False)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_return_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_return_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_observer, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_observer, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_target, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_target, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_threshold, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in__threshold, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_max_results, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in__max_results, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_hsv, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_hsv, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.bool_use_hsv, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_return_var(self):
        self.__ch_return_var.Set(list(VARIABLES.keys()))
        if self.keys['return_var'] is not None:
            self.__ch_return_var.Select(list(VARIABLES.keys()).index(self.keys['return_var']))

    def choice_return_var(self, event):
        self.keys['return_var'] = self.__ch_return_var.GetString(self.__ch_return_var.GetSelection())

    def update_ch_observer(self):
        self.__ch_observer.Set(list(VARIABLES.keys()))
        if self.keys['observer'] is not None:
            self.__ch_observer.Select(list(VARIABLES.keys()).index(self.keys['observer']))

    def choice_observer(self, event):
        self.keys['observer'] = self.__ch_observer.GetString(self.__ch_observer.GetSelection())

    def update_ch_target(self):
        self.__ch_target.Set(list(VARIABLES.keys()))
        if self.keys['target'] is not None:
            self.__ch_target.Select(list(VARIABLES.keys()).index(self.keys['target']))

    def choice_target(self, event):
        self.keys['target'] = self.__ch_target.GetString(self.__ch_target.GetSelection())

    def update_ch_hsv(self):
        self.__ch_hsv.Set(list(VARIABLES.keys()))
        if self.keys['hsv'] is not None:
            self.__ch_hsv.Select(list(VARIABLES.keys()).index(self.keys['hsv']))

    def choice_hsv(self, event):
        self.keys['hsv'] = self.__ch_hsv.GetString(self.__ch_hsv.GetSelection())

    def bool_input(self, event):
        obj = event.GetEventObject()
        if obj.IsChecked():
            self.keys['use_hsv'] = True
            self.__ch_hsv.Show()
        else:
            self.keys['use_hsv'] = False
            self.__ch_hsv.Show(False)
        self.bg_panel.Layout()

    @overrides(Block)
    def update(self):
        self.update_ch_return_var()
        self.update_ch_observer()
        self.update_ch_target()
        self.update_ch_hsv()

    def update_keys(self):
        self.keys['threshold'] = float(self.__in__threshold.GetValue())
        self.keys['max_results'] = int(self.__in__max_results.GetValue())

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}


class List(Block):
    def __init__(self, panel, list_var=None, action=None, value=None, index_type=None, index_int=None, index_var=None, index=None):
        super().__init__(panel=panel, name='list', keys=ACTIONS_LIST['list'], index=index)
        self.keys['list_var'] = list_var
        self.keys['action'] = action
        self.keys['value'] = value
        self.keys['index_type'] = index_type
        self.keys['index_int'] = index_int
        self.keys['index_var'] = index_var

        if self.keys['list_var'] is not None:
            VARIABLES[self.keys['list_var']] = {}
            self.update_ch_list_var()

        if self.keys['action'] is not None:
            self.__ch_action.Select(['append', 'insert', 'set', 'remove', 'clear'].index(self.keys['action']))
        else:
            self.keys['action'] = 'append'

        if self.keys['index_type'] is None:
            self.keys['index_type'] = 'integer'

        if self.keys['index_int'] is not None:
            self.__in_index_int.SetValue(str(self.keys['index_int']))
        else:
            self.__in_index_int.SetValue('0')

        if self.keys['index_var'] is not None:
            VARIABLES[self.keys['index_var']] = {}
            self.update_ch_index_var()


        self.action_update()

        self.bg_panel.Layout()


    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='List  ')

        self.__ch_list_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_list_var()
        self.__ch_list_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_list_var)
        self.__ch_list_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_action = wx.StaticText(self.bg_panel, label=' Action:')
        self.__ch_action = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_action.Set(['append', 'insert', 'set', 'remove', 'clear'])
        self.__ch_action.Bind(event=wx.EVT_CHOICE, handler=self.choice_action)
        self.__ch_action.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_action.Select(0)

        self.txt_value = wx.StaticText(self.bg_panel, label=' Value:')
        self.__ch_value = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_value()
        self.__ch_value.Bind(event=wx.EVT_CHOICE, handler=self.choice_value)
        self.__ch_value.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.txt_index = wx.StaticText(self.bg_panel, label=' Index:')
        self.__ch_index_type = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_index_type.Set(['integer', 'variable'])
        self.__ch_index_type.Select(0)
        self.__ch_index_type.Bind(event=wx.EVT_CHOICE, handler=self.choice_index_type)
        self.__ch_index_type.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__in_index_int = wx.TextCtrl(self.bg_panel, size=(96, -1))
        self.__in_index_int.Bind(wx.EVT_CHAR, integer_input_filter)

        self.__ch_index_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1))
        self.update_ch_index_var()
        self.__ch_index_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_index_var)
        self.__ch_index_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)


        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_list_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_action, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_action, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.txt_value, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.txt_index, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_index_type, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in_index_int, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_index_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_index_var(self):
        self.__ch_index_var.Set(list(VARIABLES.keys()))
        if self.keys['index_var'] is not None:
            self.__ch_index_var.Select(list(VARIABLES.keys()).index(self.keys['index_var']))

    def choice_index_var(self, event):
        self.keys['index_var'] = self.__ch_index_var.GetString(self.__ch_index_var.GetSelection())

    def update_ch_list_var(self):
        self.__ch_list_var.Set(list(VARIABLES.keys()))
        if self.keys['list_var'] is not None:
            self.__ch_list_var.Select(list(VARIABLES.keys()).index(self.keys['list_var']))

    def choice_list_var(self, event):
        self.keys['list_var'] = self.__ch_list_var.GetString(self.__ch_list_var.GetSelection())

    def update_ch_value(self):
        self.__ch_value.Set(list(VARIABLES.keys()))
        if self.keys['value'] is not None:
            self.__ch_value.Select(list(VARIABLES.keys()).index(self.keys['value']))

    def choice_value(self, event):
        self.keys['value'] = self.__ch_value.GetString(self.__ch_value.GetSelection())

    def choice_index_type(self, event):
        self.keys['index_type'] = self.__ch_index_type.GetString(self.__ch_index_type.GetSelection())
        self.index_update()

    def choice_action(self, event):
        self.keys['action'] = self.__ch_action.GetString(self.__ch_action.GetSelection())
        self.action_update()

    def index_update(self):
        if self.keys['action'] in ['append', 'clear']:
            return
        self.txt_index.Show()
        self.__ch_index_type.Show()
        if self.keys['index_type'] == 'integer':
            self.__in_index_int.Show()
            self.__ch_index_var.Hide()
        elif self.keys['index_type'] == 'variable':
            self.__in_index_int.Hide()
            self.__ch_index_var.Show()
        self.bg_panel.Layout()

    def action_update(self):
        # ['append', 'insert', 'set', 'remove', 'clear']
        # [true, true, true, false, false] value
        # [false, true, true, true, false] index
        if self.keys['action'] in ['remove', 'clear']:
            self.txt_value.Hide()
            self.__ch_value.Hide()
        else:
            self.txt_value.Show()
            self.__ch_value.Show()

        if self.keys['action'] in ['append', 'clear']:
            self.txt_index.Hide()
            self.__ch_index_type.Hide()
            self.__in_index_int.Hide()
            self.__ch_index_var.Hide()
            self.bg_panel.Layout()
        else:
            self.index_update()

    @overrides(Block)
    def update(self):
        self.update_ch_list_var()
        self.update_ch_value()
        self.update_ch_index_var()

    def update_keys(self):
        self.keys['index_int'] = int(self.__in_index_int.GetValue())

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}


class Math(Block):
    operations = ['*', '/', '+', '-', 'root', 'pow']

    def __init__(self, panel, return_var=None, value1_type=None, value1_num=None, value1_var=None, operation=None, value2_type=None, value2_num=None, value2_var=None, index=None):
        super().__init__(panel=panel, name='math', keys=ACTIONS_LIST['math'], index=index)
        self.keys['return_var'] = return_var
        self.keys['value1_type'] = value1_type
        self.keys['value1_num'] = value1_num
        self.keys['value1_var'] = value1_var
        self.keys['operation'] = operation
        self.keys['value2_type'] = value2_type
        self.keys['value2_num'] = value2_num
        self.keys['value2_var'] = value2_var

        if self.keys['return_var'] is not None:
            VARIABLES[self.keys['return_var']] = {}
            self.update_ch_return_var()


        if self.keys['value1_type'] is None:
            self.keys['value1_type'] = 'number'

        if self.keys['value1_num'] is not None:
            self.__in_value1_num.SetValue(str(self.keys['value1_num']))
        else:
            self.__in_value1_num.SetValue('0')

        if self.keys['value1_var'] is not None:
            VARIABLES[self.keys['value1_var']] = {}
            self.update_ch_value1_var()

        if self.keys['operation'] is not None:
            self.__ch_operation.Select(self.operations.index(self.keys['operation']))
        else:
            self.keys['operation'] = self.operations[0]

        if self.keys['value2_type'] is None:
            self.keys['value2_type'] = 'number'

        if self.keys['value2_num'] is not None:
            self.__in_value2_num.SetValue(str(self.keys['value2_num']))
        else:
            self.__in_value2_num.SetValue('0')

        if self.keys['value2_var'] is not None:
            VARIABLES[self.keys['value2_var']] = {}
            self.update_ch_value2_var()


        self.value1_type_update()
        self.value2_type_update()

        self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Math  ')

        self.__ch_return_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_return_var()
        self.__ch_return_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_return_var)
        self.__ch_return_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_value1 = wx.StaticText(self.bg_panel, label=' = ')
        self.__ch_value1_type = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_value1_type.Set(['number', 'variable'])
        self.__ch_value1_type.Select(0)
        self.__ch_value1_type.Bind(event=wx.EVT_CHOICE, handler=self.choice_value1_type)
        self.__ch_value1_type.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__in_value1_num = wx.TextCtrl(self.bg_panel, size=(96, -1))
        self.__in_value1_num.Bind(wx.EVT_CHAR, number_input_filter)

        self.__ch_value1_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1))
        self.update_ch_value1_var()
        self.__ch_value1_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_value1_var)
        self.__ch_value1_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_operation = wx.StaticText(self.bg_panel, label=' ')
        self.__ch_operation = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_operation.Set(self.operations)
        self.__ch_operation.Bind(event=wx.EVT_CHOICE, handler=self.choice_operation)
        self.__ch_operation.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)
        self.__ch_operation.Select(0)

        txt_value2 = wx.StaticText(self.bg_panel, label=' ')
        self.__ch_value2_type = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_value2_type.Set(['number', 'variable'])
        self.__ch_value2_type.Select(0)
        self.__ch_value2_type.Bind(event=wx.EVT_CHOICE, handler=self.choice_value2_type)
        self.__ch_value2_type.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__in_value2_num = wx.TextCtrl(self.bg_panel, size=(96, -1))
        self.__in_value2_num.Bind(wx.EVT_CHAR, number_input_filter)

        self.__ch_value2_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1))
        self.update_ch_value2_var()
        self.__ch_value2_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_value2_var)
        self.__ch_value2_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_return_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_value1, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value1_type, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in_value1_num, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value1_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_operation, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_operation, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_value2, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value2_type, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in_value2_num, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value2_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_return_var(self):
        self.__ch_return_var.Set(list(VARIABLES.keys()))
        if self.keys['return_var'] is not None:
            self.__ch_return_var.Select(list(VARIABLES.keys()).index(self.keys['return_var']))

    def choice_return_var(self, event):
        self.keys['return_var'] = self.__ch_return_var.GetString(self.__ch_return_var.GetSelection())

    def update_ch_value2_var(self):
        self.__ch_value2_var.Set(list(VARIABLES.keys()))
        if self.keys['value2_var'] is not None:
            self.__ch_value2_var.Select(list(VARIABLES.keys()).index(self.keys['value2_var']))

    def choice_value2_var(self, event):
        self.keys['value2_var'] = self.__ch_value2_var.GetString(self.__ch_value2_var.GetSelection())

    def update_ch_value1_var(self):
        self.__ch_value1_var.Set(list(VARIABLES.keys()))
        if self.keys['value1_var'] is not None:
            self.__ch_value1_var.Select(list(VARIABLES.keys()).index(self.keys['value1_var']))

    def choice_value1_var(self, event):
        self.keys['value1_var'] = self.__ch_value1_var.GetString(self.__ch_value1_var.GetSelection())

    def choice_value1_type(self, event):
        self.keys['value1_type'] = self.__ch_value1_type.GetString(self.__ch_value1_type.GetSelection())
        self.value1_type_update()

    def choice_value2_type(self, event):
        self.keys['value2_type'] = self.__ch_value2_type.GetString(self.__ch_value2_type.GetSelection())
        self.value2_type_update()

    def choice_operation(self, event):
        self.keys['operation'] = self.__ch_operation.GetString(self.__ch_operation.GetSelection())

    def value1_type_update(self):
        if self.keys['value1_type'] == 'number':
            self.__in_value1_num.Show()
            self.__ch_value1_var.Hide()
        elif self.keys['value1_type'] == 'variable':
            self.__in_value1_num.Hide()
            self.__ch_value1_var.Show()
        self.bg_panel.Layout()

    def value2_type_update(self):
        if self.keys['value2_type'] == 'number':
            self.__in_value2_num.Show()
            self.__ch_value2_var.Hide()
        elif self.keys['value2_type'] == 'variable':
            self.__in_value2_num.Hide()
            self.__ch_value2_var.Show()
        self.bg_panel.Layout()

    @overrides(Block)
    def update(self):
        self.update_ch_return_var()
        self.update_ch_value1_var()
        self.update_ch_value2_var()

    def update_keys(self):
        self.keys['value1_num'] = float(self.__in_value1_num.GetValue())
        self.keys['value2_num'] = float(self.__in_value2_num.GetValue())

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}


class If(Block):
    def __init__(self, panel, condition=None, actions=None, index=None):
        super().__init__(panel=panel, name='if', keys=ACTIONS_LIST['if'], index=index)
        self.keys['condition'] = condition
        self.keys['actions'] = actions


        if self.keys['condition'] is None:
            self.keys['condition'] = {
                "type": "compare",
                "keys": {
                    "left_key": {
                        "type": "empty"
                    },
                    "operator": "==",
                    "right_key": {
                        "type": "empty"
                    }
                }
            }

        if self.keys['actions'] is not None:
            self.find_var_names(self.keys['actions'])
        else:
            self.keys['actions'] = []
        self.__action_count_label.SetLabel(f"Action count: {len(self.keys['actions'])}")

    def find_var_names(self, actions):
        for action in actions:
            if action['action_name'] == 'set' and not list(VARIABLES.keys()).__contains__(action['keys']['var_name']):
                VARIABLES[action['keys']['var_name']] = {}
            elif action['action_name'] == 'while' or action['action_name'] == 'if':
                self.find_var_names(action['keys']['actions'])

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='If     ')
        self.__ch_condition = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Condition', style=4)
        self.__ch_condition.SetBackgroundColour(wx.Colour(224, 224, 224))
        self.__ch_condition.Bind(event=wx.EVT_LEFT_UP, handler=self.on_condition)

        text = wx.StaticText(self.bg_panel, label='do')

        b_script = PlateButton(self.bg_panel, id=wx.ID_ANY, label='Script', style=4)
        b_script.SetBackgroundColour(wx.Colour(224, 224, 224))
        b_script.Bind(event=wx.EVT_LEFT_UP, handler=self.open_script)

        self.__action_count_label = wx.StaticText(self.bg_panel, label='')

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_condition, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(text, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(b_script, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__action_count_label, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def choice(self, event):
        if self.__ch_condition.GetString(self.__ch_condition.GetSelection()) == 'True':
            self.keys['condition'] = True
        elif self.__ch_condition.GetString(self.__ch_condition.GetSelection()) == 'False':
            self.keys['condition'] = False

    def on_condition(self, event):
        with SetConditionDialog(self.keys['condition'], self.set_condition) as dlg:
            result = dlg.ShowModal()

    def set_condition(self, condition):
        self.keys['condition'] = condition

    def open_script(self, event):
        with ScriptDialog(self.keys['actions'], self.set_actions) as dlg:
            dlg.SetPosition(self.panel.get_pos())
            result = dlg.ShowModal()

    def set_actions(self, actions):
        self.keys['actions'] = actions
        self.__action_count_label.SetLabel(f"Action count: {len(self.keys['actions'])}")

    def get_condition(self):
        return self.keys['condition']


class ApplyHSV(Block):
    def __init__(self, panel, return_var=None, image_var=None, hsv=None, index=None):
        super().__init__(panel=panel, name='apply_hsv', keys=ACTIONS_LIST['apply_hsv'], index=index)
        self.keys['return_var'] = return_var
        self.keys['image_var'] = image_var
        self.keys['hsv'] = hsv

        if self.keys['return_var'] is not None:
            VARIABLES[self.keys['return_var']] = {}
            self.update_ch_return_var()

        if self.keys['image_var'] is not None:
            VARIABLES[self.keys['image_var']] = {}
            self.update_ch_image_var()

        if self.keys['hsv'] is not None:
            VARIABLES[self.keys['hsv']] = {}
            self.update_ch_hsv()

        self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Apply HSV   Image:')

        self.__ch_return_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_return_var()
        self.__ch_return_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_return_var)
        self.__ch_return_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_image_var = wx.StaticText(self.bg_panel, label='= Image:')
        self.__ch_image_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_image_var()
        self.__ch_image_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_image_var)
        self.__ch_image_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_hsv = wx.StaticText(self.bg_panel, label='with Filter:')
        self.__ch_hsv = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_hsv()
        self.__ch_hsv.Bind(event=wx.EVT_CHOICE, handler=self.choice_hsv)
        self.__ch_hsv.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_return_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_image_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_image_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_hsv, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_hsv, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_return_var(self):
        self.__ch_return_var.Set(list(VARIABLES.keys()))
        if self.keys['return_var'] is not None:
            self.__ch_return_var.Select(list(VARIABLES.keys()).index(self.keys['return_var']))

    def choice_return_var(self, event):
        self.keys['return_var'] = self.__ch_return_var.GetString(self.__ch_return_var.GetSelection())

    def update_ch_image_var(self):
        self.__ch_image_var.Set(list(VARIABLES.keys()))
        if self.keys['image_var'] is not None:
            self.__ch_image_var.Select(list(VARIABLES.keys()).index(self.keys['image_var']))

    def choice_image_var(self, event):
        self.keys['image_var'] = self.__ch_image_var.GetString(self.__ch_image_var.GetSelection())

    def update_ch_hsv(self):
        self.__ch_hsv.Set(list(VARIABLES.keys()))
        if self.keys['hsv'] is not None:
            self.__ch_hsv.Select(list(VARIABLES.keys()).index(self.keys['hsv']))

    def choice_hsv(self, event):
        self.keys['hsv'] = self.__ch_hsv.GetString(self.__ch_hsv.GetSelection())

    @overrides(Block)
    def update(self):
        self.update_ch_return_var()
        self.update_ch_image_var()
        self.update_ch_hsv()


class Wait(Block):

    def __init__(self, panel, value_type=None, value_num=None, value_var=None, index=None):
        super().__init__(panel=panel, name='wait', keys=ACTIONS_LIST['wait'], index=index)
        self.keys['value_type'] = value_type
        self.keys['value_num'] = value_num
        self.keys['value_var'] = value_var

        if self.keys['value_type'] is None:
            self.keys['value_type'] = 'number'

        if self.keys['value_num'] is not None:
            self.__in_value_num.SetValue(str(self.keys['value_num']))
        else:
            self.__in_value_num.SetValue('0.01')

        if self.keys['value_var'] is not None:
            VARIABLES[self.keys['value_var']] = {}
            self.update_ch_value_var()

        self.value_type_update()

        self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Wait  ')

        txt_value = wx.StaticText(self.bg_panel, label=' Seconds:')
        self.__ch_value_type = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.__ch_value_type.Set(['number', 'variable'])
        self.__ch_value_type.Select(0)
        self.__ch_value_type.Bind(event=wx.EVT_CHOICE, handler=self.choice_value_type)
        self.__ch_value_type.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        self.__in_value_num = wx.TextCtrl(self.bg_panel, size=(96, -1))
        self.__in_value_num.Bind(wx.EVT_CHAR, number_input_filter)

        self.__ch_value_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1))
        self.update_ch_value_var()
        self.__ch_value_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_value_var)
        self.__ch_value_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_value, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value_type, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__in_value_num, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_value_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_value_var(self):
        self.__ch_value_var.Set(list(VARIABLES.keys()))
        if self.keys['value_var'] is not None:
            self.__ch_value_var.Select(list(VARIABLES.keys()).index(self.keys['value_var']))

    def choice_value_var(self, event):
        self.keys['value_var'] = self.__ch_value_var.GetString(self.__ch_value_var.GetSelection())

    def choice_value_type(self, event):
        self.keys['value_type'] = self.__ch_value_type.GetString(self.__ch_value_type.GetSelection())
        self.value_type_update()

    def value_type_update(self):
        if self.keys['value_type'] == 'number':
            self.__in_value_num.Show()
            self.__ch_value_var.Hide()
        elif self.keys['value_type'] == 'variable':
            self.__in_value_num.Hide()
            self.__ch_value_var.Show()
        self.bg_panel.Layout()

    @overrides(Block)
    def update(self):
        self.update_ch_value_var()

    def update_keys(self):
        self.keys['value_num'] = float(self.__in_value_num.GetValue())

    @overrides(Block)
    def dump_save(self):
        self.update_keys()
        return {'action_name': self.action_name,
                'keys': self.keys}


class Sum(Block):
    def __init__(self, panel, return_var=None, list_var=None, index=None):
        super().__init__(panel=panel, name='sum', keys=ACTIONS_LIST['sum'], index=index)
        self.keys['return_var'] = return_var
        self.keys['list_var'] = list_var

        if self.keys['return_var'] is not None:
            VARIABLES[self.keys['return_var']] = {}
            self.update_ch_return_var()

        if self.keys['list_var'] is not None:
            VARIABLES[self.keys['list_var']] = {}
            self.update_ch_list_var()

        self.bg_panel.Layout()

    @overrides(Block)
    def add_elements(self):
        label = wx.StaticText(self.bg_panel, label='Sum  ')

        self.__ch_return_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_return_var()
        self.__ch_return_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_return_var)
        self.__ch_return_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        txt_list_var = wx.StaticText(self.bg_panel, label=' List:')
        self.__ch_list_var = wx.Choice(self.bg_panel, id=wx.ID_ANY, size=(96, -1), )
        self.update_ch_list_var()
        self.__ch_list_var.Bind(event=wx.EVT_CHOICE, handler=self.choice_list_var)
        self.__ch_list_var.Bind(event=wx.EVT_MOUSEWHEEL, handler=do_nothing)

        empty_txt = wx.StaticText(self.bg_panel, label="")

        sizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(label, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_return_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(txt_list_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)
        sizer.Add(self.__ch_list_var, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 2)

        sizer.Add(empty_txt, 1, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 2)

        self.sizer.Add(sizer, 1, wx.ALL | wx.EXPAND, 2)

    def update_ch_return_var(self):
        self.__ch_return_var.Set(list(VARIABLES.keys()))
        if self.keys['return_var'] is not None:
            self.__ch_return_var.Select(list(VARIABLES.keys()).index(self.keys['return_var']))

    def choice_return_var(self, event):
        self.keys['return_var'] = self.__ch_return_var.GetString(self.__ch_return_var.GetSelection())

    def update_ch_list_var(self):
        self.__ch_list_var.Set(list(VARIABLES.keys()))
        if self.keys['list_var'] is not None:
            self.__ch_list_var.Select(list(VARIABLES.keys()).index(self.keys['list_var']))

    def choice_list_var(self, event):
        self.keys['list_var'] = self.__ch_list_var.GetString(self.__ch_list_var.GetSelection())

    @overrides(Block)
    def update(self):
        self.update_ch_return_var()
        self.update_ch_list_var()
