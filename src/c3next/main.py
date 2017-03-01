from twisted.application import internet, service
from twisted.internet import protocol
from c3next.listenerd import ListenerProtocol, DataPersistanceService
from c3next.web import WebService

application = service.Application("C3Next")

f = protocol.ServerFactory()
f.protocol = ListenerProtocol
listener_service = internet.TCPServer(9999, f)
listener_service.setServiceParent(application)

db_persistance_service = DataPersistanceService(5)
db_persistance_service.setServiceParent(application)

web_service = WebService("tcp:8000")
web_service.setServiceParent(application)
