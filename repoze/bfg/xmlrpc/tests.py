import unittest
from repoze.bfg import testing

class TestXMLRPCMarshal(unittest.TestCase):
    def _callFUT(self, value):
        from repoze.bfg.xmlrpc import xmlrpc_marshal
        return xmlrpc_marshal(value)
        
    def test_xmlrpc_marshal_normal(self):
        data = 1
        marshalled = self._callFUT(data)
        import xmlrpclib
        self.assertEqual(marshalled, xmlrpclib.dumps((data,),
                                                     methodresponse=True))

    def test_xmlrpc_marshal_fault(self):
        import xmlrpclib
        fault = xmlrpclib.Fault(1, 'foo')
        data = self._callFUT(fault)
        self.assertEqual(data, xmlrpclib.dumps(fault))

class TestXMLRPResponse(unittest.TestCase):
    def _callFUT(self, value):
        from repoze.bfg.xmlrpc import xmlrpc_response
        return xmlrpc_response(value)
        
    def test_xmlrpc_response(self):
        import xmlrpclib
        data = 1
        response = self._callFUT(data)
        self.assertEqual(response.content_type, 'text/xml')
        self.assertEqual(response.body, xmlrpclib.dumps((1,),
                                                        methodresponse=True))
        self.assertEqual(response.content_length, len(response.body))
        self.assertEqual(response.status, '200 OK')
        
class TestParseXMLRPCRequest(unittest.TestCase):
    def _callFUT(self, request):
        from repoze.bfg.xmlrpc import parse_xmlrpc_request
        return parse_xmlrpc_request(request)

    def test_normal(self):
        import xmlrpclib
        param = 1
        packet = xmlrpclib.dumps((param,), methodname='__call__')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)
        params, method = self._callFUT(request)
        self.assertEqual(params[0], param)
        self.assertEqual(method, '__call__')

    def test_toobig(self):
        request = testing.DummyRequest()
        request.content_length = 1 << 24
        self.assertRaises(ValueError, self._callFUT, request)

class TestXMLRPCView(unittest.TestCase):
    def _callFUT(self, unwrapped):
        from repoze.bfg.xmlrpc import xmlrpc_view
        return xmlrpc_view(unwrapped)

    def test_normal(self):
        def unwrapped(context, what):
            return what
        wrapped = self._callFUT(unwrapped)
        self.assertEqual(wrapped.__name__, 'unwrapped')
        self.assertEqual(wrapped.__grok_module__, unwrapped.__module__)
        context = testing.DummyModel()
        request = testing.DummyRequest()
        param = 'what'
        import xmlrpclib
        packet = xmlrpclib.dumps((param,), methodname='__call__')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)
        response = wrapped(context, request)
        self.assertEqual(response.body, xmlrpclib.dumps((param,),
                                                       methodresponse=True))
