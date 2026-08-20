import tkinter as tk
from tkinter import ttk
import psutil
import socket
import time
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import docker
from threading import Thread

class DevDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title('LocalDev Stack Insight & Performance Dashboard')
        self.root.geometry('1200x800')
        self.root.configure(bg='#2e2e2e')
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TFrame', background='#2e2e2e')
        self.style.configure('TLabel', background='#2e2e2e', foreground='white')
        self.style.configure('TNotebook', background='#2e2e2e', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#3e3e3e', foreground='white', padding=[10,5])
        
        self.create_widgets()
        self.docker_client = docker.from_env()
        self.running = True
        self.update_thread = Thread(target=self.update_data)
        self.update_thread.daemon = True
        self.update_thread.start()
    
    def create_widgets(self):
        # Main notebook
        notebook = ttk.Notebook(self.root)
        notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # System Metrics Tab
        metrics_frame = ttk.Frame(notebook)
        notebook.add(metrics_frame, text='System Metrics')
        
        # CPU Usage
        cpu_frame = ttk.LabelFrame(metrics_frame, text='CPU Usage')
        cpu_frame.grid(row=0, column=0, padx=10, pady=10, sticky='nsew')
        self.cpu_fig = plt.figure(figsize=(6, 3), dpi=100)
        self.cpu_ax = self.cpu_fig.add_subplot(111)
        self.cpu_ax.set_facecolor('#2e2e2e')
        self.cpu_fig.patch.set_facecolor('#2e2e2e')
        self.cpu_ax.tick_params(colors='white')
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_fig, cpu_frame)
        self.cpu_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Memory Usage
        mem_frame = ttk.LabelFrame(metrics_frame, text='Memory Usage')
        mem_frame.grid(row=0, column=1, padx=10, pady=10, sticky='nsew')
        self.mem_fig = plt.figure(figsize=(6, 3), dpi=100)
        self.mem_ax = self.mem_fig.add_subplot(111)
        self.mem_ax.set_facecolor('#2e2e2e')
        self.mem_fig.patch.set_facecolor('#2e2e2e')
        self.mem_ax.tick_params(colors='white')
        self.mem_canvas = FigureCanvasTkAgg(self.mem_fig, mem_frame)
        self.mem_canvas.get_tk_widget().pack(fill='both', expand=True)
        
        # Docker Status Tab
        docker_frame = ttk.Frame(notebook)
        notebook.add(docker_frame, text='Docker Status')
        
        self.docker_tree = ttk.Treeview(docker_frame, columns=('Name', 'Status', 'CPU %', 'Memory %', 'Ports'), show='headings')
        self.docker_tree.heading('Name', text='Container Name')
        self.docker_tree.heading('Status', text='Status')
        self.docker_tree.heading('CPU %', text='CPU %')
        self.docker_tree.heading('Memory %', text='Memory %')
        self.docker_tree.heading('Ports', text='Ports')
        self.docker_tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Port Scanner Tab
        port_frame = ttk.Frame(notebook)
        notebook.add(port_frame, text='Port Scanner')
        
        self.port_tree = ttk.Treeview(port_frame, columns=('Port', 'Service', 'Status'), show='headings')
        self.port_tree.heading('Port', text='Port')
        self.port_tree.heading('Service', text='Service')
        self.port_tree.heading('Status', text='Status')
        self.port_tree.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Configure grid weights
        metrics_frame.grid_columnconfigure(0, weight=1)
        metrics_frame.grid_columnconfigure(1, weight=1)
        metrics_frame.grid_rowconfigure(0, weight=1)
        
    def update_data(self):
        self.cpu_data = []
        self.mem_data = []
        
        # Scan ports once on startup
        self.scan_ports()
        
        while self.running:
            # Update CPU and Memory usage
            cpu_percent = psutil.cpu_percent()
            mem_percent = psutil.virtual_memory().percent
            
            self.cpu_data.append(cpu_percent)
            self.mem_data.append(mem_percent)
            
            if len(self.cpu_data) > 60:
                self.cpu_data = self.cpu_data[-60:]
                self.mem_data = self.mem_data[-60:]
            
            # Update charts
            self.update_charts()
            
            # Update Docker containers
            self.update_docker_containers()
            
            time.sleep(2)
    
    def update_charts(self):
        # Clear axes
        self.cpu_ax.clear()
        self.mem_ax.clear()
        
        # Set axis colors
        self.cpu_ax.set_facecolor('#2e2e2e')
        self.cpu_ax.tick_params(colors='white')
        self.cpu_ax.set_title('CPU Usage (%)', color='white')
        
        self.mem_ax.set_facecolor('#2e2e2e')
        self.mem_ax.tick_params(colors='white')
        self.mem_ax.set_title('Memory Usage (%)', color='white')
        
        # Plot data
        self.cpu_ax.plot(self.cpu_data, color='#41a7ff')
        self.mem_ax.plot(self.mem_data, color='#41ff7f')
        
        # Update canvas
        self.cpu_canvas.draw()
        self.mem_canvas.draw()
    
    def update_docker_containers(self):
        try:
            containers = self.docker_client.containers.list(all=True)
            
            # Clear existing items
            for item in self.docker_tree.get_children():
                self.docker_tree.delete(item)
            
            for container in containers:
                stats = container.stats(stream=False)
                cpu_percent = 0.0
                mem_percent = 0.0
                
                if stats:
                    # Calculate CPU usage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_delta) * 100 * stats['cpu_stats']['online_cpus'] if system_delta != 0 else 0
                    
                    # Calculate memory usage
                    mem_usage = stats['memory_stats']['usage'] - stats['memory_stats']['stats']['cache']
                    mem_limit = stats['memory_stats']['limit']
                    mem_percent = (mem_usage / mem_limit) * 100 if mem_limit != 0 else 0
                
                # Get ports
                ports = ', '.join([f"{k}" for k in container.ports.keys()]) if container.ports else 'N/A'
                
                self.docker_tree.insert('', 'end', values=(
                    container.name,
                    container.status,
                    f"{cpu_percent:.2f}%",
                    f"{mem_percent:.2f}%",
                    ports
                ))
        except Exception as e:
            print(f"Error updating Docker containers: {e}")
    
    def scan_ports(self):
        # Clear existing items
        for item in self.port_tree.get_children():
            self.port_tree.delete(item)
        
        # Scan common ports
        common_ports = {
            22: 'SSH',
            80: 'HTTP',
            443: 'HTTPS',
            3306: 'MySQL',
            5432: 'PostgreSQL',
            27017: 'MongoDB',
            8080: 'HTTP Alt',
            8000: 'Django/HTTP'
        }
        
        for port, service in common_ports.items():
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            status = 'Open' if result == 0 else 'Closed'
            sock.close()
            
            self.port_tree.insert('', 'end', values=(port, service, status))
    
    def on_close(self):
        self.running = False
        self.update_thread.join()
        self.root.destroy()

if __name__ == '__main__':
    root = tk.Tk()
    app = DevDashboard(root)
    root.protocol('WM_DELETE_WINDOW', app.on_close)
    root.mainloop()