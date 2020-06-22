"""
    DNS Authenticator for Hurricane Electric.
"""
import re
import logging

import six
import requests
from bs4 import BeautifulSoup

import zope.interface

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common

logger = logging.getLogger(__name__)


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    description = ('Obtain certificates using a DNS TXT record (if you are using Hurricane Electric for DNS).')
    ttl = 120

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None
        self.dns_api = None

    @classmethod
    def add_parser_arguments(cls, add):
        super(Authenticator, cls).add_parser_arguments(add)
        add('credentials', help='Hurricane Electric credentials INI file.')

    def more_info(self):
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'Hurricane Electric.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'Hurricane Electric credentials INI file',
            {
                'user': 'username of the Hurricane Electric account',
                'pass': 'account password'
            }
        )

    def _login(self):
        if self.dns_api is None:
            self.dns_api = HEDNSAPI(self.credentials.conf('user'), self.credentials.conf('pass'))

        return self.dns_api.login()

    def _perform(self, domain, validation_name, validation):
        logged_in = self._login()
        if not logged_in:
            raise errors.PluginError('Unable to authenticate to HE DNS')

        # Fetch all domains and find the target by name
        all_domains = self.dns_api.get_domains()
        #Added while loop to match he.net hosted domains
        #without the hostname or subdomain for the cert
        partial_domain = domain.lower()
        domain_parts_left = domain.count('.')

        while domain_parts_left >= 1 :
          target_domain = next((x for x in all_domains if x.name.lower() == partial_domain), None)
          if target_domain:
            break
          partial_domain = partial_domain.split('.',1)[1]
          domain_parts_left = partial_domain.count('.')

        if not target_domain:
            raise errors.PluginError('Unable to find domain: {0}'.format(domain))

        # Fetch all records and check if the record already exists
        all_records = self.dns_api.get_domain_records(target_domain)
        for record in all_records:
            if record.type == 'TXT' and record.name.lower() == validation_name.lower() and record.value == validation:
                logger.warning('[DNS-HE] Record %r already exists', record)
                return

        # Insert a record
        new_record = HERecord(validation_name, 'TXT', validation, ttl=300)
        try:
            logger.info('[DNS-HE] Putting record %r', new_record)
            self.dns_api.put_record(target_domain, new_record)
        except Exception as e:
            raise errors.PluginError('Unable to create TXT: {0}'.format(e))


    def _cleanup(self, domain, validation_name, validation):

        logged_in = self._login()
        if not logged_in:
            raise errors.PluginError('Unable to authenticate to HE DNS')

        # Fetch all domains and find the target by name
        all_domains = self.dns_api.get_domains()
        #Added while loop to match he.net hosted domains 
        #without the hostname or subdomain for the cert
        partial_domain = domain.lower()
        domain_parts_left = domain.count('.')

        while domain_parts_left >= 1 :
          target_domain = next((x for x in all_domains if x.name.lower() == partial_domain), None)
          if target_domain:
            break
          partial_domain = partial_domain.split('.',1)[1]
          domain_parts_left = partial_domain.count('.')

        if not target_domain:
            raise errors.PluginError('Unable to find domain: {0}'.format(domain))

        # Fetch all records and delete the matching one
        all_records = self.dns_api.get_domain_records(target_domain)
        for record in all_records:
            if record.type == 'TXT' and record.name.lower() == validation_name.lower() and record.value == validation:
                logger.info('[DNS-HE] Deleting record %r', record)
                self.dns_api.delete_record(target_domain, record)
                break


# So-and-so API client for HE itself

class HEDNSAPI(object):
    BASE = 'https://dns.he.net/'

    def __init__(self, user, password):
        self.user = user
        self.password = password

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.99 Safari/537.36',
            'Referer' : 'https://dns.he.net/'
        })

        self.logged_in = False

    def login(self):
        if not self.logged_in:
            # Get a session cookie first
            r = self.session.get(self.BASE)

            data = {
                # HE calls it email, but only accepts the username
                'email' : self.user,
                'pass'  : self.password
            }
            s, r = self.request_soup(data=data)

            error_div = s.select_one('#dns_err')
            self.logged_in = not bool(error_div)

        return self.logged_in

    def _request(self, endpoint='', params={}, data={}):
        if data:
            r = self.session.post(self.BASE + endpoint, params=params, data=data)
        else:
            r = self.session.get(self.BASE + endpoint, params=params)
        return r

    def request_soup(self, *args, **kwargs):
        r = self._request(*args, **kwargs)
        return BeautifulSoup(r.text, 'lxml'), r


    def get_domains(self):
        ''' Get all domains associated with the account '''
        if not self.logged_in:
            raise Exception('Not logged in')

        s, r = self.request_soup()

        domain_table = s.select_one('#domains_table tbody')
        domain_rows = domain_table.select('tr')

        domains = []
        for domain_row in domain_rows:
            domain_name = domain_row.select_one('span').text
            edit_icon   = domain_row.select_one('img[alt="edit"]')
            domain_id   = int(re.search(r'hosted_dns_zoneid=(\d+)', edit_icon.attrs['onclick']).group(1))
            domains.append(HEDomain(domain_id, domain_name))

        return domains


    def get_domain_records(self, domain):
        ''' Get all records associated with the given domain '''
        if not self.logged_in:
            raise Exception('Not logged in')

        params = {
            'hosted_dns_zoneid' : domain.id,
            'menu' : 'edit_zone',
            'hosted_dns_editzone' : '1'
        }
        s, r = self.request_soup(params=params)

        records = self._parse_records(s)

        return records

    def _parse_records(self, soup):
        rows = soup.select('#dns_main_content table tr.dns_tr')

        records = []
        for row in rows:
            children = list(c for c in row.children if not isinstance(c, six.text_type))

            record_id = int(row.attrs['id'])

            record_name     = children[2].text
            record_type     = children[3].contents[0].text.upper()
            record_ttl      = int(children[4].text)
            record_priority = children[5].text
            record_value    = children[6].attrs['data']

            if record_type == 'TXT':
                # Strip outermost quotes from TXT value
                record_value = record_value[1:-1]

            record_priority = None if record_priority == '-' else int(record_priority)

            record = HERecord(
                id=record_id,
                name=record_name,
                type=record_type,
                value=record_value,
                ttl=record_ttl,
                priority=record_priority,
            )
            records.append(record)
        return records


    def delete_record(self, domain, domain_record):
        ''' Deletes the given record from the given domain '''
        if not self.logged_in:
            raise Exception('Not logged in')

        data = {
            'menu' : 'edit_zone',
            'hosted_dns_editzone'   : 1,
            'hosted_dns_delrecord'  : 1,

            'hosted_dns_delconfirm' : 'delete',
            'hosted_dns_zoneid'     : domain.id,
            'hosted_dns_recordid'   : domain_record.id,
        }
        s, r = self.request_soup(data=data)

        error_div = s.select_one('#dns_err')
        if error_div:
            raise Exception('Delete failed: ' + error_div.text)


    def put_record(self, domain, domain_record):
        ''' Inserts the given record into the given domain '''
        if not self.logged_in:
            raise Exception('Not logged in')

        data = {
            'menu' : 'edit_zone',
            'hosted_dns_editrecord' : 'Submit',
            'hosted_dns_editzone'   : 1,
            'hosted_dns_zoneid'     : domain.id,

            'Name'     : domain_record.name,
            'Type'     : domain_record.type.upper(),
            'Content'  : domain_record.value,
            'Priority' : domain_record.priority or '',
            'TTL'      : domain_record.ttl
        }

        if domain_record.id:
            # In case of an existing domain, Update
            data['hosted_dns_editrecord'] = 'Update'
            data['hosted_dns_recordid']   = domain_record.id

        s, r = self.request_soup(data=data)

        error_div = s.select_one('#dns_err')
        if error_div:
            raise Exception('Put failed: ' + error_div.text)

        records = self._parse_records(s)
        return records


class HEDomain(object):
    def __init__(self, domain_id, domain_name):
        self.id   = domain_id
        self.name = domain_name

    def __repr__(self):
        return '<{}:{} {}>'.format(type(self).__name__, self.id, self.name)

class HERecord(object):
    def __init__(self, name, type, value, ttl=86400, priority=None, id=None):
        self.id    = id
        self.name  = name
        self.type  = type
        self.value = value
        self.ttl   = ttl
        self.priority = priority

    def __repr__(self):
        return '<{}:{} [{}] {} {} TTL:{}>'.format(
            type(self).__name__,
            self.id, self.type, self.name, self.value, self.ttl
        )
