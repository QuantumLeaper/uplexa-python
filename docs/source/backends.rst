Backends
========

Backends are the protocols and methods used to communicate with the uPlexa daemon and interact with
the wallet. As of the time of this writing, the only backends available in this library are:

 * ``jsonrpc`` for the HTTP based RPC server,
 * ``offline`` for running the wallet without Internet connection and even without the wallet file.

JSON RPC
----------------

This backend requires a running ``uplexa-wallet-rpc`` process with a uPlexa wallet file opened.
This can be on your local system or a remote node, depending on where the wallet file lives and
where the daemon is running. Refer to the quickstart for general setup information.

The Python `requests`_ library is used in order to facilitate HTTP requests to the JSON RPC
interface. It makes POST requests and passes proper headers, parameters, and payload data as per
the official `Wallet RPC`_ documentation.

.. _`requests`: http://docs.python-requests.org/

.. automodule:: uplexa.backends.jsonrpc
   :members:

Offline
----------------

This backend allows creating a `Wallet` instance without network connection or even without the
wallet itself. In version 0.5 the only practical use is to cold-generate
:doc:`subaddresses <address>` like in the example below:

.. code-block:: python

   In [8]: w = Wallet(OfflineWallet('47ewoP19TN7JEEnFKUJHAYhGxkeTRH82sf36giEp9AcNfDBfkAtRLX7A6rZz18bbNHPNV7ex6WYbMN3aKisFRJZ8Ebsmgef', view_key='6d9056aa2c096bfcd2f272759555e5764ba204dd362604a983fa3e0aafd35901'))

   In [9]: w.get_address(100,37847)
   Out[9]: 883Gcsq65iqh4UL3fJTWLxY45skXyFVNQJZ4bdw4TJcqd8vafvtpX4p6HNmawqFMQ6TwJP7adzyLT1fbU6z1n9dqB9bJrfn

.. automodule:: uplexa.backends.offline
   :members:
