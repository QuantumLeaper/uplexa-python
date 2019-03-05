#!/usr/bin/env python

# Electrum - lightweight Bitcoin client
# Copyright (C) 2011 thomasv@gitorious
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction,
# including without limitation the rights to use, copy, modify, merge,
# publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so,
# subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
# BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Note about US patent no 5892470: Here each word does not represent a given digit.
# Instead, the digit represented by a word is variable, it depends on the previous word.
#
# Copied 17 February 2018 from uPlexaPy, originally from Electrum:
#     https://github.com/bigreddmachine/uPlexaPy/blob/master/uplexapy/mnemonic.py ch: 80cc16c39b16c55a8d052fbf7fae68644f7a5f02
#     https://github.com/spesmilo/electrum/blob/master/lib/old_mnemonic.py ch:9a0aa9b4783ea03ea13c6d668e080e0cdf261c5b
#
# Significantly modified on 26 May 2018 by Michal Salaban:
#   + support for 12/13-word seeds
#   + simplified interface, changed exceptions (assertions -> explicit raise)
#   + optimization

from uplexa import wordlists
from uplexa import ed25519
from uplexa import base58
from uplexa.address import address
from binascii import hexlify, unhexlify
from os import urandom
from sha3 import keccak_256

class Seed(object):
    """Creates a seed object either from local system randomness or an imported phrase.

    :rtype: :class:`Seed <uplexa.seed.Seed>`
    """

    def __init__(self, phrase_or_hex="", wordlist="English"):
        """If user supplied a seed string to the class, break it down and determine
        if it's hexadecimal or mnemonic word string. Gather the values and store them.
        If no seed is passed, automatically generate a new one from local system randomness.

        :rtype: :class:`Seed <uplexa.seed.Seed>`
        """
        self.phrase = "" #13 or 25 word mnemonic word string
        self.hex = "" # hexadecimal

        self.word_list = wordlists.get_wordlist(wordlist)

        self._ed_pub_spend_key = None
        self._ed_pub_view_key = None

        if phrase_or_hex:
            seed_split = phrase_or_hex.split(" ")
            if len(seed_split) >= 24:
                # standard mnemonic
                self.phrase = phrase_or_hex
                if len(seed_split) == 25:
                    # with checksum
                    self._validate_checksum()
                self._decode_seed()
            elif len(seed_split) >= 12:
                # myuplexa mnemonic
                self.phrase = phrase_or_hex
                if len(seed_split) == 13:
                    # with checksum
                    self._validate_checksum()
                self._decode_seed()
            elif len(seed_split) == 1:
                # single string, probably hex, but confirm
                if not len(phrase_or_hex) % 8 == 0:
                    raise ValueError("Not valid hexadecimal: {hex}".format(hex=phrase_or_hex))
                self.hex = phrase_or_hex
                self._encode_seed()
            else:
                raise ValueError("Not valid mnemonic phrase or hex: {arg}".format(arg=phrase_or_hex))
        else:
            self.hex = generate_hex()
            self._encode_seed()

    def is_myuplexa(self):
        """Returns True if the seed is MyuPlexa-style (12/13-word)."""
        return len(self.hex) == 32

    def _encode_seed(self):
        """Convert hexadecimal string to mnemonic word representation with checksum.
        """
        self.phrase = self.word_list.encode(self.hex)

    def _decode_seed(self):
        """Calculate hexadecimal representation of the phrase.
        """
        self.hex = self.word_list.decode(self.phrase)

    def _validate_checksum(self):
        """Given a mnemonic word string, confirm seed checksum (last word) matches the computed checksum.

        :rtype: bool
        """
        phrase = self.phrase.split(" ")
        if self.word_list.get_checksum(self.phrase) == phrase[-1]:
            return True
        raise ValueError("Invalid checksum")

    def sc_reduce(self, input):
        integer = ed25519.decodeint(input)
        modulo = integer % ed25519.l
        return hexlify(ed25519.encodeint(modulo)).decode()

    def hex_seed(self):
        return self.hex

    def _hex_seed_keccak(self):
        h = keccak_256()
        h.update(unhexlify(self.hex))
        return h.digest()

    def secret_spend_key(self):
        a = self._hex_seed_keccak() if self.is_myuplexa() else unhexlify(self.hex)
        return self.sc_reduce(a)

    def secret_view_key(self):
        b = self._hex_seed_keccak() if self.is_myuplexa() else unhexlify(self.secret_spend_key())
        h = keccak_256()
        h.update(b)
        return self.sc_reduce(h.digest())

    def public_spend_key(self):
        if self._ed_pub_spend_key:
            return self._ed_pub_spend_key
        self._ed_pub_spend_key = ed25519.public_from_secret_hex(self.secret_spend_key())
        return self._ed_pub_spend_key

    def public_view_key(self):
        if self._ed_pub_view_key:
            return self._ed_pub_view_key
        self._ed_pub_view_key = ed25519.public_from_secret_hex(self.secret_view_key())
        return self._ed_pub_view_key

    def public_address(self, net='mainnet'):
        """Returns the master :class:`Address <uplexa.address.Address>` represented by the seed.

        :param net: the network, one of 'mainnet', 'testnet', 'stagenet'. Default is 'mainnet'.

        :rtype: :class:`Address <uplexa.address.Address>`
        """
        if net not in ('mainnet', 'testnet', 'stagenet'):
            raise ValueError(
                "Invalid net argument. Must be one of ('mainnet', 'testnet', 'stagenet').")
        netbyte = 18 if net == 'mainnet' else 53 if net == 'testnet' else 24
        data = "{:x}{:s}{:s}".format(netbyte, self.public_spend_key(), self.public_view_key())
        h = keccak_256()
        h.update(unhexlify(data))
        checksum = h.hexdigest()
        return address(base58.encode(data + checksum[0:8]))


def generate_hex(n_bytes=32):
    """Generate a secure and random hexadecimal string. 32 bytes by default, but arguments can override.

    :rtype: str
    """
    h = hexlify(urandom(n_bytes))
    return "".join(h.decode("utf-8"))
