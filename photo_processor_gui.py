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

FONT_TITLE = ("Arial", 20, "bold")
FONT_SUBTITLE = ("Arial", 12)
FONT_LABEL = ("Arial", 10, "bold")
FONT_TEXT = ("Arial", 10)
FONT_BUTTON = ("Arial", 11, "bold") # Ajuste para um tamanho bom nos botões

# Constantes para processamento
TARGET_RESOLUTION = (1920, 1080)
WATERMARK_TEXT = "@tioadaotvnafesta"
VIDEO_FPS = 30
VIDEO_CODEC = "mp4v" # Usando mp4v para maior compatibilidade
VIDEO_ZOOM_PERCENTAGE = 0.20 # 20% de ampliação
IMAGES_PER_LOT = 50

# --- Classe Principal da Aplicação ---
class PhotoProcessorApp:
    def __init__(self, master):
        self.master = master
        master.title("CodeBuddy - Processador de Fotos")
        master.geometry("800x600")
        master.resizable(False, False) # Janela não redimensionável
        master.configure(bg=COLOR_BACKGROUND)

        # Variáveis de controle
        self.input_folder = tk.StringVar()
        self.output_folder = tk.StringVar(value=str(Path.home() / "FT TRATADAS 2025")) # Pasta de destino padrão
        self.image_count = tk.IntVar(value=0)
        self.create_videos = tk.BooleanVar(value=True)
        self.video_duration = tk.IntVar(value=10) # Duração padrão de 10 segundos
        self.processing_status = tk.StringVar(value="Aguardando...")
        self.processed_count = tk.IntVar(value=0)
        self.total_to_process = tk.IntVar(value=0)

        self.geolocator = Nominatim(user_agent="photo_processor_app") # Inicializa o geocodificador

        self._create_widgets()

    def _create_widgets(self):
        """Cria e organiza todos os widgets da interface gráfica."""

        # Título principal
        tk.Label(self.master, text="Processador de Fotos em Massa", bg=COLOR_BACKGROUND, fg=COLOR_TEXT,
                 font=FONT_TITLE).pack(pady=10)

        # --- Seções da Interface (LabelFrames) ---

        # Passo 1: Seleção de Pasta
        self.frame_step1 = self._create_labeled_frame("PASSO 1: Selecione a Pasta de Origem")
        self.frame_step1.pack(fill="x", padx=20, pady=5)
        self._setup_step1(self.frame_step1)

        # Passo 2: Configurações
        self.frame_step2 = self._create_labeled_frame("PASSO 2: Configure as Opções")
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
        """Configura os widgets para o Passo 1."""
        frame_content = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_content.pack(fill="x")

        tk.Label(frame_content, text="Pasta de Entrada:", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))

        entry_folder = tk.Entry(frame_content, textvariable=self.input_folder, width=60, state="readonly", font=FONT_TEXT)
        entry_folder.pack(side="left", fill="x", expand=True)

        btn_browse = tk.Button(frame_content, text="Procurar", command=self._browse_folder,
                               bg=COLOR_BUTTON_BROWSE, fg=COLOR_TEXT, font=FONT_BUTTON,
                               relief="raised", bd=2, highlightbackground=COLOR_BUTTON_BROWSE)
        btn_browse.pack(side="left", padx=10)

        tk.Label(parent_frame, textvariable=self.image_count, bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_TEXT).pack(anchor="w", pady=5)
        tk.Label(parent_frame, text="(Formatos aceitos: JPG, JPEG, PNG, BMP, TIFF)", bg=COLOR_FRAME, fg="#cccccc", font=("Arial", 8)).pack(anchor="w", pady=(0, 5))

    def _setup_step2(self, parent_frame):
        """Configura os widgets para o Passo 2."""
        frame_content = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_content.pack(fill="x")

        # Opção de criação de vídeos
        chk_create_videos = tk.Checkbutton(frame_content, text="Criar Vídeos (Zoom Lento)", variable=self.create_videos,
                                           bg=COLOR_FRAME, fg=COLOR_TEXT, selectcolor=COLOR_FRAME,
                                           font=FONT_LABEL, command=self._toggle_video_options)
        chk_create_videos.pack(anchor="w", pady=5)

        # Opções de duração do vídeo (visíveis apenas se 'Criar Vídeos' estiver marcado)
        self.frame_video_options = tk.Frame(frame_content, bg=COLOR_FRAME)
        self.frame_video_options.pack(anchor="w", padx=20, pady=5)

        tk.Label(self.frame_video_options, text="Duração do Vídeo:", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))

        rb_10s = tk.Radiobutton(self.frame_video_options, text="10 Segundos", variable=self.video_duration, value=10,
                                bg=COLOR_FRAME, fg=COLOR_TEXT, selectcolor=COLOR_FRAME, font=FONT_TEXT)
        rb_10s.pack(side="left")

        rb_15s = tk.Radiobutton(self.frame_video_options, text="15 Segundos", variable=self.video_duration, value=15,
                                bg=COLOR_FRAME, fg=COLOR_TEXT, selectcolor=COLOR_FRAME, font=FONT_TEXT, padx=10)
        rb_15s.pack(side="left")

        self._toggle_video_options() # Esconde/mostra no início

        # Pasta de destino
        frame_output = tk.Frame(parent_frame, bg=COLOR_FRAME)
        frame_output.pack(fill="x", pady=5)

        tk.Label(frame_output, text="Pasta de Destino:", bg=COLOR_FRAME, fg=COLOR_TEXT, font=FONT_LABEL).pack(side="left", padx=(0, 10))

        entry_output_folder = tk.Entry(frame_output, textvariable=self.output_folder, width=60, font=FONT_TEXT)
        entry_output_folder.pack(side="left", fill="x", expand=True)

        btn_alter_output = tk.Button(frame_output, text="Alterar", command=self._alter_output_folder,
                                      bg=COLOR_BUTTON_ALTER, fg=COLOR_TEXT, font=FONT_BUTTON,
                                      relief="raised", bd=2, highlightbackground=COLOR_BUTTON_ALTER)
        btn_alter_output.pack(side="left", padx=10)

    def _toggle_video_options(self):
        """Controla a visibilidade das opções de duração do vídeo."""
        if self.create_videos.get():
            self.frame_video_options.pack(anchor="w", padx=20, pady=5)
        else:
            self.frame_video_options.pack_forget()

    def _setup_step3(self, parent_frame):
        """Configura os widgets para o Passo 3."""
        btn_process = tk.Button(parent_frame, text="TRATAR FOTOS AGORA", command=self._start_processing_thread,
                                bg=COLOR_BUTTON_PROCESS, fg=COLOR_TEXT, font=FONT_BUTTON,
                                relief="raised", bd=2, highlightbackground=COLOR_BUTTON_PROCESS)
        btn_process.pack(pady=10)

    def _setup_step4(self, parent_frame):
        """Configura os widgets para o Passo 4."""
        btn_download = tk.Button(parent_frame, text="ABRIR PASTA TRATADAS", command=self._open_output_folder,
                                 bg=COLOR_BUTTON_DOWNLOAD, fg=COLOR_TEXT, font=FONT_BUTTON,
                                 relief="raised", bd=2, highlightbackground=COLOR_BUTTON_DOWNLOAD,
                                 state="disabled") # Desabilitado até o fim do processamento
        btn_download.pack(pady=10)
        self.btn_download = btn_download # Guarda a referência para habilitar depois

    def _browse_folder(self):
        """Abre uma caixa de diálogo para selecionar a pasta de entrada e conta as imagens."""
        folder_selected = filedialog.askdirectory()
        if folder_selected:
            self.input_folder.set(folder_selected)
            self._count_images_in_folder(folder_selected)
        else:
            self.input_folder.set("")
            self.image_count.set(0)

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

        if not input_path or not os.path.isdir(input_path):
            messagebox.showwarning("Erro", "Por favor, selecione uma pasta de entrada válida.")
            return
        
        # Cria a pasta de saída se não existir
        Path(output_path).mkdir(parents=True, exist_ok=True)
        
        if not os.access(output_path, os.W_OK):
             messagebox.showwarning("Erro", "Não foi possível escrever na pasta de destino selecionada. Por favor, escolha outra.")
             return

        # Desabilita botões para evitar cliques múltiplos
        self.master.children["!labelframe3"].children["!button"].config(state="disabled")
        self.master.children["!labelframe1"].children["!frame"].children["!button"].config(state="disabled")
        self.master.children["!labelframe2"].children["!frame"].children["!checkbutton"].config(state="disabled")
        self.master.children["!labelframe2"].children["!frame"].children["!frame"].children["!radiobutton"].config(state="disabled")
        self.master.children["!labelframe2"].children["!frame"].children["!frame"].children["!radiobutton2"].config(state="disabled")
        self.master.children["!labelframe2"].children["!frame2"].children["!button"].config(state="disabled")


        self.processing_status.set("Preparando para processar...")
        self.progressbar.config(mode="indeterminate")
        self.progressbar.start()
        self.processed_count.set(0) # Zera contador de processados

        # Inicia a thread de processamento
        process_thread = threading.Thread(target=self._process_photos)
        process_thread.start()

    def _process_photos(self):
        """Lógica principal de processamento das fotos."""
        input_dir = Path(self.input_folder.get())
        output_base_dir = Path(self.output_folder.get())
        
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
                # 1. Carregamento e Redimensionamento
                img = Image.open(image_path).convert("RGB")
                original_width, original_height = img.size
                
                # Calcula as novas dimensões mantendo a proporção
                ratio = min(TARGET_RESOLUTION[0] / original_width, TARGET_RESOLUTION[1] / original_height)
                new_width = int(original_width * ratio)
                new_height = int(original_height * ratio)
                
                img_resized = img.resize((new_width, new_height), Image.LANCZOS)
                
                # Cria um canvas preto e cola a imagem redimensionada no centro
                final_img = Image.new("RGB", TARGET_RESOLUTION, (0, 0, 0)) # Fundo preto
                x_offset = (TARGET_RESOLUTION[0] - new_width) // 2
                y_offset = (TARGET_RESOLUTION[1] - new_height) // 2
                final_img.paste(img_resized, (x_offset, y_offset))

                # 2. Melhoria de Qualidade (Nitidez, Contraste, Brilho)
                enhancer = ImageEnhance.Sharpness(final_img)
                final_img = enhancer.enhance(1.2) # Aumenta a nitidez
                enhancer = ImageEnhance.Contrast(final_img)
                final_img = enhancer.enhance(1.1) # Aumenta o contraste
                enhancer = ImageEnhance.Brightness(final_img)
                final_img = enhancer.enhance(1.05) # Aumenta um pouco o brilho

                # 3. Extração de Metadados
                metadata = self._extract_metadata(image_path)

                # 4. Aplicação de Marca d'água
                final_img = self._apply_watermark(final_img)

                # 5. Organização de Arquivos e Nomenclatura
                base_name = image_path.stem # Nome do arquivo original sem extensão
                processed_name_prefix = f"{i + 1:03d}-{current_lot_count + 1:02d}"

                # Nomeclatura: 001-25 - Local - Data - Nome
                location_str = metadata["exif_data"]["location"]["city"] if metadata["exif_data"]["location"]["city"] else "SemLocal"
                date_str = datetime.strptime(metadata["exif_data"]["datetime"].split("T")[0], "%Y-%m-%d").strftime("%d%m%Y")
                
                final_filename_stem = f"{processed_name_prefix} - {location_str} - {date_str} - {base_name}"
                
                # Salva a imagem processada
                processed_image_path = current_lot_dir / f"{final_filename_stem}.jpg"
                final_img.save(processed_image_path, "JPEG", quality=95, optimize=True)

                # Salva os metadados
                metadata_path = current_lot_dir / f"{final_filename_stem}_metadata.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(metadata, f, indent=4, ensure_ascii=False)

                # 6. Criação de Vídeos (se selecionado)
                if self.create_videos.get():
                    video_path = current_lot_dir / f"{final_filename_stem}.mp4"
                    self._create_video_with_zoom(final_img, video_path, self.video_duration.get())
                
                current_lot_count += 1

            except Exception as e:
                self.processing_status.set(f"Erro ao processar {image_path.name}: {e}")
                print(f"Erro ao processar {image_path.name}: {e}") # Loga o erro no console
                continue # Continua para a próxima foto mesmo com erro

            self.processed_count.set(self.processed_count.get() + 1)

        self._processing_complete()

    def _extract_metadata(self, image_path):
        """Extrai metadados EXIF, GPS e faz geocoding."""
        metadata = {
            "original_file": str(image_path),
            "processed_date": datetime.now().isoformat(),
            "exif_data": {
                "datetime": "N/A",
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
                    # Decodifica as tags EXIF
                    exif = {
                        ExifTags.TAGS[k]: v
                        for k, v in exif_data.items()
                        if k in ExifTags.TAGS
                    }

                    # Data/Hora
                    if "DateTimeOriginal" in exif:
                        metadata["exif_data"]["datetime"] = datetime.strptime(exif["DateTimeOriginal"], "%Y:%m:%d %H:%M:%S").isoformat()
                    elif "DateTime" in exif:
                        metadata["exif_data"]["datetime"] = datetime.strptime(exif["DateTime"], "%Y:%m:%d %H:%M:%S").isoformat()

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
                                    if "manaus" in metadata["exif_data"]["location"]["city"].lower():
                                        metadata["exif_data"]["location"]["city"] = "Manaus" # Padroniza para "Manaus"
                            except (GeocoderTimedOut, GeocoderServiceError, requests.exceptions.RequestException) as geocoding_err:
                                print(f"Erro no geocoding: {geocoding_err}")
                                metadata["exif_data"]["location"]["city"] = "SemLocal" # Define como 'SemLocal' em caso de erro

        except Exception as e:
            print(f"Erro ao extrair EXIF ou geocoding para {image_path.name}: {e}")

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

    def _apply_watermark(self, image):
        """Aplica a marca d'água na imagem."""
        draw = ImageDraw.Draw(image)
        width, height = image.size

        try:
            # Tenta carregar a fonte Arial. Se falhar, usa a fonte padrão PIL.
            font = ImageFont.truetype("arial.ttf", 40)
        except IOError:
            font = ImageFont.load_default() # Fallback para fonte padrão
            print("Aviso: Fonte Arial não encontrada, usando fonte padrão.")

        text_width, text_height = draw.textbbox((0, 0), WATERMARK_TEXT, font=font)[2:] # getbbox returns (left, top, right, bottom)
        
        # Posição: canto inferior direito com padding
        padding = 20
        x = width - text_width - padding
        y = height - text_height - padding

        # Desenha a sombra (preta)
        draw.text((x + 2, y + 2), WATERMARK_TEXT, font=font, fill=(0, 0, 0)) # Desloca 2px para criar sombra
        # Desenha o texto (branco)
        draw.text((x, y), WATERMARK_TEXT, font=font, fill=(255, 255, 255))

        return image

    def _create_video_with_zoom(self, pil_image, output_video_path, duration_seconds):
        """Cria um vídeo com efeito de zoom lento a partir de uma imagem PIL."""
        width, height = pil_image.size
        
        # Define o codec e o objeto VideoWriter
        fourcc = cv2.VideoWriter_fourcc(*VIDEO_CODEC)
        out = cv2.VideoWriter(str(output_video_path), fourcc, VIDEO_FPS, (width, height))

        if not out.isOpened():
            print(f"Erro: Não foi possível abrir o arquivo de vídeo para escrita: {output_video_path}")
            return

        total_frames = duration_seconds * VIDEO_FPS
        
        # Converte a imagem PIL para formato OpenCV (BGR)
        opencv_image = np.array(pil_image) 
        opencv_image = cv2.cvtColor(opencv_image, cv2.COLOR_RGB2BGR)

        for i in range(total_frames):
            # Calcula o fator de zoom linear
            # Começa em 1.0 (0% zoom) e vai até 1.0 + VIDEO_ZOOM_PERCENTAGE
            zoom_factor = 1.0 + (VIDEO_ZOOM_PERCENTAGE * (i / total_frames))
            
            # Calcula as novas dimensões da imagem zoomizada
            zoomed_width = int(width * zoom_factor)
            zoomed_height = int(height * zoom_factor)

            # Redimensiona a imagem usando interpolação cúbica para suavidade
            img_zoomed = cv2.resize(opencv_image, (zoomed_width, zoomed_height), interpolation=cv2.INTER_CUBIC)

            # Calcula o corte para centralizar a imagem no frame original
            crop_x = (zoomed_width - width) // 2
            crop_y = (zoomed_height - height) // 2
            
            # Garante que o corte não exceda as bordas da imagem zoomizada
            cropped_frame = img_zoomed[max(0, crop_y):min(zoomed_height, crop_y + height),
                                       max(0, crop_x):min(zoomed_width, crop_x + width)]
            
            # Se o cropped_frame não tiver as dimensões exatas (pode acontecer por arredondamento), redimensiona-o
            if cropped_frame.shape[0] != height or cropped_frame.shape[1] != width:
                cropped_frame = cv2.resize(cropped_frame, (width, height), interpolation=cv2.INTER_CUBIC)

            out.write(cropped_frame)

        out.release() # Libera o objeto VideoWriter

    def _processing_complete(self):
        """Chamado quando o processamento é concluído."""
        self.progressbar.stop()
        self.progressbar.config(mode="determinate", value=self.total_to_process.get())
        self.processing_status.set(f"Processamento Concluído! {self.processed_count.get()} fotos processadas.")
        
        # Habilita o botão de download
        self.btn_download.config(state="normal")
        
        # Habilita novamente os botões de controle de UI
        self.master.children["!labelframe3"].children["!button"].config(state="normal")
        self.master.children["!labelframe1"].children["!frame"].children["!button"].config(state="normal")
        self.master.children["!labelframe2"].children["!frame"].children["!checkbutton"].config(state="normal")
        self.master.children["!labelframe2"].children["!frame"].children["!frame"].children["!radiobutton"].config(state="normal")
        self.master.children["!labelframe2"].children["!frame"].children["!frame"].children["!radiobutton2"].config(state="normal")
        self.master.children["!labelframe2"].children["!frame2"].children["!button"].config(state="normal")

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

# --- Execução da Aplicação ---
if __name__ == "__main__":
    # Garante que a pasta padrão 'FT TRATADAS 2025' existe para evitar erros iniciais
    Path(Path.home() / "FT TRATADAS 2025").mkdir(parents=True, exist_ok=True)

    root = tk.Tk()
    app = PhotoProcessorApp(root)
    root.mainloop()
