# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Owais Lone hello@owaislone.org
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE


import threading
import imaplib2
import re
import time
from gi.repository import GObject
from email.header import decode_header
from email.utils import parseaddr, parsedate, formatdate
from email.parser import HeaderParser


class Watcher(threading.Thread):
    stop_waiting_event = threading.Event()
    seen_mail = []
    kill_now = False
    IDLE_TIMEOUT = 29  # Mins

    def __init__(self, username, password, labels, last_checked):
        self.username = username
        self.password = password
        self.labels = [L[1] for L in labels if L[0]]
        self.last_checked = last_checked
        self.last_checked_str = time.strftime("%d-%b-%Y",time.localtime(self.last_checked))
        print self.last_checked_str
        threading.Thread.__init__(self)

    def run(self):
        self.imap = imaplib2.IMAP4_SSL("imap.gmail.com")
        try:
            self.imap.login(self.username, self.password)
        except imaplib2.IMAP4_SSL.error:
            self.report_error('Invalid Credentials')
            return
        self.handle_new_mail()
        while not self.kill_now:
            self.wait_for_server()

    def set_callback(self, callback):
        self.callback = callback

    def get_mail_headers(self, id):
        typ, header = self.imap.uid(
            "FETCH",
            id,
            "(BODY.PEEK[HEADER.FIELDS "
            "(subject from date)] X-GM-MSGID X-GM-LABELS X-GM-THRID)"
        )
        results = {}
        parser = HeaderParser()
        header_data = parser.parsestr(header[0][1])
        _from = []
        for item in parseaddr(header_data['from']):
            value, charset = decode_header(item)[0]
            _from.append(value.decode(charset or 'ascii'))
        results['from'] = "%s <%s>" % (_from[0], _from[1])

        _subject = header_data['subject']
        value, charset = decode_header(_subject)[0]
        results['subject'] = value.decode(charset or 'ascii')
        results['date'] = header_data['date']
        results['time'] = time.mktime(parsedate(results['date']))
        match = re.search(
            'X-GM-THRID (?P<THRID>\d+) X-GM-MSGID (?P<MSGID>\d+) X-GM-LABELS \((?P<LABELS>.*)\) UID',
            header[0][0])
        results['msg_id'] = match.groupdict()['MSGID']
        results['thread_id'] = match.groupdict()['THRID']
        labels = match.groupdict()['LABELS']
        labels = re.findall('"([^"]+)"', labels)
        results['system_labels'] = [label.strip('\\\\')
                                    for label
                                    in labels
                                    if label.startswith('\\\\')]
        results['labels'] = [label
                             for label
                             in labels
                             if not label.startswith('\\\\')]
        if 'Starred' in results['system_labels']:
            results['system_labels'].remove('Starred')
            results['starred'] = 'starred'
        else:
            results['starred'] = ''
        return results

    def handle_new_mail(self):
        for label in self.labels:
            self.imap.select(label)
            typ, data = self.imap.uid('SEARCH', None, '(SINCE %s UNSEEN)' % self.last_checked_str)
            new_mail = {}  # thread_id : message
            for uid in data[0].split():
                if not uid in self.seen_mail:
                    self.seen_mail.append(uid)
                    mail_headers = self.get_mail_headers(uid)
                    thread_id = mail_headers['thread_id']
                    mail_list = new_mail.get(thread_id, [])
                    mail_list.append(mail_headers)
                    new_mail[thread_id] = mail_list
            if new_mail:
                GObject.idle_add(self.callback, self.username, label, new_mail)
        self.imap.select("[Gmail]/All Mail")

    def kill(self):
        self.kill_now = True  # to stop while loop in run()
        #self.imap.close()
        #self.imap.logout()
        # to let wait() to return and let execution continue
        self.stop_waiting_event.set()

    def wait_for_server(self):
        print 'waiting'
        self.IDLEArgs = ''
        self.stop_waiting_event.clear()
        self.imap.select("[Gmail]/All Mail")

        def _idle_callback(args):
            self.IDLEArgs = args
            self.stop_waiting_event.set()

        self.imap.idle(
            timeout=60 * self.IDLE_TIMEOUT,
            callback=_idle_callback
        )
        self.stop_waiting_event.wait()
        if not self.kill_now:
            self.handle_new_mail()
        else:
            return


def new_watcher_thread(account, values):
    watcher = Watcher(account,
                      values['password'],
                      values['folders'],
                      values['last_checked'])
    watcher.setDaemon(True)
    return watcher