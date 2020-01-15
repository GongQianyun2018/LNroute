import random
from numpy import *
import networkx as nx
import matplotlib.pyplot as plt
# import Node


class SmallWorld:
    #N:表示N个节点
    #K为偶数
    #Matrix：邻接矩阵
    def __init__(self, N, K, p):
        self.N=N
        self.K=K
        self.p=p
        self.matrix=zeros((N, N))
        self.G=nx.Graph()
        if K%2==1:
            print("error: K is odd")
        elif K>N:
            print("error: K is greater than N")

        #每个节点都与左右相邻的各k/2节点相连，k为偶数
        for i in range(N):#[0,N-1]
            for j in range(int(K/2+1)):#[0,K/2]
                if i-j>=0 and i+j<=(N-1):
                    self.matrix[i][i-j]=self.matrix[i][i+j]=1
                    self.matrix[i-j][i]=self.matrix[i+j][i]=1
                elif i-j < 0:
                    self.matrix[i][N+i-j]=self.matrix[i][i+j]=1
                    self.matrix[N+i-j][i]=self.matrix[i+j][i]=1
                elif i+j>(N-1):
                    self.matrix[i][i+j-N]=self.matrix[i][i-j]=1
                    self.matrix[i+j-N][i]=self.matrix[i-j][i]=1

        #把自身连接清空
        for i in range(N):
            self.matrix[i][i]=0

        #记录下未随机连接前的邻接矩阵图
        self.matrix_before=self.matrix



        #随机化重连，以概率p随机的重新连接网络中原有的一条边，即把一条边的一个端点保持不变
        #另外一个端点改取网络中随机选择的另外的一个端点，其中规定不可以有自连和重边
        #随机产生一个概率p_change,如果p_change<p,重新连接边
        p_change = 0.0
        edge_change = 0
        for i in range(N):
            for j in range(N):
                if self.matrix_before[i][j]==1:
                    p_change = (random.randint(0, N-1))/(double)(N)
                    if p_change < p:
                        #随机选择一个节点，排除自身连接和重边两种情况
                        while(1):
                            nodeNewConnect=(random.randint(0, N-1))
                            if self.matrix[i][nodeNewConnect]==0 and nodeNewConnect!=i:
                                break
                        self.matrix[i][j]=self.matrix[j][i]=0
                        self.matrix[i][nodeNewConnect]=self.matrix[nodeNewConnect][i]=1


    def Draw(self):
        for i in range(self.N):
            print(self.matrix[i])

        for i in range(self.N):
            self.G.add_node(i)

        for i in range(self.N):
            for j in range(self.N):
                if self.matrix[i][j]==1:
                    self.G.add_edge(i, j)

        pos = nx.circular_layout(self.G)
        nx.draw(self.G, pos, with_labels=True, node_size=350)
        plt.show()

    #def Create(self):






sw = SmallWorld(20, 4, 0.2)
sw.Draw()

