import os
import zipfile
import shutil
import sys
from tkinter import Tk, filedialog, messagebox, Label, Entry, Button, Frame, StringVar, Text, Scrollbar

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
    
    for root, _, files in os.walk(extract_dir):
        for file in files:
            # Procesar todos los archivos o usar una lista más amplia de extensiones
            xml_path = os.path.join(root, file)
            try:
                # Primero intentar leer como binario para detectar BOM
                with open(xml_path, "rb") as f:
                    binary_content = f.read()
                
                # Ver primeros bytes para debug
                log(f"📄 Analizando archivo: {file} - Primeros bytes: {binary_content[:20]}")
                
                # Detectar si parece texto o binario
                is_text = True
                try:
                    binary_content.decode('utf-8')
                except UnicodeDecodeError:
                    try:
                        binary_content.decode('latin1')
                    except UnicodeDecodeError:
                        is_text = False
                
                if not is_text and not file.endswith((".xml", ".proj", ".xmp", ".txt")):
                    log(f"⏭️ Omitiendo archivo binario: {file}")
                    continue
                
                # Convertir a texto con varias codificaciones
                encodings = ['utf-8-sig', 'utf-8', 'latin1', 'utf-16', 'utf-16-le', 'utf-16-be']
                content = None
                used_encoding = None
                
                for encoding in encodings:
                    try:
                        content = binary_content.decode(encoding)
                        used_encoding = encoding
                        log(f"📄 Archivo {file} decodificado con {encoding}")
                        if old_text in content:
                            log(f"🔎 ¡Coincidencia encontrada con codificación {encoding}!")
                        break
                    except UnicodeDecodeError:
                        continue
                
                if content is None:
                    log(f"⚠️ No se pudo leer el archivo {file} con ninguna codificación")
                    continue
                
                # Intentar varias formas del texto a buscar
                variations = [
                    old_text,
                    old_text.replace("\"", "'"),  # Comillas diferentes
                    old_text.replace(" ", ""),    # Sin espacios
                    old_text.replace("?>", "?>\r"), # Con retorno
                    old_text.replace("?>", "?>\n"), # Con nueva línea
                ]
                
                replacement_made = False
                for variant in variations:
                    if variant in content:
                        before_count = content.count(variant)
                        content = content.replace(variant, new_text)
                        after_count = content.count(new_text) - (content.count(new_text) - before_count)
                        replacements_count += before_count
                        log(f"🔄 Se encontraron {before_count} coincidencias de variante '{variant}' en {file}")
                        replacement_made = True
                
                if replacement_made:
                    # Guardar el archivo modificado
                    with open(xml_path, "w", encoding=used_encoding) as f:
                        f.write(content)
                
            except Exception as e:
                log(f"❌ Error al procesar {file}: {str(e)}")
    
    if replacements_count == 0:
        log(f"⚠️ No se encontraron coincidencias de '{old_text}' en ningún archivo")
    else:
        log(f"✅ Se realizaron {replacements_count} reemplazos en total")

    # Reempaquetar
    log(f"📦 Reempaquetando proyecto modificado...")
    mod_zip_path = os.path.join(output_dir, f"{name_wo_ext}_mod.zip")
    with zipfile.ZipFile(mod_zip_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
        for root, _, files in os.walk(extract_dir):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, extract_dir)
                new_zip.write(full_path, arcname)

    # Renombrar como .prproj
    final_project = os.path.join(output_dir, f"{name_wo_ext}_mod.prproj")
    os.rename(mod_zip_path, final_project)

    # Limpiar temporales
    os.remove(zip_path)
    shutil.rmtree(extract_dir)

    log(f"✅ Archivo procesado: {final_project}")

def extract_archive(zip_path, extract_dir):
    """Intenta extraer el archivo usando diferentes métodos."""
    try:
        # Primer intento: usando zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
        log("📦 Extracción realizada con zipfile")
        return True
    except zipfile.BadZipFile:
        # Segundo intento: usando unzip (si está disponible)
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
            
        # Tercer intento: usando 7z (si está disponible)
        log("⚠️ Error con unzip, intentando con 7z...")
        try:
            result = subprocess.run(['7z', 'x', zip_path, f'-o{extract_dir}'], 
                                   capture_output=True, text=True)
            if result.returncode == 0:
                log("📦 Extracción realizada con 7z")
                return True
        except Exception as e:
            log(f"❌ Error con 7z: {e}")
            
        # Si llegamos aquí, todos los métodos han fallado
        log("❌ Todos los métodos de extracción han fallado")
        return False

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

def main():
    global log_text
    
    root = Tk()
    root.title("Reemplazador de Texto en Proyectos Premiere")
    root.geometry("700x500")  # Mayor tamaño para acomodar el área de log
    
    # Variables
    old_text_var = StringVar(value=r"\\192.168.1.50\\")
    new_text_var = StringVar(value=r"\\192.168.1.100\\")
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
