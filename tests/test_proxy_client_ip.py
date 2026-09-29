"""Behind the host nginx, rate limits must key on the real client address.

Without ProxyFix every request's REMOTE_ADDR is the Docker gateway, so all
users share one rate-limit bucket: on 2026-09-29 a login reload loop spent the
shared page limit and every visitor got 429 on every page.
"""

import pytest
from flask_limiter.util import get_remote_address

from vtt import create_app
from vtt.config import Config, ProductionConfig, TestingConfig

DOCKER_GATEWAY = {'REMOTE_ADDR': '172.19.0.1'}


@pytest.fixture
def proxied_client(monkeypatch):
    monkeypatch.setattr(TestingConfig, 'TRUSTED_PROXY_HOPS', 1, raising=False)
    app = create_app('testing')
    # The limiter's key_func (vtt/extensions.py), served through the full WSGI stack.
    app.add_url_rule('/_rate_limit_key', 'rate_limit_key', get_remote_address)
    return app.test_client()


def test_users_behind_the_proxy_get_separate_rate_limit_keys(proxied_client):
    keys = {proxied_client.get('/_rate_limit_key', environ_base=DOCKER_GATEWAY,
                               headers={'X-Forwarded-For': ip}).text
            for ip in ('203.0.113.7', '198.51.100.4')}
    assert keys == {'203.0.113.7', '198.51.100.4'}


def test_client_supplied_forwarded_for_cannot_choose_the_key(proxied_client):
    # nginx appends the real peer ($proxy_add_x_forwarded_for); only that hop is trusted.
    response = proxied_client.get('/_rate_limit_key', environ_base=DOCKER_GATEWAY,
                                  headers={'X-Forwarded-For': '10.0.0.1, 203.0.113.7'})
    assert response.text == '203.0.113.7'


def test_only_production_trusts_a_proxy_by_default():
    assert Config.TRUSTED_PROXY_HOPS == 0
    assert ProductionConfig.TRUSTED_PROXY_HOPS == 1
