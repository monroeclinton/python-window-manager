from pwm.utils import KeyUtil
import logging
import subprocess
import xcffib
import xcffib.xproto
import xpybutil
import xpybutil.keybind
import yaml


# Constants to use in window manager
NEXT_WINDOW = 'NEXT_WINDOW'
PREVIOUS_WINDOW = 'PREVIOUS_WINDOW'


class WindowManager:
    def __init__(self):
        # Load config file. This should be moved into ~/.config/ and be read from there.
        with open('config.yaml') as f:
            self.config = yaml.safe_load(f)

        # Connect to X server. Since we don't specify params it will connect to display 1
        # that was set in preview.sh.
        self.conn = xcffib.connect()

        # Class that contains utils for switching between keycodes/keysyms
        self.key_util = KeyUtil(self.conn)

        # Get first available screen
        self.screen = self.conn.get_setup().roots[0]

        # All windows have a parent, the root window is the final parent of the tree of windows.
        # It is created when a screen is added to the X server. It is used for background images
        # and colors. It also can recieve events that happen to its children such as mouse in/out,
        # window creation/deletion, etc.
        self.root_window = self.screen.root

        # An array of windows
        self.windows = []
        self.current_window = 0

    def run(self):
        """
        Setup and run window manager. This includes checking if another window manager is
        running, listening for certain key presses, and handling events.
        """

        # Tell X server which events we wish to recieve for the root window.
        cookie = self.conn.core.ChangeWindowAttributesChecked(
            self.root_window,
            xcffib.xproto.CW.EventMask,  # Window attribute to set which events we want
            [
                # We want to recieve any substrucutre changes. This includes window
                # creation/deletion, resizes, etc.
                xcffib.xproto.EventMask.SubstructureNotify |
                # We want X server to redirect children substructure notifications to the
                # root window. Our window manager then processes these notifications.
                # Only a single X client can use SubstructureRedirect at a time.
                # This means if the request to changes attributes fails, another window manager
                # is probably running.
                xcffib.xproto.EventMask.SubstructureRedirect,
            ]
        )

        # Check if request was valid
        try:
            cookie.check()
        except:
            logging.error(logging.traceback.format_exc())
            print('Is another window manager running?')
            exit()

        # Loop through actions listed in config and grab keys. This means we
        # will get a KeyPressEvent if the key combination is pressed.
        for action in self.config['actions']:
            # Get keycode from string
            keycode = self.key_util.get_keycode(
                KeyUtil.string_to_keysym(action['key'])
            )

            # Get modifier from string
            modifier = getattr(xcffib.xproto.KeyButMask, self.config['modifier'], 0)

            self.conn.core.GrabKeyChecked(
                # We want owner_events to be false so all key events are sent to root window
                False,
                self.root_window,
                modifier,
                keycode,
                xcffib.xproto.GrabMode.Async,
                xcffib.xproto.GrabMode.Async
            ).check()

        while True:
            event = self.conn.wait_for_event()

            if isinstance(event, xcffib.xproto.KeyPressEvent):
                self._handle_key_press_event(event)
            if isinstance(event, xcffib.xproto.MapRequestEvent):
                self._handle_map_request_event(event)
            if isinstance(event, xcffib.xproto.ConfigureRequestEvent):
                self._handle_configure_request_event(event)

            # Flush requests to send to X server
            self.conn.flush()

    def _handle_action(self, action):
        """
        Handle actions defined in config.yaml

        :param action: Window manager action to handle
        """

        # Cycle to the next window
        if action == NEXT_WINDOW:
            if len(self.windows) == 0: return

            self.conn.core.UnmapWindow(self.windows[self.current_window])

            # Get the next window
            self.current_window += 1
            # If overflowed go to the first window
            if self.current_window >= len(self.windows):
                self.current_window = 0

            self.conn.core.MapWindow(self.windows[self.current_window])

        # Cycle to the previous window
        if action == PREVIOUS_WINDOW:
            if len(self.windows) == 0: return

            self.conn.core.UnmapWindow(self.windows[self.current_window])

            # Get the previous window
            self.current_window -= 1
            # If underflowed go to last window
            if self.current_window < 0:
                self.current_window = len(self.windows) - 1

            self.conn.core.MapWindow(self.windows[self.current_window])

    def _handle_key_press_event(self, event):
        """
        We recieve key press events on windows below the root_window that match keysyms we are
        listening on from the GrabKey method above.

        :param event: KeyPressEvent to handle
        """

        for action in self.config['actions']:
            keycode = self.key_util.get_keycode(
                KeyUtil.string_to_keysym(action['key'])
            )

            modifier = getattr(xcffib.xproto.KeyButMask, self.config['modifier'], 0)

            # If the keycode and modifier of the action match the event's keycode/modifier then
            # run the command.
            if keycode == event.detail and modifier == event.state:
                if 'command' in action:
                    subprocess.Popen(action['command'])
                if 'action' in action:
                    self._handle_action(action['action'])

    def _handle_map_request_event(self, event):
        """
        When a window wants to map, meaning make itself visibile, it send a MapRequestEvent that
        gets send to the window manager. Here we add it to our client list and finish by sending
        a MapWindow request to the server. This request tells the X server to make the window
        visible.

        :param event: MapRequestEvent to handle
        """

        # Get attributes associated with the window
        attributes = self.conn.core.GetWindowAttributes(
            event.window
        ).reply()

        # If the window has the override_redirect attribute set as true then the window manager
        # should not manage the window.
        if attributes.override_redirect:
            return

        # Send map window request to server, telling the server to make this window visible
        self.conn.core.MapWindow(event.window)

        # Resize the window to take up whole screen
        self.conn.core.ConfigureWindow(
            event.window,
            xcffib.xproto.ConfigWindow.X |
            xcffib.xproto.ConfigWindow.Y |
            xcffib.xproto.ConfigWindow.Width |
            xcffib.xproto.ConfigWindow.Height,
            [
                0,
                0,
                self.screen.width_in_pixels,
                self.screen.height_in_pixels,
            ]
        )

        # Add event window to window list
        if event.window not in self.windows:
            self.windows.insert(0, event.window)
            self.current_window = 0

    def _handle_configure_request_event(self, event):
        """
        A configure request is a request that is asking to change a certain thing about a window.
        This can include width/height, x/y, border width, border color, etc.

        :param event: ConfigureRequestEvent to handle
        """

        # Pass on configure request to X server
        self.conn.core.ConfigureWindow(
            event.window,
            xcffib.xproto.ConfigWindow.X |
            xcffib.xproto.ConfigWindow.Y |
            xcffib.xproto.ConfigWindow.Width |
            xcffib.xproto.ConfigWindow.Height |
            xcffib.xproto.ConfigWindow.BorderWidth |
            xcffib.xproto.ConfigWindow.Sibling |
            xcffib.xproto.ConfigWindow.StackMode,
            [
                event.x,
                event.y,
                event.width,
                event.height,
                event.border_width,
                # Siblings are windows that share the same parent. When configuring a window
                # you can specify a sibling window and a stack mode. For example if you
                # specify a sibling window and Above as the stack mode, the window
                # will appear above the sibling window specified.
                event.sibling,
                # Stacking order is where the window should appear.
                # For example above/below the sibling window above.
                event.stack_mode
            ]
        )
