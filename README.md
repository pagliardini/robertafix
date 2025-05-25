# roberta-fix

## Descripción general
Este proyecto proporciona una herramienta para el procesamiento por lotes de archivos de proyecto de Adobe Premiere Pro (.prproj), permitiendo a los usuarios extraer, editar y volver a empaquetar el contenido XML dentro de estos archivos.

## Características
- Crear copias de archivos .prproj
- Cambiar la extensión de archivo a .zip para su extracción
- Extraer el contenido XML para su edición
- Reemplazar texto dentro de los archivos XML mediante una interfaz gráfica de usuario (GUI)
- Recomprimir los archivos editados de nuevo al formato .prproj

## Instalación
1. Clona el repositorio:
   ```
   git clone <repository-url>
   ```
2. Navega al directorio del proyecto:
   ```
   cd python-prproj-editor
   ```
3. Instala las dependencias requeridas:
   ```
   pip install -r requirements.txt
   ```

## Uso
1. Coloca tus archivos .prproj en una carpeta designada.
2. Ejecuta la aplicación:
   ```
   python src/app.py
   ```
3. Sigue las indicaciones de la GUI para seleccionar archivos y realizar reemplazos de texto.

## Contribuciones
¡Las contribuciones son bienvenidas! Por favor, envía un pull request o abre un issue para cualquier mejora o corrección de errores.

## Licencia
Este proyecto está licenciado bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.