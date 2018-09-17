## Unquill: Copyright (C) 2003  Janez Demsar
##
## During development I peeked a lot at Unquill from John Elliott, 1996-2000.
##
## This program is free software; you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation; either version 2 of the License, or
## (at your option) any later version.
##
## This program is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with this program; if not, write to the Free Software
## Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import pickle
import time
from PyQt5 import QtCore, QtWidgets, QtWidgets
from random import randint

class Quill:
    class Event:
        NIL, LOC, MSG, OBJ, SWAP, PLC = tuple(range(100, 106))
        cond_ops = [("AT", "data.location_no == param1"),
                    ("NOT AT", "data.location_no != param1"),
                    ("AT GT", "data.location_no > param1"),
                    ("AT LT", "data.location_no < param1"),
                    ("PRESENT",
                     "data.objects[param1].location == data.location_no"),
                    ("ABSENT",
                     "data.objects[param1].location != data.location_no"),
                    ("WORN",
                     "data.objects[param1].location == data.Object.WORN"),
                    ("NOT WORN",
                     "data.objects[param1].location != data.Object.WORN"),
                    ("CARRIED",
                     "data.objects[param1].location == data.Object.CARRIED"),
                    ("NOT CARR",
                     "data.objects[param1].location != data.Object.CARRIED"),
                    ("CHANCE", "param1 < randint(1, 100)"),
                    ("ZERO", "not data.flags[param1]"),
                    ("NOT ZERO", "data.flags[param1]"),
                    ("EQ", "data.flags[param1]==param2"),
                    ("GT", "data.flags[param1]>param2"),
                    ("LT", "data.flags[param1]<param2")]

        ptas = {
            0: (["INVEN", "DESC", "QUIT", "END", "DONE", "OK",
                 "ANYKEY", "SAVE", "LOAD", "TURNS", "SCORE",
                 "PAUSE", "GOTO", "MESSAGE", "REMOVE", "GET",
                 "DROP", "WEAR", "DESTROY", "CREATE", "SWAP",
                 "SET", "CLEAR", "PLUS", "MINUS", "LET", "BEEP"],
                [0] * 11 + [1] * 9 + [2, 1, 1] + [2]*16,
                [NIL] * 12 + [LOC, MSG] + [OBJ] * 6 + [SWAP] + [NIL] * 18),
            5: (["INVEN", "DESC", "QUIT", "END", "DONE", "OK",
                 "ANYKEY", "SAVE", "LOAD", "TURNS", "SCORE",
                 "CLS", "DROPALL", "PAUSE", "PAPER", "INK",
                 "BORDER", "GOTO", "MESSAGE", "REMOVE", "GET",
                 "DROP", "WEAR", "DESTROY", "CREATE", "SWAP",
                 "PLACE", "SET", "CLEAR", "PLUS", "MINUS",
                 "LET", "BEEP"],
                [0] * 13 + [1] * 12 + [2, 2, 1, 1] + [2] * 10,
                [NIL] * 17 + [LOC, MSG] + [OBJ] * 6 + [SWAP, PLC] + [NIL]*12),
            7: (["INVEN", "DESC", "QUIT", "END", "DONE", "OK",
                 "ANYKEY", "SAVE", "LOAD", "TURNS", "SCORE",
                 "CLS", "DROPALL", "AUTOG", "AUTOD", "AUTOW",
                 "AUTOR", "PAUSE", "PAPER", "INK", "BORDER",
                 "GOTO", "MESSAGE", "REMOVE", "GET", "DROP",
                 "WEAR", "DESTROY", "CREATE", "SWAP", "PLACE",
                 "SET", "CLEAR", "PLUS", "MINUS", "LET", "BEEP"],
                [0] * 17 + [1] * 12 + [2, 2, 1] + [2] * 7,
                [NIL] * 21 + [LOC, MSG] + [OBJ] * 6 + [SWAP, PLC] + [NIL] * 8)}

        def __init__(self, sna, ptr, dbver=0):
            self.act_ops, self.nparams, self.types = self.ptas[dbver]

            self.word1 = sna[ptr]
            self.word2 = sna[ptr + 1]
            p = sna[ptr + 2] + 256 * sna[ptr + 3]

            self.conditions = []
            while sna[p] != 0xff:
                opcode = sna[p]
                param1 = sna[p + 1]
                if opcode > 12:
                    param2 = sna[p + 2]
                    p += 3
                else:
                    param2 = None
                    p += 2
                self.conditions.append((opcode, param1, param2))

            p += 1
            self.actions = []
            while sna[p] != 0xff:
                opcode = sna[p]
                nparams = self.nparams[opcode]
                params = tuple(sna[p + 1:p + 1 + nparams])
                self.actions.append((opcode, params))
                p += 1 + nparams

        # returns: -1 for error,
        #           0 for not matching,
        #           1 for matching and done (no further processing),
        #           2 for matching, but process further
        def __call__(self, data, system, word1, word2):
            def match(w, sw):
                return w == sw or (not w and sw == 255)
            if system or match(word1, self.word1) and match(word2, self.word2):
                for op, param1, param2 in self.conditions:
                    if not eval(self.cond_ops[op][1]):
                        return 0
                for action in self.actions:
                    meth = getattr(data,
                                   "do_" + self.act_ops[action[0]].lower())
                    res = meth(*action[1])
                    if res:
                        return res
                return 2

    class Location:
        def __init__(self, description, conn=None):
            self.description = description
            self.connections = conn or {}

    class Object:
        INVALID, CARRIED, WORN, NOT_CREATED = 0xff, 0xfe, 0xfd, 0xfc

        def __init__(self, description, initial=NOT_CREATED):
            self.description = description
            self.initial = self.location = initial

    #######################################
    # Actions
    def do_get(self, param1):
        loc = self.objects[param1].location
        if loc == self.Object.WORN or loc == self.Object.CARRIED:
            self.printout("To vendar že nosim!")
            return -1
        elif loc != self.location_no:
            self.printout("Saj ni tukaj.")
            return -1
        elif self.flags[1] == self.nobjects_carry:
            return -1
        else:
            self.objects[param1].location = self.Object.CARRIED
            self.flags[1] += 1

    def do_wear(self, param1):
        loc = self.objects[param1].location
        if loc == self.Object.WORN:
            self.printout("To vendar že nosim!")
            return -1
        elif loc != self.Object.CARRIED:
            self.printout("Tega sploh nimam!")
            return -1
        else:
            self.objects[param1].location = self.Object.WORN

    def do_drop(self, param1):
        loc = self.objects[param1].location
        if (loc == self.Object.WORN) or (loc == self.Object.CARRIED):
            self.objects[param1].location = self.location_no
        else:
            self.printout("Tega sploh nimam.")
            return -1

    def do_remove(self, param1):
        loc = self.objects[param1].location
        if loc != self.Object.WORN:
            self.printout("Tega sploh ne nosim!")
            return -1
        else:
            self.objects[param1].location = self.Object.CARRIED

    def do_dropall(self):
        for obj in self.objects:
            if obj.location == self.Object.WORN or \
                    obj.location == self.Object.CARRIED:
                obj.location = self.location_no
            self.flags[1] = 0

    def do_goto(self, locno):
        self.location = self.locations[locno]
        self.location_no = locno
        self.flags[2] = locno

    def do_create(self, objno):
        loc = self.objects[objno].location
        if loc == self.Object.WORN or loc == self.Object.CARRIED:
            self.flags[1] -= 1
        self.objects[objno].location = self.location_no

    def do_destroy(self, objno):
        loc = self.objects[objno].location
        if loc == self.Object.WORN or loc == self.Object.CARRIED:
            self.flags[1] -= 1
        self.objects[objno].location = self.Object.NOT_CREATED

    def do_place(self, objno, locno):
        loc = self.objects[objno].location
        if loc == self.Object.WORN or loc == self.Object.CARRIED:
            self.flags[1] -= 1
        self.objects[objno].location = locno

    def do_print(self, flagno):
        if flagno > 47:
            self.printout(self.flags[flagno] + 256 * self.flags[flagno+1])
        else:
            self.printout(self.flags[flagno])

    def do_plus(self, flagno, no):
        self.flags[flagno] += no
        if self.flags[flagno] > 255:
            if flagno > 47:
                self.flags[flagno] -= 256
                self.flags[flagno + 1] = (self.flags[flagno + 1] + 1) % 256
            else:
                self.flags[flagno] = 255

    def do_minus(self, flagno, no):
        self.flags[flagno] -= no
        if self.flags[flagno] < 0:
            if flagno > 47:
                self.flags[flagno] += 256
                self.flags[flagno + 1] -= 1
                if self.flags[flagno] == -1:
                    self.flags[flagno] = 0
            else:
                self.flags[flagno] = 0

    def do_inven(self):
        inv = ""
        for obj in self.objects:
            if obj.location == Quill.Object.CARRIED:
                inv += "<LI>%s</LI>" % obj.description
            elif obj.location == Quill.Object.WORN:
                inv += "<LI>%s (nosim)</LI>" % obj.description
        if inv:
            inv = "Prenašam pa tole:<UL>"+inv+"</UL"
        else:
            inv = "Prenašam pa tole:<UL>pravzaprav nič</UL"
        self.printout(inv)

    def do_message(self, msgno):
        self.printout(self.messages[msgno])

    do_mes = do_message

    def do_set(self, flagno):
        self.flags[flagno] = 255

    def do_clear(self, flagno):
        self.flags[flagno] = 0

    def do_let(self, flagno, no):
        self.flags[flagno] = no

    def do_add(self, flg1, flg2):
        return self.do_plus(flg1, self.flags[flg2])

    def do_sum(self, flg1, flg2):
        return self.do_minus(flg1, self.flags[flg2])

    def do_swap(self, obj1, obj2):
        self.objects[obj1].location, self.objects[obj2].location = \
            self.objects[obj2].location, self.objects[obj1].location

    def do_desc(self):
        self.update_location()

    def do_quit(self):
        self.reset()
        self.update_location()

    def do_end(self):
        self.anykey()
        self.reset()
        self.update_location()

    def do_ok(self):
        self.printout("OK")
        return 1

    @staticmethod
    def do_done():
        return 1

    def do_anykey(self):
        self.anykey()

    def do_save(self):
        self.printout("Shranjevati pa še ne znam ...")

    def do_load(self):
        self.printout("Nalagati pa znam ...")

    def do_star(self, _):
        self.printout("'STAR' ni implementiran")

    def do_jsr(self, *_):
        self.printout("'JSR' ni implementiran")

    def do_sound(self, lsb, msg):
        pass

    def do_beep(self, lsb, msg):
        pass

    def do_turns(self):
        self.printout("Ukazov dal si %4i zares<br>" % self.turns)

    def do_score(self):
        self.printout("Nabral si %i odstotkov<br>" % self.flags[30])

    @staticmethod
    def do_pause(s50):
        time.sleep(s50/50)

    def do_cls(self):
        pass

    #######################################
    # Initialization from an .sna file
    def __init__(self, name="kontra.sna", dbver=0):
        def single_string(ptr):
            # TODO: Simplify
            s = ""
            while sna[ptr] != 0xe0:
                s += chr(255 - sna[ptr])
                ptr += 1
            return s

        def word(ptr):
            return sna[ptr] + 256 * sna[ptr + 1]

        def get_sign_ptr():
            sign_ptr = -1
            while True:
                sign_ptr = sna.find(b"\x10", sign_ptr + 1)
                if sign_ptr == -1:
                    raise ValueError("Quill signature not found")
                if sna[sign_ptr+2:sign_ptr+12:2] == b"\x11\x12\x13\x14\x15":
                    return sign_ptr

        def read_vocabulary():
            vocabulary = {}
            index_to_word = []
            pv = self.pvocabulary
            while sna[pv]:
                index = sna[pv + 4]
                w = "".join(chr(255 - x) for x in sna[pv:pv + 4]).strip()
                vocabulary[w] = index
                if index >= len(index_to_word):
                    index_to_word += [None] * (index - len(index_to_word) + 1)
                if not index_to_word[index]:
                    index_to_word[index] = w
                pv += 5
            return vocabulary, index_to_word

        def get_cond_table(ptr):
            events = []
            while sna[ptr]:
                events.append(self.Event(sna, ptr))
                ptr += 4
            return events

        colors = ["#000000", "#0000ff", "#ff0000", "#ff00ff", "#00ff00",
                  "#00ffff", "#ffff00", "#ffffff"]
        replacs = {"&": "&amp", "<": "&lt;", ">": "&gt;", "\x60": "&pound;",
                   "\x7f": "&copy;", "\x95": "č", "\x94": "š", "\xa0": "ž",
                   "\x92": "Č", "\xa2": "Š", "\x90": "Ž"}
        # How would these codes be reset?
        # codes = {"\x12": "<big>", "\x13": "<b>", "\x14": "<i>", "\x15": "<u>"}

        def get_items(ptr, n):
            items = []
            for i in range(n):
                s = ""
                xpos = 0
                while 1:
                    c = chr(255 - sna[ptr])
                    ptr += 1
                    if c in replacs:
                        s += replacs[c]
                        xpos += 1
                    elif c >= ' ':
                        s += c
                        xpos += 1
                    elif c == "\x1f":
                        break
                    elif c == "\x06":
                        if 255 - sna[ptr] == 6:
                            s += "<P>"
                            xpos = 0
                            ptr += 1
                        else:
                            s += " "
                            xpos = 0
                    elif c == "\x10":  # INK
                        cl = 255 - sna[ptr]
                        ptr += 1
                        if cl < 8:
                            s += "<FONT COLOR=%s>" % colors[cl]
                    elif c == "\x11":  # PAPER
                        ptr += 1
                    # elif c in codes:
                    #     if sna[ptr] != 255:
                    #         s += "<%s>" % codes[c]
                    #     else:
                    #         s += "</%s>" % codes[c]
                    #     ptr += 1
                    if xpos == 32:
                        if sna[ptr] != ' ':
                            s += " "
                        xpos = 0
                items.append(s)
            return items

        def read_connections():
            ptr = word(self.pconnections)
            for location in self.locations:
                while sna[ptr] != 0xff:
                    location.connections[sna[ptr]] = sna[ptr + 1]
                    ptr += 2
                ptr += 1

        def read_object_positions():
            ptr = self.pobject_locations
            for i in range(len(self.objects)):
                self.objects[i].initial = sna[ptr + i]

        sna = b"\x00" * (16384 - 27) + open(name, "rb").read()
        ptr = get_sign_ptr() + 13
        self.nobjects_carry = sna[ptr]
        self.nobjects = sna[ptr+1]
        self.nlocations = sna[ptr+2]
        self.nmessages = sna[ptr+3]
        if dbver:
            ptr += 1
            self.nsystem_messages = sna[ptr+3]
            self.pdictionary = ptr + 29

        self.presponse = word(ptr+4)
        self.pprocess = word(ptr+6)
        self.pobjects = word(ptr+8)
        self.plocations = word(ptr+10)
        self.pmessages = word(ptr+12)

        off = 2 if dbver else 0
        self.pconnections = word(ptr + 14 + off)
        self.pvocabulary = word(ptr+16 + off)
        self.pobject_locations = word(ptr+18 + off)

        if dbver:
            psystem_messages = word(ptr+14)
            self.system_messages = \
                get_items(word(psystem_messages), self.nsystem_messages)
            self.pobject_map = word(ptr+22)
        else:
            self.system_messages = [single_string(ptr) for ptr in [
                27132, 27152, 27175, 27209, 27238, 27260, 27317, 27349, 27368,
                27390, 27397, 27451, 27492, 27525, 27551, 27568, 27573, 27584,
                27590, 27613, 27645, 27666, 27681, 27707, 27726]]
            self.pobject_map = None

        self.vocabulary, self.index_to_word = read_vocabulary()
        self.dir_codes = [self.vocabulary[i]
                          for i in ["SZ", "S", "SV", "Z", "V", "JZ", "J", "JV",
                                    "NOTE", "VEN", "GOR", "DOL"]]

        self.responses = get_cond_table(self.presponse)
        self.process = get_cond_table(self.pprocess)
        self.objects = [Quill.Object(x)
                        for x in get_items(word(self.pobjects), self.nobjects)]
        read_object_positions()
        self.locations = [Quill.Location(x)
                          for x in get_items(word(self.plocations),
                                             self.nlocations)]
        read_connections()
        self.messages = get_items(word(self.pmessages), self.nmessages)

        self.location = self.locations[1]
        self.location_no = 1
        self.flags = [0]*64
        self.flags[1] = 255
        self.flags[2] = self.location_no

        self.cheat_locations = {}

        self.turns = 0
        self.izpisano = ""
        self.dlg = self.izpis = self.ukazna = None
        self.setup_ui()
        self.goljufija_const()
        self.reset()

    #######################################
    # Processing
    def reset(self):
        self.flags[2] = self.location_no = 0
        self.location = self.locations[self.location_no]
        self.turns = 0
        for obj in self.objects:
            obj.location = obj.initial
        self.update_location()
        self.process_events(self.process, 1)
        self.goljufija()

    def update_location(self):
        self.izpisano = ""
        if self.flags[0]:
            self.set_location_description(
                "Temno je kot v rogu. Nič ne vidim.", (0,) * 12)
            return

        desc = self.location.description
        inv = [obj.description for obj in self.objects
               if obj.location == self.location_no]
        if len(inv) == 1:
            desc += "<br>Vidim tudi " + inv[0] + "<br>"
        elif inv:
            desc += "<br>Vidim tudi: " + "".join("<br>- %s" % i for i in inv)
        self.set_location_description(
            desc, [direct in self.location.connections
                   for direct in self.dir_codes])

    #######################################
    # GUI
    def setup_ui(self):
        goljufam = True

        dlg = self.dlg = QtWidgets.QWidget()
        dlg.setWindowTitle("Kontrabant")
        dlg.setEnabled(True)
        dlg.resize(1024 if goljufam else 544, 380)

        dlg.setLayout(QtWidgets.QHBoxLayout())
        vbox1 = QtWidgets.QWidget()
        vbox1.setFixedWidth(350)
        vbox1.setLayout(QtWidgets.QVBoxLayout())
        dlg.layout().addWidget(vbox1)

        self.izpis = QtWidgets.QTextEdit()
        self.izpis.setReadOnly(True)
        self.izpis.setMinimumHeight(290)
        self.izpis.setFocusPolicy(QtCore.Qt.NoFocus)
        self.izpis.setStyleSheet(
            "font-family: Arial; font-size: 14; color: white; background: blue")
        self.izpisano = ""

        self.ukazna = QtWidgets.QLineEdit()
        self.ukazna.setFocus()
        self.ukazna.returnPressed.connect(self.user_command)

        vbox1.layout().addWidget(self.izpis)
        vbox1.layout().addWidget(self.ukazna)
        dlg.show()

        tabs = QtWidgets.QTabWidget()
        tabs.setMinimumSize(350, 290)
        dlg.layout().addWidget(tabs)

        self.g_lokacija = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_lokacija, "Lokacija")
        self.g_lokacija.setHeaderHidden(True)

        self.g_predmeti = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_predmeti, "Predmeti")
        self.g_predmeti.setColumnCount(3)
        # GPredmeti->setColumnAlignment(1, AlignHCenter);
        # GPredmeti->setColumnAlignment(2, AlignHCenter);
        self.g_predmeti.setColumnWidth(0, 340)
        # self.g_predmeti.setColumnWidthMode(0, QListView::Manual);
        self.g_predmeti.setSortingEnabled(True)

        self.g_dogodki = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_dogodki, "Dogodki")
        self.g_dogodki.setColumnCount(1)
        self.g_dogodki.setHeaderHidden(True)

        self.g_lokacije = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_lokacije, "Lokacije")
        self.g_dogodki.setHeaderHidden(True)

        self.g_zastavice = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_zastavice, "Zastavice")
        self.g_zastavice.setColumnCount(1)
        self.g_zastavice.setHeaderHidden(True)

        self.g_sporocila = QtWidgets.QTreeWidget()
        tabs.addTab(self.g_sporocila, "Ukazi")
        self.g_sporocila.setColumnCount(1)
        self.g_predmeti.setColumnWidth(0, 100)
        self.g_sporocila.setHeaderHidden(True)

    #######################################
    # Controller
    def process_events(self, table, system, word1=None, word2=None):
        match = 0
        for event in table:
            res = event(self, system, word1, word2)
            if res in [-1, 1]:
                return res
            elif res:
                match = 1
        return match

    def user_command(self):
        command = self.ukazna.text().upper()
        if not command:
            return

        self.ukazna.setText("")
        self.printout('<font color="yellow">&gt;&nbsp; %s</font>' % command)
        self.turns += 1

        commsplit = command.split()
        if commsplit and (commsplit[0] in ["SHRA", "SAVE"]):
            self.save()
            return

        if commsplit and (commsplit[0] in ["NALO", "LOAD"]):
            self.load()
            self.goljufija()
            return

        trans = []
        for w in commsplit:
            t = self.vocabulary.get(w[:4], None)
            if t:
                trans.append(t)

        if not len(trans):
            self.printout("Tega sploh ne razumem. "
                          "Poskusi povedati kako drugače.")

        elif len(trans) == 1 and trans[0] in self.location.connections:
            self.flags[2] = self.location_no = \
                self.location.connections[trans[0]]
            self.location = self.locations[self.location_no]
            self.update_location()

        else:
            if len(trans) == 1:
                m = self.process_events(self.responses, 0, trans[0])
            else:
                m = self.process_events(self.responses, 0, trans[0], trans[1])
            if m == 0:
                if len(trans) == 1 and trans[0] < 16:
                    self.printout("Mar ne vidiš, da v to smer ni poti?")
                else:
                    self.printout("Tega pa ne morem.")

        self.process_events(self.process, 1)
        self.goljufija()

    def save_position(self, fname):
        f = open(fname, "wb")
        pickle.dump(self.flags, f, 1)
        pickle.dump([o.location for o in self.objects], f, 1)

    def load_position(self, fname):
        f = open(fname, "rb")
        self.flags = pickle.load(f)
        object_locations = pickle.load(f)

        self.location_no = self.flags[2]
        self.location = self.locations[self.location_no]

        for r in range(len(object_locations)):
            self.objects[r].location = object_locations[r]
        self.update_location()

    def printout(self, msg):
        self.izpisano += msg + "<br>"
        self.izpis.setHtml(self.izpisano)
        self.izpis.scrollContentsBy(0, 30000)

    def anykey(self):
        return
        QtWidgets.QMessageBox.information(
            None, "Čakam...", "Pritisni OK, pa bova nadaljevala")

    def set_location_description(self, msg, dirs):
        self.printout(msg)

    #######################################
    # Cheating
    def ldesc(self, n):
        return self.locations[n].description[:40]

    def ldesci(self, n):
        return self.ldesc(n), n

    def lidesc(self, n):
        return n, self.ldesc(n)

    def repr_action(self, event, system, skipat=0, adddict=""):
        ldesci = self.ldesci
        lidesc = self.lidesc
        if not system:
            if event.word2 != 255:
                tc = " ".join((self.index_to_word[event.word1],
                              self.index_to_word[event.word2], adddict))
            elif event.word1 != 255:
                tc = " ".join((self.index_to_word[event.word1], adddict))
            else:
                tc = adddict
        else:
            tc = adddict

        ta = []
        for op, param1, param2 in event.conditions:
            if self.Event.cond_ops[op][0] == "AT":
                if skipat:
                    continue
                else:
                    if tc:
                        tc += "  [AT %s (%i)]" % ldesci(param1)
                    else:
                        tc = "AT %s (%i)" % ldesci(param1)
            else:
                s = "--> %s " % self.Event.cond_ops[op][0]
                if param1:
                    if op < 4:
                        s += "%i (%s...) " % lidesc(param1)
                    elif op < 10:
                        s += "%i (%s) " % (param1,
                                           self.objects[param1].description)
                    elif op < 13:
                        s += "%i " % param1
                    else:
                        s += "%i %i " % (param1, param2)
                ta.append(s)

        for action in event.actions:
            tt = event.act_ops[action[0]]
            atype = event.types[action[0]]
            param1, param2 = (action[1] + (None, None))[:2]
            if atype == self.Event.LOC:
                tt += " %i (%s...)" % lidesc(param1)
            elif atype == self.Event.MSG:
                tt += " '%s'" % self.messages[param1]
            elif atype == self.Event.OBJ:
                tt += " '%s' (%i)" % (
                    self.objects[param1].description, param1)
            elif atype == self.Event.SWAP:
                tt += " '%s' (%i) '%s' (%i)" % (
                    self.objects[param1].description, param1,
                    self.objects[param2].description, param2)
            elif event.nparams[action[0]] == 1:
                tt += " %i" % param1
            elif event.nparams[action[0]] == 2:
                tt += " %i %i" % (param1, param2)
            ta.append(tt)
        return tc, ta, not tc

    @staticmethod
    def parse_tree(tree_widget, tree):
        tree_widget.clear()
        for state, events in tree:
            it = QtWidgets.QTreeWidgetItem(state)
            tree_widget.addTopLevelItem(it)
            for event in events:
                text, subnodes, is_open = (event + (None, None))[:3]
                if isinstance(text, str):
                    it2 = QtWidgets.QTreeWidgetItem([text])
                    it.addChild(it2)
                    if subnodes:
                        it2.addChildren([QtWidgets.QTreeWidgetItem([i])
                                         for i in subnodes])
                    it2.setExpanded(True)
                else:
                    it.addChildren(QtWidgets.QTreeWidgetItem([i]) for i in text)

    def goljufija_const(self):
        repr_act = self.repr_action
        ldesci = self.ldesci

        def getlocations():
            def process_events(loc, table, system):
                acts, spec_exits, spec_approaches = [], [], []
                for event in table:
                    for op, param1, param2 in event.conditions:
                        if op <= 1 and param1 == loc:
                            for action in event.actions:
                                if event.act_ops[action[0]] == "GOTO":
                                    if action[1][0] != loc:
                                        spec_exits.append(
                                            repr_act(event, system, 1,
                                                     "-> %s (%i)"
                                                     % ldesci(action[1][0])))
                                    else:
                                        spec_approaches.append(
                                            repr_act(event, system, 1,
                                                     "<- %s (%i)"
                                                     % ldesci(param1)))
                                    break
                            else:
                                # It is not an exit
                                acts.append(repr_act(event, system, 0))
                            break
                    else:
                        # There is no 'AT location';
                        # check whether this can be a special approach
                        for action in event.actions:
                            if event.act_ops[action[0]] == "GOTO" and \
                                    action[1][0] == loc:
                                spec_approaches.append(repr_act(event, system))
                                break

                    # There is an 'AT location';
                    # check whether this is an exit event
                return acts, spec_exits, spec_approaches

            def process_exits(loc):
                return ["%s -> %s (%i)" %
                        ((self.index_to_word[d],) + ldesci(n))
                        for d, n in self.locations[loc].connections.items()]

            def process_approaches(loc):
                app = []
                for src, location in enumerate(self.locations):
                    if loc in list(location.connections.values()):
                        for d, n in location.connections.items():
                            if n == loc:
                                app.append("%s (%i) -> %s" %
                                           (ldesci(src) +
                                            (self.index_to_word[d], )))
                return app

            self.cheat_locations = {}

            for i in range(len(self.locations)):
                exits = process_exits(i)
                approaches = process_approaches(i)

                responses, se, sa = process_events(i, self.responses, 0)
                exits += se
                approaches += sa

                processes, se, sa = process_events(i, self.process, 1)
                exits += se
                approaches += sa

                self.cheat_locations[i] = (responses, processes)

                it = QtWidgets.QTreeWidgetItem(
                    ["%s (%i)" % (self.locations[i].description, i)])
                self.g_lokacije.addTopLevelItem(it)
                for name, content in (
                        ("Vhodi", approaches), ("Izhodi", exits),
                        ("Ukazi", responses), ("Dogodki", processes)):
                    if not content:
                        continue
                    it2 = QtWidgets.QTreeWidgetItem([name])
                    it.addChild(it2)
                    for con in content:
                        if isinstance(con, str):
                            it3 = QtWidgets.QTreeWidgetItem([con])
                        else:
                            it3 = QtWidgets.QTreeWidgetItem([con[0]])
                            it3.addChildren([QtWidgets.QTreeWidgetItem([i])
                                             for i in con[1]])
                        it3.setExpanded(True)
                        it2.addChild(it3)
                    it2.setExpanded(True)

        def getmessages():
            def process_events(msg_no, table, system):
                acts = []
                for event in table:
                    for action in event.actions:
                        if event.act_ops[action[0]][:3] == "MES" and \
                                action[1][0] == msg_no:
                            break
                    else:
                        continue
                    acts.append(repr_act(event, system))
                return acts
            return [("%s (%i)" % (self.messages[i], i),
                     process_events(i, self.responses, 0) +
                     process_events(i, self.process, 1))
                    for i in range(len(self.messages))]

        def add_event_to_tree(tree, event, skip_at=0):
            tc, ta, isopen = repr_act(event, skip_at)
            it = QtWidgets.QTreeWidgetItem([tc])
            tree.addTopLevelItem(it)
            it.addChildren([QtWidgets.QTreeWidgetItem([i]) for i in ta])

        def get_responses():
            acts = []
            trivial = {self.vocabulary["DAJ"]: "DROP",
                       self.vocabulary["VZEM"]: "GET",
                       self.vocabulary["OBLE"]: "WEAR",
                       self.vocabulary["SLEC"]: "REMOVE"}
            for event in self.responses:
                if (not event.conditions and len(event.actions) == 2 and
                        event.act_ops[event.actions[1][0]] in ["OK", "DONE"] and
                        trivial.get(event.word1, None) ==
                        event.act_ops[event.actions[0][0]]):
                    continue
                if event.word1 < 16:
                    for op, param1, param2 in event.conditions:
                        if not op:
                            break
                    else:
                        self.g_sporocila.addTopLevelItem(
                            QtWidgets.QTreeWidgetItem([repr_act(event, 0)]))
                        continue
                add_event_to_tree(self.g_sporocila, event)

        def get_process():
            for event in self.process:
                add_event_to_tree(self.g_dogodki, event, 1)

        return (getlocations(), getmessages(),
                get_responses(), get_process(), None)

    def goljufija(self):
        repr_act = self.repr_action

        def getlocation():
            self.g_lokacija.clear()
            conn = list(self.location.connections.items())
            if conn:
                it = QtWidgets.QTreeWidgetItem(["Izhodi"])
                self.g_lokacija.addTopLevelItem(it)
                it.addChildren([QtWidgets.QTreeWidgetItem(
                    ["%s: %s (%i)" % (
                        self.index_to_word[dire],
                        self.locations[loc].description[:40], loc)])
                    for dire, loc in conn])
                it.setExpanded(True)

            responses, processes = self.cheat_locations[self.location_no]
            if responses:
                it = QtWidgets.QTreeWidgetItem(["Ukazi"])
                self.g_lokacija.addTopLevelItem(it)
                for content in responses:
                    it2 = QtWidgets.QTreeWidgetItem([content[0]])
                    it.addChild(it2)
                    it2.addChildren([QtWidgets.QTreeWidgetItem([i])
                                     for i in content[1]])
                    it2.setExpanded(True)
                it.setExpanded(True)

            if processes:
                it = QtWidgets.QTreeWidgetItem(["Dogodki"])
                self.g_lokacija.addTopLevelItem(it)
                for content in processes:
                    it2 = QtWidgets.QTreeWidgetItem([content[0]])
                    it.addChild(it2)
                    it2.addChildren([QtWidgets.QTreeWidgetItem([i])
                                     for i in content[1]])
                    it2.setExpanded(True)
                it.setExpanded(True)

        objlocs = {self.Object.CARRIED: "imam",
                   self.Object.WORN: "nosim",
                   self.Object.NOT_CREATED: "ne obstaja",
                   self.Object.INVALID: "ne obstaja"}

        def getobjects():
            def process_events(object_no, table, system):
                acts = []
                trivial = {self.vocabulary["DAJ"]: "DROP",
                           self.vocabulary["VZEM"]: "GET",
                           self.vocabulary["OBLE"]: "WEAR",
                           self.vocabulary["SLEC"]: "REMOVE"}
                for event in table:
                    if not system and not event.conditions and \
                            len(event.actions) == 2 and \
                            event.act_ops[event.actions[1][0]] in ["OK",
                                                                   "DONE"] \
                            and trivial.get(event.word1, None) == \
                            event.act_ops[event.actions[0][0]]:
                        continue
                    for op, param1, param2 in event.conditions:
                        if 4 <= op <= 9 and param1 == object_no:
                            break
                    else:
                        for action in event.actions:
                            atype = event.types[action[0]]
                            if (atype in [event.OBJ, event.SWAP] and
                                    action[1][0] == object_no or
                                    atype == self.Event.SWAP and
                                    action[1][1] == object_no):
                                break
                        else:
                            continue  # not interesting, does not mention
                                      # object_no neither in conditions nor
                                      # in actions
                    acts.append(repr_act(event, system))
                return acts

            def objloc(objno):
                loc = self.objects[objno].location
                if loc < 0xfc:
                    return str(loc)
                else:
                    return objlocs[loc]

            if not hasattr(self, "cheatobjects"):
                self.cheatobjects = [([self.objects[i].description, str(i),
                                       objloc(i)],
                                      process_events(i, self.responses, 0) +
                                      process_events(i, self.process, 1))
                                     for i in range(len(self.objects))]
            else:
                for i in range(len(self.objects)):
                    self.cheatobjects[i][0][2] = objloc(i)
            return self.cheatobjects

        def getflags():
            flops = [Quill.Event.ptas[0][0].index(x)
                     for x in ["PLUS", "MINUS", "SET", "CLEAR", "LET"]]

            def process_events(flag_no, table, system):
                acts = []
                for event in table:
                    for op, param1, param2 in event.conditions:
                        if op >= 11 and param1 == flag_no:
                            break
                    else:
                        for action in event.actions:
                            if action[0] in flops and flag_no == action[1][0]:
                                break
                        else:
                            continue  # not interesting, does not mention the
                                     # flag neither in conditions nor in action
                    acts.append(repr_act(event, system))
                return acts

            if not hasattr(self, "cheatflags"):
                self.cheatflags = [(["%i = %i" % (i, self.flags[i])],
                                    process_events(i, self.responses, 0) +
                                    process_events(i, self.process, 1))
                                   for i in range(len(self.flags))]
            else:
                self.cheatflags = [(["%i = %i" % (i, self.flags[i])],
                                    self.cheatflags[i][1])
                                   for i in range(len(self.flags))]
            return self.cheatflags[:3] + [x for x in self.cheatflags[3:]
                                          if x[1]]

        getlocation()
        self.parse_tree(self.g_zastavice, getflags())
        self.parse_tree(self.g_predmeti, getobjects())


app = QtWidgets.QApplication([])
q = Quill()
app.exec()
