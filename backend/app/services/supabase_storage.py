"""
Serviço para integração com Supabase Storage
Gerencia upload, download e exclusão de imagens de produtos
"""
import os
import uuid
import mimetypes
from io import BytesIO
from typing import Optional, Tuple, List
from PIL import Image
from supabase import create_client, Client
from supabase.client import ClientOptions
from werkzeug.datastructures import FileStorage

class SupabaseStorageService:
    def __init__(self):
        """Inicializa o cliente Supabase com tratamento de erros"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY") 
        self.bucket_name = os.getenv("SUPABASE_BUCKET", "product-images")
        
        # Estado da conexão
        self.client: Optional[Client] = None
        self.connection_error: Optional[str] = None
        self.is_connected = False
        
        # Inicializa conexão
        self._initialize_connection()
        
    def _initialize_connection(self):
        """Inicializa conexão com Supabase de forma segura"""
        try:
            # Verifica se as variáveis de ambiente estão configuradas
            if not self.supabase_url or not self.supabase_key:
                self.connection_error = "SUPABASE_URL e SUPABASE_KEY devem estar configurados no .env"
                print(f"Erro de configuração Supabase: {self.connection_error}")
                return
            
            # Tenta criar cliente
            options = ClientOptions(
                auto_refresh_token=True,
                persist_session=False
            )
            
            self.client = create_client(
                supabase_url=self.supabase_url,
                supabase_key=self.supabase_key,
                options=options
            )
            
            # Testa conexão básica
            self._test_connection()
            
        except Exception as e:
            self.connection_error = f"Erro ao conectar com Supabase: {str(e)}"
            print(f"Aviso: {self.connection_error}")
            print("Verifique SUPABASE_URL, SUPABASE_KEY e conectividade de rede.")
            
    def _test_connection(self):
        """Testa a conexão com Supabase fazendo uma operação simples"""
        try:
            if not self.client:
                raise Exception("Cliente Supabase não inicializado")
                
            # Testa conectividade tentando acessar diretamente o bucket
            try:
                # Tenta fazer uma operação simples no bucket específico
                result = self.client.storage.from_(self.bucket_name).list()
                
                # Se chegou aqui, o bucket existe e está acessível
                self.is_connected = True
                print("Supabase Storage conectado com sucesso!")
                print(f"Bucket '{self.bucket_name}' confirmado e acessível")
                
            except Exception as bucket_error:
                # Se falhou, tenta listar buckets para diagnóstico
                try:
                    buckets = self.client.storage.list_buckets()
                    if buckets and isinstance(buckets, list):
                        bucket_names = [b.name if hasattr(b, 'name') else str(b) for b in buckets]
                        print(f"Buckets disponíveis: {bucket_names}")
                        if self.bucket_name not in bucket_names:
                            print(f"Aviso: Bucket '{self.bucket_name}' não encontrado. Verifique o nome no .env")
                        else:
                            print(f"Bucket '{self.bucket_name}' existe mas pode ter problemas de acesso")
                    else:
                        print(f"Erro ao listar buckets: {buckets}")
                except Exception as list_error:
                    print(f"Erro ao verificar buckets: {str(list_error)}")
                
                # Mesmo com erro no bucket, mantém conexão se as credenciais estão válidas
                self.is_connected = True
                self.connection_error = f"Bucket '{self.bucket_name}' inacessível: {str(bucket_error)}"
                print(f"Aviso: {self.connection_error}")
            
        except Exception as e:
            self.is_connected = False
            self.connection_error = f"Falha no teste de conexão: {str(e)}"
            print(f"Aviso: {self.connection_error}")
            
    def is_available(self) -> bool:
        """Verifica se o serviço Supabase está disponível"""
        return self.is_connected and self.client is not None
        
    def get_connection_status(self) -> dict:
        """Retorna status da conexão para health check"""
        return {
            "status": "UP" if self.is_connected else "DOWN",
            "error": self.connection_error,
            "bucket": self.bucket_name if self.is_connected else None
        }
        
    def _generate_filename(self, original_filename: str) -> str:
        """Gera nome único para o arquivo"""
        # Extrai extensão do arquivo original
        _, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.jpg'  # Default para JPG se não tiver extensão
            
        # Gera UUID único + extensão
        unique_filename = f"{uuid.uuid4().hex}{ext.lower()}"
        return unique_filename
        
    def _validate_image(self, file: FileStorage) -> bool:
        """Valida se o arquivo é uma imagem válida"""
        if not file.content_type:
            return False
            
        # Tipos MIME permitidos
        allowed_types = [
            'image/jpeg', 'image/jpg', 'image/png', 
            'image/webp', 'image/gif'
        ]
        
        return file.content_type in allowed_types
        
    def _resize_image(self, file: FileStorage, max_width: int = 1200, max_height: int = 1200) -> BytesIO:
        """Redimensiona imagem para otimizar armazenamento"""
        try:
            # Abre a imagem
            image = Image.open(file.stream)
            
            # Calcula novo tamanho mantendo proporção
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Converte para RGB se necessário (para JPEG)
            if image.mode in ('RGBA', 'LA', 'P'):
                rgb_image = Image.new('RGB', image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[-1] if 'A' in image.mode else None)
                image = rgb_image
            
            # Salva em BytesIO
            output = BytesIO()
            format = 'JPEG' if file.content_type == 'image/jpeg' else 'PNG'
            quality = 85 if format == 'JPEG' else None
            
            save_kwargs = {'format': format}
            if quality:
                save_kwargs['quality'] = quality
                save_kwargs['optimize'] = True
                
            image.save(output, **save_kwargs)
            output.seek(0)
            
            return output
            
        except Exception as e:
            # Se falhar o redimensionamento, retorna original
            file.stream.seek(0)
            return BytesIO(file.stream.read())
    
    def upload_image(self, file: FileStorage, product_id: Optional[int] = None) -> Tuple[bool, str]:
        """
        Faz upload de uma imagem para o Supabase Storage
        
        Args:
            file: Arquivo de imagem enviado
            product_id: ID do produto (opcional, para organização)
            
        Returns:
            Tuple[bool, str]: (sucesso, url_publica_ou_mensagem_erro)
        """
        # Verifica se o serviço está disponível
        if not self.is_available():
            return False, f"Serviço de storage indisponível: {self.connection_error or 'Conexão não estabelecida'}"
            
        try:
            # Valida se é uma imagem
            if not self._validate_image(file):
                return False, "Arquivo deve ser uma imagem válida (JPEG, PNG, WebP, GIF)"
            
            # Gera nome único
            filename = self._generate_filename(file.filename)
            
            # Adiciona prefixo do produto se fornecido
            if product_id:
                filename = f"product_{product_id}/{filename}"
            
            # Redimensiona imagem
            resized_image = self._resize_image(file)
            
            # Detecta tipo MIME
            mime_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'
            
            # Upload para Supabase com tratamento de erro melhorado
            try:
                result = self.client.storage.from_(self.bucket_name).upload(
                    path=filename,
                    file=resized_image.getvalue(),
                    file_options={"content-type": mime_type}
                )
                
                if hasattr(result, 'error') and result.error:
                    error_msg = result.error.message if hasattr(result.error, 'message') else str(result.error)
                    if 'violates row-level security policy' in str(error_msg).lower():
                        # Tenta obter novo token e repetir upload
                        self.client.auth.sign_in_with_password({
                            'email': os.getenv('SUPABASE_SERVICE_ROLE_EMAIL'),
                            'password': os.getenv('SUPABASE_SERVICE_ROLE_KEY')
                        })
                        # Tenta upload novamente
                        result = self.client.storage.from_(self.bucket_name).upload(
                            path=filename,
                            file=resized_image.getvalue(),
                            file_options={"content-type": mime_type}
                        )
                        if hasattr(result, 'error') and result.error:
                            return False, f"Erro de autorização persistente: {error_msg}"
                    else:
                        return False, f"Erro no upload: {error_msg}"
            except Exception as e:
                if 'unauthorized' in str(e).lower() or 'permission' in str(e).lower():
                    return False, f"Erro de autorização: Verifique as permissões do bucket"
                return False, f"Erro interno no upload: {str(e)}"
            
            # Gera URL pública com token de download
            try:
                # Gera URL pública usando o método do SDK
                result = self.client.storage.from_(self.bucket_name).get_public_url(filename)
                if not result or not isinstance(result, str):
                    # Fallback: construir URL manualmente
                    public_url = f"{self.supabase_url}/storage/v1/object/public/{self.bucket_name}/{filename}"
                else:
                    public_url = result
                
                # Garante que a URL é absoluta
                if not public_url.startswith('http'):
                    public_url = f"{self.supabase_url}{public_url}"
                
                # Adiciona token de download
                download_token = self.client.storage.from_(self.bucket_name).create_signed_url(
                    path=filename,
                    expires_in=31536000  # 1 ano em segundos
                )
                
                if download_token and isinstance(download_token, dict) and 'signedURL' in download_token:
                    return True, download_token['signedURL']
                
                return True, public_url
            except Exception as e:
                return False, f"Erro ao gerar URL pública: {str(e)}"
            
        except Exception as e:
            return False, f"Erro interno no upload: {str(e)}"
    
    def delete_image(self, image_url: str) -> Tuple[bool, str]:
        """
        Deleta uma imagem do Supabase Storage
        
        Args:
            image_url: URL pública da imagem
            
        Returns:
            Tuple[bool, str]: (sucesso, mensagem)
        """
        # Verifica se o serviço está disponível
        if not self.is_available():
            return False, f"Serviço de storage indisponível: {self.connection_error or 'Conexão não estabelecida'}"
            
        try:
            # Extrai o path da URL
            # Exemplo: https://project.supabase.co/storage/v1/object/public/bucket/path
            # Queremos apenas o 'path'
            if '/object/public/' in image_url:
                path = image_url.split('/object/public/')[1]
                # Remove bucket name do início se estiver presente
                if path.startswith(f"{self.bucket_name}/"):
                    path = path[len(self.bucket_name)+1:]
            else:
                return False, "URL de imagem inválida"
            
            # Deleta do Supabase
            result = self.client.storage.from_(self.bucket_name).remove([path])
            
            if hasattr(result, 'error') and result.error:
                return False, f"Erro ao deletar: {result.error.message}"
            
            return True, "Imagem deletada com sucesso"
            
        except Exception as e:
            return False, f"Erro interno ao deletar: {str(e)}"
    
    def list_product_images(self, product_id: int) -> Tuple[bool, List[str]]:
        """
        Lista todas as imagens de um produto
        
        Args:
            product_id: ID do produto
            
        Returns:
            Tuple[bool, List[str]]: (sucesso, lista_de_urls)
        """
        # Verifica se o serviço está disponível
        if not self.is_available():
            return False, []
            
        try:
            path_prefix = f"product_{product_id}/"
            
            # Lista arquivos no diretório do produto
            result = self.client.storage.from_(self.bucket_name).list(path_prefix)
            
            if hasattr(result, 'error') and result.error:
                return False, []
            
            # Gera URLs públicas
            image_urls = []
            for file_info in result:
                filename = file_info['name']
                public_url = self.client.storage.from_(self.bucket_name).get_public_url(f"{path_prefix}{filename}")
                image_urls.append(public_url)
            
            return True, image_urls
            
        except Exception as e:
            return False, []
    
    def get_image_info(self, image_url: str) -> dict:
        """
        Obtém informações sobre uma imagem
        
        Args:
            image_url: URL pública da imagem
            
        Returns:
            dict: Informações da imagem
        """
        # Verifica se o serviço está disponível
        if not self.is_available():
            return {"error": f"Serviço de storage indisponível: {self.connection_error or 'Conexão não estabelecida'}"}
            
        try:
            # Extrai path da URL
            if '/object/public/' in image_url:
                path = image_url.split('/object/public/')[1]
                if path.startswith(f"{self.bucket_name}/"):
                    path = path[len(self.bucket_name)+1:]
            else:
                return {"error": "URL inválida"}
            
            # Busca informações do arquivo
            result = self.client.storage.from_(self.bucket_name).get_file_info(path)
            
            if hasattr(result, 'error') and result.error:
                return {"error": result.error.message}
            
            return {
                "size": result.get("ContentLength", 0),
                "content_type": result.get("ContentType", ""),
                "last_modified": result.get("LastModified", ""),
                "url": image_url
            }
            
        except Exception as e:
            return {"error": str(e)}

# Instância global do serviço.
# __init__ trata os próprios erros de conexão internamente (via
# _initialize_connection), então a construção nunca lança por indisponibilidade.
storage_service = SupabaseStorageService()
