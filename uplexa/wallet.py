from binascii import hexlify, unhexlify
from sha3 import keccak_256
import struct

from . import address
from . import base58
from . import ed25519
from . import prio
from .transaction import Payment, PaymentManager


class Wallet(object):
    """
    uPlexa wallet.

    Provides interface to operate on a wallet.

    Wallet consists of :class:`accounts <uplexa.account.Account>`. In uPlexa 0.11 and earlier the wallet has only a single account
    with index 0. In later versions there might be multiple accounts, but a fresh wallet starts
    with only one.

    The list of accounts will be initialized under the `accounts` attribute.

    The wallet exposes a number of methods that operate on the default account (of index 0).

    :param backend: a wallet backend
    """
    accounts = None

    def __init__(self, backend):
        self._backend = backend
        self.incoming = PaymentManager(0, backend, 'in')
        self.outgoing = PaymentManager(0, backend, 'out')
        self.refresh()

    def refresh(self):
        """
        Reloads the wallet and its accounts. By default, this method is called only once,
        on :class:`Wallet` initialization. When the wallet is accessed by multiple clients or
        exists in multiple instances, calling `refresh()` will be necessary to update
        the list of accounts.
        """
        self.accounts = self.accounts or []
        idx = 0
        for _acc in self._backend.accounts():
            _acc.wallet = self
            try:
                if self.accounts[idx]:
                    continue
            except IndexError:
                pass
            self.accounts.append(_acc)
            idx += 1

    def height(self):
        """
        Returns the height of the wallet.

        :rtype: int
        """
        return self._backend.height()

    def spend_key(self):
        """
        Returns private spend key. None if wallet is view-only.

        :rtype: str or None
        """
        key = self._backend.spend_key()
        if key.strip('0') == '':
            return None
        return key

    def view_key(self):
        """
        Returns private view key.

        :rtype: str
        """
        return self._backend.view_key()

    def seed(self):
        """
        Returns word seed.

        :rtype: str
        """
        return self._backend.seed()

    def new_account(self, label=None):
        """
        Creates new account, appends it to the :class:`Wallet`'s account list and returns it.

        :rtype: :class:`Account`
        """
        acc, addr = self._backend.new_account(label=label)
        assert acc.index == len(self.accounts)
        self.accounts.append(acc)
        return acc

    def confirmations(self, txn_or_pmt):
        """
        Returns the number of confirmations for given
        :class:`Transaction <uplexa.transaction.Transaction>` or
        :class:`Payment <uplexa.transaction.Payment>` object.

        :rtype: int
        """
        if isinstance(txn_or_pmt, Payment):
            txn = txn_or_pmt.transaction
        else:
            txn = txn_or_pmt
        try:
            return max(0, self.height() - txn.height)
        except TypeError:
            return 0

    def export_outputs(self):
        """
        Exports outputs in hexadecimal format.

        :rtype: str
        """
        return self._backend.export_outputs()

    def import_outputs(self, outputs_hex):
        """
        Imports outputs in hexadecimal format. Returns number of imported outputs.

        :rtype: int

        """
        return self._backend.import_outputs(outputs_hex)

    def export_key_images(self):
        """
        Exports signed key images as a list of dicts.

        :rtype: [dict, dict, ...]
        """
        return self._backend.export_key_images()

    def import_key_images(self, key_images_hex):
        """
        Imports key images from a list of dicts. Returns tuple of (height, spent, unspent).

        :rtype: (int, Decimal, Decimal)

        """
        return self._backend.import_key_images(key_images_hex)

    # Following methods operate on default account (index=0)
    def balances(self):
        """
        Returns a tuple of balance and unlocked balance.

        :rtype: (Decimal, Decimal)
        """
        return self.accounts[0].balances()

    def balance(self, unlocked=False):
        """
        Returns specified balance.

        :param unlocked: if `True`, return the unlocked balance, otherwise return total balance
        :rtype: Decimal
        """
        return self.accounts[0].balance(unlocked=unlocked)

    def address(self):
        """
        Returns wallet's master address.

        :rtype: :class:`Address <uplexa.address.Address>`
        """
        return self.accounts[0].addresses()[0]

    def addresses(self):
        """
        Returns all addresses of the default account.

        :rtype: list of :class:`Address <uplexa.address.Address>` and
                :class:`SubAddress <uplexa.address.SubAddress>`
        """
        return self.accounts[0].addresses()

    def new_address(self, label=None):
        """
        Creates a new address in the default account.

        :rtype: :class:`SubAddress <uplexa.address.SubAddress>`
        """
        return self.accounts[0].new_address(label=label)

    def get_address(self, major, minor):
        """
        Calculates sub-address for account index (`major`) and address index within
        the account (`minor`).

        :rtype: :class:`BaseAddress <uplexa.address.BaseAddress>`
        """
        # ensure indexes are within uint32
        if major < 0 or major >= 2**32:
            raise ValueError('major index {} is outside uint32 range'.format(major))
        if minor < 0 or minor >= 2**32:
            raise ValueError('minor index {} is outside uint32 range'.format(minor))
        master_address = self.address()
        if major == minor == 0:
            return master_address
        master_svk = unhexlify(self.view_key())
        master_psk = unhexlify(self.address().spend_key())
        # m = Hs("SubAddr\0" || master_svk || major || minor)
        hsdata = b''.join([
                b'SubAddr\0', master_svk,
                struct.pack('<I', major), struct.pack('<I', minor)])
        m = keccak_256(hsdata).digest()
        # D = master_psk + m * B
        D = ed25519.add_compressed(
                ed25519.decodepoint(master_psk),
                ed25519.scalarmult(ed25519.B, ed25519.decodeint(m)))
        # C = master_svk * D
        C = ed25519.scalarmult(D, ed25519.decodeint(master_svk))
        netbyte = bytearray([
                42 if master_address.is_mainnet() else \
                63 if master_address.is_testnet() else 36])
        data = netbyte + ed25519.encodepoint(D) + ed25519.encodepoint(C)
        checksum = keccak_256(data).digest()[:4]
        return address.SubAddress(base58.encode(hexlify(data + checksum)))

    def transfer(self, address, amount,
            priority=prio.NORMAL, payment_id=None, unlock_time=0,
            relay=True):
        """
        Sends a transfer from the default account. Returns a list of resulting transactions.

        :param address: destination :class:`Address <uplexa.address.Address>` or subtype
        :param amount: amount to send
        :param priority: transaction priority, implies fee. The priority can be a number
                    from 1 to 4 (unimportant, normal, elevated, priority) or a constant
                    from `uplexa.prio`.
        :param payment_id: ID for the payment (must be None if
                        :class:`IntegratedAddress <uplexa.address.IntegratedAddress>`
                        is used as the destination)
        :param unlock_time: the extra unlock delay
        :param relay: if `True`, the wallet will relay the transaction(s) to the network
                        immediately; when `False`, it will only return the transaction(s)
                        so they might be broadcasted later
        :rtype: list of :class:`Transaction <uplexa.transaction.Transaction>`
        """
        return self.accounts[0].transfer(
                address,
                amount,
                priority=priority,
                payment_id=payment_id,
                unlock_time=unlock_time,
                relay=relay)

    def transfer_multiple(self, destinations,
            priority=prio.NORMAL, payment_id=None, unlock_time=0,
            relay=True):
        """
        Sends a batch of transfers from the default account. Returns a list of resulting
        transactions.

        :param destinations: a list of destination and amount pairs: [(address, amount), ...]
        :param priority: transaction priority, implies fee. The priority can be a number
                    from 1 to 4 (unimportant, normal, elevated, priority) or a constant
                    from `uplexa.prio`.
        :param payment_id: ID for the payment (must be None if
                        :class:`IntegratedAddress <uplexa.address.IntegratedAddress>`
                        is used as a destination)
        :param unlock_time: the extra unlock delay
        :param relay: if `True`, the wallet will relay the transaction(s) to the network
                        immediately; when `False`, it will only return the transaction(s)
                        so they might be broadcasted later
        :rtype: list of :class:`Transaction <uplexa.transaction.Transaction>`
        """
        return self.accounts[0].transfer_multiple(
                destinations,
                priority=priority,
                payment_id=payment_id,
                unlock_time=unlock_time,
                relay=relay)
