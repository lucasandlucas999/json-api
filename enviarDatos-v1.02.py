import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
import configparser
import pymysql
import json
import requests
from datetime import datetime
import threading

VERSION = "v1.02.2025.03.20"

# Cambios:
# 2025-03-20 09:31 = Cambiar character set de utf8mb4 para agarrar de charset en config.ini -> v1.02.2025.03.20
# ini 
config = configparser.ConfigParser()
config.read('config.ini')

class DatabaseManager:
    @staticmethod
    def connect():
        try:
            return pymysql.connect(
                host=config.get('database', 'host'),
                user='',
                password='',  
                database=config.get('database', 'database'),
                port=config.getint('database', 'port'),
                charset=config.get('database', 'charset', fallback='utf8'),
                cursorclass=pymysql.cursors.DictCursor
            )
        except pymysql.Error as e:
            raise Exception(f"Error de conexión: {e}")

class APIClient:
    @staticmethod
    def send_data(data):
        try:
            response = requests.post(
                config.get('api', 'url'),
                headers={
                    'Authorization': f'Bearer {config.get("api", "token")}',
                    'Content-Type': 'application/json'
                },
                data=json.dumps(data),
                timeout=10
            )
            return response
        except Exception as e:
            raise Exception(f"Error en la solicitud HTTP: {e}")

class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(config.get('titulo', 'empresa'))
        self.geometry("400x300")
        self._create_widgets()
        
    def _create_widgets(self):
        self.frame = ttk.Frame(self, padding=20)
        self.frame.pack(expand=True)
        
        ttk.Label(self.frame, text="Seleccione la fecha:").pack(pady=5)
        self.date_entry = DateEntry(self.frame, date_pattern='dd-mm-y')
        self.date_entry.pack(pady=5)
        
        self.send_btn = ttk.Button(
            self.frame,
            text="Enviar Datos",
            command=self._start_sending_thread
        )
        self.send_btn.pack(pady=15)
        
        self.status_label = ttk.Label(self.frame, text="")
        self.status_label.pack()
        self.version_label = ttk.Label(self, text=VERSION, font=("Arial", 8))
        self.version_label.pack(side="bottom", anchor="se", padx=10, pady=10)

    def _start_sending_thread(self):
        threading.Thread(target=self._send_data_process, daemon=True).start()

    def _send_data_process(self):
        try:
            self.send_btn.config(state='disabled')
            selected_date = self.date_entry.get_date()
            
            with DatabaseManager.connect() as connection:
                data = self._get_sales_data(connection, selected_date)
                
                if not data['ventas']:
                    messagebox.showinfo("Información", "No hay datos para esta fecha")
                    return
                
                self._update_status("Enviando datos...")
                response = APIClient.send_data(data)
                
                if response.status_code in (200, 201):
                    messagebox.showinfo("Éxito", "Datos enviados correctamente")
                else:
                    messagebox.showerror("Error", f"Error en el servidor: {response.text}")
        
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.send_btn.config(state='normal')
            self._update_status("")

    def _get_sales_data(self, connection, fecha):
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM venta_factura WHERE fecha = %s",
                    (fecha.strftime('%Y-%m-%d'),)
                )
                results = cursor.fetchall()
                
                return {
                    "contrato": config.get('api', 'contrato'),
                    "fecha": fecha.strftime('%d-%m-%Y'),
                    "ventas": [self._format_sale(row) for row in results]
                }
        except pymysql.Error as e:
            raise Exception(f"Error en consulta SQL: {e}")

    def _format_sale(self, row):
        return {
            "comprobante": str(row.get('comprobante', '')),
            "fecha": row.get('fecha').strftime('%d-%m-%Y'),
            "tipo": str(row.get('tipo', '')),
            "moneda": str(row.get('moneda', '')),
            "tipoCambio": f"{row.get('tipoCambio', 0):.2f}",
            "gravadas10": f"{row.get('gravadas10', 0):.2f}",
            "gravadas5": f"{row.get('gravadas5', 0):.2f}",
            "exentas": f"{row.get('exentas', 0):.2f}",
            "total": f"{row.get('total', 0):.2f}",
            "cliente": str(row.get('cliente', '')),
            "ruc": str(row.get('ruc', ''))
        }

    def _update_status(self, message):
        self.status_label.config(text=message)
        self.update_idletasks()

if __name__ == "__main__":
    app = Application()
    app.mainloop()
