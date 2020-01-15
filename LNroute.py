import socket
import pickle
import hashlib  #规定使用hash256作为标准hash函数
import random
from datetime import datetime
import threading
import time
import queue
from WS import SmallWorld
random.seed(2019)

Total_TTL=0#如何统计多线程内部变量进行累加
Total_Fee=0
'''先付款后结账模式'''
class Node(threading.Thread):

    def __init__(self,name,port,init_balance,Local_IP="localhost"):
        #测试环境在本机进行，以端口号代替实际IP
        threading.Thread.__init__(self,name=name)
        self.name=name
        self.local_ip=Local_IP
        self.init_balance=init_balance
        self.balance=init_balance
        self.port=port
        self.fee=self.balance*0.001
        self.Tx=[]
        self.Tx_0=[]
        self.id=0
        self.Neigbor_Nodes=[]#临近节点信息
        self.keys=[]#hash原象存储
        self.mutex=threading.Lock()

    def create_routetable(self):
        self.routetable=routetable(self.Neigbor_Nodes,self)
        '''for route in self.routetable.route_table:
            print(route)'''

    def renew_balance(self):#renew_balance的时机选择
        self.balance=self.init_balance
        for transaction in self.Tx:
            if(transaction.sender==self.port):
                self.balance-=transaction.account
                self.balance+=transaction.real_fee
            if(transaction.next_receiver==self.port):
                self.balance+=transaction.account
                self.balance-=transaction.real_fee
        self.fee=self.balance*0.001
        print("%s当前账户余额%.2f"%(self.name,self.balance))
        self.broadcast_routetable()




    def handle_request(self,conn):
        global Total_TTL
        global Total_Fee
        data=[]
        while True:
            buff=conn.recv(1024)
            if not buff:
                break
            data.append(buff)
            if len(buff)<1024:
                break
        t=pickle.loads(b''.join(data))
        conn.close()
        if isinstance(t,transaction):
            '''尝试使用Tx_0的大小来表示交易的积压情况'''
            tx_unresolve=len(self.Tx_0)
            #t.total_time=t.total_time+tx_unresolve+1
            print("%s还有%d个交易待验证"%(self.name,tx_unresolve))
            print("%s收到交易,开始解析"%self.name)

            #解析交易，若发给自己，接受交易，添加进入Tx中；若发给别处，查询路由表，转发至最小费用ip
            if(t.receiver==self.port):
                print("确认为己方交易，进行Hash验证")
                for key in self.keys[:]:
                    hash_c=hashlib.sha256()
                    hash_c.update(key.encode("utf-8"))
                    hash_c=hash_c.hexdigest()
                    if(hash_c==t.hash):
                        t.id=self.id+1
                        print("验证成功")
                        print("收到%.2f个货币"%(t.account))
                        print("%s交易序号%d完成"%(self.name,t.id))
                        print("经过跳数：%d"%t.TTL)
                        Total_TTL+=t.TTL
                        Total_Fee+=t.real_fee
                        received_transaction=transaction(t.sender,t.receiver,t.next_receiver,t.account,0,t.id,t.hash,t.TTL)
                        self.Tx.append(received_transaction)
                        #将key发送给前一个节点
                        print("%s将KEY和总费用信息传递给上一个节点"%self.name)
                        Key=[key,t.real_fee]
                        self.send_key(t.sender,Key)
                        self.renew_balance()
                        #self.broadcast_routetable()
                        self.keys.remove(key)
                        #print("%s现在余额%f"%(self.name,self.balance))#收费冲突问题


                        break

            else:
               #出现交易额不足以支付过路费用的情况
                #t.account-=self.fee
                #print("%s收取过路费%f"%(self.name,self.fee))
                #小费收取问题
                self.Tx_0.append(t)

                for route in self.routetable.route_table:
                    if(route["Des"]==t.receiver):
                        print("%s交易转发"%self.name)
                        self.id+=1

                        transfer_transaction = transaction(self.port, t.receiver, route["Next"],t.account,real_fee=t.real_fee+self.fee, id=self.id,hash=t.hash,TTL=t.TTL+1)

                        self.Tx_0.append(transfer_transaction)
                        self.send_transaction(transfer_transaction)
                        break
        if isinstance(t,routetable):
            self.mutex.acquire()
            print("%s收到路由信息开始更新路由"%self.name)

            self.renew_routetable(t)
            self.mutex.release()

        if isinstance(t,request):
            #生成Hash,用时间不行，精确到秒会有重复
            print("%s收到请求"%self.name)
            #time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")#怎么是固定的？
            time_=time.time()
            time_=str(time_+random.random())
            #print("现在时间是:",time_)
            self.keys.append(time_)
            hash=hashlib.sha256()
            hash.update(time_.encode("utf-8"))
            hash=hash.hexdigest()
            #print(hash)
            my_responce=responce(self.port,t.sender,t.account,hash)
            print("%s开始发送回复" % self.name)
            self.send_responce(my_responce,t.sender)


        if isinstance(t,responce):
            for route in self.routetable.route_table:
                if (route["Des"] == t.sender):
                    self.id=self.id+1
                    my_transaction=transaction(self.port,t.sender,route["Next"],account=t.account,real_fee=0,id=self.id,hash=t.hash)
                    print("%s收到应答，开始传送交易" % self.name)

                    self.send_transaction(my_transaction)
                    self.Tx_0.append(my_transaction)
                    break
        if isinstance(t,list):
            verified = hashlib.sha256()
            verified.update(t[0].encode("utf-8"))
            verified = verified.hexdigest()

            flag=2
            for tx in self.Tx_0[:]:
                if (tx.hash==verified):
                    print("%s收到KEY"%self.name)

                    if tx.sender==self.port:
                        print("%s交易序号%d完成"%(self.name,tx.id))
                        print("到达判断点")
                        if tx.real_fee==0:
                            tx.real_fee=-t[1]
                            print("%s交易%d所花路费%.2f"%(self.name,tx.id,tx.real_fee))
                            self.Tx.append(tx)
                            self.Tx_0.remove(tx)
                            self.renew_balance()
                            break
                        else:
                            self.Tx.append(tx)
                            self.Tx_0.remove(tx)
                            flag-=1

                    if tx.sender!=self.port:
                        print("%s交易序号%d完成" % (self.name,tx.id))
                        self.Tx.append(tx)
                        self.Tx_0.remove(tx)
                        print("%s将KEY传给上一个节点"%(self.name))
                        self.send_key(tx.sender,t)
                        flag-=1
                    if(flag==0):

                        self.renew_balance()
                        break










    def renew_routetable(self,routetable):#核心算法，收敛速度较为关键

        broadcast_flag=0
        #对收到的路由表的信息进行遍历
        for recieve_route in routetable.route_table:
            #如果目的节点不是当前节点则做出处理并判断是否更新
            if(recieve_route["Des"]!=self.port):
                flag = 0
                # 再对自身的路由表进行遍历
                for self_route in self.routetable.route_table[:]:

                    if(recieve_route["Des"]==self_route["Des"]):
                        flag=1
                        if(recieve_route["Total_Fees"]+recieve_route["Fee"]<self_route["Total_Fees"]):#更新路径
                            broadcast_flag=1
                            self.routetable.route_table.remove(self_route)
                            route={"Source":self.port,"Next":recieve_route["Source"],"Fee":self.fee,"Des":recieve_route["Des"],"Total_Fees":recieve_route["Total_Fees"]+recieve_route["Fee"]}
                            self.routetable.route_table.append(route)
                            break
                if(flag==0):#更新路径
                    broadcast_flag=1
                    route={"Source":self.port,"Next":recieve_route["Source"],"Fee":self.fee,"Des":recieve_route["Des"],"Total_Fees":recieve_route["Total_Fees"]+recieve_route["Fee"]}
                    self.routetable.route_table.append(route)
        if(broadcast_flag==1):
            self.broadcast_routetable()



    def send_transaction(self,transaction):
        #选择下一节点路径

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.local_ip, transaction.next_receiver))
        sock.send(pickle.dumps(transaction))
        sock.close()
    def send_request(self,receive_port,account):
        if account>self.balance:
            print("交易额不足，停止交易")
            return

        my_request=request(self.port,receive_port,account)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.local_ip,receive_port))
        sock.send(pickle.dumps(my_request))
        sock.close()


    def send_responce(self,responce,receive_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.local_ip, receive_port))
        sock.send(pickle.dumps(responce))
        sock.close()
    def broadcast_routetable(self):#加上互斥锁

        print("%s向临近节点广播路由开始"%self.name)
        for node in self.Neigbor_Nodes:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((node.local_ip, node.port))
            sock.send(pickle.dumps(self.routetable))
            sock.close()
    def send_key(self,receive_port,key):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((self.local_ip, receive_port))
        sock.send(pickle.dumps(key))
        sock.close()



    def run(self):
        print("%s正在运行"%self.name)
        sock=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        sock.bind((self.local_ip,self.port))
        sock.listen(20)#节点拥堵情况记录


        while True:

            connection,address=sock.accept()

            try:

                #检测拥塞

                #此处可以使用多线程,否则仅能处理一个连接
                handle=threading.Thread(target=self.handle_request,args=(connection,),daemon=True)
                print("%s正在处理接收信息" % self.name)
                handle.start()#限制多个广播同时发生的情况
                '''print("%s正在处理接收信息" % self.name)
                self.handle_request(connection)'''



            except Exception as e:
                print(e)
            except socket.timeout:
                print("超时！")
            #connection.close()








class transaction:
    #没有验证机制的简易交易结构

    def __init__(self,sender,receiver,next_receiver,account,real_fee,id,hash,TTL=0):
        self.sender=sender
        self.receiver=receiver
        self.account=account
        self.id=id
        self.hash=hash
        self.next_receiver=next_receiver
        self.TTL=TTL
        self.real_fee=real_fee

class routetable:
    def __init__(self,Neigbor_nodes,Node):
        self.route_table=[]
        for neigbor in Neigbor_nodes:
            route={"Source":Node.port,"Next":neigbor.port,"Fee":Node.fee,"Des":neigbor.port,"Total_Fees":0}
            self.route_table.append(route)


class request:
    def __init__(self,sender,receiver,account):
        self.sender=sender
        self.receiver=receiver
        self.account=account


class responce:
    def __init__(self,sender,receiver,account,hash):
        self.sender=sender
        self.receiver=receiver
        self.hash=hash
        self.account=account
def start_transaction(Node,node_number):
     global Thread_Count
     i=0
     while (i<20):
         a = list(range(node_number))
         a.remove(Node.port-8000)
         b = [j + 8000 for j in a]
         receive_port = random.choice(b)
         account = random.randint(0, 5)
         Node.send_request(receive_port, account)
         time.sleep(2)
         i+=1
     print("<<<<<<<<<<<<<<<子线程%s交易发送结束"%Node.name)





if __name__=="__main__":

    node_number = 10
    node_init_balance = []
    for i in range(0, node_number):
        node_init_balance.append(random.randint(0, node_number))
    Nodes=[]
    threadpack=[]
    for i in range(node_number):
        Nodes.append(Node("节点%d"%(i+1),8000+i, node_init_balance[i]))

    sw = SmallWorld(node_number, 4, 0.2)
    for i in range(node_number):
        for j in range(node_number):
            # extendNodes = []
            if sw.matrix[i][j] == 1:
                # extendNodes.append(Nodes[j])
                print("i, j: ", i, j)
                # Nodes[i].Neigbor_Nodes.extend((Nodes[j]))
                Nodes[i].Neigbor_Nodes.append(Nodes[j])

    for i in range(node_number):
        Nodes[i].setDaemon(True)
        Nodes[i].start()
        Nodes[i].create_routetable()
    for i in range(node_number):
        Nodes[i].broadcast_routetable()  #产生了发送信息、处理信息、接收信息之间的矛盾,如何将路由信息传遍整个网络
    time.sleep(5)
    for i in range(node_number):
        print("%s的路由表" % Nodes[i].name)
        for route in Nodes[i].routetable.route_table:
            print(route)

    for i in range(node_number):


        start_up=threading.Thread(target=start_transaction,args=(Nodes[i],node_number,))
        start_up.start()
        threadpack.append(start_up)
    for thread in threadpack:
        thread.join()

    time.sleep(15)
    print(">>>>>>>>>>>>>>>>init balance:", node_init_balance)
    print("<<<<<<<<<<<<<<<<总跳数：%d"%Total_TTL)
    print("<<<<<<<<<<<<<<<<总费用：%f"%Total_Fee)





        #解决参数统计问题
        #解决多点并发问题



















