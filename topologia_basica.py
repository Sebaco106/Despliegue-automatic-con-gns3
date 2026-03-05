import requests
import time
import sys
from requests.auth import HTTPBasicAuth

# --- 1. CONFIGURACIÓN DEL SERVIDOR ---
GNS3_IP = "127.0.0.1"
GNS3_PORT = "3080"
BASE_URL = f"http://{GNS3_IP}:{GNS3_PORT}/v2"
PROJECT_NAME = "Topolog_basica"
AUTH = HTTPBasicAuth('admin', 'admin')

# --- 2. DATOS DE HARDWARE ---
ROUTER_IMAGE = "c3660-a3jk9s-mz.124-15.T14.image"
ROUTER_PLATFORM = "c3600"
ROUTER_CHASSIS = "3660"
ROUTER_RAM = 192

# Nombres de plantillas en tu GNS3
ROUTER_TEMPLATE_NAME = "cisco-3600"
SWITCH_TEMPLATE_NAME = "Ethernet switch"
PC_TEMPLATE_NAME = "VPCS"

# --- 3. CONFIGURACIONES DE ARRANQUE (Switch Multicapa Real) ---
configs = {
    "SW_Dist": """!
hostname SW_Distribucion
!
ip routing
!
interface FastEthernet1/0
 description Hacia_PC0_VLAN10
 switchport mode access
 switchport access vlan 10
!
interface FastEthernet1/1
 description Hacia_PC1_VLAN10
 switchport mode access
 switchport access vlan 10
!
interface FastEthernet1/2
 description Hacia_PC2_VLAN20
 switchport mode access
 switchport access vlan 20
!
interface FastEthernet1/3
 description Hacia_PC3_VLAN20
 switchport mode access
 switchport access vlan 20
!
interface FastEthernet1/4
 description Troncal_Hacia_Switch_L2
 switchport mode access
 switchport access vlan 30
!
interface Vlan10
 ip address 192.168.10.1 255.255.255.0
 no shutdown
!
interface Vlan20
 ip address 192.168.20.1 255.255.255.0
 no shutdown
!
interface Vlan30
 ip address 192.168.30.1 255.255.255.0
 no shutdown
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
        "z": -1, # Z=-1 asegura que el color quede al fondo y no tape los equipos
        "svg": svg
    }
    requests.post(f"{BASE_URL}/projects/{project_id}/drawings", json=payload, auth=AUTH)

def create_node(project_id, name, template_id, x, y, node_type, symbol=None, is_multilayer=False):
    """Crea los nodos y asigna los iconos correctos sin borrar puertos"""
    payload = {
        "name": name,
        "node_type": node_type,
        "template_id": template_id,
        "x": x,
        "y": y,
        "compute_id": "local"
    }
    
    if symbol:
        payload["symbol"] = symbol

    if is_multilayer and node_type == "dynamips":
        payload["properties"] = {
            "platform": ROUTER_PLATFORM,
            "chassis": ROUTER_CHASSIS,
            "image": ROUTER_IMAGE,
            "ram": ROUTER_RAM,
            "slot0": "Leopard-2FE",  
            "slot1": "NM-16ESW" 
        }

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
    if resp.status_code not in [200, 201]:
        print(f"❌ Error conectando cables: {resp.text}")
        sys.exit(1)

def upload_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup-config.cfg", data=config_text, auth=AUTH)

def main():
    print(f"🔌 Conectando a GNS3 Local vía API REST (requests)...")

    # 1. Obtener IDs
    router_id = get_template_id(ROUTER_TEMPLATE_NAME)
    switch_id = get_template_id(SWITCH_TEMPLATE_NAME)
    pc_id = get_template_id(PC_TEMPLATE_NAME)
    print("✅ Plantillas verificadas.")

    # 2. Proyecto
    resp = requests.get(f"{BASE_URL}/projects", auth=AUTH)
    for p in resp.json():
        if p['name'] == PROJECT_NAME:
            print("♻️  Limpiando proyecto anterior (Espera 3s)...")
            requests.delete(f"{BASE_URL}/projects/{p['project_id']}", auth=AUTH)
            time.sleep(3)
            break
            
    resp = requests.post(f"{BASE_URL}/projects", json={"name": PROJECT_NAME}, auth=AUTH)
    project_id = resp.json()['project_id']
    print(f"🔨 Proyecto creado.")

    # 3. Dibujar las áreas de colores (NUEVO)
    print("🎨 Pintando las zonas de VLANs...")
    # VLAN 10 (Verde a la izquierda)
    create_drawing(project_id, -380, -200, 160, 220, "#2ECC71") 
    # VLAN 20 (Celeste a la derecha)
    create_drawing(project_id, 220, -200, 160, 220, "#87CEEB") 
    # VLAN 30 (Verde abajo)
    create_drawing(project_id, -230, 180, 460, 150, "#2ECC71")

    # 4. Crear Nodos
    print("📦 Desplegando equipos con iconos correctos...")
    nodes = {}
    
    # Switch Central (Multicapa - Icono Redondo)
    nodes['SW_Dist'] = create_node(project_id, "SW_Distribucion", router_id, 0, -100, "dynamips", 
                                   symbol=":/symbols/classic/multilayer_switch.svg", is_multilayer=True)
    
    # Switch L2 (Icono Cuadrado Clásico)
    nodes['SW_L2'] = create_node(project_id, "Switch_L2", switch_id, 0, 100, "ethernet_switch", 
                                 symbol=":/symbols/classic/ethernet_switch.svg")
    
    # PCs
    nodes['PC0'] = create_node(project_id, "PC0_VLAN10", pc_id, -300, -150, "vpcs")
    nodes['PC1'] = create_node(project_id, "PC1_VLAN10", pc_id, -300, -50, "vpcs")
    nodes['PC2'] = create_node(project_id, "PC2_VLAN20", pc_id, 300, -150, "vpcs")
    nodes['PC3'] = create_node(project_id, "PC3_VLAN20", pc_id, 300, -50, "vpcs")
    nodes['PC4'] = create_node(project_id, "PC4_VLAN30", pc_id, 150, 250, "vpcs")
    nodes['PC5'] = create_node(project_id, "PC5_VLAN30", pc_id, -150, 250, "vpcs")

    # 5. Conectar Cables 
    print("🔗 Conectando TODO el cableado...")
    
    # Conexiones VLAN 10
    create_link(project_id, nodes['SW_Dist'], 1, 0, nodes['PC0'], 0, 0) # Fa1/0
    create_link(project_id, nodes['SW_Dist'], 1, 1, nodes['PC1'], 0, 0) # Fa1/1
    
    # Conexiones VLAN 20
    create_link(project_id, nodes['SW_Dist'], 1, 2, nodes['PC2'], 0, 0) # Fa1/2
    create_link(project_id, nodes['SW_Dist'], 1, 3, nodes['PC3'], 0, 0) # Fa1/3
    
    # Enlace Troncal: SW_Dist (Fa1/4) a Switch_L2 (Port 0)
    create_link(project_id, nodes['SW_Dist'], 1, 4, nodes['SW_L2'], 0, 0)
    
    # Conexiones VLAN 30 (Desde Switch_L2 a PCs)
    create_link(project_id, nodes['SW_L2'], 0, 1, nodes['PC4'], 0, 0) # Port 1
    create_link(project_id, nodes['SW_L2'], 0, 2, nodes['PC5'], 0, 0) # Port 2

    # 6. Configs
    print("📝 Subiendo configuraciones de Inter-VLAN Routing...")
    upload_config(project_id, nodes['SW_Dist'], configs['SW_Dist'])

    # 7. Encender
    print("🚀 Encendiendo topología...")
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/start", json={}, auth=AUTH)

    print("\n✅ ¡FINALIZADO! Abre GNS3 para ver el resultado con las áreas delimitadas.")

if __name__ == "__main__":
    main()