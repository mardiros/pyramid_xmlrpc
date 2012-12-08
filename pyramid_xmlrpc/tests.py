# -*- coding: utf-8 -*-
import unittest
from pyramid import testing


class TestXMLRPCMarshal(unittest.TestCase):

    def _callFUT(self, value):
        from pyramid_xmlrpc import xmlrpc_marshal
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

    def _callFUT(self, value, allow_none=False, charset=None):
        from pyramid_xmlrpc import xmlrpc_response
        return xmlrpc_response(value, allow_none, charset)

    def test_xmlrpc_response(self):
        import xmlrpclib
        data = 1
        response = self._callFUT(data)
        self.assertEqual(response.content_type, 'text/xml')
        self.assertEqual(response.body, xmlrpclib.dumps((1,),
                                                        methodresponse=True))
        self.assertEqual(response.content_length, len(response.body))
        self.assertEqual(response.status, '200 OK')

    def test_xmlrpc_response_nil(self):
        import xmlrpclib
        data = None
        self.assertRaises(TypeError, self._callFUT, data)
        response = self._callFUT(data, allow_none=True).body
        self.assertIsNone(xmlrpclib.loads(response)[0][0])

    def test_xmlrpc_response_charset(self):
        import xmlrpclib
        data = u"é"
        self.assertRaises(UnicodeEncodeError, self._callFUT, data, False,
                          "us-ascii")
        response = self._callFUT(data, charset="iso-8859-1").body
        self.assertEqual(response.split('>', 1)[0],
                         "<?xml version='1.0' encoding='iso-8859-1'?")


class TestParseXMLRPCRequest(unittest.TestCase):

    def _callFUT(self, request, use_datetime=0):
        from pyramid_xmlrpc import parse_xmlrpc_request
        return parse_xmlrpc_request(request, use_datetime)

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

    def test_datetime(self):
        import datetime
        import xmlrpclib
        from pyramid_xmlrpc import parse_xmlrpc_request
        param = datetime.datetime.now()
        packet = xmlrpclib.dumps((param,), methodname='__call__')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)
        params, method = self._callFUT(request)
        self.assertEqual(params[0].__class__, xmlrpclib.DateTime)
        params, method = self._callFUT(request, use_datetime=True)
        self.assertEqual(params[0].__class__, datetime.datetime)


class TestDecorator(unittest.TestCase):

    def _callFUT(self, unwrapped):
        from pyramid_xmlrpc import xmlrpc_view
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


class TestBaseClass(unittest.TestCase):

    def test_normal(self):

        from pyramid_xmlrpc import XMLRPCView

        class Test(XMLRPCView):
            def a_method(self, param):
                return param

        # set up a request
        param = 'what'
        import xmlrpclib
        packet = xmlrpclib.dumps((param,), methodname='a_method')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)

        # instantiate the view
        context = testing.DummyModel()
        instance = Test(context, request)

        # these are fair game for the methods to use if they want
        self.failUnless(instance.context is context)
        self.failUnless(instance.request is request)

        # exercise it
        response = instance()
        self.assertEqual(response.body, xmlrpclib.dumps((param,),
                                                        methodresponse=True))

    def test_marshalling_none(self):
        from pyramid_xmlrpc import XMLRPCView

        class Test(XMLRPCView):
            allow_none = True

            def a_method(self, param):
                return None

        import xmlrpclib
        packet = xmlrpclib.dumps((None,), methodname='a_method',
                                 allow_none=True)
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)

        # instantiate the view
        context = testing.DummyModel()
        instance = Test(context, request)
        # exercise it
        response = instance()
        self.assertEqual(response.body, xmlrpclib.dumps((None,),
                                                        allow_none=True,
                                                        methodresponse=True))

    def test_parse_datetime(self):
        from pyramid_xmlrpc import XMLRPCView

        class Test(XMLRPCView):
            use_datetime = True

            def a_method(self, param):
                Test.datetime = param
                return param

        import xmlrpclib
        import datetime
        packet = xmlrpclib.dumps((datetime.datetime.now(),),
                                 methodname='a_method')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)

        # instantiate the view
        context = testing.DummyModel()
        instance = Test(context, request)
        # exercise it
        response = instance()
        self.assertEqual(Test.datetime.__class__, datetime.datetime)

    def test_charset(self):
        from pyramid_xmlrpc import XMLRPCView

        class Test(XMLRPCView):
            charset = 'iso-8859-1'

            def a_method(self, param):
                return param

        import xmlrpclib
        packet = xmlrpclib.dumps(('param',), methodname='a_method')
        request = testing.DummyRequest()
        request.body = packet
        request.content_length = len(packet)

        # instantiate the view
        context = testing.DummyModel()
        instance = Test(context, request)
        # exercise it
        response = instance()
        self.assertEqual(response.body.split('>', 1)[0],
                         "<?xml version='1.0' encoding='iso-8859-1'?")


class TestConfig(unittest.TestCase):

    def test_includeme(self):
        from pyramid_xmlrpc import includeme, XMLRPCView

        settings = {'xmlrpc.charset': 'iso-8859-15',
                    'xmlrpc.allow_none': 'true'}
        self.config = testing.setUp(settings=settings)
        self.config.include(includeme)
        self.assertEqual(XMLRPCView.charset, 'iso-8859-15')
        self.assertTrue(XMLRPCView.allow_none)
