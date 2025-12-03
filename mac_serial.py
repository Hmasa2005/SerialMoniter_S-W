import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import serial
import serial.tools.list_ports
import threading
import datetime

class SerialApp:
    def __init__(self, master):
        self.master = master
        self.master.title("擬似! TeraTerm <^.^/>")
        self.serial_port = None
        self.running = False
        self.timestamp_enabled = False
        self.logging = False
        self.log_file = None

        # デバイス選択
        frame = tk.Frame(master, bg="black")
        frame.pack(pady=10)

        tk.Label(frame, text="デバイス:", fg="white", bg="black").pack(side=tk.LEFT)
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(frame, textvariable=self.device_var, width=40)
        self.device_combo.pack(side=tk.LEFT, padx=5)
        self.refresh_ports()

        tk.Button(frame, text="更新", command=self.refresh_ports).pack(side=tk.LEFT)

        # 接続ボタン群
        btn_frame = tk.Frame(master, bg="black")
        btn_frame.pack(pady=5)

        self.connect_btn = tk.Button(btn_frame, text="接続", command=self.toggle_connection)
        self.connect_btn.pack(side=tk.LEFT, padx=5)

        self.timestamp_btn = tk.Button(btn_frame, text="タイムスタンプ OFF", command=self.toggle_timestamp)
        self.timestamp_btn.pack(side=tk.LEFT, padx=5)

        self.log_btn = tk.Button(btn_frame, text="ログ記録開始", command=self.toggle_logging)
        self.log_btn.pack(side=tk.LEFT, padx=5)

        # 受信テキストエリア（黒背景・白文字）
        self.text_area = tk.Text(
            master,
            height=15,
            width=70,
            bg="black",
            fg="white",
            insertbackground="white"
        )
        self.text_area.pack(pady=0)

        # スクロールバー
        scrollbar = tk.Scrollbar(master, command=self.text_area.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.text_area.config(yscrollcommand=scrollbar.set)

        # 送信エリア
        send_frame = tk.Frame(master, bg="black")
        send_frame.pack(pady=5)

        tk.Label(send_frame, text="送信:", fg="white", bg="black").pack(side=tk.LEFT)
        self.send_entry = tk.Entry(send_frame, width=50, bg="black", fg="white", insertbackground="white")
        self.send_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(send_frame, text="送信", command=self.send_data).pack(side=tk.LEFT)

    # ------------------- ポート管理 -------------------
    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        device_list = []
        for port in ports:
            if "usbmodem" in port.device:
                display_name = f"{port.device} - Arm"
            else:
                display_name = port.device
            device_list.append(display_name)
        self.device_combo["values"] = device_list
        if device_list:
            self.device_combo.current(0)

    def toggle_connection(self):
        if not self.serial_port:
            self.connect()
        else:
            self.disconnect()

    def connect(self):
        device_label = self.device_var.get()
        if not device_label:
            messagebox.showerror("エラー", "デバイスを選択してください。")
            return

        device = device_label.split(" ")[0]
        try:
            self.serial_port = serial.Serial(device, 115200, timeout=0.1)
            self.running = True
            threading.Thread(target=self.read_loop, daemon=True).start()
            self.connect_btn.config(text="切断")
            self.append_text(f"接続しました: {device_label}\n")
        except Exception as e:
            messagebox.showerror("接続エラー", str(e))
            self.serial_port = None

    def disconnect(self):
        if self.serial_port:
            self.running = False
            self.serial_port.close()
            self.serial_port = None
            self.connect_btn.config(text="接続")
            self.append_text("切断しました。\n")

    # ------------------- タイムスタンプ -------------------
    def toggle_timestamp(self):
        self.timestamp_enabled = not self.timestamp_enabled
        state = "ON" if self.timestamp_enabled else "OFF"
        self.timestamp_btn.config(text=f"タイムスタンプ {state}")
        self.append_text(f"[INFO] タイムスタンプ {state}")

    # ------------------- ログ機能 -------------------
    def toggle_logging(self):
        if not self.logging:
            # ファイル選択ダイアログ
            file_path = filedialog.asksaveasfilename(
                title="ログ保存先を選択",
                defaultextension=".log",
                filetypes=[("ログファイル", "*.log"), ("すべてのファイル", "*.*")]
            )
            if file_path:
                try:
                    self.log_file = open(file_path, "w", encoding="utf-8")
                    self.logging = True
                    self.log_btn.config(text="記録停止")
                    self.append_text(f"[INFO] ログ記録開始: {file_path}\n")
                except Exception as e:
                    messagebox.showerror("エラー", f"ファイルを開けません: {e}")
        else:
            if self.log_file:
                self.log_file.close()
            self.logging = False
            self.log_btn.config(text="ログ記録開始")
            self.append_text("[INFO] ログ記録停止")

    # ------------------- データ送受信 -------------------
    def send_data(self):
        if self.serial_port:
            data = self.send_entry.get()
            if data:
                try:
                    self.serial_port.write((data).encode())
                    self.append_text(f"> {data}")
                    self.send_entry.delete(0, tk.END)
                except Exception as e:
                    messagebox.showerror("送信エラー", str(e))
        else:
            messagebox.showwarning("警告", "シリアルポートが開かれていません。")

    def append_text(self, text):
        self.text_area.insert(tk.END, text)
        self.text_area.see(tk.END)
        if self.logging and self.log_file:
            self.log_file.write(text)
            self.log_file.flush()

    def read_loop(self):
        while self.running:
            try:
                if self.serial_port.in_waiting > 0:
                    data = self.serial_port.read(self.serial_port.in_waiting)
                    text = data.decode(errors="replace")
                    # タイムスタンプONなら追加
                    if self.timestamp_enabled:
                        now = datetime.datetime.now().strftime("[%H:%M:%S] ")
                        text = "".join([now + line for line in text.splitlines(True)])
                    self.append_text(text)
            except Exception as e:
                print("受信エラー:", e)
                break

if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg="black")
    app = SerialApp(root)
    root.mainloop()
