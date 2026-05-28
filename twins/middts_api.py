from urllib.parse import urlencode

import requests
from django.conf import settings


_access_token = None


def _api_base_url():
    base = settings.MIDDTS_API_URL.rstrip('/')
    if base.endswith('/api'):
        return base
    return f"{base}/api"


def _token_url():
    return f"{_api_base_url()}/core/token/"


def _extract_access_token(payload):
    """Return the first supported token field from the auth payload."""
    if not isinstance(payload, dict):
        return None
    for key in ('access', 'access_token', 'token'):
        token_value = payload.get(key)
        if isinstance(token_value, str) and token_value.strip():
            return token_value.strip()
    return None


def _build_auth_headers():
    global _access_token

    configured_token = getattr(settings, 'MIDDTS_API_TOKEN', '').strip()
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
        try:
            payload = response.json()
        except ValueError as exc:
            raise requests.HTTPError(
                f"Token endpoint returned non-JSON response at {_token_url()}",
                response=response,
            ) from exc

        token = _extract_access_token(payload)
        if not token:
            detail = payload.get('detail') or payload.get('error') or str(payload)
            raise requests.HTTPError(
                f"Token endpoint response has no access token field: {detail}",
                response=response,
            )

        _access_token = token

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