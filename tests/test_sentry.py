##
## Copyright (c) 2015-2018 Canonical, Ltd.
## 
## Permission is hereby granted, free of charge, to any person obtaining a copy of
## this software and associated documentation files (the "Software"), to deal in
## the Software without restriction, including without limitation the rights to
## use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
## of the Software, and to permit persons to whom the Software is furnished to do
## so, subject to the following conditions:
## 
## The above copyright notice and this permission notice shall be included in all
## copies or substantial portions of the Software.
## 
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
## OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
## SOFTWARE.
##

import os
import logging
import time

import talisker.sentry
import talisker.logs
import talisker.revision

import raven.breadcrumbs
import raven.transport
import raven.base
import raven.handlers.logging
import raven.middleware

from tests import conftest


def test_talisker_client_defaults(monkeypatch, log):
    monkeypatch.setitem(os.environ, 'TALISKER_ENV', 'production')
    monkeypatch.setitem(os.environ, 'TALISKER_UNIT', 'talisker-1')
    monkeypatch.setitem(os.environ, 'TALISKER_DOMAIN', 'example.com')

    client = talisker.sentry.get_client.uncached(
        dsn=conftest.DSN, transport=conftest.DummyTransport)

    assert 'configured raven' in log[-1].msg

    # check client side
    assert (list(sorted(client.processors)) ==
            list(sorted(talisker.sentry.default_processors)))
    # this is unpleasant, but it saves us mocking
    assert raven.breadcrumbs.install_logging_hook.called is False
    assert raven.breadcrumbs._hook_requests.called is False
    assert raven.breadcrumbs._install_httplib.called is False

    # check message
    try:
        raise Exception('test')
    except Exception:
        client.captureException()

    messages = conftest.sentry_messages(client)
    data = messages[0]

    assert data['release'] == talisker.revision.get()
    assert data['environment'] == 'production'
    assert data['server_name'] == 'talisker-1'
    assert data['tags']['site'] == 'example.com'


def test_talisker_client_defaults_none(monkeypatch, log):
    monkeypatch.setitem(os.environ, 'TALISKER_ENV', 'production')
    monkeypatch.setitem(os.environ, 'TALISKER_UNIT', 'talisker-1')
    monkeypatch.setitem(os.environ, 'TALISKER_DOMAIN', 'example.com')

    # raven flask integration passes in all possible kwargs as None
    kwargs = {
        'release': None,
        'hook_libraries': None,
        'site': None,
        'environment': None,
        'name': None,
    }
    client = talisker.sentry.get_client.uncached(
        dsn=conftest.DSN, transport=conftest.DummyTransport, **kwargs)

    # this is unpleasant, but it saves us mocking
    assert raven.breadcrumbs.install_logging_hook.called is False
    assert raven.breadcrumbs._hook_requests.called is False
    assert raven.breadcrumbs._install_httplib.called is False

    # check message
    try:
        raise Exception('test')
    except Exception:
        client.captureException()

    messages = conftest.sentry_messages(client)
    data = messages[0]

    assert data['release'] == talisker.revision.get()
    assert data['environment'] == 'production'
    assert data['server_name'] == 'talisker-1'
    assert data['tags']['site'] == 'example.com'


def test_talisker_client_defaults_explicit_config(monkeypatch, log):
    monkeypatch.setitem(os.environ, 'TALISKER_ENV', 'production')
    monkeypatch.setitem(os.environ, 'TALISKER_UNIT', 'talisker-1')
    monkeypatch.setitem(os.environ, 'TALISKER_DOMAIN', 'example.com')

    # raven flask integration passes in all possible kwargs as None
    kwargs = {
        'release': 'release',
        'hook_libraries': ['requests'],
        'site': 'site',
        'environment': 'environment',
        'name': 'name',
    }
    client = talisker.sentry.get_client.uncached(
        dsn=conftest.DSN, transport=conftest.DummyTransport, **kwargs)

    # this is unpleasant, but it saves us mocking
    assert raven.breadcrumbs.install_logging_hook.called is False
    assert raven.breadcrumbs._hook_requests.called is True
    assert raven.breadcrumbs._install_httplib.called is False

    # check message
    try:
        raise Exception('test')
    except Exception:
        client.captureException()

    messages = conftest.sentry_messages(client)
    data = messages[0]

    assert data['release'] == 'release'
    assert data['environment'] == 'environment'
    assert data['server_name'] == 'name'
    assert data['tags']['site'] == 'site'


def test_log_client(monkeypatch, log):
    dsn = 'http://user:pass@host:8000/app'
    client = talisker.sentry.TaliskerSentryClient(dsn=dsn)
    talisker.sentry.log_client(client, False)
    assert 'pass' not in log[-1]._structured['dsn']
    assert 'from SENTRY_DSN' not in log[-1].msg
    talisker.sentry.log_client(client, True)
    assert 'pass' not in log[-1]._structured['dsn']
    assert 'from SENTRY_DSN' in log[-1].msg


def test_get_middlware():
    mw = talisker.sentry.get_middleware(lambda: None)
    assert isinstance(mw, talisker.sentry.TaliskerSentryMiddleware)
    assert mw.client == talisker.sentry.get_client()
    updates = talisker.sentry.sentry_globals['updates']
    assert len(updates) == 1
    assert updates[0].__closure__[0].cell_contents == mw


def test_middleware_soft_request_timeout(
        monkeypatch, environ, sentry_messages):
    monkeypatch.setitem(os.environ, 'TALISKER_SOFT_REQUEST_TIMEOUT', '0')

    def app(environ, start_response):
        start_response(200, [])
        return []

    mw = talisker.sentry.get_middleware(app)
    body, _, _ = conftest.run_wsgi(mw, environ)
    list(body)
    assert 'Start_response over timeout: 0' == sentry_messages[0]['message']


def test_middleware_soft_request_timeout_non_zero(
        monkeypatch, environ, sentry_messages):
    monkeypatch.setitem(os.environ, 'TALISKER_SOFT_REQUEST_TIMEOUT', '100')

    def app(environ, start_response):
        time.sleep(200 / 1000.0)
        start_response(200, [])
        return []

    mw = talisker.sentry.get_middleware(app)
    body, _, _ = conftest.run_wsgi(mw, environ)
    list(body)
    assert 'Start_response over timeout: 100' == sentry_messages[0]['message']


def test_middleware_soft_request_timeout_disabled_by_default(
        environ, sentry_messages):
    def app(environ, start_response):
        start_response(200, [])
        return []

    mw = talisker.sentry.get_middleware(app)
    body, _, _ = conftest.run_wsgi(mw, environ)
    list(body)
    assert len(sentry_messages) == 0


def test_get_log_handler():
    lh = talisker.sentry.get_log_handler()
    assert isinstance(lh, raven.handlers.logging.SentryHandler)
    assert lh.client == talisker.sentry.get_client()
    updates = talisker.sentry.sentry_globals['updates']
    assert len(updates) == 1
    assert updates[0].__closure__[0].cell_contents == lh


def test_update_client():
    client = talisker.sentry.get_client()
    lh = talisker.sentry.get_log_handler()
    mw = talisker.sentry.get_middleware(lambda: None)
    assert lh.client is client
    assert mw.client is client
    new_client = talisker.sentry.configure_client()
    assert talisker.sentry.get_client() is new_client
    assert lh.client is new_client
    assert mw.client is new_client


def test_logs_ignored():
    client = talisker.sentry.get_client.uncached(
        dsn=conftest.DSN, transport=conftest.DummyTransport)

    client.context.clear()
    # set up a root logger with a formatter
    logging.getLogger('talisker.slowqueries').info('talisker.slowqueries')
    logging.getLogger('talisker.requests').info('talisker.requests')
    logging.getLogger('talisker').info('talisker')
    try:
        raise Exception('test')
    except Exception:
        client.captureException()

    messages = conftest.sentry_messages(client)
    data = messages[0]
    assert len(data['breadcrumbs']) == 1
    crumb = data['breadcrumbs']['values'][0]
    assert crumb['message'] == 'talisker'
    assert crumb['category'] == 'talisker'
