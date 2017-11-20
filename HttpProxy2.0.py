import socket
import select
import httplib
import sys
import re
import Queue
import thread
from threading import Thread, current_thread

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
MAX_CLIENTS = 5
MAX_RETRY = 3
MAX_BUFFER_LEN = 1024
HTTP_PORT      = 80
HTTP_COMMANDS = ["GET", "POST", "HEAD"]

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
#TODO: make most prints to a file output named "proxy_log.txt, using a seperate thread to log multiple queued requests"
def getRequest(clientSock):
	request = ''
	while True:
		data = clientSock.recv(MAX_BUFFER_LEN)
		request += data
		if len(data) < MAX_BUFFER_LEN:
				break
	return request

def getHeaders(request):
	headers = {}
	parser = re.compile(r'\s*(?P<key>.+\S)\s*:\s+(?P<value>.*\S)\s*')
	headerList = parser.findall(request)
	for key, value in headerList:
		headers[key] = value
	return headers

def parseRequest(request):
	headers = request.split("\n")

	#TODO: Add compatability with more commands or recheck if the current ones are enough
	#Command (for following the flow)
	command =  headers[0].split(" ")[0]
	if not (command in HTTP_COMMANDS):
		return (None, None)

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

def httpRequest(clientSock, clientAddress, clients):
	print "Thread with id %s handles client %s" %(current_thread(), clientAddress)
	request = getRequest(clientSock)
	#print "CLIENT REQUEST %s" %request
	if not request:
		print "Client %s gave no request" %clientAddress
		return False

	server, command = parseRequest(request)
	if command == None:
		print "Request was not of a HTTP type"
		return False

	print "Requested http command %s" %command

	try:
		serverSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	except socket.error, e:
		print "Error creating socket: %s" %e
		print "\nEnding the http request"
		serverSock.close()
		return False

	serverSock.settimeout(5)

	retry = 0
	while True:
		try:
			print "Connecting to server %s port %s" %server	
			serverSock.connect(server)
			break
		except socket.error, e:
			print "Error connecting to server: %s" %e
			if retry != MAX_RETRY:
				retry += 1
				print "Try again, retry no: %d" %retry
				continue
			else:
				print "\nEnding the http request"
				serverSock.close()
				return False

	keep_alive = True

	try:
		print "Sending http request to %s from %s" %(server, clientAddress)
		'''while keep_alive:
			if request == None:
				print "KEPT-ALIVE YAAAAAAAA\n"
				#request = getRequest(clientSock)
				#serverSock.send(request)
			else:
				serverSock.send(request)
			#TODO: check if request is in cache
		'''
		serverSock.send(request)
		
		print "Receiving/Sending server response"
		data = serverSock.recv(MAX_BUFFER_LEN)
		headers = getHeaders(data)
		clientSock.send(data)
		#print "SERVER RESPONSE %s" %data
		while len(data) == MAX_BUFFER_LEN:
			data = serverSock.recv(MAX_BUFFER_LEN)
			clientSock.send(data)

			'''
			if (headers != None) and ("Connection" in headers):
				if headers["Connection"] != "Keep-Alive":
					keep_alive = False
			else:
				keep_alive = False

			request = None
			'''

	except socket.error, e:
		print "Error sending/receiving request: %s" %e

	#TODO: Come back for KEEP-ALIVE connections
	print "Closing connection between %s and %s" %(server, clientAddress)
	clients.remove(clientSock)
	clientSock.close()
	serverSock.close()

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

	clients = []

	#Listening for clients
	proxySock.listen(MAX_CLIENTS)

	while True:
		print "Listening for clients"
		try:
			clientSock, clientAddress = proxySock.accept()
			print "New client from %s" %(clientAddress, )
			clients.append(clientSock) 

			#TODO: new thread to start request
			thread.start_new_thread(httpRequest, (clientSock, clientAddress, clients))
		except KeyboardInterrupt:
			print "\nProxy closing"
			proxySock.close()
			sys.exit(1)

	proxySock.close()
	
server()
#request = "GET http://www.cplusplus.org/ HTTP/1.1\nHost: cplusplus.org\n\n"
#httpRequest(request, ("d", "f"), [])