import socket
import json
import threading
import time
from pynput import keyboard


class TcpClient:
    def __init__(self, host, port, cid):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((host, port))

        # 运行标志
        self.running = True
        # 客户端ID
        self.cid = cid
        # 主窗口引用
        self.main_window = None
        # 线程引用
        self.heartbeat_thread = None
        self.receive_thread = None

    def set_main_window(self, main_window):
        self.main_window = main_window

    def send_heartbeat(self):
        """定时发送心跳包"""
        while self.running:
            try:
                heartbeat_packet = {
                    "cmd": 0x40,
                    "from": self.cid
                }
                self.send(heartbeat_packet)
                print("Heartbeat sent")
                time.sleep(10)  # 每10秒发送一次心跳
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
                            # print(f"Received: {line}")
                            packet = json.loads(line)
                            body = packet.get('body')

                            if packet.get('cmd') == 0x30:
                                # 处理绑定客户端发送的信息
                                print(f"Server send: {body}")
                                # self.main_window.currentWidget.animate()
                                # 改为通过信号触发（假设主窗口有相应信号）
                                if hasattr(self.main_window, 'trigger_key'):
                                    self.main_window.trigger_key_with_data.emit(body)
                            elif packet.get('cmd') == 0x40:
                                # 处理服务器的心跳确认
                                print(f"Server heartbeat: {body}")

                                # 处理绑定
                                if body in ("unbind", "bind offline", "bind online"):
                                    self.main_window.update_target_status(body)

                else:
                    # 服务器关闭连接
                    break
            except Exception as e:
                print(f"Error receiving message: {e}")
                break

    def bind(self, target):
        """绑定客户端"""
        heartbeat_packet = {
            "cmd": 0x10,
            "from": self.cid,
            "to": target
        }
        self.send(heartbeat_packet)
        print(f"bind {target}")
        # 发送心跳包，检查绑定对象状态
        heartbeat_packet = {
            "cmd": 0x40,
            "from": self.cid
        }
        self.send(heartbeat_packet)

    def offline(self):
        """离线模式，注销服务器信息"""
        offline_packet = {
            "cmd": 0x50,
            "from": self.cid
        }
        self.send(offline_packet)
        print("offLine")


    def start(self):
        """启动客户端"""
        self.running = True
        # 启动心跳线程
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        # 启动消息接收线程
        self.receive_thread = threading.Thread(target=self.receive_messages)
        self.receive_thread.daemon = True
        self.receive_thread.start()

    def stop(self):
        """停止客户端"""
        self.running = False

        # 等待线程结束（增加超时时间避免无限阻塞）
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=1)

        if self.receive_thread and self.receive_thread.is_alive():
            self.receive_thread.join(timeout=1)

        # 通知服务器注销
        self.offline()
        # 更新绑定状态
        self.main_window.update_target_status("unbind")

    def send(self, packet):
        """发送信息"""
        self.client_socket.sendall((json.dumps(packet) + "\n").encode('utf-8'))


    def on_key_press(self, key_value):

        packet = {
            "cmd": 0x30,
            "from": self.cid,
            "body": key_value
        }
        self.send(packet)


# 使用示例
if __name__ == "__main__":
    client = TcpClient('localhost', 9000, "1")
    try:
        client.bind("2")
        client.start()
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()
