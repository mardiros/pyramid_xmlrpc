import xmlrpclib
import webob

from pyramid.settings import asbool


def xmlrpc_marshal(data, allow_none=False, encoding=None):
    """ Marshal a Python data structure into an XML document suitable
    for use as an XML-RPC response and return the document.  If
    ``data`` is an ``xmlrpclib.Fault`` instance, it will be marshalled
    into a suitable XML-RPC fault response."""
    if isinstance(data, xmlrpclib.Fault):
        return xmlrpclib.dumps(data, allow_none=allow_none, encoding=encoding)
    else:
        return xmlrpclib.dumps((data,), methodresponse=True,
                               allow_none=allow_none,
                               encoding=encoding)


def xmlrpc_response(data, allow_none=False, encoding=None):
    """ Marshal a Python data structure into a webob ``Response``
    object with a body that is an XML document suitable for use as an
    XML-RPC response with a content-type of ``text/xml`` and return
    the response."""
    xml = xmlrpc_marshal(data, allow_none=allow_none, encoding=encoding)
    response = webob.Response(xml)
    response.content_type = 'text/xml'
    response.content_length = len(xml)
    return response


def parse_xmlrpc_request(request, use_datetime=False):
    """ Deserialize the body of a request from an XML-RPC request
    document into a set of params and return a two-tuple.  The first
    element in the tuple is the method params as a sequence, the
    second element in the tuple is the method name."""
    if request.content_length > (1 << 23):
        # protect from DOS (> 8MB body)
        raise ValueError('Body too large (%s bytes)' % request.content_length)
    params, method = xmlrpclib.loads(request.body, use_datetime)
    return params, method


def xmlrpc_view(wrapped):
    """ This decorator turns functions which accept params and return Python
    structures into functions suitable for use as Pyramid views that speak
    XML-RPC.  The decorated function must accept a ``context`` argument and
    zero or more positional arguments (conventionally named ``*params``).

    E.g.::

      from pyramid_xmlrpc import xmlrpc_view

      @xmlrpc_view
      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    Equates to::

      from pyramid_xmlrpc import parse_xmlrpc_request
      from pyramid_xmlrpc import xmlrpc_response

      def say_view(context, request):
          params, method = parse_xmlrpc_request(request)
          return say(context, *params)

      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    Note that if you use :class:`~pyramid.view.view_config`, you must
    decorate your view function in the following order for it to be
    recognized by the convention machinery as a view::

      from pyramid.view import view_config
      from pyramid_xmlrpc import xmlrpc_view

      @view_config(name='say')
      @xmlrpc_view
      def say(context, what):
          if what == 'hello'
              return {'say':'Hello!'}
          else:
              return {'say':'Goodbye!'}

    In other words do *not* decorate it in :func:`~pyramid_xmlrpc.xmlrpc_view`,
    then :class:`~pyramid.view.view_config`; it won't work.
    """

    def _curried(context, request):
        params, method = parse_xmlrpc_request(request)
        value = wrapped(context, *params)
        return xmlrpc_response(value)
    _curried.__name__ = wrapped.__name__
    _curried.__grok_module__ = wrapped.__module__

    return _curried


class XMLRPCView:
    """A base class for a view that serves multiple methods by XML-RPC.

    Subclass and add your methods as described in the documentation.
    """
    allow_none = False
    charset = None
    use_datetime = False

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        """
        This method de-serializes the XML-RPC request and
        dispatches the resulting method call to the correct
        method on the :class:`~pyramid_xmlrpc.XMLRPCView`
        subclass instance.

        .. warning::
          Do not override this method in any subclass if you
          want XML-RPC to continute to work!

        """
        params, method = parse_xmlrpc_request(self.request, self.use_datetime)
        return xmlrpc_response(getattr(self, method)(*params), self.allow_none,
                               self.charset)


def includeme(config):
    settings = config.registry.settings
    XMLRPCView.allow_none = asbool(settings.get('xmlrpc.allow_none', False))
    XMLRPCView.use_datetime = asbool(settings.get('xmlrpc.use_datetime',
                                                  False))
    XMLRPCView.charset = settings.get('xmlrpc.charset')
