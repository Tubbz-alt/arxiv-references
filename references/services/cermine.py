"""Service layer integration for CERMINE."""

import os
import requests
# See http://flask.pocoo.org/docs/0.12/extensiondev/
from flask import _app_ctx_stack as stack
from urllib.parse import urljoin
from .util import get_application_config, get_application_global


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
        response = requests.get(urljoin(self.endpoint, '/cermine/status'))
        if not response.ok:
            raise IOError('CERMINE endpoint not available: %s' %
                          response.content)

    def extract_references(self, filename: str, cleanup: bool=False):
        """
        Extract references from the PDF represented by ``filehandle``.

        Parameters
        ----------
        filename : str

        Returns
        -------
        str
            Raw XML response from Cermine.
        """
        # This can take a while.
        response = requests.post(urljoin(self.endpoint, '/cermine/extract'),
                                 files={'file': open(filename, 'rb')},
                                 timeout=300)
        if not response.ok:
            raise IOError('%s: CERMINE extraction failed: %s' %
                          (filename, response.content))
        return response.content


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


def current_session():
    """Get/create :class:`.MetricsSession` for this context."""
    g = get_application_global()
    if g is None:
        return get_session()
    if 'cermine' not in g:
        g.cermine = get_session()
    return g.cermine


def extract_references(filename: str, cleanup: bool=False) -> dict:
    """
    Extract references from the PDF at ``filename``.

    See :meth:`.CermineSession.extract_references`.
    """
    return current_session().extract_references(filename)
