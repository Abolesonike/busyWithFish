from utils.TcpClient import HeartbeatClient

# 使用示例
if __name__ == "__main__":
    client = HeartbeatClient('localhost', 9000, "2")
    try:
        client.bind("1")
        client.start()
    except KeyboardInterrupt:
        print("Stopping client...")
        client.stop()