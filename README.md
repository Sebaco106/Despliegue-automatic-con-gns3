# 🚀 Despliegue Automatizado de Topologías de Red con GNS3

Este proyecto aplica el paradigma de **Infraestructura como Código (IaC)** para automatizar la creación, cableado y configuración lógica de laboratorios de red en el emulador GNS3. Utiliza Python y la API REST nativa de GNS3 para desplegar escenarios complejos en cuestión de segundos, eliminando errores humanos de configuración manual.

Este proyecto fue desarrollado como parte de las Prácticas Pre-Profesionales en la Facultad de Ingeniería en Informática y Sistemas.

## 📋 Características Principales
- **Despliegue Instantáneo:** Creación de nodos (Routers Cisco, Switches Multicapa y VPCS) y cableado estructural de forma 100% automatizada.
- **Inyección de Configuraciones:** Carga automática de `startup-config` para Routers (OSPF, Inter-VLAN Routing) y asignación estática de IPs para PCs.
- **Delimitación Visual:** Inyección de código SVG para dibujar fondos de colores que delimitan las áreas de las VLANs directamente en el lienzo de GNS3.
- **Menú Interactivo:** Los scripts permiten al usuario elegir entre desplegar la topología en blanco o con configuraciones completas de conectividad.
- **Manejo de Errores:** Rutinas robustas de limpieza y cierre forzado de proyectos previos (Status 409) para evitar corrupción de archivos.

## 🛠️ Requisitos Previos

Para ejecutar estos scripts en tu entorno local, necesitas cumplir con los siguientes requisitos:

### Software
1. **GNS3** (v2.2.55 recomendado) instalado junto con la **GNS3 VM** en VMware Workstation.
2. **Python 3.12.2 instalado y agregado al PATH del sistema.
3. El puerto `3080` de GNS3 debe estar habilitado para escuchar peticiones de la API REST local (`127.0.0.1`).

### Dependencias de Python
El proyecto utiliza la librería estándar `requests` para consumir la API. Instálala ejecutando:
```bash
pip install requests
