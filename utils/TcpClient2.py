from utils.TcpClient import TcpClient

# 使用示例
if __name__ == "__main__":
    client = TcpClient('localhost', 9000, "2")
    try:
        client.bind("1")
        client.start()
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()