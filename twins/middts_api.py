from urllib.parse import urlencode

import requests
from django.conf import settings


_access_token = None


def _token_url():
    return f"{settings.MIDDTS_API_URL.rstrip('/')}/core/token/"


def _build_auth_headers():
    global _access_token

    configured_token = getattr(settings, 'MIDDTS_API_TOKEN', '')
    if configured_token:
        return {'Authorization': f'Bearer {configured_token}'}

    if not _access_token:
        query = urlencode(
            {
                'username': settings.MIDDTS_API_USERNAME,
                'password': settings.MIDDTS_API_PASSWORD,
            }
        )
        response = requests.post(
            f"{_token_url()}?{query}",
            timeout=settings.MIDDTS_API_TIMEOUT,
        )
        response.raise_for_status()
        _access_token = response.json()['access']

    return {'Authorization': f'Bearer {_access_token}'}


def request(method, url, retry_on_401=True, **kwargs):
    global _access_token

    headers = dict(kwargs.pop('headers', {}) or {})
    headers.update(_build_auth_headers())
    response = requests.request(
        method,
        url,
        headers=headers,
        timeout=kwargs.pop('timeout', settings.MIDDTS_API_TIMEOUT),
        **kwargs,
    )
    if response.status_code == 401 and retry_on_401 and not getattr(settings, 'MIDDTS_API_TOKEN', ''):
        _access_token = None
        return request(method, url, retry_on_401=False, headers=headers, **kwargs)
    return response


def get(url, **kwargs):
    return request('GET', url, **kwargs)


def post(url, **kwargs):
    return request('POST', url, **kwargs)


def put(url, **kwargs):
    return request('PUT', url, **kwargs)


def delete(url, **kwargs):
    return request('DELETE', url, **kwargs)