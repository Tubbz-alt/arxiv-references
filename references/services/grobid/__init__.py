"""Service layer integration for GROBID."""

import os
from functools import wraps
from typing import List
from urllib.parse import urljoin
from urllib3 import Retry
import requests

from arxiv.status import HTTP_200_OK, HTTP_405_METHOD_NOT_ALLOWED
from arxiv.base.globals import get_application_config, get_application_global
from references.domain import Reference

from .parse import format_grobid_output


class GrobidSession(object):
    """Represents a configured session with Grobid."""

    def __init__(self, endpoint: str, path: str) -> None:
        """
        Set up configuration for Grobid, and test the connection.

        Parameters
        ----------
        endpoint : str
        path : str

        Raises
        ------
        IOError
            Raised when unable to contact Grobid with the provided parameters.
        """
        self.endpoint = endpoint
        self.path = path
        self._session = requests.Session()
        self._adapter = requests.adapters.HTTPAdapter(max_retries=2)
        self._session.mount('http://', self._adapter)
        try:
            head = self._session.head(urljoin(self.endpoint, self.path))
        except Exception as e:
            raise IOError('Failed to connect to Grobid at %s: %s' %
                          (self.endpoint, e)) from e

        # Grobid doesn't allow HEAD, but at least a 405 tells us it's running.
        if head.status_code != HTTP_405_METHOD_NOT_ALLOWED:
            raise IOError('Failed to connect to Grobid at %s: %s' %
                          (self.endpoint, head.content))

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
        self._adapter.max_retries = Retry(connect=30, read=10,
                                          backoff_factor=20)
        try:
            _target = urljoin(self.endpoint, self.path)
            response = self._session.post(_target, files={
                'input': open(filename, 'rb')
            })
        except requests.exceptions.ConnectionError as e:
            raise IOError('%s: GROBID extraction failed: %s' % (filename, e))
        if not response.ok:
            raise IOError('%s: GROBID extraction failed: %s' %
                          (filename, response.content))
        return format_grobid_output(response.content)


def init_app(app: object = None) -> None:
    """Set default configuration parameters for an application instance."""
    config = get_application_config(app)
    config.setdefault('GROBID_ENDPOINT', 'http://localhost:8080')
    config.setdefault('GROBID_PATH', 'processFulltextDocument')


def get_session(app: object = None) -> GrobidSession:
    """Get a new Grobid session."""
    config = get_application_config(app)
    endpoint = config.get('GROBID_ENDPOINT', 'http://localhost:8080')
    path = config.get('GROBID_PATH', 'processFulltextDocument')
    return GrobidSession(endpoint, path)


def current_session() -> GrobidSession:
    """Get/create :class:`.GrobidSession` for this context."""
    g = get_application_global()
    if g is None:
        return get_session()
    if 'grobid' not in g:
        g.grobid = get_session()
    session: GrobidSession = g.grobid
    return session


@wraps(GrobidSession.extract_references)
def extract_references(filename: str) -> List[Reference]:
    """
    Extract references from the PDF at ``filename``.

    See :meth:`.GrobidSession.extract_references`.
    """
    return current_session().extract_references(filename)
