import socket
import time
import rsa # sudo pip install rsa


def sendVote(ip,port,username,voterAddress,token):
	try:
		sock = socket.create_connection((ip, port),timeout=4)

		def read_line(source):
			line = ""
			while True:
				c = source.recv(1)
				if c.decode("utf-8") == '\n':
					break
				line += c.decode("utf-8")
			return line

		read_line(sock)
	except:
		return (False,"Unable to connect to Votifier. Check the ip & port entered is correct.")

	data = "VOTE\n%s\n%s\n%s\n%s\n" % ("mcserver-lists", username, voterAddress, int(time.time()))

	public_key_encoded = token

	header = "-----BEGIN PUBLIC KEY-----\n"
	footer = "\n-----END PUBLIC KEY-----"

	if not public_key_encoded[0] == '-':
		public_key_encoded = header + public_key_encoded
	if not public_key_encoded[-1] == '-':
		public_key_encoded += footer
	
	try:
		public_key = rsa.PublicKey.load_pkcs1_openssl_pem(bytes(public_key_encoded, encoding='utf8'))

		encrypted = rsa.encrypt(bytes(data, encoding='utf8'), public_key)
	except:
		return(False,"Invalid Votifier key, check it is correct and contains no spaces.")

	try:
		sock.sendall(encrypted)

		remaining = 256 - len(encrypted)
		while remaining > 0:
			remaining -= sock.send(chr(0))
	except:
		sock.close()
		return (False,"Unable to connect to Votifier. Check the ip & port entered is correct.")
	sock.close()
	return(True,"Successfully sent test vote to server.")