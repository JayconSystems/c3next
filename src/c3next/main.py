from twisted.application import internet, service
from c3next.listenerd import ListenerProtocol, DataPersistanceService
from c3next.web import WebService

application = service.Application("C3Next")

listener_service = internet.UDPServer(9999, ListenerProtocol())
listener_service.setServiceParent(application)

db_persistance_service = DataPersistanceService(5)
db_persistance_service.setServiceParent(application)

web_service = WebService("tcp:8000")
web_service.setServiceParent(application)
