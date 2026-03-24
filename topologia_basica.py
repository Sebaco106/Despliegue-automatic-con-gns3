import requests
import time
import sys
from requests.auth import HTTPBasicAuth

# --- 1. CONFIGURACIÓN DEL SERVIDOR parametros ---
GNS3_IP = "127.0.0.1"
GNS3_PORT = "3080"
BASE_URL = f"http://{GNS3_IP}:{GNS3_PORT}/v2"
PROJECT_NAME = "Topolog_basica"
AUTH = HTTPBasicAuth('admin', 'admin')

# HARDWARE
ROUTER_IMAGE = "c3660-a3jk9s-mz.124-15.T14.image"
ROUTER_PLATFORM = "c3600"
ROUTER_CHASSIS = "3660"
ROUTER_RAM = 192

# Nombres plantillas
ROUTER_TEMPLATE_NAME = "cisco-3600"
SWITCH_TEMPLATE_NAME = "Ethernet switch"
PC_TEMPLATE_NAME = "VPCS"

# --- 2. CONFIGURACIONES DE ARRANQUE ---
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
""",
    # IPs automáticas para las PCs (Formato VPCS: ip [direccion] [mascara] [gateway])
    "PC0": "ip 192.168.10.2 255.255.255.0 192.168.10.1\n",
    "PC1": "ip 192.168.10.3 255.255.255.0 192.168.10.1\n",
    "PC2": "ip 192.168.20.2 255.255.255.0 192.168.20.1\n",
    "PC3": "ip 192.168.20.3 255.255.255.0 192.168.20.1\n",
    "PC4": "ip 192.168.30.2 255.255.255.0 192.168.30.1\n",
    "PC5": "ip 192.168.30.3 255.255.255.0 192.168.30.1\n"
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

def create_node(project_id, name, template_id, x, y, node_type, symbol=None, is_multilayer=False):
    payload = {"name": name, "node_type": node_type, "template_id": template_id, "x": x, "y": y, "compute_id": "local"}
    if symbol: payload["symbol"] = symbol
    if is_multilayer and node_type == "dynamips":
        payload["properties"] = {
            "platform": ROUTER_PLATFORM, "chassis": ROUTER_CHASSIS, "image": ROUTER_IMAGE, "ram": ROUTER_RAM,
            "slot0": "Leopard-2FE", "slot1": "NM-16ESW" 
        }
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/nodes", json=payload, auth=AUTH)
    if resp.status_code not in [200, 201]:
        print(f"❌ Error creando {name}: {resp.text}")
        sys.exit(1)
    return resp.json()['node_id']

def create_link(project_id, node_a, adapter_a, port_a, node_b, adapter_b, port_b):
    payload = {"nodes": [{"node_id": node_a, "adapter_number": adapter_a, "port_number": port_a},
                         {"node_id": node_b, "adapter_number": adapter_b, "port_number": port_b}]}
    resp = requests.post(f"{BASE_URL}/projects/{project_id}/links", json=payload, auth=AUTH)
    if resp.status_code not in [200, 201]:
        print(f"❌ Error conectando cables: {resp.text}")
        sys.exit(1)

def upload_config(project_id, node_id, config_text):
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup-config.cfg", data=config_text, auth=AUTH)

def upload_vpcs_config(project_id, node_id, config_text):
    """Sube la configuración de red (IPs) específicamente a los nodos VPCS"""
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/{node_id}/files/startup.vpc", data=config_text, auth=AUTH)

# --- FLUJO PRINCIPAL ---
def main():
    # MENÚ INTERACTIVO
    print("\n" + "="*50)
    print("🚀 AUTOMATIZACIÓN DE RED GNS3 - TOPOLOGÍA BÁSICA")
    print("="*50)
    print("Seleccione el modo de despliegue:")
    print("1. Sin configuración (Solo despliega equipos y cables en blanco)")
    print("2. Con configuración total (Aplica Inter-VLAN Routing e IPs a PCs)")
    
    opcion = input("\nIngrese 1 o 2: ")
    if opcion not in ["1", "2"]:
        print("❌ Opción no válida. Cancelando ejecución.")
        sys.exit(1)

    print(f"\n🔌 Conectando a GNS3 Local vía API REST (requests)...")

    router_id = get_template_id(ROUTER_TEMPLATE_NAME)
    switch_id = get_template_id(SWITCH_TEMPLATE_NAME)
    pc_id = get_template_id(PC_TEMPLATE_NAME)
    print("✅ Plantillas verificadas.")

    # 2. Proyecto limpio
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
    print(f"🔨 Proyecto '{PROJECT_NAME}' creado exitosamente.")

    # 3. Dibujar las áreas de colores 
    print("🎨 Pintando las zonas de VLANs...")
    create_drawing(project_id, -380, -200, 160, 220, "#2ECC71") # VLAN 10
    create_drawing(project_id, 220, -200, 160, 220, "#87CEEB") # VLAN 20
    create_drawing(project_id, -230, 180, 460, 150, "#2ECC71") # VLAN 30

    # 4. Crear Nodos
    print("📦 Desplegando equipos con iconos correctos...")
    nodes = {}
    nodes['SW_Dist'] = create_node(project_id, "SW_Distribucion", router_id, 0, -100, "dynamips", symbol=":/symbols/classic/multilayer_switch.svg", is_multilayer=True)
    nodes['SW_L2'] = create_node(project_id, "Switch_L2", switch_id, 0, 100, "ethernet_switch", symbol=":/symbols/classic/ethernet_switch.svg")
    nodes['PC0'] = create_node(project_id, "PC0_VLAN10", pc_id, -300, -150, "vpcs")
    nodes['PC1'] = create_node(project_id, "PC1_VLAN10", pc_id, -300, -50, "vpcs")
    nodes['PC2'] = create_node(project_id, "PC2_VLAN20", pc_id, 300, -150, "vpcs")
    nodes['PC3'] = create_node(project_id, "PC3_VLAN20", pc_id, 300, -50, "vpcs")
    nodes['PC4'] = create_node(project_id, "PC4_VLAN30", pc_id, 150, 250, "vpcs")
    nodes['PC5'] = create_node(project_id, "PC5_VLAN30", pc_id, -150, 250, "vpcs")

    # 5. Conectar Cables 
    print("🔗 Conectando TODO el cableado...")
    create_link(project_id, nodes['SW_Dist'], 1, 0, nodes['PC0'], 0, 0)
    create_link(project_id, nodes['SW_Dist'], 1, 1, nodes['PC1'], 0, 0)
    create_link(project_id, nodes['SW_Dist'], 1, 2, nodes['PC2'], 0, 0)
    create_link(project_id, nodes['SW_Dist'], 1, 3, nodes['PC3'], 0, 0)
    create_link(project_id, nodes['SW_Dist'], 1, 4, nodes['SW_L2'], 0, 0)
    create_link(project_id, nodes['SW_L2'], 0, 1, nodes['PC4'], 0, 0)
    create_link(project_id, nodes['SW_L2'], 0, 2, nodes['PC5'], 0, 0)

    # 6. LÓGICA CONDICIONAL DE CONFIGURACIÓN
    if opcion == "2":
        print("📝 Opción 2 seleccionada: Inyectando configs de Inter-VLAN Routing e IPs en PCs...")
        upload_config(project_id, nodes['SW_Dist'], configs['SW_Dist'])
        upload_vpcs_config(project_id, nodes['PC0'], configs['PC0'])
        upload_vpcs_config(project_id, nodes['PC1'], configs['PC1'])
        upload_vpcs_config(project_id, nodes['PC2'], configs['PC2'])
        upload_vpcs_config(project_id, nodes['PC3'], configs['PC3'])
        upload_vpcs_config(project_id, nodes['PC4'], configs['PC4'])
        upload_vpcs_config(project_id, nodes['PC5'], configs['PC5'])
    else:
        print("⚠️  Opción 1 seleccionada: Desplegando equipos en blanco. Omitiendo inyección de código.")

    # 7. Encender
    print("🚀 Encendiendo topología...")
    requests.post(f"{BASE_URL}/projects/{project_id}/nodes/start", json={}, auth=AUTH)

    print("\n✅ ¡FINALIZADO! Abre GNS3 para ver tu laboratorio.")

if __name__ == "__main__":
    main()