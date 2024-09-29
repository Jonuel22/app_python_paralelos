from multiprocessing import Manager, Process
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_file
import mysql.connector
from threading import Thread
from datetime import datetime
import os
import json

app = Flask(__name__)
app.secret_key = '04022002'  # Cambia esto por una clave secreta real para sesiones

# Conexión a la base de datos
def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',  # Cambia por tu usuario de MySQL
        password='',  # Cambia por tu contraseña de MySQL
        database='gestion_asistencias'
    )

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form['username']
    password = request.form['password']

    connection = get_db_connection()
    if connection is None:
        flash('Error en la conexión a la base de datos')
        return redirect(url_for('login'))

    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT password_hash, id FROM usuarios WHERE usuario = %s', (username,))
    user = cursor.fetchone()

    cursor.close()
    connection.close()

    # Verifica si el usuario existe y la contraseña es correcta
    if user and password == user['password_hash']:  # Comparación directa
        session['user_id'] = user['id']
        return redirect(url_for('menu'))
    else:
        flash('Nombre de usuario o contraseña incorrectos')
        return redirect(url_for('login'))

@app.route('/menu')
def menu():
    return render_template('menu_principal.html')

# Funciones de hilo
def agregar_trabajador_thread(nombre, apellido, email, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    cursor.execute('INSERT INTO trabajadores (nombre, apellido, email) VALUES (%s, %s, %s)',
                   (nombre, apellido, email))
    connection.commit()
    cursor.close()
    connection.close()

    retorno.append('Trabajador agregado exitosamente.')

def obtener_trabajadores_thread(retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute('SELECT id, nombre, apellido, email, fecha_registro FROM trabajadores')
    trabajadores = cursor.fetchall()

    cursor.close()
    connection.close()

    retorno.append(trabajadores)

# Mantenimiento de Trabajadores
@app.route('/mantenimiento_trabajadores', methods=['GET', 'POST'])
def mantenimiento_trabajadores():
    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']

        retorno = []

        # Crear hilos
        t1 = Thread(target=agregar_trabajador_thread, args=(nombre, apellido, email, retorno))
        t2 = Thread(target=obtener_trabajadores_thread, args=(retorno,))

        # Iniciar hilos
        t1.start()
        t2.start()

        # Esperar que los hilos terminen
        t1.join()
        t2.join()

        # Captura los mensajes y la lista de trabajadores
        flash(retorno[0])  # Mensaje de éxito o error
        trabajadores = retorno[1] if len(retorno) > 1 else []

    else:
        retorno = []
        obtener_trabajadores_thread(retorno)
        trabajadores = retorno[0] if retorno else []

    return render_template('mantenimiento_trabajadores.html', trabajadores=trabajadores)

#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Editar Trabajador

# Función para editar un trabajador en un hilo
def editar_trabajador_en_hilo(id, nombre, apellido, email, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Actualizar el trabajador en la base de datos
    cursor.execute('UPDATE trabajadores SET nombre = %s, apellido = %s, email = %s WHERE id = %s',
                   (nombre, apellido, email, id))
    connection.commit()
    cursor.close()
    connection.close()

    # Agregar mensaje de éxito al retorno
    retorno['mensaje'] = 'Trabajador editado exitosamente.'

# Ruta para editar un trabajador
@app.route('/editar_trabajador/<int:id>', methods=['GET', 'POST'])
def editar_trabajador(id):
    retorno = {}

    if request.method == 'POST':
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        email = request.form['email']

        # Crear un hilo para editar el trabajador
        t = Thread(target=editar_trabajador_en_hilo, args=(id, nombre, apellido, email, retorno))
        t.start()
        t.join()  # Esperar a que termine el hilo para continuar

        # Mostrar mensaje de éxito o error
        flash(retorno.get('mensaje', 'Error al editar el trabajador.'))
        return redirect(url_for('mantenimiento_trabajadores'))

    # Obtener los datos del trabajador a editar
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM trabajadores WHERE id = %s', (id,))
    trabajador = cursor.fetchone()
    cursor.close()
    connection.close()

    return render_template('editar_trabajador.html', trabajador=trabajador)

#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Eliminar Trabajador

# Función para eliminar un trabajador en un hilo
def eliminar_trabajador_en_hilo(id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Eliminar el trabajador de la base de datos
    cursor.execute('DELETE FROM trabajadores WHERE id = %s', (id,))
    connection.commit()
    cursor.close()
    connection.close()

    # Agregar mensaje de éxito al retorno
    retorno['mensaje'] = 'Trabajador eliminado exitosamente.'

# Ruta para eliminar un trabajador
@app.route('/eliminar_trabajador/<int:id>', methods=['POST'])
def eliminar_trabajador(id):
    retorno = {}

    # Crear un hilo para eliminar el trabajador
    t = Thread(target=eliminar_trabajador_en_hilo, args=(id, retorno))
    t.start()
    t.join()  # Esperar a que termine el hilo para continuar

    # Mostrar mensaje de éxito o error
    flash(retorno.get('mensaje', 'Error al eliminar el trabajador.'))
    
    return redirect(url_for('mantenimiento_trabajadores'))


#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Mantenimiento de horas

# Función para insertar horas en un hilo
def insertar_horas_en_hilo(trabajador_id, fecha, hora_entrada, hora_salida, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Insertar las horas en la base de datos
    cursor.execute('INSERT INTO asistencias (trabajador_id, fecha, hora_entrada, hora_salida) VALUES (%s, %s, %s, %s)',
                   (trabajador_id, fecha, hora_entrada, hora_salida))

    connection.commit()
    cursor.close()
    connection.close()
    
    # Agregar mensaje de éxito
    retorno['mensaje'] = 'Horas registradas exitosamente.'

# Función para obtener trabajadores y asistencias en un hilo
def obtener_trabajadores_y_asistencias(retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Obtener lista de trabajadores
    cursor.execute('SELECT id, nombre, apellido FROM trabajadores')
    trabajadores = cursor.fetchall()

    today = datetime.today().date()

    # Obtener las asistencias de hoy
    cursor.execute('SELECT * FROM asistencias WHERE fecha = %s', (today,))
    asistencias = cursor.fetchall()

    cursor.close()
    connection.close()

    # Agregar los resultados al retorno
    retorno['trabajadores'] = trabajadores
    retorno['asistencias'] = asistencias
    retorno['today'] = today

# Ruta del mantenimiento de horas
@app.route('/mantenimiento_horas', methods=['GET', 'POST'])
def mantenimiento_horas():
    retorno = {}

    if request.method == 'POST':
        trabajador_id = request.form['trabajador_id']
        fecha = request.form['fecha']
        hora_entrada = request.form['hora_entrada']
        hora_salida = request.form['hora_salida']

        # Crear un hilo para la inserción de horas
        t1 = Thread(target=insertar_horas_en_hilo, args=(trabajador_id, fecha, hora_entrada, hora_salida, retorno))
        t1.start()
        t1.join()  # Esperar a que termine el hilo para continuar

        # Mostrar mensaje de éxito o error
        #flash(retorno.get('mensaje', 'Error al registrar horas.'))

    # Crear un hilo para obtener trabajadores y asistencias
    t2 = Thread(target=obtener_trabajadores_y_asistencias, args=(retorno,))
    t2.start()
    t2.join()  # Esperar a que termine el hilo

    # Renderizar la plantilla con los datos obtenidos
    return render_template('mantenimiento_horas.html', 
                           trabajadores=retorno.get('trabajadores', []), 
                           asistencias=retorno.get('asistencias', []), 
                           today=retorno.get('today', datetime.today().date()))



#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Horas Globales

def obtener_asistencias(trabajador_id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM asistencias WHERE trabajador_id = %s ORDER BY fecha ASC', (trabajador_id,))
    asistencias = cursor.fetchall()
    
    # Convertir fechas a formato ISO antes de agregar a retorno
    for asistencia in asistencias:
        asistencia['fecha'] = asistencia['fecha'].isoformat()  # Convierte la fecha a cadena ISO

    cursor.close()
    connection.close()
    retorno[trabajador_id] = asistencias

# Horas Globales
@app.route('/horas_globales', methods=['GET', 'POST'])
def horas_globales():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute('SELECT id, nombre, apellido FROM trabajadores')
    trabajadores = cursor.fetchall()

    trabajadores_horas = {}

    # Usamos threading para obtener asistencias en paralelo
    retorno = {}
    threads = []

    for trabajador in trabajadores:
        t = Thread(target=obtener_asistencias, args=(trabajador['id'], retorno))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    for trabajador in trabajadores:
        if trabajador['id'] in retorno:
            trabajadores_horas[trabajador['id']] = {
                'nombre': trabajador['nombre'],
                'apellido': trabajador['apellido'],
                'asistencias': retorno[trabajador['id']]
            }

    cursor.close()
    connection.close()

    return render_template('horas_globales.html', trabajadores_horas=trabajadores_horas)

#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Editar Horas

# Función para actualizar asistencia en un hilo
def actualizar_horas_editar_horas(trabajador_id, fecha, hora_entrada, hora_salida, id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Actualizar los datos de la asistencia
    cursor.execute('''UPDATE asistencias 
                      SET trabajador_id = %s, fecha = %s, hora_entrada = %s, hora_salida = %s 
                      WHERE id = %s''',
                   (trabajador_id, fecha, hora_entrada, hora_salida, id))
    connection.commit()
    
    cursor.close()
    connection.close()

    retorno.append('Horas editadas exitosamente.')

# Función para obtener asistencia en un hilo
def obtener_asistencia_editar_horas(id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Obtener la asistencia específica y los datos del trabajador asociado
    cursor.execute('''
        SELECT a.*, t.nombre AS trabajador_nombre, t.apellido AS trabajador_apellido
        FROM asistencias a
        JOIN trabajadores t ON a.trabajador_id = t.id
        WHERE a.id = %s
    ''', (id,))
    asistencia = cursor.fetchone()

    cursor.close()
    connection.close()

    retorno.append(asistencia)


# Editar Horas
@app.route('/editar_horas/<int:id>', methods=['GET', 'POST'])
def editar_horas(id):
    retorno = []

    if request.method == 'POST':
        # Capturar los datos del formulario enviado
        trabajador_id = request.form['trabajador_id']
        fecha = request.form['fecha']
        hora_entrada = request.form['hora_entrada']
        hora_salida = request.form['hora_salida']

        # Crear un hilo para actualizar las horas
        t1 = Thread(target=actualizar_horas_editar_horas, args=(trabajador_id, fecha, hora_entrada, hora_salida, id, retorno))
        
        # Iniciar el hilo
        t1.start()

        # Esperar a que el hilo termine
        t1.join()

        # Mostrar el mensaje de éxito o error
        flash(retorno[0])
        return redirect(url_for('horas_globales'))

    else:
        # Crear un hilo para obtener la asistencia específica
        t2 = Thread(target=obtener_asistencia_editar_horas, args=(id, retorno))
        
        # Iniciar el hilo
        t2.start()

        # Esperar a que el hilo termine
        t2.join()

        asistencia = retorno[0] if retorno else {}

    return render_template('editar_horas.html', asistencia=asistencia)



#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

#eliminar horas

# Función para eliminar asistencia en un hilo
def eliminar_horas_en_hilo(id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor()

    # Eliminar el registro de asistencia de la base de datos
    cursor.execute('DELETE FROM asistencias WHERE id = %s', (id,))
    connection.commit()

    cursor.close()
    connection.close()

    retorno.append('Horas eliminadas exitosamente.')

# Ruta para eliminar horas
@app.route('/eliminar_horas/<int:id>', methods=['POST'])
def eliminar_horas(id):
    retorno = []

    # Crear un hilo para eliminar las horas
    t = Thread(target=eliminar_horas_en_hilo, args=(id, retorno))
    
    # Iniciar el hilo
    t.start()

    # Esperar a que el hilo termine
    t.join()

    # Mostrar el mensaje de éxito o error
    if retorno:
        flash(retorno[0])
    else:
        flash('Error al eliminar las horas.')

    return redirect(url_for('mantenimiento_horas'))


#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

# Consulta de Horas

# Función para obtener asistencias de un trabajador
def obtener_asistencias_consulta_horas(trabajador_id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT * FROM asistencias WHERE trabajador_id = %s ORDER BY fecha ASC', (trabajador_id,))
    asistencias = cursor.fetchall()
    
    # Convertir fechas a formato ISO antes de agregar a retorno
    for asistencia in asistencias:
        asistencia['fecha'] = asistencia['fecha'].isoformat()  # Convierte la fecha a cadena ISO

    cursor.close()
    connection.close()
    retorno['asistencias'] = asistencias

# Función para obtener información del trabajador
def obtener_trabajador_consulta_horas(trabajador_id, retorno):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute('SELECT nombre, apellido FROM trabajadores WHERE id = %s', (trabajador_id,))
    trabajador = cursor.fetchone()
    retorno['trabajador'] = trabajador
    cursor.close()
    connection.close()

#----------------------------------------------------------------------------------------------------------

@app.route('/consulta_horas', methods=['GET', 'POST'])
def consulta_horas():
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # Obtener la lista de trabajadores para el formulario
    cursor.execute('SELECT id, nombre, apellido FROM trabajadores')
    trabajadores = cursor.fetchall()

    asistencias = []
    trabajador = None

    if request.method == 'POST':
        trabajador_id = request.form['trabajador_id']

        # Usar hilos para obtener asistencias e información del trabajador
        retorno = {}
        threads = []

        # Crear hilos
        t1 = Thread(target=obtener_asistencias_consulta_horas, args=(trabajador_id, retorno))
        t2 = Thread(target=obtener_trabajador_consulta_horas, args=(trabajador_id, retorno))
        
        threads.append(t1)
        threads.append(t2)

        # Iniciar hilos
        for t in threads:
            t.start()

        # Esperar a que todos los hilos terminen
        for t in threads:
            t.join()

        # Asignar resultados a las variables
        asistencias = retorno.get('asistencias', [])
        trabajador = retorno.get('trabajador', None)

    cursor.close()
    connection.close()

    return render_template('consulta_horas.html', trabajadores=trabajadores, asistencias=asistencias, trabajador=trabajador)


#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------
#----------------------------------------------------------------------------------------------------------

#JSON

from flask import send_file, redirect, url_for

@app.route('/descargar_json', methods=['GET'])
def descargar_json():
    trabajadores_horas = {}
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    cursor.execute('SELECT id, nombre, apellido FROM trabajadores')
    trabajadores = cursor.fetchall()

    retorno = Manager().dict()  # Usar un diccionario compartido entre procesos
    processes = []

    for trabajador in trabajadores:
        p = Process(target=obtener_asistencias, args=(trabajador['id'], retorno))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

    for trabajador in trabajadores:
        if trabajador['id'] in retorno:
            trabajadores_horas[trabajador['id']] = {
                'nombre': trabajador['nombre'],
                'apellido': trabajador['apellido'],
                'asistencias': retorno[trabajador['id']]
            }

    cursor.close()
    connection.close()

    # Crear el archivo JSON
    filename = f'asistencias_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    filepath = os.path.join('C:\\Users\\Jonuel Collado\\Desktop\\json', filename)  # Asegúrate de que la ruta sea válida
    with open(filepath, 'w') as json_file:
        json.dump(trabajadores_horas, json_file, default=str)

    # Redirigir para visualizar el JSON
    return redirect(url_for('visualizar_json', filename=filename))

@app.route('/visualizar_json/<filename>', methods=['GET'])
def visualizar_json(filename):
    # Devuelve el archivo JSON como texto para visualización
    return send_file(os.path.join('C:\\Users\\Jonuel Collado\\Desktop\\json', filename), mimetype='application/json')


if __name__ == '__main__':
    app.run(debug=True)
