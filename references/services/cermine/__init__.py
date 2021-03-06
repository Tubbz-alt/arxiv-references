"""Service layer integration for CERMINE."""

import os
from urllib.parse import urljoin
from urllib3 import Retry
from typing import List

import requests
from flask import _app_ctx_stack as stack

from arxiv.base.globals import get_application_config, get_application_global
from references.domain import Reference

from .parse import cxml_to_json


class ExtractionError(Exception):
    """Encountered an unexpected state during extraction."""

    pass


class CermineSession(object):
    """Represents a configured Cermine session."""

    def __init__(self, endpoint: str) -> None:
        """
        Set the Cermine endpoint.

        Parameters
        ----------
        endpoint : str
        """
        self.endpoint = endpoint
        self._session = requests.Session()
        self._adapter = requests.adapters.HTTPAdapter(max_retries=2)
        self._session.mount('http://', self._adapter)
        response = self._session.get(urljoin(self.endpoint, '/cermine/status'))
        if not response.ok:
            raise IOError('CERMINE endpoint not available: %s' %
                          response.content)

    def extract_references(self, filename: str) -> List[Reference]:
        """
        Extract references from the PDF represented by ``filehandle``.

        Parameters
        ----------
        filename : str

        Returns
        -------
        list
            Items are :class:`.Reference` instances.
        """
        # This can take a while.
        self._adapter.max_retries = Retry(connect=30, read=10,
                                          backoff_factor=20)
        _target = urljoin(self.endpoint, '/cermine/extract')
        try:
            response = self._session.post(_target,
                                          files={'file': open(filename, 'rb')})
        except requests.exceptions.ConnectionError as e:
            raise IOError('%s: CERMINE extraction failed: %s' % (filename, e))
        if not response.ok:
            raise IOError('%s: CERMINE extraction failed: %s' %
                          (filename, response.content))
        return cxml_to_json(response.content)


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('REFLINK_CERMINE_DOCKER_IMAGE', 'arxiv/cermine')


def get_session(app: object = None) -> CermineSession:
    """Get a new Cermine session."""
    endpoint = get_application_config(app).get('CERMINE_ENDPOINT')
    if not endpoint:
        raise RuntimeError('Cermine endpoint is not set.')
    return CermineSession(endpoint)


def current_session() -> CermineSession:
    """Get/create :class:`.CermineSession` for this context."""
    g = get_application_global()
    if g is None:
        return get_session()
    if 'cermine' not in g:
        g.cermine = get_session()
    session: CermineSession = g.cermine
    return session


def extract_references(filename: str) -> List[Reference]:
    """
    Extract references from the PDF at ``filename``.

    See :meth:`.CermineSession.extract_references`.
    """
    return current_session().extract_references(filename)
