import os
import zipfile
import shutil
import sys
from tkinter import Tk, filedialog, messagebox, Label, Entry, Button, Frame, StringVar, Text, Scrollbar
import subprocess
import json

# Variable global para el widget de log
log_text = None

def log(message):
    """Registra un mensaje tanto en la consola como en el widget de texto de la GUI."""
    print(message)  # Mantiene la salida en la consola
    
    if log_text:
        # Añadir texto y desplazar automáticamente
        log_text.config(state="normal")
        log_text.insert("end", message + "\n")
        log_text.see("end")  # Desplaza automáticamente al final
        log_text.config(state="disabled")
        log_text.update()  # Actualiza la GUI inmediatamente

def process_project(path, output_dir, old_text, new_text):
    base_name = os.path.basename(path)
    name_wo_ext = os.path.splitext(base_name)[0]

    # Copia de seguridad
    backup_path = os.path.join(output_dir, f"{name_wo_ext}_backup.prproj")
    shutil.copy(path, backup_path)
    log(f"📁 Creando copia de seguridad: {backup_path}")

    # Renombrar como ZIP y extraer
    zip_path = os.path.join(output_dir, f"{name_wo_ext}.zip")
    shutil.copy(path, zip_path)
    log(f"🔄 Preparando archivo para procesamiento: {zip_path}")

    extract_dir = os.path.join(output_dir, f"{name_wo_ext}_temp")
    os.makedirs(extract_dir, exist_ok=True)
    
    log(f"📦 Extrayendo contenido del proyecto...")
    extraction_success = extract_archive(zip_path, extract_dir)
    
    if not extraction_success:
        messagebox.showerror("Error", f"No se pudo extraer {base_name} con ninguno de los métodos disponibles.")
        log(f"❌ Error: No se pudo extraer {base_name}")
        return

    # Buscar y reemplazar dentro del XML
    replacements_count = 0
    log(f"🔍 Buscando '{old_text}' para reemplazar con '{new_text}'...")
    
    text_extensions = (".xml", ".xmp", ".prtl", ".prproj", ".txt", ".mlt", ".json", ".js", ".css", ".html")
    
    for root, _, files in os.walk(extract_dir):
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            xml_path = os.path.join(root, file)
            
            log(f"🔍 Examinando: {file}")
            
            try:
                # Detección binaria
                is_binary = False
                with open(xml_path, "rb") as f:
                    chunk = f.read(1024)
                    if b'\x00' in chunk or sum(1 for b in chunk if b < 32 and b not in (9, 10, 13)) > len(chunk) * 0.3:
                        is_binary = True
                        
                if is_binary and not file.lower().endswith(text_extensions):
                    log(f"⏭️ Omitiendo archivo binario: {file}")
                    continue
                
                # Leer contenido
                with open(xml_path, "rb") as f:
                    binary_content = f.read()
                
                encodings = ['utf-8', 'utf-8-sig', 'latin1', 'cp1252', 'utf-16-le', 'utf-16-be', 'ascii']
                content = None
                used_encoding = None
                
                for encoding in encodings:
                    try:
                        content = binary_content.decode(encoding)
                        used_encoding = encoding
                        log(f"📄 Archivo {file} decodificado con {encoding}")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    log(f"⚠️ No se pudo decodificar {file} - saltando")
                    continue
                
                # Variaciones del texto a buscar
                variations = [
                    old_text,
                    old_text.replace("\\", "\\\\"),
                    old_text.replace("\\", "/"),
                    old_text.replace("\\\\", "\\"),
                    old_text.replace("\"", "'"),
                    old_text.replace(" ", ""),
                    old_text.replace("?>", "?>\r"),
                    old_text.replace("?>", "?>\n"),
                ]
                
                replacement_made = False
                for variant in variations:
                    if variant in content:
                        before_count = content.count(variant)
                        content = content.replace(variant, new_text)
                        replacements_count += before_count
                        log(f"🔄 ¡ÉXITO! Se reemplazaron {before_count} coincidencias de '{variant}' en {file}")
                        replacement_made = True
                
                if replacement_made:
                    with open(xml_path, "w", encoding=used_encoding) as f:
                        f.write(content)
                    log(f"✅ Guardado archivo modificado: {file}")
                
            except Exception as e:
                log(f"❌ Error al procesar {file}: {str(e)}")
    
    if replacements_count == 0:
        log(f"⚠️ No se encontraron coincidencias de '{old_text}' en ningún archivo")
    else:
        log(f"✅ Se realizaron {replacements_count} reemplazos en total")

    # REEMPAQUETAR CON GZIP (MÉTODO QUE FUNCIONA)
    log(f"📦 Reempaquetando proyecto con GZIP...")
    
    mod_gzip_path = os.path.join(output_dir, f"{name_wo_ext}_mod.tar.gz")
    
    try:
        import tarfile
        
        # Crear archivo tar.gz
        with tarfile.open(mod_gzip_path, "w:gz") as tar:
            for root, dirs, files in os.walk(extract_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    arcname = os.path.relpath(full_path, extract_dir)
                    tar.add(full_path, arcname=arcname)
        
        log(f"✅ Archivo GZIP creado exitosamente: {mod_gzip_path}")
        
        # Renombrar como .prproj
        final_project = os.path.join(output_dir, f"{name_wo_ext}_mod.prproj")
        
        if os.path.exists(final_project):
            try:
                os.remove(final_project)
                log(f"🗑️ Eliminado archivo existente: {final_project}")
            except Exception as e:
                log(f"⚠️ No se pudo eliminar el archivo existente: {e}")
        
        try:
            os.rename(mod_gzip_path, final_project)
            log(f"✅ Archivo renombrado exitosamente a: {final_project}")
        except Exception as e:
            log(f"❌ Error al renombrar: {e}")
            try:
                shutil.copy2(mod_gzip_path, final_project)
                os.remove(mod_gzip_path)
                log("✅ Archivo copiado y original eliminado")
            except Exception as copy_error:
                log(f"❌ Error al copiar: {copy_error}")
                messagebox.showerror("Error", f"No se pudo renombrar/copiar el archivo: {e}")
                return False
        
        # Limpiar temporales
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(extract_dir):
            shutil.rmtree(extract_dir)
        
        log(f"✅ Archivo procesado exitosamente: {final_project}")
        messagebox.showinfo("Éxito", f"Proyecto procesado y guardado como:\n{final_project}")
        return True
        
    except Exception as e:
        log(f"❌ Error con compresión GZIP: {e}")
        messagebox.showerror("Error", f"No se pudo reempaquetar el proyecto: {e}")
        return False

def extract_archive(zip_path, extract_dir):
    """Intenta extraer el archivo usando diferentes métodos."""
    try:
        # Primer intento: usando zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        log("📦 Extracción realizada con zipfile")
        return True
    except zipfile.BadZipFile:
        # Detectar sistema operativo
        is_windows = os.name == 'nt'
        
        if not is_windows:
            # Segundo intento en Linux/Unix: usando unzip
            log("⚠️ Error con zipfile, intentando con unzip...")
            try:
                import subprocess
                result = subprocess.run(['unzip', zip_path, '-d', extract_dir], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log("📦 Extracción realizada con unzip")
                    return True
            except Exception as e:
                log(f"❌ Error con unzip: {e}")
        
        # Tercer intento: usando 7z (con rutas específicas para Windows)
        log("⚠️ Error con método anterior, intentando con 7z...")
        try:
            import subprocess
            
            # Posibles rutas de 7zip en Windows
            seven_zip_paths = [
                '7z',  # Por si está en el PATH
                r'C:\Program Files\7-Zip\7z.exe',
                r'C:\Program Files (x86)\7-Zip\7z.exe',
            ]
            
            # Encontrar la primera ruta que exista
            cmd = None
            for path in seven_zip_paths:
                if not is_windows or os.path.exists(path) or path == '7z':
                    cmd = path
                    break
            
            if cmd:
                result = subprocess.run([cmd, 'x', zip_path, f'-o{extract_dir}', '-y'], 
                                      capture_output=True, text=True)
                if result.returncode == 0:
                    log(f"📦 Extracción realizada with 7z ({cmd})")
                    return True
                else:
                    log(f"⚠️ 7z encontrado en {cmd} pero falló: {result.stderr}")
            else:
                log("⚠️ No se encontró instalación de 7-Zip")
                
        except Exception as e:
            log(f"❌ Error con 7z: {e}")
        
        # Último intento: usar patool si está disponible
        return extract_archive_with_patool(zip_path, extract_dir)

def extract_archive_with_patool(zip_path, extract_dir):
    """Extrae el archivo usando patool, que es más tolerante y soporta múltiples formatos."""
    try:
        import patoolib
        patoolib.extract_archive(zip_path, outdir=extract_dir)
        log("📦 Extracción realizada con patool")
        return True
    except Exception as e:
        log(f"❌ Error con patool: {e}")
        return False

def log_file_info(zip_path):
    """Registra información sobre el archivo para diagnóstico."""
    try:
        with open(f"{zip_path}_info.txt", "w") as f:
            file_size = os.path.getsize(zip_path)
            f.write(f"Tamaño: {file_size} bytes\n")
            
            # Leer primeros bytes para verificar firma de archivo
            with open(zip_path, "rb") as bin_f:
                header = bin_f.read(10).hex()
                f.write(f"Encabezado (hex): {header}\n")
        log(f"📝 Información del archivo guardada en {zip_path}_info.txt")
    except Exception as e:
        log(f"❌ Error al diagnosticar archivo: {e}")

def analyze_zip_structure(zip_path, label):
    """Analiza la estructura detallada de un archivo ZIP para comparación."""
    log(f"🔍 === ANÁLISIS DE {label} ===")
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            info_list = zip_ref.infolist()
            
            log(f"📊 Número total de archivos: {len(info_list)}")
            log(f"📊 Tamaño del archivo: {os.path.getsize(zip_path)} bytes")
            
            # Analizar cada archivo dentro del ZIP
            for i, info in enumerate(info_list):
                if i < 5:  # Solo mostrar los primeros 5 para no saturar el log
                    log(f"   📄 {info.filename}")
                    log(f"      Método compresión: {info.compress_type}")
                    log(f"      Tamaño original: {info.file_size}")
                    log(f"      Tamaño comprimido: {info.compress_size}")
                    log(f"      CRC32: {hex(info.CRC)}")
                    log(f"      Fecha modificación: {info.date_time}")
            
            if len(info_list) > 5:
                log(f"   ... y {len(info_list) - 5} archivos más")
                
            # Analizar métodos de compresión únicos
            compression_methods = set(info.compress_type for info in info_list)
            log(f"📊 Métodos de compresión encontrados: {compression_methods}")
            
            # Mapear números a nombres
            compression_names = {
                0: "Stored (sin compresión)",
                8: "Deflated (compresión estándar)",
                12: "BZIP2",
                14: "LZMA"
            }
            
            for method in compression_methods:
                name = compression_names.get(method, f"Desconocido ({method})")
                count = sum(1 for info in info_list if info.compress_type == method)
                log(f"   {name}: {count} archivos")
                
    except Exception as e:
        log(f"❌ Error analizando {label}: {e}")

def create_reference_zip_manually(extract_dir, reference_path):
    """Crea un ZIP de referencia usando diferentes métodos para comparar."""
    log("🔬 Creando ZIP de referencia con diferentes métodos...")
    
    methods_to_test = [
        (zipfile.ZIP_STORED, "SIN_COMPRESION"),
        (zipfile.ZIP_DEFLATED, "DEFLATED_DEFAULT"),
        # También podemos probar diferentes niveles de compresión si es necesario
    ]
    
    for compress_type, method_name in methods_to_test:
        test_zip_path = reference_path.replace(".zip", f"_TEST_{method_name}.zip")
        
        try:
            with zipfile.ZipFile(test_zip_path, 'w', compress_type) as test_zip:
                for root, _, files in os.walk(extract_dir):
                    for file in files:
                        full_path = os.path.join(root, file)
                        arcname = os.path.relpath(full_path, extract_dir)
                        test_zip.write(full_path, arcname)
            
            log(f"✅ Creado ZIP de prueba: {method_name}")
            analyze_zip_structure(test_zip_path, f"PRUEBA {method_name}")
            
        except Exception as e:
            log(f"❌ Error creando {method_name}: {e}")

def test_powershell_compression_levels():
    """Prueba diferentes niveles de compresión de PowerShell."""
    levels = ["Fastest", "Optimal", "NoCompression"]
    
    for level in levels:
        log(f"🧪 Probando nivel de compresión PowerShell: {level}")
        # Este código se integraría en el proceso principal
        return level  # Por ahora solo retorna para mostrar la estructura

def main():
    global log_text
    
    root = Tk()
    root.title("Reemplazador de Texto en Proyectos Premiere")
    root.geometry("700x500")  # Mayor tamaño para acomodar el área de log
    
    # Variables - VALORES MODIFICADOS
    old_text_var = StringVar(value="172.16.70.70")
    new_text_var = StringVar(value="172.16.7.250")
    folder_path = StringVar()
    
    # Layout
    main_frame = Frame(root, padx=20, pady=20)
    main_frame.pack(fill="both", expand=True)
    
    # Sección de entrada de datos
    input_frame = Frame(main_frame)
    input_frame.pack(fill="x", pady=10)
    
    Label(input_frame, text="Texto a reemplazar:").grid(row=0, column=0, sticky="w", pady=5)
    Entry(input_frame, textvariable=old_text_var, width=40).grid(row=0, column=1, pady=5, padx=5)
    
    Label(input_frame, text="Nuevo texto:").grid(row=1, column=0, sticky="w", pady=5)
    Entry(input_frame, textvariable=new_text_var, width=40).grid(row=1, column=1, pady=5, padx=5)
    
    Label(input_frame, text="Carpeta seleccionada:").grid(row=2, column=0, sticky="w", pady=5)
    Entry(input_frame, textvariable=folder_path, width=40, state="readonly").grid(row=2, column=1, pady=5, padx=5)
    
    # Botones
    button_frame = Frame(main_frame)
    button_frame.pack(fill="x", pady=10)
    
    Button(button_frame, text="Seleccionar carpeta", command=lambda: select_folder(folder_path)).pack(side="left", padx=10)
    Button(button_frame, text="Procesar archivos", command=lambda: process_files(folder_path, old_text_var, new_text_var)).pack(side="left", padx=10)
    Button(button_frame, text="Limpiar log", command=lambda: clear_log()).pack(side="right", padx=10)
    
    # Área de log
    log_frame = Frame(main_frame)
    log_frame.pack(fill="both", expand=True, pady=10)
    
    Label(log_frame, text="Log de operaciones:").pack(anchor="w")
    
    # Scrollbar para el log
    scrollbar = Scrollbar(log_frame)
    scrollbar.pack(side="right", fill="y")
    
    # Text widget para el log
    log_text = Text(log_frame, height=15, width=80, wrap="word", yscrollcommand=scrollbar.set)
    log_text.pack(fill="both", expand=True)
    log_text.config(state="disabled")  # Solo lectura
    
    scrollbar.config(command=log_text.yview)
    
    # Mensaje inicial
    log("📝 Aplicación iniciada. Selecciona una carpeta con archivos .prproj para comenzar.")
    
    root.mainloop()

def clear_log():
    """Limpia el área de log."""
    log_text.config(state="normal")
    log_text.delete(1.0, "end")
    log_text.config(state="disabled")
    log("📝 Log limpiado")

def select_folder(folder_path):
    """Selecciona una carpeta y actualiza la variable de ruta."""
    folder = filedialog.askdirectory(title="Selecciona la carpeta con archivos .prproj")
    if folder:
        folder_path.set(folder)
        log(f"📁 Carpeta seleccionada: {folder}")

def process_files(folder_path, old_text_var, new_text_var):
    """Procesa todos los archivos .prproj en la carpeta seleccionada."""
    folder = folder_path.get()
    old_text = old_text_var.get()
    new_text = new_text_var.get()
    
    if not folder:
        messagebox.showwarning("Error", "No se ha seleccionado ninguna carpeta.")
        log("❌ Error: No se ha seleccionado ninguna carpeta")
        return
        
    if not old_text or not new_text:
        messagebox.showwarning("Error", "Los campos de texto no pueden estar vacíos.")
        log("❌ Error: Los campos de texto no pueden estar vacíos")
        return
    
    prproj_files = [f for f in os.listdir(folder) if f.endswith(".prproj")]
    
    if not prproj_files:
        messagebox.showwarning("Sin archivos", "No se encontraron archivos .prproj en la carpeta seleccionada.")
        log("⚠️ No se encontraron archivos .prproj en la carpeta seleccionada")
        return
    
    log(f"🔍 Encontrados {len(prproj_files)} archivos .prproj para procesar")
    
    for file in prproj_files:
        log(f"🔄 Procesando archivo: {file}")
        full_path = os.path.join(folder, file)
        process_project(full_path, folder, old_text, new_text)
    
    messagebox.showinfo("Proceso completo", "Todos los proyectos fueron modificados y respaldados correctamente.")
    log("✅ Proceso completo. Todos los proyectos fueron modificados y respaldados.")

if __name__ == "__main__":
    main()
