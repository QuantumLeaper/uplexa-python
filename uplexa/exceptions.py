class uPlexaException(Exception):
    pass

class BackendException(uPlexaException):
    pass

class NoDaemonConnection(BackendException):
    pass

class AccountException(uPlexaException):
    pass

class WrongAddress(AccountException):
    pass

class WrongPaymentId(AccountException):
    pass

class NotEnoughMoney(AccountException):
    pass

class NotEnoughUnlockedMoney(NotEnoughMoney):
    pass

class AmountIsZero(AccountException):
    pass

class TransactionNotPossible(AccountException):
    pass

class TransactionBroadcastError(BackendException):
    def __init__(self, message, details=None):
        self.details = details
        super(TransactionBroadcastError, self).__init__(message)

class TransactionNotFound(AccountException):
    pass

class SignatureCheckFailed(uPlexaException):
    pass

class WalletIsNotDeterministic(uPlexaException):
    pass
