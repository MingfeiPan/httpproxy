# -*- coding:utf-8 -*- 
# @author mingfei


import socket
import logging
import sys
import os
import threading

backlog = 50
bufsize = 8192
threads = []
threads_lock = threading.Lock()
threads_local = threading.local()

def proxy_thread(conn, addr):
	buf = conn.recv(bufsize)
	lines = buf.split('\r\n'.encode('utf-8'))
	url = lines[0].split(' '.encode('utf-8'))[1]
	# host = lines[1].split(' '.encode('utf-8'))[1]

	logging.info('http request %s, %s' %(url.decode('utf-8'), addr[0]))

	s = socket.socket()
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

	#consider https
	http_part = url.find('://'.encode('utf-8'))
	if http_part == -1:
		path = url
	else:
		path = url[(http_part+3):]

	port_part = path.find(':'.encode('utf-8'))
	web_part = path.find('/'.encode('utf-8'))

	if web_part == -1:
		web_part = len(path)

	if port_part == -1 or web_part < port_part:
		port = 80
		host = path[:web_part]
	else:
		port = int(path[port_part+1:])
		host = path[:port_part]

	logging.info('host is %s' % host)
	logging.info('port is %s' % str(port))
	s = socket.socket()
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)		
	s.connect((host, port))
	s.send(buf)		
	try:
		while True:
			recvbuf = s.recv(bufsize)
			if len(recvbuf) > 0:
				logging.info(recvbuf)
				conn.send(recvbuf)
			else:
				break

		s.close()
		conn.close()
	except:
		s.close()
		conn.close()
		logging.info('peer reset %s, %s' %(url, addr[0]))
	return

def do_thread(handler, conn, addr):
	def do_t():
		try:
			handler(conn, addr)
		finally:
			with threads_lock: threads.remove(t)
			logging.info('the thread end')

	t = threading.Thread(target=do_t)
	with threads_lock: threads.append(t)
	t.start()
	logging.info('start new thread')
	return t


def main():
	logging.basicConfig(level=logging.INFO)
	if len(sys.argv) < 2:
		logging.info('proxy with default port: 8080...')
		port = 8080
	else:
		port = int(sys.argv[1])


	s = socket.socket()
	s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	s.bind(('',port))
	s.listen(backlog)

	while True:
		try:
			conn, addr = s.accept()
		except socket.error as err:
			if err.errno == errno.EINTR:
				continue
			raise
		do_thread(proxy_thread, conn, addr)

	while threads:
		threads[0].join()				

if __name__ == '__main__':
	main()