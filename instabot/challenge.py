import email
import imaplib
import re
import random
import os

from loguru import logger as templogger
from instagrapi import Client
from instagrapi.mixins.challenge import ChallengeChoice

CHALLENGE_EMAIL = os.getenv('GMAIL_USER')
CHALLENGE_PASSWORD = os.getenv('GMAIL_PWD')

def get_code_from_email(username, logger=templogger):
    mail = imaplib.IMAP4_SSL('imap.gmail.com')
    mail.login(CHALLENGE_EMAIL, CHALLENGE_PASSWORD)
    mail.select('inbox')
    result, data = mail.search(None, '(UNSEEN)')
    assert result == 'OK', 'Error1 during get_code_from_email: %s' % result
    ids = data.pop().split()
    logger.info(f'emails to parse: {len(ids)}')
    for num in reversed(ids):
        mail.store(num, '+FLAGS', '\\Seen')  # mark as read
        result, data = mail.fetch(num, '(RFC822)')
        assert result == 'OK', 'Error2 during get_code_from_email: %s' % result
        msg = email.message_from_string(data[0][1].decode())
        payloads = msg.get_payload()
        if not isinstance(payloads, list):
            payloads = [msg]
        code = None
        for payload in payloads:
            if payload.get_payload(decode=True):
                try:
                    body = payload.get_payload(decode=True).decode()
                except Exception as e:
                    continue
                if '<div' not in body:
                    continue
                match = re.search('>([^>]*?({u})[^<]*?)<'.format(u=username), body)
                if not match:
                    continue
                logger.info(f'Match from email: {match.group(1)}')
                match = re.search(r'>(\d{6})<', body)
                if not match:
                    logger.info(f'Skip this email, code not found')
                    continue
                code = match.group(1)
                if code:
                    logger.info(f'code found {code}')
                    return code

    return False

