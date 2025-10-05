#========================================
#   HP67/97 Woodstock Assembler
#========================================
#
# Kjell Christenson 2025
#
# The original code was written by Oliver De Smet
# v1.7.3 (2011) https://www.hpcalc.org/details/9548
#
# Ported to python v3, enhanced and modified
#
# Use --help for usage
#========================================

# Original HP firmware MD5 checksums;
# hp97:
# md5 bank 0 c77ec4a018a39945dbb9742f6c37323e
# md5 bank 1 1cd95f427cba732025569be58aaa3aae

# hp67:
# md5 bank 0 8603efa8aadb3a6da3c39be41717be10
# md5 bank 1 2464468d155d8989ef0b83c851143450

from hashlib import md5
import sys
import argparse

class MyException(Exception):
    pass

class HP67():
    _rom = {}
    _labels = {}
    _last_global = ''
    _pc = 0
    _bank = 0
    _ifthen = 0
    _cy = 0
    _del_rom = 0
    _del_rom_emit = 0
    _delta_labels = 0
    _del_rom_force = 0
    _del_rom_force_rom = 0
    _defines = {}
    _cur_define = ''
    _do_line = True             # 1/true: process source lines
    _do_line_skip_elses = False # 1/true: one if/elif caluse was - all elses are skipped
    _do_line_stack = []         # [do_line, do_line_skip_elses] history
    
    _pass = 0

    _op_arith = ('0 -> a[%s]', '0 -> b[%s]',               # .. ..
                 'a <-> b[%s]', 'a -> b[%s]',              # .. ..
                 'a <-> c[%s]', 'c -> a[%s]',              # .. ..
                 'b -> c[%s]', 'b <-> c[%s]',              # .. ..
                 '0 -> c[%s]', 'a + b -> a[%s]',           # .. CY
                 'a + c -> a[%s]', 'c + c -> c[%s]',       # CY CY
                 'a + c -> c[%s]', 'a + 1 -> a[%s]',       # CY CY
                 'shift left a[%s]', 'c + 1 -> c[%s]',     # .. CY
                 'a - b -> a[%s]', 'a - c -> c[%s]',       # CY CY
                 'a - 1 -> a[%s]', 'c - 1 -> c[%s]',       # CY CY
                 '0 - c -> c[%s]', '0 - c - 1 -> c[%s]',   # CY CY
                 'if b[%s] = 0', 'if c[%s] = 0',           # .. ..
                 'if a >= c[%s]', 'if a >= b[%s]',         # .. ..
                 'if a[%s] # 0', 'if c[%s] # 0',           # .. ..
                 'a - c -> a[%s]', 'shift right a[%s]',    # CY ..
                 'shift right b[%s]', 'shift right c[%s]') # .. ..
    _op_arith_cy = ( 0, 0, 0, 0, 0, 0, 0, 0,
                     0, 1, 1, 1, 1, 1, 0, 1,
                     1, 1, 1, 1, 1, 1, 0, 0,
                     0, 0, 0, 0, 1, 0, 0, 0 )
    _op_tef = ('p', 'wp', 'xs', 'x', 's', 'm', 'w', 'ms')
    
    _op_misc_0a = ('nop', 'crc ready?', 'crc ?20?', 'crc test f1',
                  'crc set f2', 'crc test f2', 'crc ?60?', 'crc test f3',
                  'crc set f4', 'crc test f4', 'crc set f0', 'crc clear f0',
                  'crc set f1', 'crc clear f1', 'crc ?E0?', 'crc card r/w')
    _op_misc_0b = ('no operation', 'crc 100', 'crc 200', 'crc 300',
                  'crc 400', 'crc 500', 'crc 600', 'crc 700',
                  'crc 1000', 'crc 1100', 'crc 1200', 'crc 1300',
                  'crc 1400', 'crc 1500', 'crc 1600', 'crc 1700')

    _op_misc_1 = ('1 -> S0', '1 -> S1', '1 -> S2', '1 -> S3',
                  '1 -> S4', '1 -> S5', '1 -> S6', '1 -> S7',
                  '1 -> S8', '1 -> S9', '1 -> S10', '1 -> S11',
                  '1 -> S12', '1 -> S13', '1 -> S14', '1 -> S15')

    _op_misc_2a= ('clear reg', 'clear S', 'display toggle', 'display off',
                  'm1 <-> c', 'm1 -> c', 'm2 <-> c', 'm2 -> c',
                    'stack -> a', 'down rotate', 'y -> a', 'c -> stack',
                    'decimal', 'unknown D2', 'f -> a', 'f <-> a')
    _op_misc_2b= ('clear reg', 'clear status', 'display toggle', 'display off',
                  'm1 exchange c', 'm1 -> c', 'm2 exchange c', 'm2 -> c',
                    'stack -> a', 'down rotate', 'y -> a', 'c -> stack',
                    'decimal', 'unknown D2', 'f -> a', 'f exchange a')

    _op_misc_3 = ('0 -> S0', '0 -> S1', '0 -> S2', '0 -> S3',
                  '0 -> S4', '0 -> S5', '0 -> S6', '0 -> S7',
                  '0 -> S8', '0 -> S9', '0 -> S10', '0 -> S11',
                  '0 -> S12', '0 -> S13', '0 -> S14', '0 -> S15')

    _op_misc_4a= ('keys -> rom addr', 'keys -> a', 'a -> rom addr',
                  'display reset twf', 'binary', 'circulate a left',
                  'p - 1 -> p', 'p + 1 -> p', 'return',
                  'pik home?', 'pik cr?', 'pik keys?', 'pik ?C4?',
                  'pik ?D4?', 'pik ?E4?', 'pik print3')
    _op_misc_4b= ('keys -> rom address', 'keys -> a', 'a -> rom address',
                  'display reset twf', 'binary', 'rotate a left',
                  'p - 1 -> p', 'p + 1 -> p', 'return',
                  'pik home?', 'pik cr?', 'pik keys?', 'pik ?C4?',
                  'pik ?D4?', 'pik ?E4?', 'pik print3')

    _op_misc_5 = ('if S0 = 1', 'if S1 = 1', 'if S2 = 1', 'if S3 = 1',
                  'if S4 = 1', 'if S5 = 1', 'if S6 = 1', 'if S7 = 1',
                  'if S8 = 1', 'if S9 = 1', 'if S10 = 1', 'if S11 = 1',
                  'if S12 = 1', 'if S13 = 1', 'if S14 = 1', 'if S15 = 1')

    _op_misc_6 = ('load constant 0', 'load constant 1', 'load constant 2', 'load constant 3',
                  'load constant 4', 'load constant 5', 'load constant 6', 'load constant 7',
                  'load constant 8', 'load constant 9', 'load constant 10', 'load constant 11',
                  'load constant 12', 'load constant 13', 'load constant 14', 'load constant 15')

    _op_misc_7 = ('if S0 = 0', 'if S1 = 0', 'if S2 = 0', 'if S3 = 0',
                  'if S4 = 0', 'if S5 = 0', 'if S6 = 0', 'if S7 = 0',
                  'if S8 = 0', 'if S9 = 0', 'if S10 = 0', 'if S11 = 0',
                  'if S12 = 0', 'if S13 = 0', 'if S14 = 0', 'if S15 = 0')

    _op_misc_8 = ('sel rom 0', 'sel rom 1', 'sel rom 2', 'sel rom 3',
                  'sel rom 4', 'sel rom 5', 'sel rom 6', 'sel rom 7',
                  'sel rom 8', 'sel rom 9', 'sel rom A', 'sel rom B',
                  'sel rom C', 'sel rom D', 'sel rom E', 'sel rom F')

    _op_misc_9 = ('if p = 4', 'if p = 8', 'if p = 12', 'if p = 2',
                  'if p = 9', 'if p = 1', 'if p = 6', 'if p = 3',
                  'if p = 1', 'if p = 13', 'if p = 5', 'if p = 0',  # duplicate 1 ?
                  'if p = 11', 'if p = 10', 'if p = 7', 'if p = 4') # duplicate 4 ?
    
    _op_misc_A1= ('c -> data r0', 'c -> data r1', 'c -> data r2', 'c -> data r3',
                  'c -> data r4', 'c -> data r5', 'c -> data r6', 'c -> data r7',
                  'c -> data r8', 'c -> data r9', 'c -> data rA', 'c -> data rB',
                  'c -> data rC', 'c -> data rD', 'c -> data rE', 'c -> data rF')
    _op_misc_A2= ('c -> data register 0', 'c -> data register 1', 'c -> data register 2', 'c -> data register 3',
                  'c -> data register 4', 'c -> data register 5', 'c -> data register 6', 'c -> data register 7',
                  'c -> data register 8', 'c -> data register 9', 'c -> data register 10', 'c -> data register 11',
                  'c -> data register 12', 'c -> data register 13', 'c -> data register 14', 'c -> data register 15')

    _op_misc_B = ('if p # 4', 'if p # 8', 'if p # 12', 'if p # 2',
                  'if p # 9', 'if p # 1', 'if p # 6', 'if p # 3',
                  'if p # 1', 'if p # 13', 'if p # 5', 'if p # 0',  # duplicate 1 ?
                  'if p # 11', 'if p # 10', 'if p # 7', 'if p # 4') # duplicate 4 ?

    _op_misc_C1= ('crc set disp digits', 'crc clear disp digits', 'crc motor on', 'crc motor off',
                  'crc ?4C?', 'crc card in?', 'crc set wr mode', 'crc set rd mode',
                  'bank switch', 'c -> addr', 'clear data regs', 'c -> data',
                  'rom selftest', 'crc ?DC?', 'pik print6', "hi i'm woodstock")
    _op_misc_C2= ('crc 60', 'crc 160', 'crc 260', 'crc 360',
                  'crc 460', 'crc 560', 'crc 660', 'crc 760',
                  'bank switch', 'c -> data address', 'clear data registers', 'c -> data',
                  'rom selftest', 'crc 1560', 'pik print6', "hi i'm woodstock")

    _op_misc_D1= ('del sel rom 0', 'del sel rom 1', 'del sel rom 2', 'del sel rom 3',
                  'del sel rom 4', 'del sel rom 5', 'del sel rom 6', 'del sel rom 7',
                  'del sel rom 8', 'del sel rom 9', 'del sel rom A', 'del sel rom B',
                  'del sel rom C', 'del sel rom D', 'del sel rom E', 'del sel rom F')
    _op_misc_D2= ('delayed select rom 0', 'delayed select rom 1', 'delayed select rom 2', 'delayed select rom 3',
                  'delayed select rom 4', 'delayed select rom 5', 'delayed select rom 6', 'delayed select rom 7',
                  'delayed select rom 8', 'delayed select rom 9', 'delayed select rom 10', 'delayed select rom 11',
                  'delayed select rom 12', 'delayed select rom 13', 'delayed select rom 14', 'delayed select rom 15')

    _op_misc_E1= ('data r0 -> c', 'data r1 -> c', 'data r2 -> c', 'data r3 -> c',
                  'data r4 -> c', 'data r5 -> c', 'data r6 -> c', 'data r7 -> c',
                  'data r8 -> c', 'data r9 -> c', 'data rA -> c', 'data rB -> c',
                  'data rC -> c', 'data rD -> c', 'data rE -> c', 'data rF -> c')
    _op_misc_E2= ('data register 0 -> c', 'data register 1 -> c', 'data register 2 -> c', 'data register 3 -> c',
                  'data register 4 -> c', 'data register 5 -> c', 'data register 6 -> c', 'data register 7 -> c',
                  'data register 8 -> c', 'data register 9 -> c', 'data register 10 -> c', 'data register 11 -> c',
                  'data register 12 -> c', 'data register 13 -> c', 'data register 14 -> c', 'data register 15 -> c')

    _op_misc_F = ('14 -> p', '4 -> p', '7 -> p', '8 -> p',  # 14 -> p, invalid or same as 0 -> p?
                  '11 -> p', '2 -> p', '10 -> p', '12 -> p',
                  '1 -> p', '3 -> p', '13 -> p', '6 -> p',
                  '0 -> p', '9 -> p', '5 -> p', '14 -> p')  # 14 -> p, invalid or same as 0 -> p?

    _op_branch = ('then go to', 'if n/c go to', 'go to', 'jsb', 'if no carry go to')

    def _get_address(self, l):
        addr = 0
        if (len(l) > 0):
            try:
                if (l[0] == '$'):
                    addr = int(l[1:], 16)
                else:
                    addr = int(l[0:], 0)
            except:
                print("0x%X%03X: " % (self._bank, self._pc), l)
                raise MyException('Error: Bad address')
        return addr

    def _match(self, l, ops):
        found = -1
        length = 0
        j = 0
        ## print('ops=', ops, " ll=", l)
        for op in ops:
            o = op.split()
            o_l = len(o)
            l_l = len(l)
            if (o_l <= l_l):
                nok = 0
                for i in range(o_l):
                    if (o[i].lower() != l[i].lower()):
                        nok = 1
                        break
                if (nok == 0):
                    length = o_l
                    found = j
                    ##print('--found=', j, ' len=', length, ' op=', op) ###
            j = j + 1
            if (found >= 0):
                break
        return (found, length,)
    
    def _calc_code(self, col, line, klass):
        return col << 6 | line << 2 | klass
    
    def _find_misc(self, ll):
        found, length = self._match(ll, self._op_misc_0a)
        if (found >= 0):
            return (self._calc_code(found, 0, 0), length,)
        found, length = self._match(ll, self._op_misc_0b)
        if (found >= 0):
            return (self._calc_code(found, 0, 0), length,)
        found, length = self._match(ll, self._op_misc_1)
        if (found >= 0):
            return (self._calc_code(found, 1, 0), length,)
        found, length = self._match(ll, self._op_misc_2a)
        if (found >= 0):
            return (self._calc_code(found, 2, 0), length,)
        found, length = self._match(ll, self._op_misc_2b)
        if (found >= 0):
            return (self._calc_code(found, 2, 0), length,)
        found, length = self._match(ll, self._op_misc_3)
        if (found >= 0):
            return (self._calc_code(found, 3, 0), length,)
        found, length = self._match(ll, self._op_misc_4a)
        if (found >= 0):
            return (self._calc_code(found, 4, 0), length,)
        found, length = self._match(ll, self._op_misc_4b)
        if (found >= 0):
            return (self._calc_code(found, 4, 0), length,)
        found, length = self._match(ll, self._op_misc_5)
        if (found >= 0):
            self._ifthen = 1
            return (self._calc_code(found, 5, 0), length,)
        found, length = self._match(ll, self._op_misc_6)
        if (found >= 0):
            return (self._calc_code(found, 6, 0), length,)
        found, length = self._match(ll, self._op_misc_7)
        if (found >= 0):
            self._ifthen = 1
            return (self._calc_code(found, 7, 0), length,)
        found, length = self._match(ll, self._op_misc_8)
        if (found >= 0):
            return (self._calc_code(found, 8, 0), length,)
        found, length = self._match(ll, self._op_misc_9)
        if (found >= 0):
            self._ifthen = 1
            return (self._calc_code(found, 9, 0), length,)
        found, length = self._match(ll, self._op_misc_A1)
        if (found >= 0):
            return (self._calc_code(found, 10, 0), length,)
        found, length = self._match(ll, self._op_misc_A2)
        if (found >= 0):
            return (self._calc_code(found, 10, 0), length,)
        found, length = self._match(ll, self._op_misc_B)
        if (found >= 0):
            self._ifthen = 1
            return (self._calc_code(found, 11, 0), length,)
        found, length = self._match(ll, self._op_misc_E1)    # must do E2 before C1, else match on "c -> data"
        if (found >= 0):
            return (self._calc_code(found, 14, 0), length,)
        found, length = self._match(ll, self._op_misc_E2)
        if (found >= 0):
            return (self._calc_code(found, 14, 0), length,)
        found, length = self._match(ll, self._op_misc_C2)    # must do C2 before C1, else match on "c -> data"
        if (found >= 0):
            return (self._calc_code(found, 12, 0), length,)
        found, length = self._match(ll, self._op_misc_C1)
        if (found >= 0):
            return (self._calc_code(found, 12, 0), length,)
        found, length = self._match(ll, self._op_misc_D1)
        if (found >= 0):
            return (self._calc_code(found, 13, 0), length,)
        found, length = self._match(ll, self._op_misc_D2)
        if (found >= 0):
            return (self._calc_code(found, 13, 0), length,)
        found, length = self._match(ll, self._op_misc_F)
        if (found >= 0):
            return (self._calc_code(found, 15, 0), length,)
        return (-1, 0,)

    def _find_arith(self, ll):
        k = 0
        for tef in self._op_tef:
            arith = []
            for op in self._op_arith:
                arith.append(op % tef)
            #print arith
            if (len(ll) > 2 and ll[1] == "exchange"):
                ll[1] = "<->"
            found, length = self._match(ll, arith)
            if (found >= 0):
                self._cy = self._op_arith_cy[found]
                if ((found >= 22) and (found <= 27)):
                    self._ifthen = 1
                return (found << 5 | k << 2 | 0x002, length,)
            k = k + 1
        return (-1, 0,)
        
    def _find_opcode(self, ll, passe, last):
        found, length = self._match(ll, self._op_branch)
        if (found >= 0):
            if (found == 0):            # then go to
                if (self._ifthen == 0):
                    print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                    raise MyException('Error: "then go to" - without if')
                else:
                    self._ifthen = 0
                    if (passe == 0):  # pass 0
                        code = 0x000
                        return (code, length + 1,)
                    if (passe == 1):  # pass 1,2,3...
                        if (ll[length][0] == '$'):   # direct offset 0..3ff
                            adr = (self._pc & 0xfc00) + (self._get_address(ll[length]) & 0x3ff)
                        else:
                            adr = self._find_label(ll[length])
                        if (last):
                            if (adr < 0):
                                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                                raise MyException('Error: Label not found')
                        code = adr - (self._pc & 0xC00)
                        if ((code < 0) or (code > 1023)):
                            if (last):
                                print("0x%x%03X: " % (self._bank, self._pc), " ".join(ll),
                                      " [ dest=0x%X%03X (%d) ]" % (self._bank, adr, code))
                                raise MyException('Error: "then go to" - too far')
                        return (code, length + 1,)
            elif (found == 1 or found == 4):        # "if n/c go to"  or "if no carry go to"
                if (self._cy == 0 and found == 1):  # only test for the "n/c" mnemonic  FIXME: use a switch?
                    print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                    raise MyException('Error: "if n/c go to" without CY operation')
                else:
                    self._cy = 0
                    if (passe == 0):   # pass 0
                        code = 0x003
                        return (code, length + 1,)
                    if (passe == 1):   # pass 1,2,3...
                        if (ll[length][0] == '$'):   # direct offset 0..ff
                            adr = (self._pc & 0xff00) + (self._get_address(ll[length]) & 0xff)  # FIXME: check bank# pc & 0xc00 == addr & 0xc00
                        else:
                            adr = self._find_label(ll[length])
                        if (last):
                            if (adr < 0):
                                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                                raise MyException('Error: Label not found')
                        dist = adr - (self._pc & 0xF00)
                        if (last and self._del_rom_force == 0 and (self._pc & 0xFF) == 0xFF):
                            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                            raise MyException('Error: "go to" not allowed on last word in ROM')
                        if ((dist < 0) or (dist > 255)):
                            if (last):
                                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll),
                                      " [ dest=0x%X%03X (%d) ]" % (self._bank, adr, dist))
                                raise MyException('Error, "if n/c go to" - too far')
                        code = dist << 2 | 0x003
                        return (code, length + 1,)
            elif ((found == 2) or (found == 3)):          # go to or jsb
                    self._cy = 0
                    if (passe == 0):    # pass 0
                        if (ll[length][0] == '$'):        # direct offset 0..ff
                            if (self._del_rom_force):     # a "del_sel_rom" is active
                                adr = (self._del_rom_force_rom << 8) + (self._get_address(ll[length]) & 0xff)
                            else:
                                adr = (self._pc & 0xff00) + (self._get_address(ll[length]) & 0xff)  # FIXME: check bank# pc & 0xc00 == addr & 0xc00
                        else:
                            adr = self._find_label(ll[length])
                        if (adr >= 0):
                            dist = adr - (self._pc & 0xF00)
                            if ((dist < 0) or (dist > 255)):
                                if (self._del_rom_force): # FIXME: would 'auto' be used w/ direct offsets?
                                    pass
                                else:
                                    self._del_rom_emit = 1  # emit 'dly sel bank' before long go-to
                                    self._del_rom = (adr >> 8) << 6 | 0x034
                                dist = adr & 0x0FF
                            if (found == 3):
                                code = dist << 2 | 0x001
                            else:
                                code = dist << 2 | 0x003
                        else:
                            if (found == 3):
                                code = 0x001
                            else:
                                code = 0x003
                        self._del_rom_force = 0             # del sel rom used
                        return (code, length + 1,)

                    if (passe == 1):    # pass 1,2,3
                        if (ll[length][0] == '$'):    # direct offset 0..ff
                            if (self._del_rom_force): # FIXME: would 'auto' be used w/ direct offsets?
                                adr = (self._del_rom_force_rom << 8) + (self._get_address(ll[length]) & 0xff)
                            else:
                                adr = (self._pc & 0xff00) + (self._get_address(ll[length]) & 0xff)  # FIXME: check bank# pc & 0xc00 == addr & 0xc00
                        else:
                            adr = self._find_label(ll[length])
                        if (last):
                            if (adr < 0):
                                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                                raise MyException('Error: Label not found')
                        dist = adr - (self._pc & 0xF00)
                        #print(ll[length], adr, dist)
                        if (dist >= 0 and dist <= 255 and self._del_rom_force == 2):
                            # jsb/goto in same rom with "del sel rom auto"
                            self._del_rom_force = 0  # auto not needed
                        if (last and self._del_rom_force == 0 and (self._pc & 0xFF) == 0xFF):
                            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                            raise MyException('Error: "jsb/go to" not allowed on last word in ROM')
                        if ((dist < 0) or (dist > 255)):  # jsb/goto to another rom?
                            if (self._del_rom_force == 1):
                                if (last):
                                    if ((adr >> 8) != self._del_rom_force_rom):
                                        print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll),
                                              " [ select-rom: %x00 != %x, " % (self._del_rom_force_rom, adr & 0xf00),
                                              "bank=%d" % self._bank, "]")
                                        raise MyException('Error: manual "del sel rom" not on target')
                            else:
                                self._del_rom_emit = 1  # emit 'dly sel bank' before long go-todel_
                                if (self._del_rom_force == 2):          # auto
                                    self._del_rom_force_rom = adr >> 8  # auto set rom target to label dest
                                self._del_rom = (adr >> 8 ) << 6 | 0x034
                                if (last and self._del_rom_force != 2):
                                    # do not emit info for 'del sel rom auto'
                                    print('Info: Auto inserted "del sel rom %d" at 0x%X%03X:' % (adr >> 8, self._bank, self._pc), " ".join(ll))
                            dist = adr & 0x0FF
                        if (found == 3):
                            code = dist << 2 | 0x001
                        else:
                            code = dist << 2 | 0x003
                        self._del_rom_force = 0             # del sel rom used
                        return (code, length + 1,)
        else:
            self._del_rom_force = 0
            code, length = self._find_misc(ll)
            if (code >= 0):
                #print('  len=', length, " line=", " ".join(ll))
                if (code == 0x230):                 # bank switch
                    if (last):
                        if (length >= len(ll)):
                            print('0x%X%03X: ' % (self._bank, self._pc), " ".join(ll))
                            print('Warning: "bank switch" missing label')
                            #raise MyException('Warning: "bank switch" missing label')
                        elif (self._find_label(ll[length]) != (self._pc + 1)):
                            print('0x%X%03X: ' % (self._bank, self._pc), " ".join(ll),
                                  " [ target: 0x%04X != 0x%04X" % (self._find_label(ll[length]), self._pc+1), "]")
                            raise MyException('Error: "bank switch" not on target')
                    length = length + 1
                if ((code & 0x03F) == 0x020):       # sel rom
                    if (last):
                        dest = ((code >> 6) << 8) | (self._pc & 0x0FF) + 1
                        if (length >= len(ll)):
                            print('0x%X%03X: ' % (self._bank, self._pc), " ".join(ll))
                            print('Warning: "sel rom" missing label')
                            #raise MyException('WARNING: "sel rom" missing label')
                        elif (self._find_label(ll[length]) != dest):
                            print('0x%X%03X: ' % (self._bank, self._pc), " ".join(ll),
                                  " [ target: 0x%04X != 0x%04X" % (self._find_label(ll[length]), dest), "]")
                            raise MyException('Error: "sel rom" not on target')
                    # length = length + 1
                if ((code & 0x03F) == 0x034):       # del sel rom
                    self._del_rom_force = 1
                    self._del_rom_force_rom = (code >> 6)
                return (code, length,)
            code, length = self._find_arith(ll)
            if (code >= 0):
                return (code, length,)

            # special directives
            if ll[0] == 'org':                      # org 0xXXX
                org = self._get_address(ll[1])
                if ((self._bank == 0 and (org & 0x1000) != 0) or
                    (self._bank == 1 and (org & 0x1000) != 0x1000)):
                    print('0x%X%03X: ' % (self._bank, (self._pc & 0xfff)), " ".join(ll))
                    raise MyException('Error: org does not match bank')
                org = org & 0xfff
                if (last):
                    if (self._pc > org):
                        print('0x%X%03X: ' % (self._bank, self._pc), " ".join(ll))
                        raise MyException('Error: org base > current pc')
                    if (self._pc < org and not (self._bank == 1 and org == 0x400)):
                        print("Info: Empty words (%d) before org 0x%X, bank=%d" % (org - self._pc, org, self._bank))
                self._pc = org
                return (-1, 2,)

            elif ll[0] == 'bank':                   # bank 0 1
                self._bank = (ll[1] != '0')     
                return (-1, 2,)

            elif ll[0] == 'public':                 # public label
                if (last):
                    # write symbol to publics file (if defined)
                    if (self._pub != None):
                        adr = self._find_label(ll[1])
                        if (adr < 0):
                            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                            raise MyException('Error: Export label not found')
                        else:
                            # NOTE: assume symbol is in the same bank as current PC
                            self._pub.write("#define %s 0x%X%03X\n" % (ll[1], self._bank, adr))
                return (-1, 2,)

            # delayed select rom auto
            elif (ll[0] == 'delayed' and ll[1] == 'select' and
                  ll[2] == 'rom' and ll[3] == 'auto'):
                # let the goto add the "del sel rom" w/o warning
                self._del_rom_force = 2
                self._del_rom_force_rom = 0
                return (-1, 4,)

            else:
                if (last):
                    print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                    raise MyException('Error: Bad opcode')
        return (-1, 0,)

    def _add_label(self, name, address):
        ##print('Adding label=%s 0x%04x' % (name, address))
        if (len(name) == 0):
            return
        if (name[-1] != ':'):   # labels must end with ':'
            print('Label: %s = 0x%04x' % (name, address))
            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
            raise MyException('Error: Bad label, must end with :')
        name = name[:-1]        # strip colon
        if (name[0] != '.'):    # locals starts with '.'
            self._last_global = name
        else:
            name = self._last_global + name
        if name in self._labels.keys():
            print("0x%X%03X: " % (self._bank, self._pc), "%s: [ %s = 0x%04X ]" % (name, name, self._labels[name]))
            raise MyException('Error: label already defined')
        self._labels[name] = address | (self._bank << 12)
    
    def _correct_label(self, name, address):
        if (len(name) == 0):
            return
        if (name[0] == '#' or name[0] == '//'):  # this is a comment, ignore
            return
        name = name[:-1]        # strip colon
        if (name[0] != '.'):
            self._last_global = name
        else:
            name = self._last_global + name
        if name not in self._labels.keys():
            print("0x%X%03X: " % (self._bank, self._pc), 'Label="%s"' % name)
            raise MyException('Error: label not defined')
        if (self._labels[name] != (address | (self._bank << 12))):
            self._delta_labels = 1
            self._labels[name] = address | (self._bank << 12)

    def _find_label(self, name):
        if (name[0] == '.'):
            name = self._last_global + name
        if name in self._labels.keys():
            return self._labels[name] & 0xFFF
        return -1

    def _add_define(self, name, value):
        if name in self._defines.keys():
            print("0x%X%03X: " % (self._bank, self._pc), '#define', name, value)
            raise MyException('Error: #define already defined')
        self._defines[name] = value

    def _find_define(self, name):
        if name in self._defines.keys():
            return self._defines[name]
        else:
            return 0   # 0 if undefined

    def _is_defined(self, name):
        return name in self._defines.keys()

    def _find_number_or_define(self, token):
        if (token.isnumeric()):
            val = int(token, 0)            # it's a number
        else:
            val = self._find_define(token) # else assume it's a define
        return val

    # write header-file data
    def _write_header(self, h, addr, opc):
        if ((addr % 8) == 0):
            h.write("\n  ");
        if ((addr % 1024) == 0):
            h.write("/* 0x%04x */\n  " % addr);
        if (addr == 8191):
            h.write("%05o\n" % opc)
        else:
            h.write("%05o, " % opc)

    # write rom-file data (for x11-calc)
    def _write_rom(self, h, addr, opc):
        h.write("%05o:%05o\n" % (addr, opc))

    # evaluate #if/#elif expressions
    def _eval_expression(self, ll):
        value1 = self._find_number_or_define(ll[1])
        result = False  # assume false
        if (len(ll) == 2 or (len(ll) >= 3 and (ll[2][0] == '#' or ll[2][0:2] == '//'))):
            result = (value1 > 0) # single argument (or single with a comment)
        elif (len(ll) == 3 and ll[2] != '#' and ll[2] != '//'):
            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
            raise MyException('Error: bad #if/#elif')
        elif (len(ll) >= 4):
            value2 = self._find_number_or_define(ll[3])
            if ll[2] == '==':
                result = (value1 == value2)
            elif ll[2] == '!=':
                result = (value1 != value2)
            elif ll[2] == '>':
                result = (value1 > value2)
            elif ll[2] == '>=':
                result = (value1 >= value2)
            elif ll[2] == '<':
                result = (value1 < value2)
            elif ll[2] == '<=':
                result = (value1 <= value2)
            elif ll[2] == '&&':
                result = ((value1 & value2) > 0)
            elif ll[2] == '||':
                result = ((value1 | value2) > 0)
            else:
                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                raise MyException('Error: bad #if/#elif expression')
        return result

    # handle #if, #ifdef, #else, #endif, labels and comments
    # returns: int define (0 or 1), and label (empty if none)
    def _handle_if_else_endif(self, ll):
        if ll[0] == '#define' and self._do_line:
            if (len(ll) < 3):
                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                raise MyException('Error: bad #define')
            self._add_define(ll[1], int(ll[2], 0))   # new define
            return 1, ''

        elif ll[0] == '#if':
            self._cur_define = ll[1]
            self._do_line_stack.insert(0, [self._do_line, self._do_line_skip_elses]) # save curr state
            if self._do_line:      # only evaluate if current state is true
                self._do_line = self._eval_expression(ll)
                self._do_line_skip_elses = self._do_line # skip the following elses if true
            # print(f"{' '.join(ll)}, lvl=", len(self._do_line_stack))
            return 1, ''

        elif (ll[0] == '#ifdef' and self._do_line):
            self._cur_define = ll[1]
            self._do_line_stack.insert(0, [self._do_line, self._do_line_skip_elses]) # save curr state
            if self._do_line:  # only evaluate this if current state is true
                self._do_line = self._is_defined(ll[1])
                self._do_line_skip_elses = self._do_line # skip the following elses if true
            return 1, ''

        elif (ll[0] == '#ifndef' and self._do_line):
            self._cur_define = ll[1]
            self._do_line_stack.insert(0, [self._do_line, self._do_line_skip_elses]) # save curr state
            if self._do_line:  # only evaluate this if current state is true
                self._do_line = not self._is_defined(ll[1])
                self._do_line_skip_elses = self._do_line # skip the following elses if true
            return 1, ''

        elif ll[0] == '#else':
            if (len(self._do_line_stack) == 0):
                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                raise MyException('Error: #else without #if/#ifdef')
            if (not self._do_line_skip_elses and self._do_line_stack[0][0]):
                # don't skip elses -> this one will be active, if previous state is enabled
                self._do_line = True
                self._do_line_skip_elses = True # skip the following elses (should not be any)
            else:
                self._do_line = False
            return 1, ''

        elif ll[0] == '#elif':
            if (len(self._do_line_stack) == 0):
                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                raise MyException('Error: #elif without #if')
            if (not self._do_line_skip_elses and self._do_line_stack[0][0]):
                # don't skip elses -> this one should be evaluated, if previous state is enabled
                self._do_line = self._eval_expression(ll)
                if (self._do_line):
                    self._do_line_skip_elses = True # skip the following elses if true
            else:
                self._do_line = False
            # print(f"{' '.join(ll)}, lvl=", len(self._do_line_stack))
            return 1, ''

        elif ll[0] == '#endif':
            if (len(self._do_line_stack) == 0):
                print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
                raise MyException('Error: #endif without #if/#ifdef')
            self._do_line, self._do_line_skip_elses = self._do_line_stack.pop(0) # restore state
            self._cur_define = ''
            # print("#endif, lvl=", len(self._do_line_stack))
            return 0, ''

        elif ll[0] == '#error' and self._do_line:
            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
            raise MyException('Error: stop at #error')

        elif ll[0][0] == '#' and self._do_line:
            print("0x%X%03X: " % (self._bank, self._pc), " ".join(ll))
            raise MyException('Error: bad directive')

        # no define, then it's a label, or a comment
        label = ''
        if (self._do_line):
            if ((ll[0][0] != '#' and ll[0][0:2] != '//') and ll[0][-1] == ':'): # not a comment and ends with ':'
                label = ll[0]        # then it's a label
                ll.pop(0)            # remove from line
        return 0, label

    # drop optional leading 3 digit hex opcode before the opcode-mnemonic
    def _drop_hex_opcode(self, ll):
        if (len(ll) > 0 and len(ll[0]) == 3 and ll[0][0] >= '0' and ll[0][0] <= '3'):
            ll.pop(0)            # drop the hex opcode
        if (len(ll) > 0 and len(ll[0]) == 3 and ll[0][0] >= '0' and ll[0][0] <= '3'):
            ll.pop(0)            # drop the second hex opcode

    # do the assembly
    def assemble(self, file_in, file_lst, file_pub, file_out0, file_out1, fw_type, display=0, mirror=0):
        self._last_global = ''
        self._pc = 0
        self._bank = 0
        self._ifthen = 0
        self._cy = 0
        self._del_rom = 0
        self._del_rom_emit = 0
        self._delta_labels = 0
        self._del_rom_force = 0
        self._del_sel_force_rom = 0
        self._defines = {}
        self._rom = 8192 * [0]
        self._cur_define = ''
        self._do_line = True
        self._do_line_skip_elses = False
        self._do_line_stack = []  # save stack for _do_line when new #if/#ifdef
        self._pub = None

        f = open(file_in, 'rt')
        lines = f.readlines()
        f.close()

        if (file_pub != ''):
            self._pub = open(file_pub, 'wt')
            self._pub.write(";;; PUBLICS FROM HP67 FW\n")

        define = 0
        
        #
        # pass 0 - parsing labels
        #
        print('pass 0')
        for line in lines:
            ll = line.split()
            ##print('ll=', " ".join(ll)) # for debug
            if (len(ll) > 0):
                label = ''
                if (line[0] > ' '): # first char non empty, this is a #if/endif or a label
                    # handle #define/ifdef/else/endif, comment or label
                    define, label = self._handle_if_else_endif(ll)
                    if (len(label) > 0):
                        self._add_label(label, self._pc) # add the new label
                else:
                    define = 0
                    label = ''
                if (define):
                    pass
                    #print('%X%03X %s' % (self._bank, self._pc, string.join(ll[0:])))
                elif (self._do_line):
                    self._drop_hex_opcode(ll)  # drop opcode before mnemonic (if any)

                    label = label + 20*' '
                    label = label[0:20]
                    code = -1
                    length = len(ll)
                    if (length > 0):
                        code, length = self._find_opcode(ll, 0, 0)
                    if (code < 0):
                        length = len(ll)
                    if (self._del_rom_emit):
                        #print('%X%03X %s %03X %03X    %s' % (self._bank, self._pc, label, self._del_rom, code, string.join(ll[0:length])))
                        self._pc = self._pc + 2
                        self._del_rom_emit = 0
                    elif (code >= 0):
                        #print('%X%03X %s %03X     %s' % (self._bank, self._pc, label, code, string.join(ll[0:length])))
                        self._pc = self._pc + 1
                    else:
                        pass
                        #print('%X%03X %s         %s' % (self._bank, self._pc, label, string.join(ll[0:length])))

        #
        # pass 1 and 2 and ...
        #
        finished = 0
        last = 0
        self._pass = 0
        while(finished == 0):
            self._last_global = ''
            self._pc = 0
            self._bank = 0
            self._ifthen = 0
            self._cy = 0
            self._del_rom = 0
            self._del_rom_emit = 0
            self._delta_labels = 0
            self._del_rom_force = 0
            self._del_sel_force_rom = 0
            self._defines = {}
            self._cur_define = ''
            self._do_line = True
            self._do_line_skip_elses = False

            self._pass = self._pass + 1
            print('pass %d' % self._pass)

            for line in lines:
                ll = line.split()
                label = ''
                com_line = ''
                if (len(ll) == 0):   # keep empty lines in list-file
                    ll = ['#']       # NOTE: comment char does not matter
                if (len(ll) > 0):
                    if (line[0] > ' '):
                        # handle #define/ifdef/else/endif (if any)
                        define, label = self._handle_if_else_endif(ll)
                        if (len(label) > 0):
                            self._correct_label(label, self._pc) # update the address
                    else:
                        define = 0
                        label = ''

                    if (define):
                        if (last):
                            if (display):
                                print('%X%03X %s' % (self._bank, self._pc, " ".join(ll[0:])))
                            h.write('%s' % (line))
                    elif (self._do_line):
                        self._drop_hex_opcode(ll)  # drop opcode before mnemonic (if any)

                        label = label + 20*' '
                        label = label[0:20]
                        code = -1
                        length = len(ll)
                        com = ''
                        if length > 0:
                            if (ll[0][0:1] == '#' or ll[0][0:2] == '//'): # no opcode, just a full-line comment
                                opcode = ''
                                length = 0
                                com_line = line
                            else:
                                code, length = self._find_opcode(ll, 1, last)
                                if (len(ll) > length):
                                    com = " ".join(ll[length:])
                                else:
                                    com = ''
                                if (length > 0):
                                    opcode = " ".join(ll[0:length])
                                    if (len(opcode) < 30):
                                        opcode = opcode + ' '*(30 - len(opcode))
                                    else:
                                        opcode = opcode[:27] + '...'
                                else:
                                    opcode = ''
                        else:
                            opcode = ''
                        if (self._del_rom_emit):  # double op-codes!
                            if (last):
                                self._rom[self._pc | (self._bank << 12)] = self._del_rom
                                self._rom[self._pc + 1 | (self._bank << 12)] = code
                                if (display):
                                    print('%X%03X %s %03X %03X %30s %s' % (self._bank, self._pc, label, self._del_rom, code, opcode, com))
                                h.write('%X%03X %s %03X %03X %30s %s\n' % (self._bank, self._pc, label, self._del_rom, code, opcode, com))
                            self._pc = self._pc + 2
                            self._del_rom_emit = 0
                        elif (code >= 0):
                            if (last):
                                self._rom[self._pc | (self._bank << 12)] = code
                                if (display):
                                    print('%X%03X %s %03X     %s %s' % (self._bank, self._pc, label, code, opcode, com))
                                h.write('%X%03X %s %03X     %s %s\n' % (self._bank, self._pc, label, code, opcode, com))
                            self._pc = self._pc + 1
                        else:
                            if (last):
                                if (opcode == ''):
                                    if (len(com_line) > 0):           # only comment on this line
                                        com_pos = com_line.find('#')
                                        if (com_pos == 0):
                                            com_pos = com_line.find('//')
                                        if (com_pos == 0):
                                            com_line = '     ' + com_line  # offset for whole line comment
                                        elif (com_pos > 24):
                                            com_line = '              ' + com_line # offset for partial line comm
                                        if (display):
                                            print(com_line[0:-1])
                                        h.write('%s' % (com_line))
                                    else:
                                        h.write('%X%03X %s         %s\n' % (self._bank, self._pc, label, com))
                                else:
                                    if (display):
                                        print('%X%03X %s         %s %s' % (self._bank, self._pc, label, opcode, com))
                                    h.write('%X%03X %s         %s %s\n' % (self._bank, self._pc, label, opcode, com))
                        self._pc = self._pc & 0xFFF
            if (self._delta_labels == 0):
                if (last == 0):
                    h = open(file_lst, 'wt')
                    last = 1
                else:
                    finished = 1
        h.close()
        if (self._pub != None):
            self._pub.close()

        m0 = md5()
        m1 = md5()
        
        #
        # write output files bank, rom or header
        #
        file_type = 'wb' if (fw_type == 'b') else 'w'
        f0 = open(file_out0, file_type) if (len(file_out0) > 0) else None
        f1 = open(file_out1, file_type) if (len(file_out1) > 0) else None

        if (fw_type == 'r' or fw_type == 'h'):  # add config comment
            f0.write("/* source defines: %s */\n" % (self._defines))

        if (fw_type == 'h'):
            f0.write("int fw_rom[] = {")

        # bank0 + header
        addr = 0
        for i in range(4096):
            opc = self._rom[i]
            adata = bytes([opc & 0xff, opc >> 8])
            m0.update(adata)
            if (fw_type == 'b'):
                f0.write(adata)
            if (fw_type == 'r'):
                self._write_rom(f0, addr, opc)
            if (fw_type == 'h'):
                self._write_header(f0, addr, opc)
            addr += 1;

        # bank1 + header
        for i in range(4096):
            opc = self._rom[i+4096]
            if (mirror and (i < 1024 or i >= 2048)):
                if (mirror and opc != 0):
                    raise MyException('Error: option mirror is used, but bank1 0x1800-0x1fff is not empty')
                opc = self._rom[i]  # mirror first 1k (1000-13ff) and last 2k (1800-1fff) from bank1
            adata = bytes([opc & 0xff, opc >> 8])
            m1.update(adata)

            if (fw_type == 'b'):
                f1.write(adata)
            if (fw_type == 'r'):
                self._write_rom(f0, addr, opc)
            if (fw_type == 'h'):
                self._write_header(f0, addr, opc)
            addr += 1;

        if (fw_type == 'h'):
             f0.write("};\n")

        if (f0 != None):
            f0.close()
        if (f1 != None):
            f1.close()

        print('MD5 sums:')
        print(' bank1 orig hp67: 8603efa8aadb3a6da3c39be41717be10')
        print('             new:', m0.hexdigest())
        if (mirror):
            print(' bank2 orig hp67: 2464468d155d8989ef0b83c851143450 (mirrored)') # (1000-1400 and 1800-ffff mirrored from bank0)')
        else:
            print(' bank2 orig hp67: 36db1b6fc49cecd88e080c4d01746267') # (1000-1400 and 1800-ffff = 0)')
        print('             new:', m1.hexdigest())
        
topcat = HP67()

parser = argparse.ArgumentParser(description="HP67/97 Woodstock Assembler")
parser.add_argument("input", help='Input file (.asm can be omitted)')
parser.add_argument('--log', action='store_true', help='Output listing during assembly')
parser.add_argument('--fwout', choices=['b', 'r', 'h'], help='Firmware output file type (b: binary bank files, r: x11-calc rom, h: C-header)')
parser.add_argument('--pub', action='store_true', help='Output public file during assembly')
parser.add_argument('--mirror', action='store_true', help='Mirror bank1 1000-13ff and 1800-1fff from bank0')
args = parser.parse_args()

fileBase = args.input
log = 1 if args.log else 0
mirror = 1 if args.mirror else 0

# remove the .src or .asm extension if present
if (fileBase[-4:] == ".src") or (fileBase[-4:] == ".asm"):
    inputFile = fileBase
    fileBase = fileBase[:-4]
else:
    inputFile = fileBase + ".asm"

listFile  = fileBase + '.lst'
fwout_file0=''
fwout_file1=''

if (args.fwout == 'b'):
    fwout_file0 = fileBase + "_fw_bank0.bin"
    fwout_file1 = fileBase + "_fw_bank1.bin"
elif (args.fwout == 'r'):
    fwout_file0 = fileBase + "_fw.rom"
elif (args.fwout =='h'):
    fwout_file0 = fileBase + "_fw.h"

pubFile = ''
if (args.pub):
    pubFile = fileBase + ".pub"

print('Assembling:  ', inputFile)
print('Output Files:', listFile, '', pubFile, '', fwout_file0, '', fwout_file1)

try:
    topcat.assemble(inputFile, listFile, pubFile,
                    fwout_file0, fwout_file1,
                    args.fwout, log, mirror)

except MyException as e:
    print(e)

except FileNotFoundError as e:
    print(e)
