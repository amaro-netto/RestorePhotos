import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageEnhance, ImageDraw, ImageFont, ExifTags
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import os
import threading
import json
from datetime import datetime
import cv2
import numpy as np
import time
from pathlib import Path

# Definindo as cores e fontes conforme as especificações
COLOR_BACKGROUND = "#2c3e50"
COLOR_FRAME = "#34495e"
COLOR_TEXT = "#ffffff"
COLOR_BUTTON_BROWSE = "#3498db"
COLOR_BUTTON_ALTER = "#9b59b6"
COLOR_BUTTON_PROCESS = "#e74c3c"
COLOR_BUTTON_DOWNLOAD = "#27ae60"
COLOR_BUTTON_DEMO_VIDEO = "#f39c12" # Nova cor para o botão de vídeo demonstrativo

FONT_TITLE = ("Arial", 20, "bold")
FONT_SUBTITLE = ("Arial", 12)
FONT_LABEL = ("Arial", 10, "bold")
FONT_TEXT = ("Arial", 10)
FONT_BUTTON = ("Arial", 11, "bold") # Ajuste para um tamanho bom nos botões

# Constantes para processamento
TARGET_RESOLUTION = (1920, 1080)
DEFAULT_WATERMARK_TEXT = "@tioadaotvnafesta" # Manter como fallback ou para referência
IMAGES_PER_LOT = 50
DEMO_VIDEO_DURATION_SECONDS = 5 # Duração do vídeo demonstrativo

# --- Classe Principal da Aplicação ---
class PhotoProcessorApp:
    def __init__(self, master):
        self.master = master
        master.title("CodeBuddy - Aplicador de Marca d'Água")
        master.geometry("800x600")
        master.resizable(False, False) # Janela não redimensionável
        master.configure(bg=COLOR_BACKGROUND)

        # Variáveis de controle
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.home() / "FT TRATADAS 2025")) # Pasta de destino padrão
        self.watermark_image_path = tk.StringVar() # Caminho para a imagem PNG da marca d'água
        self.image_count = tk.IntVar(value=0)
        self.apply_watermark = tk.BooleanVar(value=True) # Opção para aplicar ou não a marca d'água
        self.processing_status = tk.StringVar(value="Aguardando...")
        self.processed_count = tk.IntVar(value=0)
        self.total_to_process = tk.IntVar(value=0)
        self.first_processed_image_path = None # Para o vídeo demonstrativo

        self.geolocator = Nominatim(user_agent="photo_watermark_app") # Inicializa o geocodificador

        # Referências para os widgets que terão seu estado modificado
        self.btn_browse = None
        self.btn_browse_watermark = None # Novo botão para a marca d'água
        self.chk_apply_watermark = None 
        self.btn_alter_output = None
        self.btn_process = None
        self.btn_download = None
        self.btn_generate_demo_video = None # Novo botão para o vídeo demonstrativo

        self._create_widgets()

    def _create_widgets(self):
        """Cria e organiza todos os widgets da interface gráfica."""

        # Título principal
        tk.Label(self.master, text="Aplicador de Marca d'Água em Fotos", bg=COLOR_BACKGROUND, fg=COLOR_TEXT,
                 font=FONT_TITLE).pack(pady=10)

        # --- Seções da Interface (LabelFrames) ---

        # Passo 1: Seleção de Pasta de Fotos
        self.frame_step1 = self._create_labeled_frame("PASSO 1: Selecione a Pasta de Origem das Fotos")
        self.frame_step1.pack(fill="x", padx=20, pady=5)
        self._setup_step1(self.frame_step1)

        # Passo 2: Configurações (Marca d'Água e Pasta de Destino)
        self.frame_step2 = self._create_labeled_frame("PASSO 2: Configure a Marca d'Água e Destino")
        self.frame_step2.pack(fill="x", padx=20, pady=5)
        self._setup_step2(self.frame_step2)

        # Passo 3: Processamento
        self.frame_step3 = self._create_labeled_frame("PASSO 3: Iniciar Processamento")
        self.frame_step3.pack(fill="x", padx=20, pady=5)
        self._setup_step3(self.frame_step3)

        # Passo 4: Acesso aos Resultados
        self.frame_step4 = self._create_labeled_frame("PASSO 4: Resultados Finais")
        self.frame_step4.pack(fill="x", padx=20, pady=5)
        self._setup_step4(self.frame_step4)

        # Barra de progresso e status global
        self.progressbar = ttk.Progressbar(self.master, mode="determinate", length=760)
        self.progressbar.pack(pady=10)

        tk.Label(self.master, textvariable=self.processing_status, bg=COLOR_BACKGROUND, fg=COLOR_TEXT,
                 font=FONT_TEXT).pack(pady=(0, 5))

    def _create_labeled_frame(self, text):
        """Cria um LabelFrame com estilo padrão."""
        return tk.LabelFrame(self.master, text=text, bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_SUBTITLE,
                             padx=10, pady=10, relief="solid", bd=1)

    def _setup_step1(self, parent_frame):
        """Configura os widgets para o Passo 1 (Seleção de Pasta de Fotos)."""
        frame_content = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_content.pack(fill="x")

        tk.Label(frame_content, text="Pasta de Entrada:", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))

        entry_folder = tk.Entry(frame_content, textvariable=self.input_folder, width=60, state="readonly", font=FONT_TEXT)
        entry_folder.pack(side="left", fill="x", expand=True)

        self.btn_browse = tk.Button(frame_content, text="Procurar", command=self._browse_photos_folder,
                               bg=COLOR_BUTTON_BROWSE, fg=COLOR_TEXT, font=FONT_BUTTON,
                               relief="raised", bd=2, highlightbackground=COLOR_BUTTON_BROWSE)
        self.btn_browse.pack(side="left", padx=10)

        tk.Label(parent_frame, textvariable=self.image_count, bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_TEXT).pack(anchor="w", pady=5)
        tk.Label(parent_frame, text="(Formatos aceitos: JPG, JPEG, PNG, BMP, TIFF)", bg=COLOR_FRAME, fg="#cccccc", font=("Arial", 8)).pack(anchor="w", pady=(0, 5))

    def _setup_step2(self, parent_frame):
        """Configura os widgets para o Passo 2 (Marca d'Água e Pasta de Destino)."""
        frame_content = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_content.pack(fill="x")

        # Opção de aplicar marca d'água (checkbox)
        self.chk_apply_watermark = tk.Checkbutton(frame_content, text="Aplicar Marca d'Água", variable=self.apply_watermark,
                                                 bg=COLOR_FRAME, fg=COLOR_TEXT, selectcolor=COLOR_FRAME,
                                                 font=FONT_LABEL)
        self.chk_apply_watermark.pack(anchor="w", pady=5)

        # Seleção da imagem da marca d'água (PNG)
        frame_watermark = tk.Frame(frame_content, bg=COLOR_FRAME)
        frame_watermark.pack(fill="x", pady=5)

        tk.Label(frame_watermark, text="Marca d'Água (PNG):", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))
        entry_watermark = tk.Entry(frame_watermark, textvariable=self.watermark_image_path, width=50, state="readonly", font=FONT_TEXT)
        entry_watermark.pack(side="left", fill="x", expand=True)
        self.btn_browse_watermark = tk.Button(frame_watermark, text="Procurar PNG", command=self._browse_watermark_file,
                                               bg=COLOR_BUTTON_BROWSE, fg=COLOR_TEXT, font=FONT_BUTTON,
                                               relief="raised", bd=2, highlightbackground=COLOR_BUTTON_BROWSE)
        self.btn_browse_watermark.pack(side="left", padx=10)

        # Pasta de destino
        frame_output = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_output.pack(fill="x", pady=5)

        tk.Label(frame_output, text="Pasta de Destino:", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))

        entry_output_folder = tk.Entry(frame_output, textvariable=self.output_folder, width=60, font=FONT_TEXT)
        entry_output_folder.pack(side="left", fill="x", expand=True)

        self.btn_alter_output = tk.Button(frame_output, text="Alterar", command=self._alter_output_folder,
                                      bg=COLOR_BUTTON_ALTER, fg=COLOR_TEXT, font=FONT_BUTTON,
                                      relief="raised", bd=2, highlightbackground=COLOR_BUTTON_ALTER)
        self.btn_alter_output.pack(side="left", padx=10)

    def _setup_step3(self, parent_frame):
        """Configura os widgets para o Passo 3 (Iniciar Processamento)."""
        self.btn_process = tk.Button(parent_frame, text="APLICAR MARCA D'ÁGUA AGORA", command=self._start_processing_thread,
                                bg=COLOR_BUTTON_PROCESS, fg=COLOR_TEXT, font=FONT_BUTTON,
                                relief="raised", bd=2, highlightbackground=COLOR_BUTTON_PROCESS)
        self.btn_process.pack(pady=10)

    def _setup_step4(self, parent_frame):
        """Configura os widgets para o Passo 4 (Resultados Finais)."""
        btn_frame = tk.Frame(parent_frame, bg=COLOR_FRAME)
        btn_frame.pack(pady=10)

        self.btn_download = tk.Button(btn_frame, text="ABRIR PASTA TRATADAS", command=self._open_output_folder,
                                 bg=COLOR_BUTTON_DOWNLOAD, fg=COLOR_TEXT, font=FONT_BUTTON,
                                 relief="raised", bd=2, highlightbackground=COLOR_BUTTON_DOWNLOAD,
                                 state="disabled") # Desabilitado até o fim do processamento
        self.btn_download.pack(side="left", padx=10)

        self.btn_generate_demo_video = tk.Button(btn_frame, text="GERAR VÍDEO DEMONSTRATIVO", command=self._generate_demo_video,
                                            bg=COLOR_BUTTON_DEMO_VIDEO, fg=COLOR_TEXT, font=FONT_BUTTON,
                                            relief="raised", bd=2, highlightbackground=COLOR_BUTTON_DEMO_VIDEO,
                                            state="disabled") # Desabilitado até o processamento
        self.btn_generate_demo_video.pack(side="left", padx=10)
        

    def _browse_photos_folder(self):
        """Abre uma caixa de diálogo para selecionar a pasta de entrada das fotos e conta as imagens."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_folder.set(folder_selected)
            self._count_images_in_folder(folder_selected)
        else:
            self.input_folder.set("")
            self.image_count.set(0)

    def _browse_watermark_file(self):
        """Abre uma caixa de diálogo para selecionar o arquivo PNG da marca d'água."""
        file_selected = filedialog.askopenfilename(filetypes=[("PNG files", "*.png")])
        if file_selected:
            self.watermark_image_path.set(file_selected)
        else:
            self.watermark_image_path.set("")

    def _count_images_in_folder(self, folder_path):
        """Conta o número de imagens suportadas na pasta."""
        count = 0
        supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        for root, _, files in os.walk(folder_path):
            for file in files:
                if file.lower().endswith(supported_formats):
                    count += 1
        self.image_count.set(f"{count} imagens encontradas")
        self.total_to_process.set(count) # Define o total para a barra de progresso

    def _alter_output_folder(self):
        """Abre uma caixa de diálogo para selecionar a pasta de destino."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.output_folder.set(folder_selected)

    def _start_processing_thread(self):
        """Inicia o processamento em uma nova thread para não travar a UI."""
        input_path = self.input_folder.get()
        output_path = self.output_folder.get()
        watermark_path = self.watermark_image_path.get()

        if not input_path or not os.path.isdir(input_path):
            messagebox.showwarning("Erro", "Por favor, selecione uma pasta de entrada válida para as fotos.")
            return
        
        if self.apply_watermark.get() and (not watermark_path or not os.path.isfile(watermark_path)):
            messagebox.showwarning("Erro", "Por favor, selecione um arquivo PNG válido para a marca d'água ou desative a opção.")
            return

        # Cria a pasta de saída se não existir
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        if not os.access(output_path, os.W_OK):
             messagebox.showwarning("Erro", "Não foi possível escrever na pasta de destino selecionada. Por favor, escolha outra.")
             return

        # Desabilita botões para evitar cliques múltiplos
        self.btn_process.config(state="disabled")
        self.btn_browse.config(state="disabled")
        self.btn_browse_watermark.config(state="disabled")
        self.chk_apply_watermark.config(state="disabled") 
        self.btn_alter_output.config(state="disabled")
        self.btn_download.config(state="disabled")
        self.btn_generate_demo_video.config(state="disabled")


        self.processing_status.set("Preparando para aplicar marca d'água...")
        self.progressbar.config(mode="indeterminate")
        self.progressbar.start()
        self.processed_count.set(0) # Zera contador de processados
        self.first_processed_image_path = None # Reseta o caminho da primeira imagem processada

        # Inicia a thread de processamento
        process_thread = threading.Thread(target=self._process_photos)
        process_thread.start()

    def _process_photos(self):
        """Lógica principal de processamento das fotos (redimensionamento e aplicação de marca d'água)."""
        input_dir = Path(self.input_folder.get())
        output_base_dir = Path(self.output_folder.get())
        watermark_path = self.watermark_image_path.get()
        
        # Define a pasta base "FT TRATADAS 2025" dentro da pasta de destino
        processed_base_dir = output_base_dir / "FT TRATADAS 2025"
        processed_base_dir.mkdir(parents=True, exist_ok=True) # Garante que a pasta base exista

        image_files = []
        supported_formats = (".jpg", ".jpeg", ".png", ".bmp", ".tiff")
        for root, _, files in os.walk(input_dir):
            for file in files:
                if file.lower().endswith(supported_formats):
                    image_files.append(Path(root) / file)
        
        self.total_to_process.set(len(image_files))
        
        lot_number = 1
        current_lot_count = 0
        current_lot_dir = processed_base_dir / f"Lote_{lot_number:03d}"
        current_lot_dir.mkdir(exist_ok=True)

        for i, image_path in enumerate(image_files):
            if current_lot_count >= IMAGES_PER_LOT:
                lot_number += 1
                current_lot_count = 0
                current_lot_dir = processed_base_dir / f"Lote_{lot_number:03d}"
                current_lot_dir.mkdir(exist_ok=True)

            self.processing_status.set(f"Processando {i + 1}/{len(image_files)}: {image_path.name}")
            self.progressbar.config(mode="determinate", maximum=len(image_files), value=i)
            self.master.update_idletasks() # Atualiza a UI imediatamente

            try:
                # 1. Carregamento da imagem
                img = Image.open(image_path).convert("RGB")
                original_width, original_height = img.size
                
                # 2. Redimensionamento e Corte para preencher Full HD
                # Calcula os fatores de escala para largura e altura
                scale_width = TARGET_RESOLUTION[0] / original_width
                scale_height = TARGET_RESOLUTION[1] / original_height
                
                # Escolhe o maior fator de escala para que a imagem COBRIR a resolução alvo
                scale_factor = max(scale_width, scale_height)
                
                # Calcula as novas dimensões da imagem após o escalonamento
                img_scaled_width = int(original_width * scale_factor)
                img_scaled_height = int(original_height * scale_factor)
                
                # Redimensiona a imagem para as dimensões escaladas (usando LANCZOS para alta qualidade)
                img_resized = img.resize((img_scaled_width, img_scaled_height), Image.LANCZOS)
                
                # Calcula as coordenadas para cortar a imagem no centro para o tamanho alvo
                left = (img_scaled_width - TARGET_RESOLUTION[0]) / 2
                top = (img_scaled_height - TARGET_RESOLUTION[1]) / 2
                right = (img_scaled_width + TARGET_RESOLUTION[0]) / 2
                bottom = (img_scaled_height + TARGET_RESOLUTION[1]) / 2
                
                # Realiza o corte
                processed_img_pil = img_resized.crop((left, top, right, bottom))

                # 3. Extração de Metadados
                metadata = self._extract_metadata(image_path)

                # 4. Aplicação de Marca d'água (AGORA OPCIONAL E COM IMAGEM PNG)
                if self.apply_watermark.get() and watermark_path:
                    processed_img_pil = self._apply_image_watermark(processed_img_pil, watermark_path)

                # 5. Organização de Arquivos e Nomenclatura
                base_name = image_path.stem # Nome do arquivo original sem extensão
                processed_name_prefix = f"{i + 1:03d}-{current_lot_count + 1:02d}"

                # --- SANITIZAÇÃO DA STRING DE LOCALIZAÇÃO PARA O NOME DO ARQUIVO ---
                location_for_filename = metadata["exif_data"]["location"]["city"]
                if location_for_filename == "N/A":
                    location_str = "SemLocal" # Substitui "N/A" por "SemLocal" no nome do arquivo para evitar '\'
                else:
                    # Remove caracteres inválidos do nome do arquivo (ex: \ / : * ? " < > |)
                    # e substitui por um traço ou remove.
                    # Adiciona espaços e hífens como caracteres permitidos, além de alfanuméricos
                    location_str = ''.join(c if c.isalnum() or c in [' ', '-'] else '_' for c in location_for_filename)
                    location_str = location_str.strip() # Remove espaços extras no início/fim
                    if not location_str: # Se ficar vazio depois da sanitização, usa "SemLocal"
                        location_str = "SemLocal"
                # --- FIM DA SANITIZAÇÃO ---

                # --- TRATAMENTO ROBUSTO DE DATA PARA O NOME DO ARQUIVO ---
                date_str = "SemData" # Fallback padrão
                exif_datetime_str = metadata["exif_data"]["datetime"]
                
                if exif_datetime_str != "N/A":
                    try:
                        # Tenta converter a data EXIF (já em ISO format)
                        date_obj = datetime.fromisoformat(exif_datetime_str)
                        date_str = date_obj.strftime("%d%m%Y")
                    except ValueError as e:
                        print(f"Aviso: Formato de data EXIF inesperado para {image_path.name} ({exif_datetime_str}): {e}. Tentando data de modificação do arquivo.")
                        # Se falhar, tenta usar a data de modificação
                        try:
                            modification_timestamp = image_path.stat().st_mtime
                            date_obj = datetime.fromtimestamp(modification_timestamp)
                            date_str = date_obj.strftime("%d%m%Y")
                        except Exception as date_error:
                            print(f"Aviso: Não foi possível obter a data de modificação do arquivo {image_path.name}: {date_error}")
                            # Se tudo falhar, mantém "SemData"
                else:
                    # Se a data EXIF já era N/A, tenta direto a data de modificação do arquivo
                    try:
                        modification_timestamp = image_path.stat().st_mtime
                        date_obj = datetime.fromtimestamp(modification_timestamp)
                        date_str = date_obj.strftime("%d%m%Y")
                    except Exception as date_error:
                        print(f"Aviso: Não foi possível obter a data de modificação do arquivo {image_path.name}: {date_error}")
                        # Se tudo falhar, mantém "SemData"
                # --- FIM DO TRATAMENTO DE DATA ---
                
                final_filename_stem = f"{processed_name_prefix} - {location_str} - {date_str} - {base_name}"
                
                # Salva a imagem processada
                processed_image_path = current_lot_dir / f"{final_filename_stem}.jpg"
                processed_img_pil.save(processed_image_path, "JPEG", quality=95, optimize=True)

                # Armazena o caminho da primeira imagem processada para o vídeo demonstrativo
                if self.first_processed_image_path is None:
                    self.first_processed_image_path = processed_image_path

                # Salva os metadados
                metadata_path = current_lot_dir / f"{final_filename_stem}_metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)
                
                current_lot_count += 1

            except Exception as e:
                self.processing_status.set(f"Erro ao processar {image_path.name}: {e}")
                print(f"Erro ao processar {image_path.name}: {e}") # Loga o erro no console
                continue # Continua para a próxima foto mesmo com erro

            self.processed_count.set(self.processed_count.get() + 1)

        self._processing_complete()

    def _apply_image_watermark(self, base_image_pil, watermark_image_path):
        """
        Aplica uma imagem PNG como marca d'água na imagem base.
        A marca d'água será redimensionada para 20% da largura da imagem base
        e posicionada no canto inferior direito.
        """
        try:
            watermark = Image.open(watermark_image_path)
            
            # Redimensiona a marca d'água para 20% da largura da imagem base, mantendo proporção
            base_width, base_height = base_image_pil.size
            watermark_width, watermark_height = watermark.size
            
            target_watermark_width = int(base_width * 0.20) # 20% da largura da imagem base
            
            # Calcula a nova altura mantendo a proporção
            if watermark_width > 0: # Evita divisão por zero
                watermark_ratio = watermark_height / watermark_width
                target_watermark_height = int(target_watermark_width * watermark_ratio)
            else:
                target_watermark_height = watermark_height # Mantém a altura se a largura for zero, embora improvável

            watermark = watermark.resize((target_watermark_width, target_watermark_height), Image.LANCZOS)

            # Garante que a marca d'água tenha canal alfa para transparência
            if watermark.mode != 'RGBA':
                watermark = watermark.convert('RGBA')

            # Posição: canto inferior direito com padding
            padding = 20
            x = base_width - watermark.width - padding
            y = base_height - watermark.height - padding

            # Cria uma imagem temporária para colar a marca d'água com transparência
            temp_image = Image.new('RGBA', base_image_pil.size, (0, 0, 0, 0))
            temp_image.paste(watermark, (x, y), watermark)
            
            # Combina a imagem base com a marca d'água
            final_image = Image.alpha_composite(base_image_pil.convert('RGBA'), temp_image)
            return final_image.convert('RGB') # Converte de volta para RGB para salvar como JPG

        except Exception as e:
            print(f"Erro ao aplicar marca d'água de imagem: {e}")
            messagebox.showwarning("Erro na Marca d'Água", f"Não foi possível aplicar a marca d'água da imagem. Verifique o arquivo PNG.\nErro: {e}")
            return base_image_pil # Retorna a imagem original se houver erro

    def _extract_metadata(self, image_path):
        """Extrai metadados EXIF, GPS e faz geocoding."""
        metadata = {
            "original_file": str(image_path),
            "processed_date": datetime.now().isoformat(),
            "exif_data": {
                "datetime": "N/A", # Inicializa como N/A
                "location": {
                    "city": "N/A",
                    "state": "N/A",
                    "country": "N/A",
                    "postcode": "N/A",
                    "coordinates": []
                },
                "camera_info": "N/A"
            }
        }

        try:
            with Image.open(image_path) as img:
                exif_data = img._getexif()
                if exif_data:
                    exif = {
                        ExifTags.TAGS[k]: v
                        for k, v in exif_data.items()
                        if k in ExifTags.TAGS
                    }

                    # Tenta extrair e formatar a data EXIF para ISO format
                    date_found = False
                    if "DateTimeOriginal" in exif:
                        try:
                            metadata["exif_data"]["datetime"] = datetime.strptime(exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S").isoformat()
                            date_found = True
                        except ValueError:
                            pass
                    
                    if not date_found and "DateTime" in exif:
                        try:
                            metadata["exif_data"]["datetime"] = datetime.strptime(exif["DateTime"], "%Y:%m:%d %H:%M:%S").isoformat()
                            date_found = True
                        except ValueError:
                            pass

                    # Informações da Câmera
                    if "Make" in exif and "Model" in exif:
                        metadata["exif_data"]["camera_info"] = f"{exif['Make']} {exif['Model']}"
                    elif "Model" in exif:
                        metadata["exif_data"]["camera_info"] = exif["Model"]

                    # GPS
                    if "GPSInfo" in exif:
                        gps_info = exif["GPSInfo"]
                        lat = self._get_gps_coordinate(gps_info, "GPSLatitude")
                        lon = self._get_gps_coordinate(gps_info, "GPSLongitude")
                        lat_ref = gps_info.get(1, 'N')
                        lon_ref = gps_info.get(3, 'E')

                        if lat and lon:
                            decimal_lat = self._to_degrees(lat)
                            decimal_lon = self._to_degrees(lon)

                            if lat_ref != 'N':
                                decimal_lat = -decimal_lat
                            if lon_ref != 'E':
                                decimal_lon = -decimal_lon
                                
                            metadata["exif_data"]["location"]["coordinates"] = [decimal_lat, decimal_lon]

                            # Geocoding reverso
                            try:
                                time.sleep(1) # Rate limiting para API Nominatim
                                location = self.geolocator.reverse((decimal_lat, decimal_lon), language="pt-BR")
                                if location and location.address:
                                    address_details = location.raw.get('address', {})
                                    metadata["exif_data"]["location"]["city"] = address_details.get("city", address_details.get("town", address_details.get("village", "N/A")))
                                    metadata["exif_data"]["location"]["state"] = address_details.get("state", "N/A")
                                    metadata["exif_data"]["location"]["country"] = address_details.get("country", "N/A")
                                    metadata["exif_data"]["location"]["postcode"] = address_details.get("postcode", "N/A")

                                    # Detecção de Manaus
                                    if metadata["exif_data"]["location"]["city"] and "manaus" in metadata["exif_data"]["location"]["city"].lower():
                                        metadata["exif_data"]["location"]["city"] = "Manaus" # Padroniza para "Manaus"
                            except (GeocoderTimedOut, GeocoderServiceError) as geocoding_err:
                                print(f"Erro no geocoding para {image_path.name}: {geocoding_err}")
                                metadata["exif_data"]["location"]["city"] = "SemLocal" # Define como 'SemLocal' em caso de erro

        except Exception as e:
            print(f"Erro geral ao extrair metadados ou abrir {image_path.name}: {e}")

        return metadata

    def _get_gps_coordinate(self, gps_info, key):
        """Ajuda a extrair coordenadas GPS de um dicionário EXIF."""
        if key in ExifTags.GPSTAGS:
            tag = ExifTags.GPSTAGS[key]
            if tag in gps_info:
                return gps_info[tag]
        return None

    def _to_degrees(self, value):
        """Converte as coordenadas GPS (DMS) para graus decimais."""
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)

    def _processing_complete(self):
        """Chamado quando o processamento é concluído."""
        self.progressbar.stop()
        self.progressbar.config(mode="determinate", value=self.total_to_process.get())
        self.processing_status.set(f"Processamento Concluído! {self.processed_count.get()} fotos processadas.")
        
        # Habilita o botão de download e o de vídeo demonstrativo
        self.btn_download.config(state="normal")
        if self.first_processed_image_path: # Só habilita se alguma imagem foi processada
            self.btn_generate_demo_video.config(state="normal")
        
        # Habilita novamente os botões de controle de UI
        self.btn_process.config(state="normal")
        self.btn_browse.config(state="normal")
        self.btn_browse_watermark.config(state="normal")
        self.chk_apply_watermark.config(state="normal") 
        self.btn_alter_output.config(state="normal")

        # Exibe o popup de confirmação
        messagebox.showinfo("Sucesso!", "Todas as fotos foram processadas e organizadas com sucesso!")

    def _open_output_folder(self):
        """Abre a pasta de destino no explorador de arquivos do sistema."""
        output_path = self.output_folder.get()
        if os.path.exists(output_path):
            try:
                # Dependendo do SO, o comando para abrir a pasta é diferente
                if os.name == 'nt':  # Windows
                    os.startfile(output_path)
                elif os.uname().sysname == 'Darwin':  # macOS
                    os.system(f'open "{output_path}"')
                else:  # Linux
                    os.system(f'xdg-open "{output_path}"')
            except Exception as e:
                messagebox.showerror("Erro", f"Não foi possível abrir a pasta:\n{e}")
        else:
            messagebox.showwarning("Aviso", "A pasta de destino não existe.")

    def _generate_demo_video(self):
        """Gera um vídeo demonstrativo da aplicação da marca d'água."""
        if not self.first_processed_image_path or not self.first_processed_image_path.exists():
            messagebox.showwarning("Aviso", "Nenhuma imagem processada disponível para gerar o vídeo demonstrativo. Por favor, processe algumas fotos primeiro.")
            return
        
        output_dir = self.output_folder.get()
        demo_video_path = Path(output_dir) / "FT TRATADAS 2025" / "video_demonstrativo_marca_dagua.mp4"

        try:
            # Carrega a primeira imagem processada
            img_pil = Image.open(self.first_processed_image_path)
            
            width, height = img_pil.size
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # Codec para MP4
            out = cv2.VideoWriter(str(demo_video_path), fourcc, VIDEO_FPS, (width, height))

            if not out.isOpened():
                messagebox.showerror("Erro de Vídeo", "Não foi possível criar o arquivo de vídeo. Verifique as permissões ou o codec.")
                return

            # Converte a imagem PIL para formato OpenCV (BGR)
            opencv_image = np.array(img_pil) 
            opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2BGR)

            # Adiciona frames estáticos da imagem processada
            num_frames = DEMO_VIDEO_DURATION_SECONDS * VIDEO_FPS
            for _ in range(num_frames):
                out.write(opencv_image)

            out.release()
            messagebox.showinfo("Vídeo Gerado", f"Vídeo demonstrativo salvo em:\n{demo_video_path}")

        except Exception as e:
            messagebox.showerror("Erro ao Gerar Vídeo", f"Ocorreu um erro ao gerar o vídeo demonstrativo:\n{e}")
            print(f"Erro ao gerar vídeo demonstrativo: {e}")


# --- Execução da Aplicação ---
if __name__ == "__main__":
    # Garante que a pasta padrão 'FT TRATADAS 2025' existe para evitar erros iniciais
    Path(Path.home() / "FT TRATADAS 2025").mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    app = PhotoProcessorApp(root)
    root.mainloop()
