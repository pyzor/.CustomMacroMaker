from pynput import mouse, keyboard
from threading import Thread
from time import time
import win32api
import win32con
import json
import os


class InputListener:
    def __init__(self, onMouseMove=None, onMouseScroll=None, onMouseClick=None, onKeyboardPress=None,
                 onKeyboardRelease=None):
        if onMouseMove is not None:
            self.__onMouseMove = onMouseMove
        if onMouseScroll is not None:
            self.__onMouseScroll = onMouseScroll
        if onMouseClick is not None:
            self.__onMouseClick = onMouseClick
        if onKeyboardPress is not None:
            self.__onKeyboardPress = onKeyboardPress
        if onKeyboardRelease is not None:
            self.__onKeyboardRelease = onKeyboardRelease
        self.__initListeners()

    def __del__(self):
        self.__mouse_listener.stop()
        self.__keyboard_listener.stop()

    def __initListeners(self):
        self.__mouse_listener = mouse.Listener(
            on_move=self.__onMouseMove,
            on_scroll=self.__onMouseScroll,
            on_click=self.__onMouseClick
        )
        self.__keyboard_listener = keyboard.Listener(
            on_press=self.__onKeyboardPress,
            on_release=self.__onKeyboardRelease
        )

        self.__mouse_listener.start()
        self.__mouse_listener.wait()

        self.__keyboard_listener.start()
        self.__keyboard_listener.wait()

    def __onMouseMove(self, x, y):  # UNIMPLEMENTED
        pass

    def __onMouseScroll(self, x, y, dx, dy):  # UNIMPLEMENTED
        pass

    def __onMouseClick(self, x, y, button, pressed):  # UNIMPLEMENTED
        pass

    def __onKeyboardPress(self, key):  # UNIMPLEMENTED
        pass

    def __onKeyboardRelease(self, key):  # UNIMPLEMENTED
        pass


class MacrosHandler:

    def __init__(self):  # , inputHandler):
        # self.KEYS = {
        #     keyboard.Key.ctrl_l: [False, False, False, False],
        #     keyboard.Key.cmd: [False, False, False, False],
        #     keyboard.Key.alt_l: [False, False, False, False],
        #     keyboard.Key.space: [False, False, False, False],
        #     keyboard.Key.alt_r: [False, False, False, False],
        #     keyboard.Key.menu: [False, False, False, False],
        #     keyboard.Key.ctrl_r: [False, False, False, False],
        #     keyboard.Key.left: [False, False, False, False],
        #     keyboard.Key.down: [False, False, False, False],
        #     keyboard.Key.right: [False, False, False, False],
        #     keyboard.Key.up: [False, False, False, False],
        #     keyboard.Key.shift: [False, False, False, False],
        #     'z': [False, False, False, False],
        #     'x': [False, False, False, False],
        #     'c': [False, False, False, False],
        #     'v': [False, False, False, False],
        #     'b': [False, False, False, False],
        #     'n': [False, False, False, False],
        #     'm': [False, False, False, False],
        #     ',': [False, False, False, False],
        #     '.': [False, False, False, False],
        #     '/': [False, False, False, False],
        #     keyboard.Key.shift_r: [False, False, False, False],
        #     keyboard.Key.caps_lock: [False, False, False, False],
        #     'a': [False, False, False, False],
        #     's': [False, False, False, False],
        #     'd': [False, False, False, False],
        #     'f': [False, False, False, False],
        #     'g': [False, False, False, False],
        #     'h': [False, False, False, False],
        #     'j': [False, False, False, False],
        #     'k': [False, False, False, False],
        #     'l': [False, False, False, False],
        #     ';': [False, False, False, False],
        #     "'": [False, False, False, False],
        #     keyboard.Key.enter: [False, False, False, False],
        #     keyboard.Key.tab: [False, False, False, False],
        #     'q': [False, False, False, False],
        #     'w': [False, False, False, False],
        #     'e': [False, False, False, False],
        #     'r': [False, False, False, False],
        #     't': [False, False, False, False],
        #     'y': [False, False, False, False],
        #     'u': [False, False, False, False],
        #     'i': [False, False, False, False],
        #     'o': [False, False, False, False],
        #     'p': [False, False, False, False],
        #     '[': [False, False, False, False],
        #     ']': [False, False, False, False],
        #     '\\': [False, False, False, False],
        #     keyboard.Key.delete: [False, False, False, False],
        #     keyboard.Key.end: [False, False, False, False],
        #     keyboard.Key.page_down: [False, False, False, False],
        #     keyboard.Key.page_up: [False, False, False, False],
        #     keyboard.Key.home: [False, False, False, False],
        #     keyboard.Key.insert: [False, False, False, False],
        #     keyboard.Key.backspace: [False, False, False, False],
        #     '=': [False, False, False, False],
        #     '-': [False, False, False, False],
        #     '0': [False, False, False, False],
        #     '9': [False, False, False, False],
        #     '8': [False, False, False, False],
        #     '7': [False, False, False, False],
        #     '6': [False, False, False, False],
        #     '5': [False, False, False, False],
        #     '4': [False, False, False, False],
        #     '3': [False, False, False, False],
        #     '2': [False, False, False, False],
        #     '1': [False, False, False, False],
        #     '`': [False, False, False, False],
        #     keyboard.Key.f1: [False, False, False, False],
        #     keyboard.Key.f2: [False, False, False, False],
        #     keyboard.Key.f3: [False, False, False, False],
        #     keyboard.Key.f4: [False, False, False, False],
        #     keyboard.Key.f5: [False, False, False, False],
        #     keyboard.Key.f6: [False, False, False, False],
        #     keyboard.Key.f7: [False, False, False, False],
        #     keyboard.Key.f8: [False, False, False, False],
        #     keyboard.Key.f9: [False, False, False, False],
        #     keyboard.Key.f10: [False, False, False, False],
        #     keyboard.Key.f11: [False, False, False, False],
        #     keyboard.Key.f12: [False, False, False, False],
        #     keyboard.Key.print_screen: [False, False, False, False],
        #     keyboard.Key.scroll_lock: [False, False, False, False],
        #     keyboard.Key.pause: [False, False, False, False],
        #     keyboard.Key.esc: [False, False, False, False]
        # }
        self.callbacks = {'keyboard': {}, 'mouse': {}}
        self.player: Player = Player()
        self.recorder: Recorder = Recorder()
        self.handle_recording = False
        self.provoking_func = None
        # self.__input_handler: InputHandler = inputHandler
        self.mousePos = [-1, -1]
        self.__input_handler: InputListener = InputListener(
            self.__onMouseMove,
            self.__onMouseScroll,
            self.__onMouseClick,
            self.__onKeyboardPress,
            self.__onKeyboardRelease)

    def add_keyboard_callback(self, key, callback):
        if key in self.callbacks['keyboard'].keys():
            self.callbacks['keyboard'][key].append(callback)
        else:
            self.callbacks['keyboard'][key] = [callback]

    def remove_keyboard_callback(self, key, callback):
        self.callbacks['keyboard'][key].remove(callback)

    def handleRecording(self, provokingF):
        self.provoking_func = provokingF
        self.handle_recording = True

    def stopHandlingRecording(self):
        self.provoking_func = None
        self.handle_recording = False

    @staticmethod
    def loadMacrosFromJson(jsonFile):
        with open(jsonFile, 'r') as f:
            return json.load(f)

    def __onMouseMove(self, x, y):
        self.mousePos[0] = x
        self.mousePos[1] = y
        self.recorder.onMouseMove(x, y)
        # self.__input_handler.onMouseMove(x, y)

    def __onMouseScroll(self, x, y, dx, dy):
        return  # TODO UNIMPLEMENTED
        # self.__recorder.onMouseScroll(x, y, dx, dy)
        # self.__inputListenerOutput.onMouseScroll(x, y, dx, dy)

    def __onMouseClick(self, x, y, button, pressed):
        self.recorder.onMouseClick(x, y, button, pressed)
        # self.__input_handler.onMouseClick(x, y, button, pressed)

    def __onKeyboardPress(self, key):
        self.recorder.onKeyboardPress(key)
        # self.KEYS[key.vk][0] = True
        # self.updateKeys()

    # def pressed(self, key):
    #     return self.KEYS[key.vk][2]
    #
    # def justPressed(self, key):
    #     return self.KEYS[key.vk][1]
    #
    # def justReleased(self, key):
    #     return self.KEYS[key.vk][3]

    # def updateKeys(self):
    #     for pair in self.KEYS:
    #         print(pair.value)
            # if (pair.second[3]):
            #     pair.second[3] = false
            #
            # if (pair.second[1]):
            #     pair.second[1] = false
            #
            # if !pair.second[0] && pair.second[2]:
            #     pair.second[2] = false
            #     pair.second[3] = true
            #
            # if pair.second[0] && !pair.second[2]:
            #     pair.second[1] = true
            #     pair.second[2] = true

    def __onKeyboardRelease(self, key):
        self.recorder.onKeyboardRelease(key)
        # self.KEYS[key][0] = False
        # self.updateKeys()

        if key in self.callbacks['keyboard'].keys():
            for callback in self.callbacks['keyboard'][key]:
                callback()

        if self.handle_recording:
            if key == keyboard.Key.f11:
                self.provoking_func(True, [])
                self.recorder.startRecording()
            elif key == keyboard.Key.f12:
                self.recorder.stopRecording()
                self.provoking_func(False, self.recorder.getEvents())

        # if Recorder.getKeyCode(key) == 32:  # space
        #     if self.__recorder.isRecording() or self.__recorder.isDelaying():
        #         self.__recorder.stopRecording()
        #         self.cm = Player.compileMacros(self.__recorder.getEvents().copy(), normalize=False)
        #         # self.cm.changeSpeed(20)
        #         self.__recorder.save_script('test_macro')
        #         print('saved')
        #     else:
        #         self.__recorder.startRecording(0, True)
        #
        # if Recorder.getKeyCode(key) == 192:  # `~
        #     if self.__player.playing():
        #         print('stop')
        #         self.__player.stop()
        #     else:
        #         if self.cm is not None:
        #             print('play')
        #             self.cm.startingMousePos = self.mousePos.copy()
        #             self.__player.play(self.cm)
        #
        # if Recorder.getKeyCode(key) == 16:  # tab
        #     if not self.__player.playing():
        #         # self.cm = Player.compileMacrosF('privet.json', normalize=True)
        #         self.cm = Player.compileMacrosF('heart.json', normalize=False)
        #         # self.cm.changeSpeed(20)
        #         print('loaded')


class MacrosEvents:
    MOUSE_RELEASED = 'mouse.release'
    MOUSE_PRESSED = 'mouse.press'
    MOUSE_MOVED = 'mouse.move'
    KEYBOARD_RELEASED = 'keyboard.release'
    KEYBOARD_PRESSED = 'keyboard.press'

    COORDS_EVENTS = MOUSE_EVENTS = [MOUSE_RELEASED, MOUSE_PRESSED, MOUSE_MOVED]
    NO_COORDS_EVENTS = KEYBOARD_EVENTS = [KEYBOARD_RELEASED, KEYBOARD_PRESSED]
    BUTTON_EVENTS = [MOUSE_RELEASED, MOUSE_PRESSED, KEYBOARD_RELEASED, KEYBOARD_PRESSED]


class CompiledMacros:
    def __init__(self, window=None):
        self.events = []
        self.relative = False
        self.window = window
        self.startingMousePos = [-1, -1]

    def len(self):
        return len(self.events)

    def changeSpeed(self, scale):
        for event in self.events:
            event.timing = event.timing / scale


class CompiledMacrosEvent:
    def __init__(self, event, macros: CompiledMacros):
        self.timing = event['timing']
        if macros.window is None:
            if event['type'] in MacrosEvents.NO_COORDS_EVENTS:
                command = win32con.KEYEVENTF_KEYUP if event['type'] == MacrosEvents.KEYBOARD_RELEASED else 0
                key = event['keys']['key']

                def play():  # KEYBOARD EMULATION
                    win32api.keybd_event(key, 0, command, 0)
            elif event['type'] in MacrosEvents.COORDS_EVENTS:
                x = event['keys']['x']
                y = event['keys']['y']

                flag = win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE
                if event['type'] == MacrosEvents.MOUSE_MOVED:
                    pass
                elif event['type'] == MacrosEvents.MOUSE_RELEASED:
                    if event['keys']['button'] == 'left':
                        flag = flag | win32con.MOUSEEVENTF_LEFTUP
                    elif event['keys']['button'] == 'middle':
                        flag = flag | win32con.MOUSEEVENTF_MIDDLEUP
                    elif event['keys']['button'] == 'right':
                        flag = flag | win32con.MOUSEEVENTF_RIGHTUP
                    else:
                        raise RuntimeError('unsupported mouse button')
                elif event['type'] == MacrosEvents.MOUSE_PRESSED:
                    if event['keys']['button'] == 'left':
                        flag = flag | win32con.MOUSEEVENTF_LEFTDOWN
                    elif event['keys']['button'] == 'middle':
                        flag = flag | win32con.MOUSEEVENTF_MIDDLEDOWN
                    elif event['keys']['button'] == 'right':
                        flag = flag | win32con.MOUSEEVENTF_RIGHTDOWN
                    else:
                        raise RuntimeError('unsupported mouse button')
                else:
                    raise RuntimeError('unknown event type')
                if macros.relative:
                    def play():  # MOUSE EMULATION
                        win32api.mouse_event(flag, int((x + macros.startingMousePos[0]) * Player.SCREEN_SCALE_X),
                                             int((y + macros.startingMousePos[1]) * Player.SCREEN_SCALE_Y), 0, 0)
                else:
                    def play():  # MOUSE EMULATION
                        win32api.mouse_event(flag, int(x * Player.SCREEN_SCALE_X), int(y * Player.SCREEN_SCALE_Y), 0, 0)
            else:
                raise RuntimeError('unknown event type')
        else:
            def play():
                print('xd')
                pass
        self.play = play


class Player:
    SCREEN_SCALE_X = 65535 / win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
    SCREEN_SCALE_Y = 65535 / win32api.GetSystemMetrics(win32con.SM_CYSCREEN)

    def __init__(self):
        self.__macros = None
        self.__timer = None
        self.__playing = False

    @staticmethod
    def compileMacrosF(jsonFile, window=None, normalize=True):
        with open(jsonFile, 'r') as f:
            return Player.compileMacros(events=json.load(f), window=window, normalize=normalize)

    @staticmethod
    def compileMacros(events, window=None, normalize=True):
        macros = CompiledMacros(window)
        if normalize:
            first_x = -1
            first_y = -1
            for event in events:
                if event['type'] in MacrosEvents.COORDS_EVENTS and not macros.relative:
                    first_x = event['keys']['x']
                    first_y = event['keys']['y']
                    event['keys']['x'] = 0
                    event['keys']['y'] = 0
                    macros.relative = True
                elif event['type'] in MacrosEvents.COORDS_EVENTS and macros.relative:
                    event['keys']['x'] -= first_x
                    event['keys']['y'] -= first_y
        for event in events:
            macros.events.append(CompiledMacrosEvent(event, macros))
        return macros

    def __startTimer(self):
        self.__timer = time()

    def playing(self):
        return self.__playing

    def elapsedTime(self):
        return time() - self.__timer

    def play(self, macros, startingMousePos):
        #self.startingMousePos = startingMousePos.copy()
        self.__macros = macros
        self.__macros.startingMousePos = startingMousePos.copy()
        if self.__macros.len() <= 0:
            return
        self.eventIndex = 0
        self.__playing = True
        self.__startTimer()
        self.__thread = Thread(target=self.__playing_thread, args=())
        self.__thread.start()

    def stop(self):
        self.__playing = False
        self.__macros = None

    def __playing_thread(self):
        self.maxIndex = self.__macros.len()
        while self.__playing:
            elapsedTime = self.elapsedTime()
            self.__play_event(elapsedTime)

    def __play_event(self, elapsedTime):
        if self.eventIndex >= self.maxIndex:
            self.stop()
            return
        if self.__macros is None:
            return
        if elapsedTime >= self.__macros.events[self.eventIndex].timing:
            self.__macros.events[self.eventIndex].play()
            self.eventIndex += 1
            self.__play_event(elapsedTime)


class Recorder:
    def __init__(self):
        self.__delaying = False
        self.__recording = False
        self.__record_mouse_move_events = False
        self.__timer = None
        self.__unreleased_keys = []
        self.__unreleased_buttons = []
        self.__recorded_events = []

    def __startTimer(self):
        self.__timer = time()

    def elapsedTime(self):
        return time() - self.__timer

    def isRecording(self):
        return self.__recording

    def isDelaying(self):
        return self.__delaying

    def startRecording(self, delay=0, record_mouse_move_events=True):
        if self.__recording or self.__delaying:
            return
        self.__record_mouse_move_events = record_mouse_move_events
        self.__unreleased_keys = []
        self.__unreleased_buttons = []
        self.__recorded_events = []
        self.__startTimer()
        if delay > 0:
            self.__delaying = True
            self.__delaying_thread = Thread(target=self.__delayingPause, args=(delay,))
            self.__delaying_thread.start()
        else:
            self.__recording = True

    def __delayingPause(self, delay):
        self.__break_point = False

        while not self.__break_point:
            print('delaying...')
            if self.elapsedTime() >= delay:
                break

        self.__delaying = False

        if not self.__break_point:
            self.__startTimer()
            self.__recording = True

    def stopRecording(self):
        self.__break_point = True
        self.__recording = False
        self.clearEvents()
        # script_duration = self.elapsed_time()

    def __recordEvent(self, event):
        self.__recorded_events.append(event)

    def clearEvents(self):
        for key in self.__unreleased_keys:
            i = len(self.__recorded_events) - 1
            while i >= 0:
                event = self.__recorded_events[i]
                if event['type'] == MacrosEvents.KEYBOARD_PRESSED:
                    try:
                        keyString = key.char
                    except AttributeError:
                        keyString = str(key)[4:]
                    if event['keys']['key'] == keyString:
                        self.__recorded_events.pop(i)
                        break
                i -= 1

        for button in self.__unreleased_buttons:
            i = len(self.__recorded_events) - 1
            while i >= 0:
                event = self.__recorded_events[i]
                if event['type'] == MacrosEvents.MOUSE_PRESSED:
                    if event['keys']['button'] == str(button)[7:]:
                        self.__recorded_events.pop(i)
                        break
                i -= 1

    def save_script(self, scr_name):
        filepath = f'{scr_name}.json'
        with open(filepath, 'w') as f:
            json.dump(self.__recorded_events[:-2], f, indent=4)

    def getEvents(self):
        return self.__recorded_events

    def onMouseMove(self, x, y):
        if self.__recording:
            if self.__record_mouse_move_events:
                self.__recordEvent({
                    'type': MacrosEvents.MOUSE_MOVED,
                    'timing': self.elapsedTime(),
                    'keys': {
                        'x': x,
                        'y': y
                    }
                })

    def onMouseScroll(self, x, y, dx, dy):
        pass

    def onMouseClick(self, x, y, button, pressed):
        if self.__recording:
            name = button.name
            if pressed:
                if name not in self.__unreleased_buttons:
                    self.__recordEvent({
                        'type': MacrosEvents.MOUSE_PRESSED,
                        'timing': self.elapsedTime(),
                        'keys': {
                            'button': name,
                            'x': x,
                            'y': y
                        }
                    })
                    self.__unreleased_buttons.append(name)
            else:
                if name in self.__unreleased_buttons:
                    self.__recordEvent({
                        'type': MacrosEvents.MOUSE_RELEASED,
                        'timing': self.elapsedTime(),
                        'keys': {
                            'button': name,
                            'x': x,
                            'y': y
                        }
                    })
                    self.__unreleased_buttons.remove(name)

    @staticmethod
    def getKeyCode(key):
        try:
            vk = key.value.vk
        except AttributeError:
            vk = key.vk
        if vk == 160 or vk == 161:
            vk = 16
        elif vk == 162 or vk == 163:
            vk = 17
        elif vk == 164 or vk == 165:
            vk = 18
        return vk

    def onKeyboardPress(self, key):
        if self.__recording:
            vk = self.getKeyCode(key)
            if vk not in self.__unreleased_keys:
                self.__recordEvent({
                    'type': MacrosEvents.KEYBOARD_PRESSED,
                    'timing': self.elapsedTime(),
                    'keys': {
                        'key': vk
                    }
                })
                self.__unreleased_keys.append(vk)

    def onKeyboardRelease(self, key):
        if self.__recording:
            vk = self.getKeyCode(key)
            if vk in self.__unreleased_keys:
                self.__recordEvent({
                    'type': MacrosEvents.KEYBOARD_RELEASED,
                    'timing': self.elapsedTime(),
                    'keys': {
                        'key': vk
                    }
                })
                self.__unreleased_keys.remove(vk)
