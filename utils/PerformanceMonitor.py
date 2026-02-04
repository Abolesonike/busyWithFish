import psutil
import time
import threading
from typing import Dict, List, Optional
from collections import deque
from datetime import datetime


class PerformanceMonitor:
    """
    性能监控器 - 实时监控应用资源使用情况
    
    监控指标：
    - CPU使用率
    - 内存使用量
    - 线程数量
    - 文件句柄数
    - 网络I/O统计
    """
    
    def __init__(self, sample_interval: float = 1.0, history_size: int = 300):
        self.sample_interval = sample_interval
        self.history_size = history_size
        
        # 数据历史记录
        self.cpu_history: deque = deque(maxlen=history_size)
        self.memory_history: deque = deque(maxlen=history_size)
        self.thread_history: deque = deque(maxlen=history_size)
        
        # 当前状态
        self.current_stats: Dict = {}
        self.process = psutil.Process()
        
        # 控制标志
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()
        
        # 性能告警阈值
        self.thresholds = {
            'cpu_percent': 80.0,      # CPU使用率阈值(%)
            'memory_mb': 200.0,       # 内存使用阈值(MB)
            'thread_count': 50        # 线程数量阈值
        }
    
    def start_monitoring(self):
        """启动性能监控"""
        with self._lock:
            if self._running:
                return
            
            self._running = True
            self._monitor_thread = threading.Thread(
                target=self._monitor_loop,
                name="PerformanceMonitor",
                daemon=True
            )
            self._monitor_thread.start()
    
    def stop_monitoring(self):
        """停止性能监控"""
        with self._lock:
            self._running = False
        
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=2.0)
    
    def _monitor_loop(self):
        """监控主循环"""
        while True:
            with self._lock:
                if not self._running:
                    break
            
            try:
                self._collect_metrics()
                self._check_thresholds()
            except Exception as e:
                print(f"Performance monitor error: {e}")
            
            time.sleep(self.sample_interval)
    
    def _collect_metrics(self):
        """收集性能指标"""
        timestamp = datetime.now()
        
        # CPU使用率
        cpu_percent = self.process.cpu_percent()
        
        # 内存使用
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024  # 转换为MB
        
        # 线程数
        thread_count = self.process.num_threads()
        
        # 文件句柄数
        try:
            fd_count = self.process.num_fds()
        except AttributeError:
            fd_count = 0  # Windows不支持
        
        # 网络I/O
        try:
            net_io = self.process.net_io_counters()
            net_bytes_sent = net_io.bytes_sent
            net_bytes_recv = net_io.bytes_recv
        except Exception:
            net_bytes_sent = net_bytes_recv = 0
        
        # 更新当前状态
        stats = {
            'timestamp': timestamp,
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'thread_count': thread_count,
            'fd_count': fd_count,
            'net_bytes_sent': net_bytes_sent,
            'net_bytes_recv': net_bytes_recv
        }
        
        with self._lock:
            self.current_stats = stats
            self.cpu_history.append((timestamp, cpu_percent))
            self.memory_history.append((timestamp, memory_mb))
            self.thread_history.append((timestamp, thread_count))
    
    def _check_thresholds(self):
        """检查性能阈值并发出告警"""
        current = self.current_stats
        
        alerts = []
        
        # CPU使用率告警
        if current.get('cpu_percent', 0) > self.thresholds['cpu_percent']:
            alerts.append(f"High CPU usage: {current['cpu_percent']:.1f}%")
        
        # 内存使用告警
        if current.get('memory_mb', 0) > self.thresholds['memory_mb']:
            alerts.append(f"High memory usage: {current['memory_mb']:.1f}MB")
        
        # 线程数告警
        if current.get('thread_count', 0) > self.thresholds['thread_count']:
            alerts.append(f"High thread count: {current['thread_count']}")
        
        # 输出告警信息
        if alerts:
            print("PERFORMANCE ALERTS:")
            for alert in alerts:
                print(f"  ⚠️ {alert}")
    
    def get_current_stats(self) -> Dict:
        """获取当前性能统计"""
        with self._lock:
            return self.current_stats.copy()
    
    def get_history_stats(self) -> Dict[str, List]:
        """获取历史统计数据"""
        with self._lock:
            return {
                'cpu_history': list(self.cpu_history),
                'memory_history': list(self.memory_history),
                'thread_history': list(self.thread_history)
            }
    
    def get_average_stats(self, window_minutes: int = 5) -> Dict:
        """获取指定时间窗口内的平均统计"""
        current_time = datetime.now()
        cutoff_time = current_time.timestamp() - (window_minutes * 60)
        
        with self._lock:
            # 过滤时间窗口内的数据
            cpu_samples = [cpu for ts, cpu in self.cpu_history 
                          if ts.timestamp() >= cutoff_time]
            mem_samples = [mem for ts, mem in self.memory_history 
                          if ts.timestamp() >= cutoff_time]
            thread_samples = [thr for ts, thr in self.thread_history 
                             if ts.timestamp() >= cutoff_time]
        
        if not cpu_samples:
            return {'cpu_avg': 0, 'memory_avg': 0, 'thread_avg': 0}
        
        return {
            'cpu_avg': sum(cpu_samples) / len(cpu_samples),
            'memory_avg': sum(mem_samples) / len(mem_samples),
            'thread_avg': sum(thread_samples) / len(thread_samples),
            'sample_count': len(cpu_samples)
        }
    
    def set_threshold(self, metric: str, value: float):
        """设置告警阈值"""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            print(f"Threshold updated: {metric} = {value}")
        else:
            print(f"Unknown threshold metric: {metric}")
    
    def get_system_load(self) -> Dict:
        """获取系统整体负载信息"""
        try:
            return {
                'system_cpu_percent': psutil.cpu_percent(),
                'system_memory_percent': psutil.virtual_memory().percent,
                'disk_usage_percent': psutil.disk_usage('/').percent,
                'process_count': len(psutil.pids())
            }
        except Exception as e:
            print(f"Error getting system load: {e}")
            return {}


# 全局性能监控器实例
_performance_monitor: Optional[PerformanceMonitor] = None
_monitor_lock = threading.Lock()


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器单例"""
    global _performance_monitor
    
    with _monitor_lock:
        if _performance_monitor is None:
            _performance_monitor = PerformanceMonitor()
            _performance_monitor.start_monitoring()
    
    return _performance_monitor


def shutdown_performance_monitor():
    """关闭性能监控器"""
    global _performance_monitor
    
    with _monitor_lock:
        if _performance_monitor:
            _performance_monitor.stop_monitoring()
            _performance_monitor = None


def print_performance_report():
    """打印性能报告"""
    monitor = get_performance_monitor()
    
    print("\n" + "="*50)
    print("PERFORMANCE REPORT")
    print("="*50)
    
    # 当前状态
    current = monitor.get_current_stats()
    if current:
        print(f"Timestamp: {current.get('timestamp', 'N/A')}")
        print(f"CPU Usage: {current.get('cpu_percent', 0):.1f}%")
        print(f"Memory Usage: {current.get('memory_mb', 0):.1f} MB")
        print(f"Thread Count: {current.get('thread_count', 0)}")
        print(f"File Descriptors: {current.get('fd_count', 0)}")
    
    # 平均统计（最近5分钟）
    avg_stats = monitor.get_average_stats(5)
    print(f"\n5-Minute Average:")
    print(f"  CPU: {avg_stats.get('cpu_avg', 0):.1f}%")
    print(f"  Memory: {avg_stats.get('memory_avg', 0):.1f} MB")
    print(f"  Threads: {avg_stats.get('thread_avg', 0):.1f}")
    
    # 系统负载
    system_load = monitor.get_system_load()
    if system_load:
        print(f"\nSystem Load:")
        print(f"  System CPU: {system_load.get('system_cpu_percent', 0):.1f}%")
        print(f"  System Memory: {system_load.get('system_memory_percent', 0):.1f}%")
        print(f"  Disk Usage: {system_load.get('disk_usage_percent', 0):.1f}%")
        print(f"  Total Processes: {system_load.get('process_count', 0)}")
    
    print("="*50 + "\n")


# 示例使用
if __name__ == "__main__":
    # 启动监控
    monitor = get_performance_monitor()
    
    try:
        # 运行一段时间观察
        time.sleep(10)
        
        # 打印报告
        print_performance_report()
        
    finally:
        # 清理
        shutdown_performance_monitor()