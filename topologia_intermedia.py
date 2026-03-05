import requests
import time
import sys
from requests.auth import HTTPBasicAuth

# --- 1. CONFIGURACIÓN DEL SERVIDOR ---
GNS3_IP = "127.0.0.1"
GNS3_PORT = "3080"
BASE_URL = f"http://{GNS3_IP}:{GNS3_PORT}/v2"
PROJECT_NAME = "Topolog_intermedia"
AUTH = HTTPBasicAuth('admin', 'admin')

# --- 2. DATOS DE HARDWARE ---
ROUTER_IMAGE = "c3660-a3jk9s-mz.124-15.T14.image"
ROUTER_PLATFORM = "c3600"
ROUTER_CHASSIS = "3660"
ROUTER_RAM = 192

ROUTER_TEMPLATE_NAME = "cisco-3600"
SWITCH_TEMPLATE_NAME = "Ethernet switch"
PC_TEMPLATE_NAME = "VPCS"

# --- 3. CONFIGURACIONES IOS (Enrutamiento OSPF - Área 0) ---
configs = {
    "R3": """!
hostname R3
!
interface FastEthernet0/0
 description Hacia_R2
 ip address 10.10.10.1 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R1
 ip address 20.20.20.1 255.255.255.252
 no shutdown
!
router ospf 1
 network 10.10.10.0 0.0.0.3 area 0
 network 20.20.20.0 0.0.0.3 area 0
!
""",
    "R2": """!
hostname R2
!
interface FastEthernet0/0
 description Hacia_R3
 ip address 10.10.10.2 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R1
 ip address 30.30.30.1 255.255.255.252
 no shutdown
!
interface FastEthernet1/0
 description Gateway_LAN_A
 ip address 192.168.10.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 10.10.10.0 0.0.0.3 area 0
 network 30.30.30.0 0.0.0.3 area 0
 network 192.168.10.0 0.0.0.255 area 0
!
""",
    "R1": """!
hostname R1
!
interface FastEthernet0/0
 description Hacia_R3
 ip address 20.20.20.2 255.255.255.252
 no shutdown
!
interface FastEthernet0/1
 description Hacia_R2
 ip address 30.30.30.2 255.255.255.252
 no shutdown
!
interface FastEthernet1/0
 description Gateway_LAN_B
 ip address 192.168.20.1 255.255.255.0
 no shutdown
!
router ospf 1
 network 20.20.20.0 0.0.0.3 area 0
 network 30.30.30.0 0.0.0.3 area 0
 network 192.168.20.0 0.0.0.255 area 0
!
"""
}

# --- FUNCIONES DE LA API ---
def get_template_id(name):
    try:
        resp = requests.get(f"{BASE_URL}/templates", auth=AUTH)
        if resp.status_code != 200:
            print(f"❌ Error API Templates: {resp.status_code}")
            sys.exit(1)
        for t in resp.json():
            if t['name'] == name:
                return t['template_id']
        print(f"❌ No encontré la plantilla '{name}'")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        sys.exit(1)

def create_drawing(project_id, x, y, width, height, color):
    """Genera rectángulos de color en el fondo de GNS3 usando SVG"""
    svg = f'<svg width="{width}" height="{height}"><rect width="{width}" height="{height}" fill="{color}" fill-opacity="0.3" stroke="{color}" stroke-width="2" /></svg>'
    payload = {
        "x": x,
        "y": y,
        "z": -1,
        "svg": svg
    }
    requests.post(f"{BASE_URL}/projects/{project_id}/drawings", json=payload, auth=AUTH)

def create_router(project_id, name, template_id, x, y):
    payload = {
        "name": name,
        "node_type": "dynamips",
        "template_id": template_id,
        "x": x,
        "y": y,
        "compute_id": "local",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "platform": ROUTER_PLATFORM,
            "chassis": ROUTER_CHASSIS,
            "image": ROUTER_IMAGE,
            "ram": ROUTER_RAM,
            "slot0": "Leopard-2FE",  
            "slot1": "NM-1FE-TX"     
        }
    }
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando {name}: {resp.text}")
        sys.exit(1)
    return resp.json()['node_id']

def create_device(project_id, name, template_id, x, y, node_type, symbol=None):
    payload = {
        "name": name,
        "node_type": node_type,
        "template_id": template_id,
        "x": x,
        "y": y,
        "compute_id": "local",
        "properties": {}
    }
    if symbol:
        payload["symbol"] = symbol

    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando {name}: {resp.text}")
        sys.exit(1)
    return resp.json()['node_id']

def create_link(project_id, node_a, adapter_a, port_a, node_b, adapter_b, port_b):
    payload = {
        "nodes": [
            {"node_id": node_a, "adapter_number": adapter_a, "port_number": port_a},
            {"node_id": node_b, "adapter_number": adapter_b, "port_number": port_b}
        ]
    }
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/links", json=payload, auth=AUTH)

def upload_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup-config.cfg", data=config_text, auth=AUTH)

def main():
    print(f"🔌 Conectando a GNS3 Local (Topología Intermedia)...")

    router_id = get_template_id(ROUTER_TEMPLATE_NAME)
    switch_id = get_template_id(SWITCH_TEMPLATE_NAME)
    pc_id = get_template_id(PC_TEMPLATE_NAME)

    resp = requests.get(f"{BASE_URL}/projects", auth=AUTH)
    for p in resp.json():
        if p['name'] == PROJECT_NAME:
            print("♻️  Limpiando proyecto anterior (Espera 3s)...")
            requests.delete(f"{BASE_URL}/projects/{p['project_id']}", auth=AUTH)
            time.sleep(3)
            break
            
    resp = requests.post(f"{BASE_URL}/projects", json={"name": PROJECT_NAME}, auth=AUTH)
    project_id = resp.json()['project_id']
    print(f"🔨 Proyecto '{PROJECT_NAME}' creado.")

    # 3. DIBUJAR ZONAS DE COLORES
    print("🎨 Pintando las zonas de red...")
    # Fondo General (Morado Claro)
    create_drawing(project_id, -300, -350, 600, 650, "#E6E6FA") 
    
    # Cuadros de Servidores Extremos (Naranjas)
    create_drawing(project_id, -500, 0, 100, 150, "#FF8C00") # Servidor WEB (Izquierda)
    create_drawing(project_id, 400, 0, 100, 150, "#FF8C00")  # Servidor DNS (Derecha)

    # Cuadros de Oficinas (Amarillo Claro)
    create_drawing(project_id, -280, 20, 220, 260, "#FFFACD") # LAN A
    create_drawing(project_id, 60, 20, 220, 260, "#FFFACD")   # LAN B

    # 4. Crear Nodos 
    print("📦 Desplegando Routers OSPF, Switches y Servidores...")
    nodes = {}
    
    # NÚCLEO OSPF
    nodes['R3'] = create_router(project_id, "Router R3", router_id, 0, -300)
    nodes['R2'] = create_router(project_id, "Router R2", router_id, -200, -100)
    nodes['R1'] = create_router(project_id, "Router R1", router_id, 200, -100)
    
    # LAN A (Izquierda)
    nodes['SW1'] = create_device(project_id, "Switch 1", switch_id, -200, 50, "ethernet_switch", ":/symbols/classic/multilayer_switch.svg")
    nodes['SW_L2_A'] = create_device(project_id, "Switch", switch_id, -200, 150, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['Srv_Web'] = create_device(project_id, "Servidor WEB", pc_id, -450, 50, "vpcs", ":/symbols/classic/server.svg")
    nodes['PC1'] = create_device(project_id, "PC 1", pc_id, -250, 250, "vpcs")
    nodes['PC2'] = create_device(project_id, "PC 2", pc_id, -150, 250, "vpcs")

    # LAN B (Derecha)
    nodes['SW2'] = create_device(project_id, "Switch 2", switch_id, 200, 50, "ethernet_switch", ":/symbols/classic/multilayer_switch.svg")
    nodes['SW_L2_B'] = create_device(project_id, "Switch ", switch_id, 200, 150, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['Srv_DNS'] = create_device(project_id, "Servidor DNS", pc_id, 450, 50, "vpcs", ":/symbols/classic/server.svg")
    nodes['PC3'] = create_device(project_id, "PC 3", pc_id, 150, 250, "vpcs")
    nodes['PC4'] = create_device(project_id, "PC 4", pc_id, 250, 250, "vpcs")

    # 5. Conectar Cables 
    print("🔗 Conectando malla WAN y redes locales...")
    
    create_link(project_id, nodes['R3'], 0, 0, nodes['R2'], 0, 0) 
    create_link(project_id, nodes['R3'], 0, 1, nodes['R1'], 0, 0) 
    create_link(project_id, nodes['R2'], 0, 1, nodes['R1'], 0, 1) 
    
    create_link(project_id, nodes['R2'], 1, 0, nodes['SW1'], 0, 0) 
    create_link(project_id, nodes['R1'], 1, 0, nodes['SW2'], 0, 0) 

    create_link(project_id, nodes['SW1'], 0, 1, nodes['Srv_Web'], 0, 0) 
    create_link(project_id, nodes['SW1'], 0, 2, nodes['SW_L2_A'], 0, 0)
    create_link(project_id, nodes['SW_L2_A'], 0, 1, nodes['PC1'], 0, 0)
    create_link(project_id, nodes['SW_L2_A'], 0, 2, nodes['PC2'], 0, 0)

    create_link(project_id, nodes['SW2'], 0, 1, nodes['Srv_DNS'], 0, 0)
    create_link(project_id, nodes['SW2'], 0, 2, nodes['SW_L2_B'], 0, 0)
    create_link(project_id, nodes['SW_L2_B'], 0, 1, nodes['PC3'], 0, 0)
    create_link(project_id, nodes['SW_L2_B'], 0, 2, nodes['PC4'], 0, 0)

    # 6. Configs
    print("📝 Inyectando protocolo OSPF...")
    upload_config(project_id, nodes['R3'], configs['R3'])
    upload_config(project_id, nodes['R2'], configs['R2'])
    upload_config(project_id, nodes['R1'], configs['R1'])

    # 7. Encender
    print("🚀 Encendiendo topología...")
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/start", json={}, auth=AUTH)

    print("\n✅ ¡FINALIZADO! La Topología Intermedia con colores está lista.")

if __name__ == "__main__":
    main()