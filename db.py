import mysql.connector
from mysql.connector import Error

def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',  # Cambia esto si tu base de datos está en otro host
            user='root',  # Reemplaza con tu nombre de usuario de MySQL
            password='',  # Reemplaza con tu contraseña de MySQL
            database='gestion_asistencias'  # Reemplaza con el nombre de tu base de datos
        )
        
        if connection.is_connected():
            print("Conexión a la base de datos establecida")
            return connection

    except Error as e:
        print(f"Error al conectarse a la base de datos: {e}")
        return None
