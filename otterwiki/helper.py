#!/usr/bin/env python
# vim: set et ts=8 sts=4 sw=4 ai:

"""
otterwiki.helper

functions used multiple times in the otterwiki that are not as
lightweight as utils.

"""

from otterwiki.server import app, mail, storage, db, Preferences
from otterwiki.gitstorage import StorageError
from flask import flash, url_for
from threading import Thread
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, BadSignature, BadData, SignatureExpired
from otterwiki.util import get_pagename, split_path, join_path


class SerializeError(ValueError):
    pass


# initiliaze serializer
_serializer = URLSafeTimedSerializer(app.config["SECRET_KEY"])


def serialize(str, salt=None):
    return _serializer.dumps(str, salt=salt)


def deserialize(str, salt=None, max_age=86400):
    try:
        return _serializer.loads(str, salt=salt, max_age=max_age)
    except (BadSignature, SignatureExpired) as e:
        raise SerializeError


def toast(message, category=""):
    alert_map = {
        "": "alert-primary",
        "success": "alert-success",
        "warning": "alert-secondary",
        "error": "alert-danger",
        "danger": "alert-danger",
    }
    try:
        halfmoon_category = alert_map[category]
    except KeyError:
        halfmoon_category = alert_map[""]
    return flash(message, halfmoon_category)


def send_async_email(app, msg, raise_on_error=False):
    app.logger.debug("send_async_email()")
    with app.app_context():
        try:
            mail.send(msg)
        except Exception as e:
            app.logger.error("send_async_email(): Exception {}".format(e))
            if raise_on_error:
                raise e


def send_mail(subject, recipients, text_body, sender=None, html_body=None, _async=True, raise_on_error=False):
    """send_mail

    :param subject:
    :param sender:
    :param recipients:
    :param text_body:
    :param html_body:
    """
    if not type(recipients) is list:
        recipients = list(recipients)
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    if not app.config['TESTING'] and _async:
        # send mail asynchronous
        thr = Thread(target=send_async_email, args=[app, msg])
        thr.start()
    else:
        send_async_email(app, msg, raise_on_error)

def health_check():
    # check if storage is readable, the database works and auth is healthy
    msg = []
    # storage check
    try:
        log = storage.log(fail_on_git_error=True)
    except StorageError as e:
        msg += [f"StorageError in {storage.path}"]
    # db check
    try:
        p = Preferences.query.all()
    except:
        msg += [f"DB Error: Unable to query Preferences from DB."]
    if len(msg) == 0:
        return True, ["ok"]
    return False, msg

def auto_url(filename, revision=None):
    # handle attachments and pages
    arr = split_path(filename)
    if filename.endswith(".md"):
        # page
        return (get_pagename(filename, full=True),
                url_for(
                    "view", path=get_pagename(filename, full=True),
                    revision=revision
               ))
    else:
        # attachment
        pagename, attached_filename = get_pagename(join_path(arr[:-1]), full=True), arr[-1]
        return (filename,
                url_for('get_attachment',
                    pagepath=pagename,
                    filename=attached_filename, revision=revision)
               )

