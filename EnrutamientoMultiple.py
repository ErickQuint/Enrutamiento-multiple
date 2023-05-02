from flask import Flask, url_for, jsonify, request
from flask.ext.sqlalchemy import SQLAlchemy
import pexpect, paramiko, time, sys
from pexpect import pxssh

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///miRed.db'
bd = SQLAlchemy(app)

username = 'admin'
password = 'admin'

class Dispositivo(bd.Model):
    __tablename__ = 'Dispositivos'
    id = bd.Column(bd.Integer, primary_key=True)
    hostname = bd.Column(bd.String(64), unique=True)
    loopback = bd.Column(bd.String(120), unique=True)
    ip = bd.Column(bd.String(120), unique=True)
    
    def dame_url(disp):
        return url_for('dame_dispositivo', id=disp.id, _external=True)
    
    def exporta_datos(disp):
        return {
            'disp_url': disp.dame_url(),
            'hostname': disp.hostname,
            'loopback': disp.loopback,
            'ip': disp.ip,
        }

    def importa_datos(disp, datos):
        try:
            disp.hostname = datos['hostname']
            disp.loopback = datos['loopback']
            disp.ip = datos['ip']
        except KeyError as e:
            raise ValidationError('Dispositivo invalido ' + e.args[0])
        return disp

@app.route('/dispositivos/', methods=['GET'])
def dame_dispositivos():
    return jsonify({'dispositivos': [dispositivo.dame_url() 
                               for dispositivo in Dispositivo.query.all()]})


@app.route('/dispositivos/<int:id>', methods=['GET'])
def dame_dispositivo(id):
    return jsonify(Dispositivo.query.get_or_404(id).exporta_datos())


@app.route('/dispositivos/<int:id>/enrutar', methods=['GET'])
def enrutar_dispositivo(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    hostname = dispositivo.hostname
    ip = dispositivo.ip

    if id == 4:
        res = enrutar(hostname, ip, username, password)
        return hostname + " enrutado"
    else:
        res = show_ip_route(hostname, ip, username, password)
        return jsonify({"Dispositivo enrutado: ": str(res)})


@app.route('/dispositivos/<int:id>/tabla_enrutamiento', methods=['GET'])
def tabla_enrutamiento(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    hostname = dispositivo.hostname
    ip = dispositivo.ip
    res = show_ip_route(hostname, ip, username, password)
    return jsonify({"Tabla de enrutamiento: ": str(res)})

@app.route('/dispositivos/', methods=['POST'])
def nuevo_dispositivo():
    dispositivo = Dispositivo()
    dispositivo.importa_datos(request.json)
    bd.session.add(dispositivo)
    bd.session.commit()
    return jsonify({}), 201, {'Locacion': dispositivo.dame_url()}

@app.route('/dispositivos/<int:id>', methods=['PUT'])
def edita_dispositivo(id):
    dispositivo = Dispositivo.query.get_or_404(id)
    dispositivo.importa_datos(request.json)
    bd.session.add(dispositivo)
    bd.session.commit()
    return jsonify({})

with open('R4.txt', 'r') as f: 
    commands = [line for line in f.readlines()]
    
max_buffer = 65535

def clear_buffer(connection):
    if connection.recv_ready():
        return connection.recv(max_buffer)

def enrutar(dispositivo, ip, usuario, password):
    try:
        outputFileName = dispositivo + 'Enrutamiento.txt'
        connection = paramiko.SSHClient()
        connection.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        connection.connect(ip, username=usuario, password=password, look_for_keys=False, allow_agent=False)
        new_connection = connection.invoke_shell()
        salida = clear_buffer(new_connection)
        time.sleep(2)
        
        with open(outputFileName, 'wb') as f:
            for command in commands:
                new_connection.send(command)
                time.sleep(2)
                salida = new_connection.recv(max_buffer)
                f.write(salida)
        r = salida.decode('utf-8').splitlines()
        new_connection.close()  
        return dispositivo
    except:
        return 'Error al enrutar'

def show_ip_route(dispositivo, ip, usuario, password):
    child = pxssh.pxssh()
    child.login(ip, usuario, password, auto_prompt_reset=False)
    child.sendline('show ip route')
    child.expect(dispositivo+'#')
    r = child.before
    child.logout()

    return dispositivo, r

if __name__ == '__main__':
    bd.create_all()
    app.run(host='0.0.0.0', debug=True)
