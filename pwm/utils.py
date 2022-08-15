import xpybutil
import xpybutil.keybind


class KeyUtil:
    def __init__(self, conn):
        self.conn = conn

        # The number of keycodes associated with your keyboard. This number will never be less
        # than eight because the first keycodes are used for modifiers ()
        self.min_keycode = self.conn.get_setup().min_keycode
        self.max_keycode = self.conn.get_setup().max_keycode

        self.keyboard_mapping = self.conn.core.GetKeyboardMapping(
            # The array of keysyms returned by this function will start at min_keycode so that
            # the modifiers are not included.
            self.min_keycode,
            # Total number of keycodes
            self.max_keycode - self.min_keycode + 1
        ).reply()

    def string_to_keysym(string):
        return xpybutil.keysymdef.keysyms[string]

    def get_keysym(self, keycode, keysym_offset):
        """
        Get a keysym from a keycode and state/modifier.

        Only a partial implementation. For more details look at Keyboards section in X Protocol:
        https://www.x.org/docs/XProtocol/proto.pdf

        :param keycode: Keycode of keysym
        :param keysym_offset: The modifier/state/offset we are accessing
        :returns: Keysym
        """

        keysyms_per_keycode = self.keyboard_mapping.keysyms_per_keycode

        # The keyboard_mapping keysyms. This is a 2d array of keycodes x keysyms mapped to a 1d
        # array. Each keycode row has a certain number of keysym columns. Imagine we had the
        # keycode for 't'. In the 1d array we first jump to the 't' row with
        # keycode * keysyms_per_keycode. Now the next keysyms_per_keycode number
        # of items in the array are columns for the keycode row of 't'. To access a specific
        # column we just add the keysym position to the keycode * keysyms_per_keycode position.
        return self.keyboard_mapping.keysyms[
            # The keysyms array does not include modifiers, so subtract min_keycode from keycode.
            (keycode - self.min_keycode) * self.keyboard_mapping.keysyms_per_keycode + keysym_offset
        ]

    def get_keycode(self, keysym):
        """
        Get a keycode from a keysym

        :param keysym: keysym you wish to convert to keycode
        :returns: Keycode if found, else None
        """

        # X must map the keys on your keyboard to something it can understand. To do this it has
        # the concept of keysyms and keycodes. A keycode is a number 8-255 that maps to a physical
        # key on your keyboard. X then generates an array that maps keycodes to keysyms.
        # Keysyms differ from keycodes in that they take into account modifiers. With keycodes
        # 't' and 'T' are the same, but they have different keysyms. You can think of 'T'
        # as 't + CapsLock' or 't + Shift'.

        keysyms_per_keycode = self.keyboard_mapping.keysyms_per_keycode

        # Loop through each keycode. Think of this as a row in a 2d array.
        # Row: loop from the min_keycode through the max_keycode
        for keycode in range(self.min_keycode, self.max_keycode + 1):
            # Col: loop from 0 to keysyms_per_keycode. Think of this as a column in a 2d array.
            for keysym_offset in range(0, keysyms_per_keycode):
                if self.get_keysym(keycode, keysym_offset) == keysym:
                    return keycode

        return None
