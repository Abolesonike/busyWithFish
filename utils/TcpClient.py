import socket
import json
import threading
import time
from pynput import keyboard
from queue import Queue, Empty
from typing import Optional


class TcpClient:
    def __init__(self, host, port, cid):
        self.host = host
        self.port = port
        self.cid = cid
        
        # 网络连接
        self.client_socket: Optional[socket.socket] = None
        
        # 运行标志
        self.running = True
        
        # 主窗口引用
        self.main_window = None
        
        # 消息队列（优化：异步发送）
        self.send_queue = Queue(maxsize=100)
        self.receive_buffer = ""
        
        # 线程引用
        self.heartbeat_thread = None
        self.receive_thread = None
        self.sender_thread = None  # 新增发送线程
        
        # 连接状态
        self.connected = False
        self.reconnect_delay = 5  # 重连延迟（秒）
        
        # 性能统计（必须在_connect_socket之前初始化）
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'bytes_sent': 0,
            'bytes_received': 0,
            'connection_attempts': 0
        }
        
        # 建立初始连接
        self._connect_socket()

    def _connect_socket(self):
        """建立socket连接"""
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(10)  # 设置连接超时
            self.client_socket.connect((self.host, self.port))
            self.client_socket.settimeout(None)  # 清除超时设置
            self.connected = True
            self.stats['connection_attempts'] += 1
            print(f"Connected to {self.host}:{self.port}")
        except Exception as e:
            print(f"Connection failed: {e}")
            self.connected = False
            self.client_socket = None

    def set_main_window(self, main_window):
        self.main_window = main_window

    def send_heartbeat(self):
        """定时发送心跳包"""
        while self.running:
            try:
                if self.connected:
                    heartbeat_packet = {
                        "cmd": 0x40,
                        "from": self.cid
                    }
                    self.send(heartbeat_packet)
                    print("Heartbeat sent")
                time.sleep(10)  # 每10秒发送一次心跳
            except Exception as e:
                print(f"Error sending heartbeat: {e}")
                self._handle_connection_error()
                break

    def sender_worker(self):
        """异步发送消息工作者"""
        while self.running:
            try:
                # 从队列获取消息（阻塞等待）
                packet = self.send_queue.get(timeout=1.0)
                if packet is None:  # 停止信号
                    break
                    
                if self.connected and self.client_socket:
                    try:
                        message = json.dumps(packet) + "\n"
                        data = message.encode('utf-8')
                        self.client_socket.sendall(data)
                        
                        # 更新统计
                        self.stats['messages_sent'] += 1
                        self.stats['bytes_sent'] += len(data)
                        
                    except Exception as e:
                        print(f"Send error: {e}")
                        self._handle_connection_error()
                        
                self.send_queue.task_done()
                
            except Empty:
                continue
            except Exception as e:
                print(f"Sender worker error: {e}")
                break

    def receive_messages(self):
        """持续接收服务器消息"""
        while self.running:
            try:
                if not self.connected:
                    time.sleep(1)
                    continue
                    
                if not self.client_socket:
                    self._handle_connection_error()
                    continue
                
                data = self.client_socket.recv(4096)  # 增大接收缓冲区
                if not data:
                    print("Server disconnected")
                    self._handle_connection_error()
                    break
                
                # 更新统计
                self.stats['bytes_received'] += len(data)
                
                # 将接收到的数据添加到缓冲区
                self.receive_buffer += data.decode('utf-8')
                
                # 按行分割消息
                while '\n' in self.receive_buffer:
                    line, self.receive_buffer = self.receive_buffer.split('\n', 1)
                    if line:
                        try:
                            packet = json.loads(line)
                            self._process_packet(packet)
                            self.stats['messages_received'] += 1
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}")
                            
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Receive error: {e}")
                self._handle_connection_error()
                break

    def _process_packet(self, packet):
        """处理接收到的数据包"""
        body = packet.get('body')
        
        if packet.get('cmd') == 0x30:
            # 处理绑定客户端发送的信息
            print(f"Server send: {body}")
            if hasattr(self.main_window, 'trigger_key'):
                self.main_window.trigger_key_with_data.emit(body)
        elif packet.get('cmd') == 0x40:
            # 处理服务器的心跳确认
            print(f"Server heartbeat: {body}")
            # 处理绑定状态
            if body in ("unbind", "bind offline", "bind online"):
                self.main_window.update_target_status(body)

    def _handle_connection_error(self):
        """处理连接错误"""
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
        
        print(f"Connection lost, attempting reconnect in {self.reconnect_delay}s...")
        # 启动重连定时器
        if self.running:
            threading.Timer(self.reconnect_delay, self._reconnect).start()

    def _reconnect(self):
        """重连逻辑"""
        if self.running and not self.connected:
            print("Reconnecting...")
            self._connect_socket()
            if self.connected:
                print("Reconnected successfully")
                # 重启必要的线程
                self._restart_threads()
            else:
                # 如果重连失败，继续尝试
                print("Reconnect failed, will try again...")
                threading.Timer(self.reconnect_delay, self._reconnect).start()

    def _restart_threads(self):
        """重启必要的工作线程"""
        # 重启接收线程
        if not self.receive_thread or not self.receive_thread.is_alive():
            self.receive_thread = threading.Thread(target=self.receive_messages, name="TcpReceiver")
            self.receive_thread.daemon = True
            self.receive_thread.start()
            
        # 重启发送线程  
        if not self.sender_thread or not self.sender_thread.is_alive():
            self.sender_thread = threading.Thread(target=self.sender_worker, name="TcpSender")
            self.sender_thread.daemon = True
            self.sender_thread.start()

    def bind(self, target):
        """绑定客户端"""
        packet = {
            "cmd": 0x10,
            "from": self.cid,
            "to": target
        }
        self.send(packet)
        print(f"bind {target}")
        # 发送心跳包，检查绑定对象状态
        self.send({"cmd": 0x40, "from": self.cid})

    def offline(self):
        """离线模式，注销服务器信息"""
        packet = {
            "cmd": 0x50,
            "from": self.cid
        }
        self.send(packet)
        print("offLine")

    def start(self):
        """启动客户端"""
        self.running = True
        
        # 重新建立socket连接（如果当前没有连接）
        if not self.connected or not self.client_socket:
            self._connect_socket()
        
        # 启动各工作线程
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat, name="TcpHeartbeat")
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

        self.receive_thread = threading.Thread(target=self.receive_messages, name="TcpReceiver")
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        self.sender_thread = threading.Thread(target=self.sender_worker, name="TcpSender")
        self.sender_thread.daemon = True
        self.sender_thread.start()

    def stop(self, graceful=True):
        """停止客户端"""
        self.running = False

        # 发送停止信号到队列
        try:
            self.send_queue.put_nowait(None)
        except:
            pass

        # 等待线程结束
        threads = [self.heartbeat_thread, self.receive_thread, self.sender_thread]
        for thread in threads:
            if thread and thread.is_alive():
                thread.join(timeout=2)

        # 优雅关闭：通知服务器注销
        if graceful and self.connected:
            try:
                self.offline()
            except:
                pass  # 忽略离线通知的错误
        
        # 关闭socket
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
            self.client_socket = None
            
        # 重置连接状态
        self.connected = False
        
        if self.main_window:
            self.main_window.update_target_status("unbind")

    def send(self, packet):
        """异步发送信息"""
        try:
            # 尝试立即放入队列
            self.send_queue.put_nowait(packet)
        except:
            # 队列满时丢弃旧消息，保持最新
            try:
                self.send_queue.get_nowait()  # 移除最老的消息
                self.send_queue.put_nowait(packet)  # 添加新消息
                print("Message queue full, dropped oldest message")
            except:
                print("Failed to queue message")

    def on_key_press(self, key_value):
        """发送按键信息"""
        packet = {
            "cmd": 0x30,
            "from": self.cid,
            "body": key_value
        }
        self.send(packet)

    def get_stats(self):
        """获取连接统计信息"""
        return self.stats.copy()


# 使用示例
if __name__ == "__main__":
    client = TcpClient('localhost', 9000, "1")
    try:
        client.bind("2")
        client.start()
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()