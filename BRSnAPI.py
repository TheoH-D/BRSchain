import os
import json
import jwt
import hashlib
import socket
import datetime
import time
import requests
# =============================================================================
# this has everything for creating the block
# =============================================================================
class Blockchain:
    def __init__(self):
        self.direct = os.path.join(os.getcwd(), 'BRSchain', 'brsChain')
        print('initiated')
    def getPreviousBlock(self):
        Path = os.path.join(self.direct, 'length.txt')
        with open(Path, "r") as f:
            chainLen = int(f.read())
            print(chainLen)
        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%chainLen)
        with open(Path, "r") as f:
            prevFile = json.load(f)
            prevBlock = prevFile["block"]
        return prevBlock
    def createBlock(self, previousBlock, blockInfo, requestID):
#        partners = []
        previousHash = self.Hash(previousBlock)
        Path = os.path.join(self.direct, 'timestamp.txt')
        with open(Path, "r") as f:
            timestamp = f.read()
#        block = {"index": previousBlock["index"]+1,
#                 "company name": compName,
#                 "company type": compType,
#                 "UBI": busID,
#                 "share value": shareVal,
#                 "debentures": debentures,
#                 "partners": partners,
#                 "timestamp": timestamp,
#                 "previous hash": previousHash}
        blockInfo['index'] = previousBlock['index']+1
        blockInfo['timestamp'] = timestamp
        blockInfo['previous hash'] = previousHash
        blockInfo['requestID'] = requestID
        print(blockInfo)
        return blockInfo
    def Hash(self, block):
        encodedBlock = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encodedBlock).hexdigest()
    def writeBlock(self, block):
        fileItems = {"block":block}
        number = block["index"]
        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%number)
        with open(Path, "w+") as f:
            json.dump(fileItems, f)
        Path = os.path.join(self.direct, 'length.txt')
        with open(Path, "w") as f:
            f.write(str(number))
# =============================================================================
# if the node wants to connect to another node
# =============================================================================
class client:
    def __init__(self):
        self.direct = os.path.join(os.getcwd(), 'BRSchain', 'brsChain')
        #reputation of respective nodes to see which have the least issues
        Path = os.path.join(self.direct, 'nodes.json')
        with open(Path, "r") as f:
            nodes = json.load(f)
        self.API = nodes["API"]
        self.node1 = (nodes["node_1"]["address"], nodes["node_1"]["port"])
        self.node2 = (nodes["node_2"]["address"], nodes["node_2"]["port"])
        print(self.node1, self.node2)
        self.rep1 = nodes["node_1"]["reputation"]
        self.rep2 = nodes["node_2"]["reputation"]
    def send_protocol(self, sock, data):
        message = {'data': data}
        jwt_replace = jwt.encode(message, '34_kibo_lane', algorithm ='HS256')
        msgLen = len(jwt_replace)
        lenSqrd = len(str(msgLen))
        if lenSqrd < 2:
            msgLen = '000%d'%msgLen
        elif lenSqrd < 3:
            msgLen = '00%d'%msgLen
        elif lenSqrd < 4:
            msgLen = '0%d'%msgLen
        else:
            msgLen = str(msgLen)
        print(msgLen)
        sock.send(msgLen.encode())
        sock.send(jwt_replace)
    def recv_protocol(self, sock):
        recvLen = sock.recv(4)
        token = sock.recv(int(recvLen))
        message = jwt.decode(token, '34_kibo_lane', algorithm='HS256')
        return message['data']
    def start(self):
        print('i am the client')
        self.s1 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result1 = self.s1.connect_ex(self.node1)
        print(result1)
        result2 = self.s2.connect_ex(self.node2)
        print(result2)
        if result1 != 0:
            print('server aint here')
            self.send_protocol(sock = self.s2, data = {'command': 'node_down'})
            self.s2.close()
            return self.node1
        elif result2 != 0:
            print('server aint here')
            self.send_protocol(sock = self.s1, data = {'command': 'node_down'})
            self.s1.close()
            return self.node2
#        self.s1.connect(node1)
#        self.s2.connect(node2)
        self.isChainValid()
    def isChainValid(self):
        Path = os.path.join(self.direct, 'length.txt')
        with open(Path, "r") as f:
            chainLen = int(f.read())
        Path = os.path.join(self.direct, 'blocks', 'block0.json')
        with open(Path, "r") as f:
            fileBlock  = json.load(f)
            previousBlock = fileBlock["block"]
        blockIndex=1
        endProcess = False
        if chainLen > 0:
            while blockIndex <= chainLen:
                print("iteration %d"%blockIndex)
                Path = os.path.join(self.direct, 'blocks', 'block%d.json'%blockIndex)
                with open(Path, "r") as f:
                    fileBlock = json.load(f)
                    block = fileBlock["block"]
                print(block["previous hash"])
                if block["previous hash"] != self.Hash(previousBlock): 
                #checking chain of hashes is consistant
                    endProcess = True
                    blockIndex -=1
                    self.replaceChain(blockIndex, chainLen)
                    break
                blockIndex += 1
                print(blockIndex)
                previousBlock = block
        if endProcess == False:
            print('requesting length')
            self.send_protocol(sock = self.s1, data = {'command': 'length'})
            print('recieving length 1')
            node1Len = str(self.recv_protocol(sock = self.s1))
            self.send_protocol(sock = self.s2, data = {'command': 'length'})
            print('recieving length 2')
            node2Len = str(self.recv_protocol(sock = self.s2))
            lengths = {'me': chainLen, '1': int(node1Len), '2': int(node2Len)}
            print(lengths)
            print('comparing lengths')
            if chainLen == int(node1Len) == int(node2Len):
                persist = self.checkSimilar(chainLen)
                if persist == True:
                    self.send_protocol(sock = self.s1, data = {'command': 'end'})
                    self.send_protocol(sock = self.s2, data = {'command': 'end'})
                    timestamp = str(datetime.datetime.now())
                    self.send_protocol(sock = self.s1, data = {'time': timestamp})
                    self.s1.close()
                    self.send_protocol(sock = self.s2, data = {'time': timestamp})
                    self.s2.close()
                    Path = os.path.join(self.direct, 'nodes.json')
                    with open(Path, "r") as f:
                        nodes = json.load(f)
                        nodes["node_1"]["reputation"] = self.rep1
                        nodes["node_2"]["reputation"] = self.rep2
                    with open(Path, "w") as f:
                        json.dump(nodes, f)
            else:
                nlist = ['me', 'node1', 'node2']
                alist = [chainLen, int(node1Len), int(node2Len)]
                for passnum in range(len(alist)-1,0,-1):
                    for i in range(passnum):
                        print(alist)
                        if alist[i]>alist[i+1]:
                            temp = alist[i]
                            tempb = nlist[i]
                            alist[i] = alist[i+1]
                            nlist[i] = nlist[i+1]
                            alist[i+1] = temp
                            nlist[i+1] = tempb
                persist = self.checkSimilar(alist[0])
                if persist == True:
                    if nlist[2] == 'me':
                        self.send_protocol(sock = self.s1, data = {'command': 'length_check'})
                        self.send_protocol(sock = self.s2, data = {'command': 'length_check'})
                        self.checkLength(lengths, nodeChosen='me')
                    elif nlist[2] == 'node1':
                        self.send_protocol(sock = self.s1, data = {'command': 'length_check'})
                        self.send_protocol(sock = self.s2, data = {'command': 'end'})
                        self.checkLength(lengths, nodeChosen='1')
                    else:
                        self.send_protocol(sock = self.s2, data = {'command': 'length_check'})
                        self.send_protocol(sock = self.s1, data = {'command': 'end'})
                        self.checkLength(lengths, nodeChosen='2')
    def Hash(self, block):#function for creating hashes
        encodedBlock = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(encodedBlock).hexdigest()
    def replaceChain(self, falseIndex, chainLen):#replaces the chain from where the hashes are inconsistant
        #falseIndex is the starting point for the inconsitancy, blocks are sent from that point onwards
        repeat = chainLen - int(falseIndex) + 1
        print('replace chain function')
        if self.rep1>=self.rep2:#chooses to adopt the chain of the node with the highest reputation
            nodeChoice = self.s1
            self.send_protocol(sock = self.s2, data = {'command': 'end'})
        else:
            nodeChoice = self.s2
            self.send_protocol(sock = self.s1, data = {'command': 'end'})
        self.send_protocol(sock = nodeChoice, data = {'command': 'replace_chain'})
        print('sending length and false index')
        self.send_protocol(sock = nodeChoice, data = {'length': chainLen, 'index': falseIndex})
        print('recieving blocks')
        for i  in range(repeat):#checked
            blockNum = int(falseIndex) + int(i)
            fileData = self.recv_protocol(sock = nodeChoice)
            Path = os.path.join(self.direct, 'blocks', 'block%d.json'%blockNum)
            with open(Path, "wb") as f:
                f.write(fileData)
        print('sending timestamp')
        timestamp = str(datetime.datetime.now())
        self.send_protocol(sock = self.s1, data = {'time': timestamp})
        self.send_protocol(sock = self.s2, data = {'time': timestamp})
        self.s1.close()
        self.s2.close()
    def isBlockValid(self, block, length):
    #        password = "98_ngong_road_%d"%length
        response = requests.get('http://%s/bc/length'%self.API, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
        api_data = response.json()
        api_length = api_data['data']#check this
        response = requests.get('http://{}/bc/request/{}'.format(API, block['requestID']), auth=('the_tharrisondrum', '?HCrf=7%EnAa'))#check this, is it the payload ID or the other one
        data = response.json()
        if response.status_code == 204:
            return False
        if api_length == length:
#        if length == 73:
            if data['data']['node_count'] > 0:
                return True
            else:
                print('INVALID BLOCK!!!! DIFFERENCE')
                return False
        else:
            print('INVALID BLOCK!!!! LENGTH')
            return False      
#        api = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#        api_jwt = api.recv(512)
#        try:
#            api_message = jwt.decode(api_jwt, password, algorithm='HS256')
#            time_api = api_message['%d'%block["index"]]['time']
#            timeDiff = (time_api - block["timestamp"]).total_seconds
#            if timeDiff < 5: #5 seconds checkthis
#                return True
#            else:
#                return False
#        except:
#            return False
        #json web tokens validates incoming data but doesnt help if someone writes directly to the node
    def checkSimilar(self, chainLen):
        #gets the last hash from both nodes
        #the last hash would be completely different if anything in the chain was different
        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%int(chainLen))
        with open(Path) as f:
            data = json.load(f)
            thisHash = data["block"]["previous hash"]
        self.send_protocol(sock = self.s1, data = {'length': chainLen})
        hashCheck1 = self.recv_protocol(sock = self.s1)
        self.send_protocol(sock = self.s2, data = {'length': chainLen})
        hashCheck2 = self.recv_protocol(sock = self.s2)
        print(thisHash)
        print(hashCheck1)
        print(hashCheck2)
        if thisHash != hashCheck1 and thisHash != hashCheck2 and hashCheck1 != hashCheck2:
            #all the nodes disagree so we just have to take the highest rep chain
            print('its gone to shit')
            self.checkSimilarWhole(chainLen)
            return False
        elif thisHash == hashCheck1 and thisHash != hashCheck2:
            #minority chain is considered the wrong chain
            print('node 2 is wrong')
            self.rep2 -= 50
            return True
        elif thisHash == hashCheck2 and thisHash != hashCheck1:
            #function is not called since the nodes should replace themselves once they do this check
            print('node 1 is wrong')
            self.rep1 -= 50
            return True
        elif thisHash != hashCheck1 and thisHash != hashCheck2 and hashCheck1 == hashCheck2:
            print('this node is wrong')
            self.checkSimilarWhole(chainLen)
            return False
        else:
            print('hash verification good')
            self.rep1 += 1
            self.rep2 += 1
            return True
    def checkSimilarWhole(self, chainLen):#sequentially checks blocks with the highest rep node
        if self.rep1 >= self.rep2:
           nodeChoice = self.s1
        else:
            nodeChoice = self.s2
        self.send_protocol(sock = nodeChoice, data = {'command': 'check_whole'})
        print('sent check whole')
        self.send_protocol(sock = nodeChoice, data = {'length': chainLen})
        print('sent length')
        if chainLen == "0":
            repeat = 1
        else:
            repeat = chainLen
        for i in range(repeat):#checked
            checkHash = self.recv_protocol(sock = nodeChoice)
            Path = os.path.join(self.direct, 'blocks', 'block%d.json'%i)
            with open(Path) as f:
                data = json.load(f)
                thisHash = data["block"]["previous hash"]
            if thisHash != checkHash:
                self.send_protocol(sock = nodeChoice, data = {'command': 'done'})
                if i ==0:
                    falseIndex = i
                else:
                    falseIndex = i - 1
                self.replaceChain(falseIndex, chainLen)
                break
            else:
                self.send_protocol(sock = nodeChoice, data = {'command': 'continue'})
            
    def checkLength(self, lengths, nodeChosen):#checks the length of both other nodes to see if it is up to date
        if nodeChosen == 'me':
            nodes = [self.s1, self.s2]
            for node in nodes:
                if node == self.s1:
                    otherLen = lengths['1']
                else:
                    otherLen = lengths['2']
                difference = lengths['me'] - otherLen
                print('sending')
                self.send_protocol(sock = node, data = {'command': 'send'})
                self.send_protocol(sock = node, data = {'difference': difference})
                for i in range(difference):#checked
                    print("get latest blocks and validate them")
                    Path = os.path.join(self.direct, 'blocks', 'block%d.json'%(lengths['me'] - difference + int(i) + 1))
                    with open(Path, "r") as f:
                        fileData = json.load(f)
                    print('other len', otherLen)
                    check = self.isBlockValid(fileData["block"], otherLen) 
                    if check == False:
                        newLen = lengths['me'] - difference
                        Path = os.path.join(self.direct, 'length.txt')
                        with open(Path, "w") as f:
                            f.write(str(newLen))
                            #existing false files will be overwritten by new requests
                        self.send_protocol(sock = node, data = {'command': 'false_block'})
                        print("inform the api something is up")
                        requests.post('http://%s/bc/warn'%self.API, data = {'node': (nodes["self"]["address"], nodes["self"]["port"]), 'status':'515', 'id':fileData["block"]["id"]}, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
                        break
                    else:
                        #send across block
                        #do i jwt this?
                        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%(lengths['me'] - difference + int(i) + 1))
                        with open(Path, "rb") as f:
                            fileBin = f.read(1024)#check this
                        self.send_protocol(sock = node, data = {'command': 'send_block'})
                        self.send_protocol(sock = node, data = fileBin)
                        halt = self.recv_protocol(sock = node)
                        if halt['command'] == 'stop':
                            break
        else:
            if nodeChosen == '1':
                node = self.s1
                errorNode = self.node1
            else:
                node = self.s2
                errorNode = self.node2
            difference = lengths[nodeChosen] - lengths['me']
            print('recieving')
            self.send_protocol(sock = node, data = {'command': 'recieve'})
            self.send_protocol(sock = node, data = {'difference': difference})
            for i in range(difference):#checked
                newBlock = self.recv_protocol(sock = node)
                Path = os.path.join(self.direct, 'tempBlock.json')
                with open(Path, 'wb') as f:
                    f.write(newBlock)
                #json.load cannot take binary therefore file must be opened twice
                with open('tempBlock.json', 'r') as f:
                    data = json.load(f)
                print('length for validation: ', lengths['me'])
                check = self.isBlockValid(data["block"], lengths[nodeChosen])
                if check == True:
                    self.send_protocol(sock = node, data = {'command': 'valid_block'})
                    if node == self.s1:
                        self.rep1 +=1
                    else:
                        self.rep2 += 1
                    #adds recieved block to its chain
                    number =  data["block"]["index"]
                    Path = os.path.join(self.direct, 'blocks', 'block%d.json'%number)
                    with open(Path, "w+") as f:
                        json.dump(data, f)
                    Path = os.path.join(self.direct, 'length.txt')
                    with open(Path, "w") as f:
                            f.write(str(number))
                else:
                    self.send_protocol(sock = node, data = {'command': 'invalid_block'})
                    print("warn api")
                    requests.post('http://%s/bc/warn'%self.API, data = {'node': errorNode, 'status':'516'}, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
                    if node == self.s1:
                        self.rep1 -= 50
                    else:
                        self.rep2 -= 50
                    break
        timestamp = str(datetime.datetime.now())
        self.send_protocol(sock = self.s1, data = {'time': timestamp})
        self.send_protocol(sock = self.s2, data = {'time': timestamp})
        self.s1.close()
        self.s2.close()
        Path = os.path.join(self.direct, 'nodes.json')
        with open(Path, "r") as f:
            nodes = json.load(f)
            nodes["node_1"]["reputation"] = Client.rep1
            nodes["node_2"]["reputation"] = Client.rep2
        with open(Path, "w") as f:
            json.dump(nodes, f)
# =============================================================================
# if another node wants to connect to this one
# =============================================================================
class server():
#just the opposite of the client class
    def start(self):
        self.direct = os.path.join(os.getcwd(), 'BRSchain', 'brsChain')
        #connects to the node when the class is initialised
        print('i am a server')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind(("127.0.0.1", 30100))
        self.s.listen(1)
        self.conn, self.addr = self.s.accept()
        self.s.settimeout(900)#15 minutes
        print('recieving command')
        jwt_message = Client.recv_protocol(sock = self.conn)
        print(jwt_message)
        branch = jwt_message["command"]
        if branch == "length":
            Path = os.path.join(self.direct, 'length.txt')
            with open(Path, 'r') as f:
                chainLen = int(f.read())
            Client.send_protocol(sock = self.conn, data = str(chainLen))
            self.s.settimeout(11.7)
            self.check_similar()
        elif branch == "replace_chain":
            self.s.settimeout(11.7)
            self.replace_chain()
        elif branch == "end":
            self.s.settimeout(300)
            jwt_message = Client.recv_protocol(sock  = self.conn)
            Path = os.path.join(self.direct, 'timestamp.txt')
            with open(Path, "w") as f:
                f.write(jwt_message['time'])
            self.s.close()
            Path = os.path.join(self.direct, 'nodes.json')
            with open(Path, "r") as f:
                nodes = json.load(f)
                nodes["node_1"]["reputation"] = Client.rep1
                nodes["node_2"]["reputation"] = Client.rep2
            with open(Path, "w") as f:
                json.dump(nodes, f)
        elif branch == "node_down":
            self.s.close()
            return False
    def replace_chain(self):
        print('replace chain function')
        jwt_dec = Client.recv_protocol(sock = self.conn)
        print(jwt_dec)
        print('recieved length n tings')
        jwt_dec = Client.recv_protocol(sock = self.conn)
        print(jwt_dec)
        chainLen = jwt_dec['length']
        falseIndex = jwt_dec['index']
        repeat = chainLen - int(falseIndex) + 1
        print('repeat:', repeat)
        print('sending blocks')
        for i in range(repeat):#checked
            blockNum = int(falseIndex)+int(i)
            Path = os.path.join(self.direct, 'blocks', 'block%d.json'%blockNum)
            with open(Path, "rb") as f:
                fileData = f.read(1024)
                Client.send_protocol(sock = self.conn, data = fileData)
        print('recieving timestamps')
        jwt_message = Client.recv_protocol(sock = self.conn)
        Path = os.path.join(self.direct, 'nodes.json')
        with open(Path, "w") as f:
            f.write(jwt_message['time'])
        self.s.close()
        Path = os.path.join(self.direct, 'nodes.json')
        with open(Path, "r") as f:
            nodes = json.load(f)
            nodes["node_1"]["reputation"] = Client.rep1
            nodes["node_2"]["reputation"] = Client.rep2
        with open(Path, "w") as f:
            json.dump(nodes, f)
    def check_similar(self):
        print('check similar function')
        jwt_message = Client.recv_protocol(sock = self.conn)
        print(jwt_message)
        blockIndex = jwt_message['length']
        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%blockIndex)
        with open(Path, "r") as f:
            data = json.load(f)
        sendHash = data["block"]["previous hash"]
        print(sendHash)
        Client.send_protocol(sock = self.conn, data = str(sendHash))
        jwt_message = Client.recv_protocol(sock = self.conn)
        print(jwt_message)
        branch = jwt_message['command']
        self.s.settimeout(900)#15 minutes
        if branch == 'length_check':
            self.s.settimeout(11.7)
            self.check_length()
        elif branch == 'check_whole':
            self.s.settimeout(11.7)
            self.check_whole()
        elif branch == 'end':
            self.s.settimeout(11.7)
            jwt_message = Client.recv_protocol(sock = self.conn)
            Path = os.path.join(self.direct, 'timestamp.txt')
            with open(Path, "w") as f:
                f.write(jwt_message['time'])
            self.s.close()
            Path = os.path.join(self.direct, 'nodes.json')
            with open(Path, "r") as f:
                nodes = json.load(f)
                nodes["node_1"]["reputation"] = Client.rep1
                nodes["node_2"]["reputation"] = Client.rep2
            with open(Path, "w") as f:
                json.dump(nodes, f)
    def check_whole(self):
        print('check whole function')
        jwt_message = Client.recv_protocol(sock = self.conn)
        chainLen = jwt_message['length']
        if chainLen == 0:
            repeat = 1
        else:
            repeat = chainLen
        for i in range(repeat):#checked
            Path = os.path.join(self.direct, 'blocks', 'block%d.json'%i)
            with open(Path, "r") as f:
                data = json.load(f)
            sendHash = data["block"]["previous hash"]
            Client.send_protocol(sock = self.conn, data = str(sendHash))
            jwt_message = Client.recv_protocol(sock = self.conn)
            if jwt_message['command'] == 'done':
                break
        jwt_message = Client.recv_protocol(sock = self.conn)
        self.replace_chain()
    def check_length(self):
        print('length check function')
        Path = os.path.join(self.direct, 'length.txt')
        with open(Path, "r") as f:
            chainLen = int(f.read())
        jwt_message = Client.recv_protocol(sock = self.conn)
        print(jwt_message)
        if jwt_message['command'] == 'send':
            jwt_message = Client.recv_protocol(sock = self.conn)
            print(jwt_message)
            difference = jwt_message['difference']
            print('difference: ', difference)
            for i in range(difference):#checked
                jwt_message = Client.recv_protocol(sock = self.conn)
                if jwt_message['command'] == 'send_block':
                    block = Client.recv_protocol(sock = self.conn)
                    Path = os.path.join(self.direct, 'tempBlock.json')
                    with open(Path, 'wb') as f:
                        f.write(block)
                    with open(Path, 'r') as f:
                        data = json.load(f)
                    check = Client.isBlockValid(data["block"], chainLen + difference)
                    if check == True:
                        number = data["block"]["index"]
                        Path = os.path.join(self.direct, 'blocks', 'block%d.json'%number)
                        with open(Path, "w+") as f:
                            json.dump(data, f)
                        Path = os.path.join(self.direct, 'length.txt')
                        with open(Path, "w") as f:
                            f.write(str(number))
                        Client.send_protocol(sock = self.conn, data = {'command': 'continue'})
                    else:
                        print("warn api")
                        requests.post('http://%s/bc/warn'%client.API, data = {'node': self.addr, 'status':'516', 'id':data["block"]["id"]}, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
                        Client.send_protocol(sock = self.conn, data = {'command': 'stop'})
                        Path = os.path.join(self.direct, 'nodes.json')
                        with open(Path, 'r') as f:
                            nodes = json.load(f)
                        if self.addr == (nodes['node1']['address'], nodes['node1']['port']):
                            Client.rep1 -= 100
                        else:
                            Client.rep2 -= 100
                else:
                    Path = os.path.join(self.direct, 'nodes.json')
                    with open(Path, 'r') as f:
                            nodes = json.load(f)
                    if self.addr == (nodes['node_1']['address'], nodes['node_1']['port']):
                        Client.rep1 -= 50
                    else:
                        Client.rep2 -= 50
        elif jwt_message['command'] == 'recieve':
            jwt_message = Client.recv_protocol(sock = self.conn)
            difference = jwt_message['difference']
            for i in range(difference):#checked
                Path = os.path.join(self.direct, 'blocks', 'block%d.json'%(chainLen - int(difference) + int(i) + 1))
                with open(Path, "rb") as f:
                    fileData = f.read(1024)
                Client.send_protocol(sock = self.conn, data = fileData)
                jwt_message = Client.recv_protocol(sock = self.conn)
                if jwt_message['command'] == 'invalid_block':
                    break
        self.s.settimeout(900)
        jwt_message = Client.recv_protocol(sock = self.conn)
        Path = os.path.join(self.direct, 'timestamp.txt')
        with open(Path, "w") as f:
            f.write(jwt_message['time'])
        self.s.close()
        Path = os.path.join(self.direct, 'nodes.json')
        with open(Path, "r") as f:
            nodes = json.load(f)
            nodes["node_1"]["reputation"] = Client.rep1
            nodes["node_2"]["reputation"] = Client.rep2
        with open(Path, "w") as f:
            json.dump(nodes, f)
#this process is local therefore it not part of the classes
# =============================================================================
# part of the code that works its way around the block creation class to create the new block
# =============================================================================
blockchain  = Blockchain()
def executeBlockCreation(blockInfo, ID):
        previous_block = blockchain.getPreviousBlock()
        block = blockchain.createBlock(previous_block, blockInfo, ID)
        blockchain.writeBlock(block)
        print("block added")
# =============================================================================
# main loop
# =============================================================================
direct = os.path.join(os.getcwd(), 'BRSchain', 'brsChain', 'myTurn.txt')
with open(direct, "r") as f:
    endcount = int(f.read())
Client = client()
Server = server()
Path = os.path.join(os.getcwd(), 'BRSchain', 'brsChain', 'nodes.json')
with open(Path, "r") as f:
    nodes = json.load(f)
    API = nodes["API"]
while True:
    print(endcount)
    serverBlock = requests.get('http://%s/bc/request'%API, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
    if serverBlock.status_code == 200:
        newBlocks = serverBlock.json()
        time.sleep(15)
        for i in newBlocks['data']:
            blockInfo = i['payload']
            ID = i['id']
            executeBlockCreation(blockInfo, ID)
            print('send confirmation to the api after completion')#once it has this message from all 3 it is good
            requests.post('http://%s/bc/confirm'%API, data={'node': (nodes["self"]["address"], nodes["self"]["port"]), 'id': ID}, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
    if endcount == 2:
        #try:
        print('should be the client')
        time.sleep(10)#the servers must be up before the client executes, this ensures that
        checking = Client.start()
        if checking == None:
            endcount = 0
            with open("myTurn.txt", "w") as f:
                f.write(str(endcount))
        else:
            requests.post('http://%s/bc/warn'%API, data = {'status': '503', 'node':checking}, auth=('the_tharrisondrum', '?HCrf=7%EnAa'))
    else:
        #try:
        print('should be the server')
        checking = Server.start()
        if checking != False:
            endcount+= 1
            with open(direct, "w") as f:
                f.write(str(endcount))