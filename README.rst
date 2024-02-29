cerbot-dns-he
======================================

`Hurricane Electric DNS <https://dns.he.net>`_ Authenticator plugin for `Certbot <https://certbot.eff.org>`_

----

Installation
------------

Install `cerbot-dns-he <https://pypi.org/project/certbot-dns-hurricane-electric/>`_ to your Certbot's environment with pip. For example, the line below works for me after running ``certbot-auto``.

.. code-block:: bash

  $ sudo /opt/eff.org/certbot/venv/bin/pip install cerbot-dns-hurricane-electric

You can also use ``git+https://github.com/studioeng/certbot-dns-hurricane-electric.git`` or clone the repository and install from the directory, but pip is recommended.

Example usage
-------------

Create a configuration file with your username and password:

.. code-block:: ini

  certbot_dns_hurricane_electric:dns_he_user = Your HE username
  certbot_dns_hurricane_electric:dns_he_pass = Your HE password

and chmod it to ``600``:

.. code-block:: bash

  $ chmod 600 dns_he.ini

Then request a certificate with something like:

.. code-block:: bash

  $ certbot-auto certonly \
    -a certbot-dns-he:dns-he --certbot-dns-he:dns-he-propagation-seconds 30 \
    --certbot-dns-he:dns-he-credentials /home/me/dns_he.ini -d 'mydomain.com,*.mydomain.com' \
    --server https://acme-v02.api.letsencrypt.org/directory --agree-tos \
    --manual-public-ip-logging-ok --preferred-challenges dns -m me@email.com

You're done!

| ``--certbot-dns-he:dns-he-propagation-seconds`` controls the duration waited for the DNS record(s) to propagate.
| ``--certbot-dns-he:dns-he-credentials`` specifies the configuration file path.

These are stored in cerbot's renewal configuration, so they'll work on your automatic renewals.

Credits
-------

The original plugin by @tsaarist has been unchanged for a number of years.
