import socket
import select
import httplib
import sys
import Queue

def coada():
	coada = []
	ceva = Queue()
	print ceva.get_nowait()
	print ceva

	d = {}
	d["c1"] = 1
	d["c2"] = 2
	print d.pop("c1")
	print d.items()
#coada()

#Constants
MAX_BUFFER_LEN = 1024
HTTP_PORT      = 80

def removeSocket(sock, inputs, outputs, queues):
	if sock in outputs:
		outputs.remove(sock)
	inputs.remove(sock)
	sock.close()
	#TODO: try del queues[sock]
	queues.pop(sock)

def httplibTryout():
	request = httplib.HTTPConnection("www.cplusplus.org")
	request.request("GET", "/demo/history.html")
	data = request.getresponse()
	print data.status, data.reason
	data1 = data.read()

#TODO: relative paths
#TODO: a seperate thread for timeout cacheing handling(remove)
#TODO: add multiple http commands handling
#TODO: add cacheing sistem
#TODO: multithreading
#TODO: make most prints to a file output named "proxy_log.txt"
def parseRequest(request):
	headers = request.split("\n")

	#Command (for following the flow)
	command =  headers[0].split(" ")[0]

	#Getting host name
	hostPos = headers[0].find("://")
	if hostPos == -1:
		host = headers[1][6:]
	else:
		host = headers[0][hostPos + 3:].split(" ")[0]

	#Getting port (http default if none given)
	portPos = host.find(":")
	#To check for multiple ":" in URL
	#(the only ":" that can appear until the first "/" is for the port)
	pathPos = host.find("/")
	if (portPos == -1) or (pathPos < portPos):
		port = HTTP_PORT
		host = host[:pathPos]
	else:
		port = int(host[portPos + 1:])
		host = host[:portPos - pathPos - 1]

	return ((host, port), command)

def httpRequest(request, client, queues):
	server, command = parseRequest(request)

	print "Requested http command %s" %command

	try:
		serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except socket.error, e:
		print "Error creating socket: %s" %e
		print "\nEnding the http request"
		serverSock.close()
		return False

	serverSock.settimeout(5)

	try:
		print "Connecting to server %s port %s" %server	
		serverSock.connect(server)
	except socket.error, e:
		print "Error connecting to server: %s" %e
		print "\nEnding the http request"
		serverSock.close()
		return False

	try:
		print "Sending http request to %s from %s" %(server, client.getpeername())
		serverSock.send(request)

		print "Receiving server response"
		while True:
			data = serverSock.recv(MAX_BUFFER_LEN)
			queues[client].put(data)
			if len(data) < MAX_BUFFER_LEN:
				break
		serverSock.close()

	except socket.error, e:
		print "Error sending/receiving request: %s" %e

	return True

def server():
	try:
		proxyPort = int(sys.argv[1])
	except IndexError, e:
		print "Not enough arguments given"
		print "Ussage of proxy: python HttpProxy.py <port>"
		sys.exit(1)

	#A "hackish" way to find my ip address that works on both windows and ubuntu sistems
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.connect(("8.8.8.8", 80))
	proxyIP = s.getsockname()[0] 
	s.close()

	#Creating listening socket
	try:
		proxySock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except socket.error, e:
		print "Error creating socket: %s" %e
		proxySock.close()
		sys.exit(1)

	#Binding listening socket
	try:
		print "Starting up the proxy on %s port %s" %(proxyIP, proxyPort)	
		proxySock.bind((proxyIP, proxyPort))
	except socket.error, e:
		print "Error binding socket: %s" %e
		proxySock.close()
		sys.exit(1)

	inputs = [proxySock]
	outputs = []
	queues = {}

	#Listening for clients
	proxySock.listen(5)

	while inputs:
		try: 
			print "Waitting for next event"
			readable, writable, exceptional = select.select(inputs, outputs, inputs)

			for sock in readable:
				#If proxy gets requests for new client connections
				if sock == proxySock:
					clientSock, clientAddress = sock.accept()
					print "New client from %s" %clientAddress[0]
					clientSock.setblocking(0)
					inputs.append(clientSock)
					queues[clientSock] = Queue.Queue()
				else:
					request = sock.recv(MAX_BUFFER_LEN)
					#If sockets has data to be read
					if request:
						print "Received request from %s" %(sock.getpeername(), )
						status = httpRequest(request, sock, queues)
						if not status:
							print "Failed to establish connection to server"
						elif sock not in outputs:
							outputs.append(sock)

					#A readable socket without data is from a disconnected client
					else:
						print "Client %s has closed its session" %(sock.getpeername(), )
						removeSocket(sock, inputs, outputs, queues)

			for sock in writable:
				try:
					response = queues[sock].get_nowait()
				except Queue.Empty:
					#No responses to be sent
					outputs.remove(sock)
				else:
					#TODO: come back to check if to send all of the queue in one event or multiple events on set of data from queue
					#print "SENDING %s" %response
					sock.send(response)

			#Handling sockets with errors
			for sock in exceptional:
				print "Error on socket from %s" %(sock.getpeername(), )
				removeSocket(sock, inputs, outputs, queues)

		except KeyboardInterrupt:
			print "\nProxy closing"
			proxySock.close()
			sys.exit(1)
	proxySock.close()
	
server()
#request = "GET http://www.cplusplus.org/ HTTP/1.1\nHost: cplusplus.org\n\n"
#httpRequest(request, ("d", "f"), [])