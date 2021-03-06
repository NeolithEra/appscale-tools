""" Represents an Admin API UrlMap resource. """

import re

from appscale.tools.custom_exceptions import AppEngineConfigException

DELTA_REGEX = r'([0-9]+)([DdHhMm]|[sS]?)'

EXPIRATION_RE = r'^\s*({})(\s+{})*\s*$'.format(DELTA_REGEX, DELTA_REGEX)


class Handler(object):
  """ Represents an Admin API UrlMap resource. """
  API_FIELDS = {
    'secure': 'securityLevel',
    'login': 'login',
    'auth_fail_action': 'authFailAction',
    'redirect_http_response_code': 'redirectHttpResponseCode'
  }

  API_VALUES = {
    'securityLevel': {'optional': 'SECURE_OPTIONAL',
                      'never': 'SECURE_NEVER',
                      'always': 'SECURE_ALWAYS'},
    'login': {'optional': 'LOGIN_OPTIONAL',
              'required': 'LOGIN_REQUIRED',
              'admin': 'LOGIN_ADMIN'},
    'authFailAction': {'redirect': 'AUTH_FAIL_ACTION_REDIRECT',
                       'unauthorized': 'AUTH_FAIL_ACTION_UNAUTHORIZED'},
    'redirectHttpResponseCode': {301: 'REDIRECT_HTTP_RESPONSE_CODE_301',
                                 302: 'REDIRECT_HTTP_RESPONSE_CODE_302',
                                 303: 'REDIRECT_HTTP_RESPONSE_CODE_303',
                                 307: 'REDIRECT_HTTP_RESPONSE_CODE_307'}
  }

  FIELD_RULES = {
    'application_readable': lambda val: isinstance(val, bool),
    'auth_fail_action': lambda val: val in ('redirect', 'unauthorized'),
    'expiration': re.compile(EXPIRATION_RE).match,
    'http_headers': lambda val: isinstance(val, dict),
    'login': lambda val: val in ('optional', 'required', 'admin'),
    'mime_type': lambda val: isinstance(val, str),
    'redirect_http_response_code': lambda val: val in (301, 302, 303, 307),
    'script': lambda val: isinstance(val, str),
    'secure': lambda val: val in ('optional', 'never', 'always'),
    'static_dir': lambda val: isinstance(val, str),
    'static_files': lambda val: isinstance(val, str),
    'upload': lambda val: isinstance(val, str),
    'url': lambda val: isinstance(val, str),
  }

  STATIC_API_FIELDS = {
    'upload': 'uploadPathRegex',
    'http_headers': 'httpHeaders',
    'mime_type': 'mimeType',
    'expiration': 'expiration',
    'application_readable': 'applicationReadable'
  }

  def __init__(self, url):
    """ Creates a new Handler.

    Args:
      url: A string specifying a URL regex pattern.
    """
    self.url = url

    self.application_readable = None
    self.auth_fail_action = None
    self.expiration = None
    self.http_headers = None
    self.login = None
    self.mime_type = None
    self.redirect_http_response_code = None
    self.script = None
    self.secure = None
    self.static_dir = None
    self.static_files = None
    self.upload = None

  @property
  def static_defined(self):
    return self.static_dir is not None or self.static_files is not None

  @classmethod
  def from_yaml(cls, yaml_entry):
    """ Creates a Handler from a parsed section from app.yaml.

    Args:
      yaml_entry: A dictionary generated by a parsed handler section.
    Returns:
      A Handler object.
    """
    try:
      url = yaml_entry['url']
    except KeyError:
      raise AppEngineConfigException(
        'Missing url from handler: {}'.format(yaml_entry))

    handler = Handler(url)

    for field in yaml_entry:
      if field not in cls.FIELD_RULES:
        raise AppEngineConfigException(
          'Unrecognized handler field: {}'.format(field))

    for field, rule in cls.FIELD_RULES.items():
      value = yaml_entry.get(field)
      if value is not None:
        if not rule(value):
          raise AppEngineConfigException(
            'Invalid {} value: {}'.format(field, value))

        setattr(handler, field, value)

    if handler.script is not None and handler.static_defined:
      raise AppEngineConfigException(
        'Handler cannot contain both script and static elements')

    if handler.script is None and not handler.static_defined:
      raise AppEngineConfigException(
        'Handler must contain either script or static element')

    if handler.static_defined:
      if handler.static_dir is not None and handler.static_files is not None:
        raise AppEngineConfigException(
          'Handler cannot contain both static_dir and static_files')

    return handler

  def to_api_dict(self):
    """ Generates a representation that can be passed to the Admin API.

    Returns:
      A dictionary containing the handler details.
    """
    handler = {'urlRegex': self.url}
    for attr, api_field in self.API_FIELDS.items():
      value = getattr(self, attr)
      if value is not None:
        handler[api_field] = self.API_VALUES[api_field][value]

    if self.static_defined:
      if self.static_dir:
        static_section = {
          'path': self.static_dir,
          'uploadPathRegex': '{}/.*'.format(self.static_dir),
        }
      else:
        static_section = {'path': self.static_files}

      for attr, api_field in self.STATIC_API_FIELDS.items():
        value = getattr(self, attr)
        if value is not None:
          static_section[api_field] = value

      handler['staticFiles'] = static_section
    else:
      handler['script'] = {'scriptPath': self.script}

    return handler
