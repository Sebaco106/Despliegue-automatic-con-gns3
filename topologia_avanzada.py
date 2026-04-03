import requests
import time
import sys
from requests.auth import HTTPBasicAuth

# --- 1. CONFIGURACIÓN DEL SERVIDOR ---
GNS3_IP = "127.0.0.1"
GNS3_PORT = "3080"
BASE_URL = f"http://{GNS3_IP}:{GNS3_PORT}/v2"
PROJECT_NAME = "Topolog_avanzanda" 
AUTH = HTTPBasicAuth('admin', 'admin')

# --- 2. DATOS DE HARDWARE ---
ROUTER_IMAGE = "c3660-a3jk9s-mz.124-15.T14.image"
ROUTER_PLATFORM = "c3600"
ROUTER_CHASSIS = "3660"
ROUTER_RAM = 192

ROUTER_TEMPLATE_NAME = "cisco-3600"
SWITCH_TEMPLATE_NAME = "Ethernet switch"
PC_TEMPLATE_NAME = "VPCS"

# --- 3. CONFIGURACIONES (Routers OSPF y VPCS) ---
configs = {
    # --- ROUTERS OSPF MALLA CENTRAL ---
    "R3": """!
hostname R3
!
interface FastEthernet0/0
 description Hacia_Cloud_Internet
 ip address dhcp
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R1
 ip address 10.10.10.1 255.255.255.252
 no shutdown
!
router ospf 1
 network 10.10.10.0 0.0.0.3 area 0
!
""",
    "R1": """!
hostname R1
!
interface FastEthernet0/0
 description Hacia_R3
 ip address 10.10.10.2 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R4
 ip address 10.10.10.9 255.255.255.252
 no shutdown
!
interface FastEthernet1/0
 description Hacia_R2
 ip address 10.10.10.5 255.255.255.252
 no shutdown
!
interface FastEthernet2/0
 description Gateway_Bloque_Servidores
 ip address 192.168.100.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.10.10.0 0.0.0.3 area 0
 network 10.10.10.8 0.0.0.3 area 0
 network 10.10.10.4 0.0.0.3 area 0
 network 192.168.100.0 0.0.0.255 area 0
!
""",
    "R4": """!
hostname R4
!
interface FastEthernet0/0
 description Hacia_R1
 ip address 10.10.10.10 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R2
 ip address 10.10.10.13 255.255.255.252
 no shutdown
!
interface FastEthernet1/0
 description Gateway_LAN_A
 ip address 192.168.10.1 255.255.255.0
 no shutdown
!
interface FastEthernet2/0
 description Gateway_LAN_B
 ip address 192.168.20.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.10.10.8 0.0.0.3 area 0
 network 10.10.10.12 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
 network 192.168.20.0 0.0.0.255 area 0
!
""",
    "R2": """!
hostname R2
!
interface FastEthernet0/0
 description Hacia_R1
 ip address 10.10.10.6 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R4
 ip address 10.10.10.14 255.255.255.252
 no shutdown
!
interface FastEthernet1/0
 description Gateway_LAN_C
 ip address 192.168.30.1 255.255.255.0
 no shutdown
!
interface FastEthernet2/0
 description Gateway_LAN_D
 ip address 192.168.40.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.10.10.4 0.0.0.3 area 0
 network 10.10.10.12 0.0.0.3 area 0
 network 192.168.30.0 0.0.0.255 area 0
 network 192.168.40.0 0.0.0.255 area 0
!
""",
    # --- HOSTS (Bloque Servidores Morado) ---
    "Srv_Web": "ip 192.168.100.10 255.255.255.0 192.168.100.1\n",
    "Srv_DNS": "ip 192.168.100.11 255.255.255.0 192.168.100.1\n",
    "Srv_FTP": "ip 192.168.100.12 255.255.255.0 192.168.100.1\n",
    
    # --- HOSTS (Edificio A - Azul) ---
    "PC_Ventas": "ip 192.168.10.10 255.255.255.0 192.168.10.1\n",
    "PC_Admin": "ip 192.168.10.11 255.255.255.0 192.168.10.1\n",
    "PC_SrvL1": "ip 192.168.20.10 255.255.255.0 192.168.20.1\n",
    
    # --- HOSTS (Edificio C/D - Verde) ---
    "PC_SrvL2": "ip 192.168.30.10 255.255.255.0 192.168.30.1\n",
    "PC_SrvL3": "ip 192.168.30.11 255.255.255.0 192.168.30.1\n",
    "PC_SrvL4": "ip 192.168.40.10 255.255.255.0 192.168.40.1\n"
}

# --- FUNCIONES DE LA API ---
def get_template_id(name):
    try:
        resp = requests.get(f"{BASE_URL}/templates", auth=AUTH)
        for t in resp.json():
            if t['name'] == name:
                return t['template_id']
        print(f"❌ Plantilla '{name}' no encontrada.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

def create_advanced_router(project_id, name, template_id, x, y):
    payload = {
        "name": name, "node_type": "dynamips", "template_id": template_id,
        "x": x, "y": y, "compute_id": "local", "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "platform": ROUTER_PLATFORM, "chassis": ROUTER_CHASSIS, "image": ROUTER_IMAGE, "ram": ROUTER_RAM,
            "slot0": "Leopard-2FE", "slot1": "NM-1FE-TX", "slot2": "NM-1FE-TX", "slot3": "NM-1FE-TX" 
        }
    }
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    return resp.json()['node_id']

def create_device(project_id, name, template_id, x, y, node_type, symbol=None):
    payload = {
        "name": name, "node_type": node_type, "template_id": template_id,
        "x": x, "y": y, "compute_id": "local", "properties": {}
    }
    if symbol: payload["symbol"] = symbol
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    return resp.json()['node_id']

def create_link(project_id, node_a, adapter_a, port_a, node_b, adapter_b, port_b):
    payload = {"nodes": [{"node_id": node_a, "adapter_number": adapter_a, "port_number": port_a},
                         {"node_id": node_b, "adapter_number": adapter_b, "port_number": port_b}]}
    requests.post(f"{BASE_URL}/projects/{project_id}/links", json=payload, auth=AUTH)

def upload_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup-config.cfg", data=config_text, auth=AUTH)

def upload_vpcs_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup.vpc", data=config_text, auth=AUTH)

def create_drawing(project_id, x, y, width, height, color):
    svg = f'<svg width="{width}" height="{height}"><rect width="{width}" height="{height}" fill="{color}" fill-opacity="0.3" stroke="{color}" stroke-width="2" /></svg>'
    payload = {"x": x, "y": y, "z": -1, "svg": svg}
    requests.post(f"{BASE_URL}/projects/{project_id}/drawings", json=payload, auth=AUTH)

def main():
    # MENÚ INTERACTIVO
    print("\n" + "="*50)
    print("🚀 AUTOMATIZACIÓN DE RED GNS3 - TOPOLOGÍA AVANZADA")
    print("="*50)
    print("Seleccione el modo de despliegue:")
    print("1. Sin configuración (Solo despliega equipos y cables en blanco)")
    print("2. Con configuración total (Aplica OSPF, Enrutamiento e IPs a todos los PCs)")
    
    opcion = input("\nIngrese 1 o 2: ")
    if opcion not in ["1", "2"]:
        print("❌ Opción no válida. Cancelando ejecución.")
        sys.exit(1)

    print(f"\n🔌 Conectando a GNS3... Preparando Topología Avanzada.")

    router_id = get_template_id(ROUTER_TEMPLATE_NAME)
    switch_id = get_template_id(SWITCH_TEMPLATE_NAME)
    pc_id = get_template_id(PC_TEMPLATE_NAME)

    # LIMPIEZA ROBUSTA DEL PROYECTO
    resp = requests.get(f"{BASE_URL}/projects", auth=AUTH)
    for p in resp.json():
        if p['name'] == PROJECT_NAME:
            print("🔒 Cerrando el proyecto abierto en GNS3...")
            requests.post(f"{BASE_URL}/projects/{p['project_id']}/close", auth=AUTH)
            time.sleep(1)
            
            print("♻️  Borrando los archivos del proyecto viejo...")
            del_resp = requests.delete(f"{BASE_URL}/projects/{p['project_id']}", auth=AUTH)
            if del_resp.status_code not in [200, 204]:
                print(f"❌ Error: GNS3 bloqueó el borrado. Cierra GNS3 y vuelve a intentarlo.")
                sys.exit(1)
            time.sleep(3)
            break
            
    resp = requests.post(f"{BASE_URL}/projects", json={"name": PROJECT_NAME}, auth=AUTH)
    project_id = resp.json()['project_id']
    print(f"🔨 Proyecto '{PROJECT_NAME}' creado.")

    # 3. DIBUJAR ZONAS DE COLORES 
    print("🎨 Pintando las zonas LAN y Bloque de Servidores...")
    create_drawing(project_id, -450, 130, 420, 250, "#4169E1") # Azul (LAN A y B)
    create_drawing(project_id, 0, 130, 400, 250, "#2E8B57") # Verde (LAN C y D)
    create_drawing(project_id, 330, -450, 360, 330, "#9370DB") # Morado (Servidores)

    # 4. CREAR NODOS
    print("📦 Desplegando el núcleo de alta disponibilidad y hosts...")
    nodes = {}
    
    nodes['R3'] = create_advanced_router(project_id, "Router R3", router_id, 0, -400)
    nodes['R1'] = create_advanced_router(project_id, "Router R1", router_id, 0, -200)
    nodes['R4'] = create_advanced_router(project_id, "Router R4", router_id, -200, 0)
    nodes['R2'] = create_advanced_router(project_id, "Router R2", router_id, 200, 0)
    
    nodes['Cloud'] = create_device(project_id, "Cloud Internet", pc_id, -200, -500, "vpcs", ":/symbols/classic/cloud.svg")
    
    nodes['SW_Srv'] = create_device(project_id, "Switch Srv", switch_id, 400, -300, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['Srv_Web'] = create_device(project_id, "Servidor Web", pc_id, 600, -400, "vpcs", ":/symbols/classic/server.svg")
    nodes['Srv_DNS'] = create_device(project_id, "Servidor DNS", pc_id, 600, -300, "vpcs", ":/symbols/classic/server.svg")
    nodes['Srv_FTP'] = create_device(project_id, "Servidor FTP", pc_id, 500, -200, "vpcs", ":/symbols/classic/server.svg")

    nodes['SW_A'] = create_device(project_id, "Switch LAN A", switch_id, -300, 200, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['SW_B'] = create_device(project_id, "Switch LAN B", switch_id, -100, 200, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['PC_Ventas'] = create_device(project_id, "PC Ventas", pc_id, -350, 300, "vpcs")
    nodes['PC_Admin'] = create_device(project_id, "PC Admin", pc_id, -250, 300, "vpcs")
    nodes['PC_SrvL1'] = create_device(project_id, "PC Server local 1", pc_id, -100, 300, "vpcs")

    nodes['SW_C'] = create_device(project_id, "Switch LAN C", switch_id, 100, 200, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['SW_D'] = create_device(project_id, "Switch LAN D", switch_id, 300, 200, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['PC_SrvL2'] = create_device(project_id, "PC Server local 2", pc_id, 50, 300, "vpcs")
    nodes['PC_SrvL3'] = create_device(project_id, "PC Server local 3", pc_id, 150, 300, "vpcs")
    nodes['PC_SrvL4'] = create_device(project_id, "PC Server local 4", pc_id, 300, 300, "vpcs")

    # 5. CONECTAR CABLES
    print("🔗 Realizando cableado estructural...")
    create_link(project_id, nodes['Cloud'], 0, 0, nodes['R3'], 0, 0)
    
    create_link(project_id, nodes['R3'], 0, 1, nodes['R1'], 0, 0)
    create_link(project_id, nodes['R1'], 0, 1, nodes['R4'], 0, 0)
    create_link(project_id, nodes['R1'], 1, 0, nodes['R2'], 0, 0)
    create_link(project_id, nodes['R4'], 0, 1, nodes['R2'], 0, 1)

    create_link(project_id, nodes['R1'], 2, 0, nodes['SW_Srv'], 0, 0) 
    create_link(project_id, nodes['R4'], 1, 0, nodes['SW_A'], 0, 0)   
    create_link(project_id, nodes['R4'], 2, 0, nodes['SW_B'], 0, 0)   
    create_link(project_id, nodes['R2'], 1, 0, nodes['SW_C'], 0, 0)  
    create_link(project_id, nodes['R2'], 2, 0, nodes['SW_D'], 0, 0)  

    create_link(project_id, nodes['SW_Srv'], 0, 1, nodes['Srv_Web'], 0, 0)
    create_link(project_id, nodes['SW_Srv'], 0, 2, nodes['Srv_DNS'], 0, 0)
    create_link(project_id, nodes['SW_Srv'], 0, 3, nodes['Srv_FTP'], 0, 0)

    create_link(project_id, nodes['SW_A'], 0, 1, nodes['PC_Ventas'], 0, 0)
    create_link(project_id, nodes['SW_A'], 0, 2, nodes['PC_Admin'], 0, 0)
    create_link(project_id, nodes['SW_B'], 0, 1, nodes['PC_SrvL1'], 0, 0)

    create_link(project_id, nodes['SW_C'], 0, 1, nodes['PC_SrvL2'], 0, 0)
    create_link(project_id, nodes['SW_C'], 0, 2, nodes['PC_SrvL3'], 0, 0)
    create_link(project_id, nodes['SW_D'], 0, 1, nodes['PC_SrvL4'], 0, 0)

    # 6. LÓGICA CONDICIONAL DE CONFIGURACIÓN
    if opcion == "2":
        print("📝 Opción 2 seleccionada: Inyectando OSPF convergente e IPs en todos los Servidores y PCs...")
        upload_config(project_id, nodes['R3'], configs['R3'])
        upload_config(project_id, nodes['R1'], configs['R1'])
        upload_config(project_id, nodes['R4'], configs['R4'])
        upload_config(project_id, nodes['R2'], configs['R2'])
        
        upload_vpcs_config(project_id, nodes['Srv_Web'], configs['Srv_Web'])
        upload_vpcs_config(project_id, nodes['Srv_DNS'], configs['Srv_DNS'])
        upload_vpcs_config(project_id, nodes['Srv_FTP'], configs['Srv_FTP'])
        
        upload_vpcs_config(project_id, nodes['PC_Ventas'], configs['PC_Ventas'])
        upload_vpcs_config(project_id, nodes['PC_Admin'], configs['PC_Admin'])
        upload_vpcs_config(project_id, nodes['PC_SrvL1'], configs['PC_SrvL1'])
        
        upload_vpcs_config(project_id, nodes['PC_SrvL2'], configs['PC_SrvL2'])
        upload_vpcs_config(project_id, nodes['PC_SrvL3'], configs['PC_SrvL3'])
        upload_vpcs_config(project_id, nodes['PC_SrvL4'], configs['PC_SrvL4'])
    else:
        print("⚠️  Opción 1 seleccionada: Desplegando equipos en blanco.")

    # 7. ENCENDER
    print("🚀 Encendiendo y estabilizando la red...")
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/start", json={}, auth=AUTH)

    print("\n✅ ¡MAGNÍFICO! Topología Avanzada desplegada con éxito.")
    print("Revisa tu entorno GNS3. Ahora verás los recuadros de colores delimitando tus VLANs y los iconos correctos.")

if __name__ == "__main__":
    main()