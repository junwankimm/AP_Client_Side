import cv2
import socket
from sshtunnel import SSHTunnelForwarder
import io
import numpy as np
import pickle
import paramiko
import os
import shutil

class SendCaptureSSH:
    def __init__(self):
        self.cap = cv2.VideoCapture(0)
        cv2.namedWindow("Webcam Feed")
        cv2.setMouseCallback("Webcam Feed", self.on_mouse_click)
        self.server = SSHTunnelForwarder(
            ('pch-home-server3143.iptime.org', 3144),  # Replace with your server's address and SSH port
            ssh_username='ubuntu',
            ssh_pkey='/Users/junwankim/.ssh/proxmox_key',  # Or use ssh_password if you use password auth
            remote_bind_address=('127.0.0.1', 22222)  # The server's IP and a chosen port
        )
        self.server.start()
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.connect(('127.0.0.1', self.server.local_bind_port))
        
        host = 'pch-home-server3143.iptime.org'
        port = 3144
        username = 'ubuntu'
        key_file_path = '/Users/junwankim/.ssh/proxmox_key'

        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        private_key = paramiko.RSAKey(filename=key_file_path)
        ssh_client.connect(host, port, username, pkey=private_key)
        self.sftp = ssh_client.open_sftp()
        self.remote_folder = "/home/ubuntu/junwan/Semantify/logs"
        self.sftp.chdir(self.remote_folder)
        shutil.rmtree('./logs')
        os.makedirs('./logs')
        
    def send(self, data):
        image_pickle = pickle.dumps(data)
        self.s.sendall(image_pickle)
        self.s.sendall(b"END") 
        print("Image sent")
        

    def on_mouse_click(self, event, x, y, flags, param):
        global image
        if event == cv2.EVENT_LBUTTONDOWN:
            # Define the button area, e.g., bottom right corner
            button_x1, button_y1, button_x2, button_y2 = 400, 400, 500, 450
            if button_x1 <= x <= button_x2 and button_y1 <= y <= button_y2:
                _, image = self.cap.read()
                image = cv2.flip(image, 1)
                print("Frame captured")
                self.send(image)
    
    def init_unity(self):
        unity_port = 5066
        address = ('127.0.0.1', unity_port)
        unity_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        unity_s.connect(address)
        print("Connected to address:", socket.gethostbyname(socket.gethostname()) + ":" + str(unity_port))
        return unity_s
    
    def to_unity(self, unity_s, shape, exp):
        #args = (shape, exp)
        blendshapes = np.concatenate([shape.squeeze(), exp.squeeze()]) #90 concat 안해도 되긴 할듯?
        formatted_values = ["%4f" % value for value in blendshapes]
        msg = " ".join(formatted_values)
        # msg = '%.4f ' %  len(args) % args     
        unity_s.send(bytes(msg, "utf-8"))       
    
    def capture(self):
        count = 0
        unity_count = 1
        unity_s = self.init_unity()
        first = True
        while True:
            _, frame = self.cap.read()
            frame = cv2.flip(frame, 1)
    
            # Draw the button
            cv2.rectangle(frame, (400, 400), (500, 450), (0, 255, 0), -1)
            cv2.putText(frame, 'Send', (410, 435), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2, cv2.LINE_AA)
            
            cv2.imshow("Semantify", frame)
            
            remote_files = self.sftp.listdir()
            
            if ((cv2.waitKey(1) == 115) and first): # s로도 보낼 수 있음
                image = cv2.flip(frame, 1)
                print("Frame captured")
                self.send(image)
                first = False
            
            if len(remote_files) > count:
                file_list = sorted(remote_files)
                self.sftp.get(os.path.join(self.remote_folder,file_list[-1]), os.path.join('logs',f'{file_list[-1]}'))
                count += 1
    
                if len(os.listdir('./logs')) > unity_count:
                    shape = np.load(os.path.join('./logs',f'{file_list[0]}'))
                    exp = np.load(os.path.join('./logs',f'{file_list[-1]}'))
                    # exp = np.concatenate([exp, np.zeros([1,90])] ,axis=1)
                    
                    self.to_unity(unity_s, shape, exp)
                    print("Unity connected")
                    unity_count += 1
                
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        self.cap.release()
        cv2.destroyAllWindows()
        while True:
            print("waiting")
            # WAITING
    def run(self):
        self.receive_thread.start()
        self.capture()

        

capture = SendCaptureSSH()
capture.capture()