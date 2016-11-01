from twisted.application import internet, service
from twisted.internet import reactor
from twisted.web.static import File
from klein import Klein

app=Klein()

@app.route('/static/', branch=True)
def static(request):
    return File("./static")

@app.route('/')
def home(request):
    return '<html><h1>hi</h1></html>'

from c3next.listenerd import ListenerProtocol
application = service.Application("C3Next")
listener_service = internet.UDPServer(9999, ListenerProtocol())
listener_service.setServiceParent(application)
