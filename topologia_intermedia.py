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

# --- 3. CONFIGURACIONES (Routers y PCs) ---
configs = {
    # --- ROUTERS OSPF ---
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
""",
    # --- HOSTS (LAN A) ---
    "Srv_Web": "ip 192.168.10.10 255.255.255.0 192.168.10.1\n",
    "PC1": "ip 192.168.10.11 255.255.255.0 192.168.10.1\n",
    "PC2": "ip 192.168.10.12 255.255.255.0 192.168.10.1\n",
    
    # --- HOSTS (LAN B) ---
    "Srv_DNS": "ip 192.168.20.10 255.255.255.0 192.168.20.1\n",
    "PC3": "ip 192.168.20.11 255.255.255.0 192.168.20.1\n",
    "PC4": "ip 192.168.20.12 255.255.255.0 192.168.20.1\n"
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
    svg = f'<svg width="{width}" height="{height}"><rect width="{width}" height="{height}" fill="{color}" fill-opacity="0.3" stroke="{color}" stroke-width="2" /></svg>'
    payload = {"x": x, "y": y, "z": -1, "svg": svg}
    requests.post(f"{BASE_URL}/projects/{project_id}/drawings", json=payload, auth=AUTH)

def create_router(project_id, name, template_id, x, y):
    payload = {
        "name": name, "node_type": "dynamips", "template_id": template_id, "x": x, "y": y, "compute_id": "local",
        "symbol": ":/symbols/classic/router.svg",
        "properties": {
            "platform": ROUTER_PLATFORM, 
            "chassis": ROUTER_CHASSIS, 
            "image": ROUTER_IMAGE, 
            "ram": ROUTER_RAM,
            "startup_config": "startup-config.cfg", # <--- ¡ESTA ES LA LÍNEA QUE FALTABA!
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
    payload = {"name": name, "node_type": node_type, "template_id": template_id, "x": x, "y": y, "compute_id": "local", "properties": {}}
    if symbol: payload["symbol"] = symbol
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando {name}: {resp.text}")
        sys.exit(1)
    return resp.json()['node_id']

def create_link(project_id, node_a, adapter_a, port_a, node_b, adapter_b, port_b):
    payload = {"nodes": [{"node_id": node_a, "adapter_number": adapter_a, "port_number": port_a},
                         {"node_id": node_b, "adapter_number": adapter_b, "port_number": port_b}]}
    requests.post(f"{BASE_URL}/projects/{project_id}/links", json=payload, auth=AUTH)

def upload_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup-config.cfg", data=config_text, auth=AUTH)

def upload_vpcs_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup.vpc", data=config_text, auth=AUTH)

def main():
    # MENÚ INTERACTIVO
    print("\n" + "="*50)
    print("🚀 AUTOMATIZACIÓN DE RED GNS3 - TOPOLOGÍA INTERMEDIA")
    print("="*50)
    print("Seleccione el modo de despliegue:")
    print("1. Sin configuración (Solo despliega equipos y cables en blanco)")
    print("2. Con configuración total (Aplica OSPF, Inter-VLAN Routing e IPs a PCs)")
    
    opcion = input("\nIngrese 1 o 2: ")
    if opcion not in ["1", "2"]:
        print("❌ Opción no válida. Cancelando ejecución.")
        sys.exit(1)

    print(f"\n🔌 Conectando a GNS3 Local (Topología Intermedia)...")

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
    if resp.status_code not in [200, 201]:
        print(f"❌ Error de GNS3 al crear el proyecto: {resp.text}")
        sys.exit(1)
    project_id = resp.json()['project_id']
    print(f"🔨 Proyecto '{PROJECT_NAME}' creado.")

    # 3. DIBUJAR ZONAS DE COLORES
    print("🎨 Pintando las zonas de red...")
    create_drawing(project_id, -300, -350, 600, 650, "#E6E6FA") # Fondo General
    create_drawing(project_id, -500, 0, 100, 150, "#FF8C00") # Servidor WEB (Izquierda)
    create_drawing(project_id, 400, 0, 100, 150, "#FF8C00")  # Servidor DNS (Derecha)
    create_drawing(project_id, -280, 20, 220, 260, "#FFFACD") # LAN A
    create_drawing(project_id, 60, 20, 220, 260, "#FFFACD")   # LAN B

    # 4. Crear Nodos 
    print("📦 Desplegando Routers OSPF, Switches y Servidores...")
    nodes = {}
    nodes['R3'] = create_router(project_id, "Router R3", router_id, 0, -300)
    nodes['R2'] = create_router(project_id, "Router R2", router_id, -200, -100)
    nodes['R1'] = create_router(project_id, "Router R1", router_id, 200, -100)
    
    nodes['SW1'] = create_device(project_id, "Switch 1", switch_id, -200, 50, "ethernet_switch", ":/symbols/classic/multilayer_switch.svg")
    nodes['SW_L2_A'] = create_device(project_id, "Switch", switch_id, -200, 150, "ethernet_switch", ":/symbols/classic/ethernet_switch.svg")
    nodes['Srv_Web'] = create_device(project_id, "Servidor WEB", pc_id, -450, 50, "vpcs", ":/symbols/classic/server.svg")
    nodes['PC1'] = create_device(project_id, "PC 1", pc_id, -250, 250, "vpcs")
    nodes['PC2'] = create_device(project_id, "PC 2", pc_id, -150, 250, "vpcs")

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

    # 6. LÓGICA CONDICIONAL DE CONFIGURACIÓN
    if opcion == "2":
        print("📝 Opción 2 seleccionada: Inyectando OSPF en Routers e IPs en Hosts...")
        upload_config(project_id, nodes['R3'], configs['R3'])
        upload_config(project_id, nodes['R2'], configs['R2'])
        upload_config(project_id, nodes['R1'], configs['R1'])
        
        upload_vpcs_config(project_id, nodes['Srv_Web'], configs['Srv_Web'])
        upload_vpcs_config(project_id, nodes['PC1'], configs['PC1'])
        upload_vpcs_config(project_id, nodes['PC2'], configs['PC2'])
        upload_vpcs_config(project_id, nodes['Srv_DNS'], configs['Srv_DNS'])
        upload_vpcs_config(project_id, nodes['PC3'], configs['PC3'])
        upload_vpcs_config(project_id, nodes['PC4'], configs['PC4'])
    else:
        print("⚠️  Opción 1 seleccionada: Desplegando equipos en blanco.")

    # 7. Encender
    print("🚀 Encendiendo topología...")
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/start", json={}, auth=AUTH)

    print("\n✅ ¡FINALIZADO! La Topología Intermedia está lista para usarse.")

if __name__ == "__main__":
    main()