import wx
from wx.lib.platebtn import PlateButton
from wx.lib.scrolledpanel import ScrolledPanel
import blocks
import json
import threading
import random
import string
import time
import math
import vision
from window_capture import WindowCapture
import numpy as np
import cv2
from pynput import keyboard
from copy import deepcopy

from macro import MacrosHandler

from PIL import Image as im


# vars
APP_FRAME_NAME = '.CustomMacroMaker'
APP_FRAME_START_POS = (0, 0)
APP_FRAME_SIZE = (1280, 720)

PLAY_ICO = None
STOP_ICO = None


class CMMApp(wx.App):
    frame = None

    def __init__(self):
        super().__init__(clearSigInt=True)
        blocks.JBM_FONT = wx.Font(pointSize=10, family=wx.FONTFAMILY_TELETYPE, style=wx.NORMAL, weight=wx.NORMAL)
        blocks.JBM_FONT.AddPrivateFont('res/fonts/JetBrainsMono.ttf')
        global PLAY_ICO
        PLAY_ICO = wx.Bitmap()
        PLAY_ICO.LoadFile('res/ico/play.png')
        global STOP_ICO
        STOP_ICO = wx.Bitmap()
        STOP_ICO.LoadFile('res/ico/stop.png')
        blocks.CROSS_BPM = wx.Bitmap()
        blocks.CROSS_BPM.LoadFile('res/ico/cross.png')
        blocks.RECORD_ICO = wx.Bitmap()
        blocks.RECORD_ICO.LoadFile('res/ico/record.png')

        self.frame = CMMFrame(None, APP_FRAME_NAME, APP_FRAME_START_POS, APP_FRAME_SIZE)
        self.frame.Show()


class CMMFrame(wx.Frame):
    __panel = None

    def __init__(self, parent, title, pos, size):
        super().__init__(parent=None, title=title, pos=pos, size=size, style=wx.DEFAULT_FRAME_STYLE ^ wx.RESIZE_BORDER ^ wx.MAXIMIZE_BOX ^ wx.CLIP_CHILDREN ^ wx.SYSTEM_MENU)
        self.Bind(wx.EVT_CLOSE, self.__on_exit)

        icon = wx.Icon()
        icon.CopyFromBitmap(PLAY_ICO)
        self.SetIcon(icon)

        self.__panel = blocks.CMMPanel(self)

        self.__menu_bar_setup()
        self.__status_bar_setup()
        self.__tool_bar_setup()

        blocks.MACROS_HANDLER.add_keyboard_callback(keyboard.Key.f4, self.__on_play)
        blocks.MACROS_HANDLER.add_keyboard_callback(keyboard.Key.f5, self.__on_stop)
        # self.timer = wx.Timer(self)
        # self.Bind(wx.EVT_TIMER, self.update, self.timer)
        # self.timer.Start(100)

    def update(self, event=None):
        self.panel.update()
        self.__parent_frame.update_status_bar()

    def __on_new(self, event=None):
        for block in reversed(self.__panel.get_blocks()):
            if block.get_name() != 'dnd_blank':
                block.remove()

    def __on_open(self, event=None):
        file_dlg = wx.FileDialog(self.__panel, "Open macros file", "", "", "JSON file (*.json)|*.*", wx.FD_OPEN)

        if file_dlg.ShowModal() == wx.ID_OK:
            self.open_path = file_dlg.GetPath()
        else:
            return

        data = None

        with open(self.open_path) as json_file:
            data = json.load(json_file)

        self.__on_new()

        for action in data['actions']:
            self.__panel.add_block(action=action, update=False)
        self.__panel.update()
        self.__panel.show_blocks()

    def __on_save(self, event=None):
        file_dlg = wx.FileDialog(self.__panel, "Save macros file", "", "", "JSON file (*.json)|*.*", wx.FD_SAVE)

        if file_dlg.ShowModal() == wx.ID_OK:
            self.save_path = file_dlg.GetPath()
        else:
            return

        data = {'actions': []}

        for i in self.__panel.get_blocks():
            if i.get_name() != 'dnd_blank':
                data['actions'].append(i.dump_save())

        with open(self.save_path, "w") as file:
            json.dump(data, file, indent=4)

    def __on_exit(self, event=None):
        self.script_player.end_thread()
        wx.Exit()

    def __on_clear_var(self, event=None):
        used_var_names = []
        for block in self.__panel.get_blocks():
            if block.get_name() == 'set':
                used_var_names.append(block.get_var_name())
            elif block.get_name() == 'while':
                block_used_var_names = self.find_sets(block.get_key('actions'))
                if len(block_used_var_names) > 0:
                    used_var_names.append(block_used_var_names)
        used_var_names = list(dict.fromkeys(used_var_names))
        keys = list(blocks.VARIABLES.keys())
        for i in keys:
            if not used_var_names.__contains__(i):
                blocks.VARIABLES.pop(i)

        self.__panel.update()

    def find_sets(self, script):
        used_var_names = []
        for action in script:
            if action['action_name'] == 'set':
                used_var_names.append(action['var_name'])
            elif action['action_name'] == 'while':
                used_var_names.append(self.find_sets(action['keys']['script']))
        return used_var_names

    def __add_menu_item(self, menu, handler, item_id, text='', helpstring=''):
        menu.Append(wx.MenuItem(parentMenu=self.file_menu, id=item_id, text=text, helpString=helpstring))
        self.Bind(wx.EVT_MENU, handler, id=item_id)

    def __menu_bar_setup(self):
        self.menu_bar = wx.MenuBar()
        self.file_menu = wx.Menu()
        self.options_menu = wx.Menu()
        self.help_menu = wx.Menu()

        self.__add_menu_item(self.file_menu, self.__on_new, 100, 'New', 'Create new macros')
        self.__add_menu_item(self.file_menu, self.__on_open, 101, 'Open', 'Open a macros to edit')
        self.__add_menu_item(self.file_menu, self.__on_save, 102, 'Save', 'Save macros')
        self.file_menu.AppendSeparator()
        self.__add_menu_item(self.file_menu, self.__on_exit, 103, 'Exit', 'Quit ' + APP_FRAME_NAME)

        self.__add_menu_item(self.options_menu, self.__on_clear_var, 200, 'Clear variables', "Clears variable names that aren't used in the current script.")

        self.menu_bar.Append(self.file_menu, '&File')
        self.menu_bar.Append(self.options_menu, '&Options')
        self.menu_bar.Append(self.help_menu, '&Help')

        self.SetMenuBar(self.menu_bar)

    def __status_bar_setup(self):
        self.CreateStatusBar(2)
        self.GetStatusBar().SetBackgroundColour(wx.Colour(240, 240, 240))
        self.update_status_bar()

    def update_status_bar(self):
        self.GetStatusBar().SetStatusText(f'Blocks count: {len(self.__panel.get_blocks()) - 1}', 1)

    def __tool_bar_setup(self):
        self.CreateToolBar(style=wx.TB_DEFAULT_STYLE | wx.TB_FLAT | wx.TB_NODIVIDER)
        # self.GetToolBar().SetBackgroundColour(wx.Colour(255, 255, 255))
        self.GetToolBar().AddSeparator()
        self.GetToolBar().AddTool(9900, 'Play', PLAY_ICO, shortHelp='Run script')
        self.Bind(wx.EVT_TOOL, self.__on_play, id=9900)
        self.GetToolBar().AddTool(9901, 'Stop', STOP_ICO, shortHelp='Stop script')
        self.Bind(wx.EVT_TOOL, self.__on_stop, id=9901)
        self.GetToolBar().AddSeparator()
        self.GetToolBar().Realize()

        self.script_player = ScriptPlayer()

    def __on_play(self, event=None):
        self.script_player.play(self.__panel.get_list_of_actions())

    def __on_stop(self, event=None):
        self.script_player.stop()
        blocks.MACROS_HANDLER.player.stop()


class ScriptPlayer(threading.Thread):
    actions = []
    break_thrown = False

    def __init__(self):
        threading.Thread.__init__(self)
        self.exit_loop = threading.Event()
        self.running = threading.Event()
        self.variables = {}

        self.code = ''
        self.start()

        self.waiting_flag = threading.Event()

    def play(self, actions):
        self.actions = actions
        if len(self.actions) > 0:
            self.running.set()

    def end_thread(self):
        self.running.set()
        self.exit_loop.set()
        self.join()

    def stop(self):
        self.running.clear()

    def isRunning(self):
        return self.running.is_set()

    def run(self):
        while not self.exit_loop.is_set():
            if not self.running.is_set():
                self.running.wait()
            if self.exit_loop.is_set():
                break
            index = 0
            self.variables = {}
            while self.running.is_set():
                if self.check_end(self.actions, index):
                    self.running.clear()
                    break
                index = self.do_action(self.actions, index)

    @staticmethod
    def check_end(actions, index):
        if index >= len(actions):
            return True
        return False

    def do_action(self, actions, index):
        action = actions[index]
        if action['action_name'] == 'set':
            self.do_set(action)
        elif action['action_name'] == 'while':
            self.do_while(action)
        elif action['action_name'] == 'if':
            self.do_if(action)
        elif action['action_name'] == 'macros':
            self.do_macros(action)
        elif action['action_name'] == 'load_image':
            self.do_load_image(action)
        elif action['action_name'] == 'capture_image':
            self.do_capture_image(action)
        elif action['action_name'] == 'capture_image_mouse_pos':
            self.do_capture_image_mouse_pos(action)
        elif action['action_name'] == 'screenshot_image':
            self.do_screenshot_image(action)
        elif action['action_name'] == 'screenshot_image_mouse_pos':
            self.do_screenshot_image_mouse_pos(action)
        elif action['action_name'] == 'find_window':
            self.do_find_window(action)
        elif action['action_name'] == 'mouse_move':
            self.do_mouse_move(action)
        elif action['action_name'] == 'mouse_button':
            self.do_mouse_button(action)
        elif action['action_name'] == 'focus_window':
            self.do_focus_window(action)
        elif action['action_name'] == 'hsv_filter':
            self.do_hsv_filter(action)
        elif action['action_name'] == 'find':
            self.do_find(action)
        elif action['action_name'] == 'list':
            self.do_list(action)
        elif action['action_name'] == 'math':
            self.do_math(action)
        elif action['action_name'] == 'break':
            self.do_break(action)
        elif action['action_name'] == 'apply_hsv':
            self.do_apply_hsv(action)
        elif action['action_name'] == 'wait':
            self.do_wait(action)
        elif action['action_name'] == 'sum':
            self.do_sum(action)

        index += 1
        return index

    def do_sum(self, action):
        self.variables[action['keys']['return_var']] = sum(self.variables[action['keys']['list_var']])
        # print(self.variables[action['keys']['return_var']])

    def do_wait(self, action):
        if action['keys']['value_type'] == 'number':
            value_time = action['keys']['value_num']
        elif action['keys']['value_type'] == 'variable':
            value_time = self.variables[action['keys']['value_var']]

        time_start = time.time()

        while self.running.is_set():
            current_time = time.time()
            if current_time - time_start >= value_time:
                return
            else:
                time.sleep(0.01)


    def do_apply_hsv(self, action):
        self.variables[action['keys']['return_var']] = vision.CVWrapper.apply_hsv(
            self.variables[action['keys']['image_var']], self.variables[action['keys']['hsv']])

    def do_set(self, action):
        # print(action['keys']['var_name'], '=', action['keys']['value'])
        if action['keys']['value_type'] == 'get':
            self.variables[action['keys']['var_name']] = self.variables[action['keys']['value']['list']][action['keys']['value']['index']['value']]
        elif action['keys']['value_type'] == 'list' or action['keys']['value_type'] == 'coords':
            self.variables[action['keys']['var_name']] = deepcopy(action['keys']['value'])
        elif action['keys']['value'] == 'CURRENT_MOUSE_POSITION':
            self.variables[action['keys']['var_name']] = deepcopy(blocks.MACROS_HANDLER.mousePos)
        else:
            self.variables[action['keys']['var_name']] = action['keys']['value']


    def do_break(self, action):
        if action['keys']['if']:
            if self.compile_condition(action['keys']['condition']):
                self.break_thrown = True
        else:
            self.break_thrown = True

    def do_math(self, action):
        if action['keys']['value1_type'] == 'number':
            left = action['keys']['value1_num']
        elif action['keys']['value1_type'] == 'variable':
            left = self.variables[action['keys']['value1_var']]
        if action['keys']['value2_type'] == 'number':
            right = action['keys']['value2_num']
        elif action['keys']['value2_type'] == 'variable':
            right = self.variables[action['keys']['value2_var']]

        if action['keys']['operation'] == '*':
            result = left * right
        elif action['keys']['operation'] == '/':
            result = left / right
        elif action['keys']['operation'] == '+':
            result = left + right
        elif action['keys']['operation'] == '-':
            result = left - right
            # print(result, '=', left, '-', right)
        elif action['keys']['operation'] == 'root':
            result = left ** (1/float(right))
        elif action['keys']['operation'] == 'pow':
            result = left ** right
        self.variables[action['keys']['return_var']] = result
        # print(self.variables[action['keys']['return_var']])

    def do_while(self, action):
        actions = action['keys']['actions']
        index = 0
        value = self.compile_condition(action['keys']['condition'])
        while value and self.running.is_set():
            if self.break_thrown:
                self.break_thrown = False
                return
            index = self.do_action(actions, index)
            value = self.compile_condition(action['keys']['condition'])
            if index >= len(actions):
                index = 0
        return

    def do_if(self, action):
        actions = action['keys']['actions']
        index = 0
        value = self.compile_condition(action['keys']['condition'])

        while value and self.running.is_set():
            if self.break_thrown:
                self.break_thrown = False
                return
            index = self.do_action(actions, index)
            if index >= len(actions):
                break

    def do_macros(self, action):
        if "macros" in action.keys():
            blocks.MACROS_HANDLER.player.play(action["macros"])
        else:
            action["macros"] = blocks.MACROS_HANDLER.player.compileMacros(action['keys']['events'])
            blocks.MACROS_HANDLER.player.play(action["macros"], deepcopy(blocks.MACROS_HANDLER.mousePos))

    def do_list(self, action):
        # ['list_var', 'action', 'value', 'index_type', 'index_int', 'index_var']
        # ['append', 'insert', 'set', 'remove', 'clear']
        if action['keys']['action'] == 'append':
            self.variables[action['keys']['list_var']].append(self.variables[action['keys']['value']])
        elif action['keys']['action'] == 'insert':
            if action['keys']['index_type'] == 'integer':
                index = int(action['keys']['index_int'])
            else:
                index = int(self.variables[action['keys']['index_var']])
            self.variables[action['keys']['list_var']].insert(index, self.variables[action['keys']['value']])
        elif action['keys']['action'] == 'set':
            if action['keys']['index_type'] == 'integer':
                index = int(action['keys']['index_int'])
            else:
                index = int(self.variables[action['keys']['index_var']])
            self.variables[action['keys']['list_var']][index] = self.variables[action['keys']['value']]
        elif action['keys']['action'] == 'remove':
            if action['keys']['index_type'] == 'integer':
                index = int(action['keys']['index_int'])
            else:
                index = int(self.variables[action['keys']['index_var']])

            if isinstance(self.variables[action['keys']['list_var']], np.ndarray):
                np.delete(self.variables[action['keys']['list_var']], index)
            else:
                self.variables[action['keys']['list_var']].pop(index)
        elif action['keys']['action'] == 'clear':
            self.variables[action['keys']['list_var']].clear()

    def do_load_image(self, action):
        self.variables[action['keys']['var_name']] = np.array(json.loads(action['keys']['raw_image'])).astype('uint8')

    def do_mouse_move(self, action):
        if action['keys']['window_space']:
           self.variables[action['keys']['window']].mouse_move(
               #self.variables[action['keys']['window']].get_window_pos_as_long(self.variables[action['keys']['var_name']]))
               WindowCapture.s_as_long(self.variables[action['keys']['var_name']]))
        else:
            WindowCapture.s_mouse_move(self.variables[action['keys']['var_name']])

    def do_mouse_button(self, action):
        if action['keys']['button'] == 'left':
            if action['keys']['action'] == 'click':
                if action['keys']['window_space']:
                    long_pos = WindowCapture.s_as_long(self.variables[action['keys']['var_name']])
                    self.variables[action['keys']['window']].press_left(long_pos)
                    self.variables[action['keys']['window']].release_left(long_pos)
                else:
                    WindowCapture.s_press_left(self.variables[action['keys']['var_name']])
                    WindowCapture.s_release_left(self.variables[action['keys']['var_name']])
            if action['keys']['action'] == 'press':
                if action['keys']['window_space']:
                    self.variables[action['keys']['window']].press_left(
                        WindowCapture.s_as_long(self.variables[action['keys']['var_name']]))
                else:
                    WindowCapture.s_press_left(self.variables[action['keys']['var_name']])
            if action['keys']['action'] == 'release':
                if action['keys']['window_space']:
                    self.variables[action['keys']['window']].release_left(
                        WindowCapture.s_as_long(self.variables[action['keys']['var_name']]))
                else:
                    WindowCapture.s_release_left(self.variables[action['keys']['var_name']])
        elif action['keys']['button'] == 'right':
            if action['keys']['action'] == 'click':
                if action['keys']['window_space']:
                    long_pos = WindowCapture.s_as_long(self.variables[action['keys']['var_name']])
                    self.variables[action['keys']['window']].press_right(long_pos)
                    self.variables[action['keys']['window']].release_right(long_pos)
                else:
                    WindowCapture.s_press_right(self.variables[action['keys']['var_name']])
                    WindowCapture.s_release_right(self.variables[action['keys']['var_name']])
            if action['keys']['action'] == 'press':
                if action['keys']['window_space']:
                    self.variables[action['keys']['window']].press_right(
                        WindowCapture.s_as_long(self.variables[action['keys']['var_name']]))
                else:
                    WindowCapture.s_press_right(self.variables[action['keys']['var_name']])
            if action['keys']['action'] == 'release':
                if action['keys']['window_space']:
                    self.variables[action['keys']['window']].release_right(
                        WindowCapture.s_as_long(self.variables[action['keys']['var_name']]))
                else:
                    WindowCapture.s_release_right(self.variables[action['keys']['var_name']])

    def do_focus_window(self, action):
        self.variables[action['keys']['window']].focus()

    def do_hsv_filter(self, action):
        self.variables[action['keys']['var_name']] = vision.HsvFilter(
            action['keys']['h_min'], action['keys']['h_max'], action['keys']['s_min'], action['keys']['s_max'],
            action['keys']['v_min'], action['keys']['v_max'], action['keys']['s_add'], action['keys']['s_sub'],
            action['keys']['v_add'], action['keys']['v_sub'])

    def do_find(self, action):
        if action['keys']['use_hsv']:
            observer = vision.CVWrapper.apply_hsv(self.variables[action['keys']['observer']],
                                                  self.variables[action['keys']['hsv']])
            target = vision.CVWrapper.apply_hsv(self.variables[action['keys']['target']],
                                                self.variables[action['keys']['hsv']])
        else:
            observer = self.variables[action['keys']['observer']]
            target = self.variables[action['keys']['target']]
        self.variables[action['keys']['return_var']] = vision.CVWrapper.find(observer, target,
            action['keys']['threshold'], action['keys']['max_results']).tolist()
        # if len(self.variables[action['keys']['return_var']]):
        #     print('find - x ', self.variables[action['keys']['return_var']][0][0])

    def do_find_window(self, action):
        self.variables[action['keys']['var_name']] = WindowCapture(action['keys']['window_name'], action['keys']['sub_window'])

    def do_capture_image(self, action):
        self.variables[action['keys']['var_name']] = self.variables[action['keys']['window']].fast_capture(
            action['keys']['x'],
            action['keys']['y'],
            action['keys']['w'],
            action['keys']['h'])
        # cv2.imwrite("IMG_CAP\\do_capture_image.png", self.variables[action['keys']['var_name']])

    def do_capture_image_mouse_pos(self, action):
        x, y = self.variables[action['keys']['window']].get_window_pos(blocks.MACROS_HANDLER.mousePos)
        self.variables[action['keys']['var_name']] = self.variables[action['keys']['window']].fast_capture_center(
            x,
            y,
            action['keys']['w'],
            action['keys']['h'])
        # cv2.imwrite("IMG_CAP\\do_capture_image_mouse_pos.png", self.variables[action['keys']['var_name']])

    def do_screenshot_image(self, action):
        self.variables[action['keys']['var_name']] = WindowCapture.fast_screen_capture(
            action['keys']['x'],
            action['keys']['y'],
            action['keys']['w'],
            action['keys']['h'])
        # cv2.imwrite("IMG_CAP\\do_screenshot_image.png", self.variables[action['keys']['var_name']])

    def do_screenshot_image_mouse_pos(self, action):
        self.variables[action['keys']['var_name']] = WindowCapture.fast_screen_capture_center(
            blocks.MACROS_HANDLER.mousePos[0],
            blocks.MACROS_HANDLER.mousePos[1],
            action['keys']['w'],
            action['keys']['h'])
        # cv2.imwrite("IMG_CAP\\do_screenshot_image_mouse_pos.png", self.variables[action['keys']['var_name']])

    def compile_condition(self, condition):
        value = None
        if condition['type'] == 'value':
            value = condition['keys']['value']
        elif condition['type'] == 'variable':
            value = self.variables[condition['keys']['var_name']]
        elif condition['type'] == 'compare':
            left_value = self.compile_condition(condition['keys']['left_key'])
            right_value = self.compile_condition(condition['keys']['right_key'])
            operator = condition['keys']['operator']
            if operator == '==':
                value = left_value == right_value
            if operator == '!=':
                value = left_value != right_value
            if operator == '>':
                value = left_value > right_value
            if operator == '<':
                value = left_value < right_value
            if operator == '>=':
                value = left_value >= right_value
            if operator == '<=':
                value = left_value <= right_value
        elif condition['type'] == 'and':
            left_value = self.compile_condition(condition['keys']['left_key'])
            right_value = self.compile_condition(condition['keys']['right_key'])
            value = left_value and right_value
        elif condition['type'] == 'or':
            left_value = self.compile_condition(condition['keys']['left_key'])
            right_value = self.compile_condition(condition['keys']['right_key'])
            value = left_value or right_value
        elif condition['type'] == 'length':
            value = len(self.variables[condition['keys']['var_name']])

        return value